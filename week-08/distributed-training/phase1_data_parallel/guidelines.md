# Phase 1: Data Parallel Training - Guidelines

## Overview
In this phase, you'll implement the fundamental concepts of data parallel training. This is the simplest form of distributed training where each GPU processes different data but runs the same model.

## Key Concepts

### 1. Data Distribution
- **Problem**: With N GPUs and M samples, how do you ensure each GPU gets unique data?
- **Solution**: Partition the dataset into N chunks, one per GPU
- **Challenge**: What if M is not divisible by N?

### 2. Gradient Aggregation
- **Problem**: Each GPU computes gradients on its data. How do you combine them?
- **Solution**: Average gradients across all GPUs using all-reduce
- **Why averaging?** Because you want the gradient as if you processed all data together

### 3. Model Synchronization
- **Problem**: How do you ensure all GPUs start with the same model?
- **Solution**: Broadcast model parameters from rank 0 to all ranks
- **When?** Before training starts

## Implementation Steps

### Step 1: Distributed Sampler (template_data_loader.py)

#### Understanding the Problem
```
Dataset: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  (10 samples)
GPUs: 4

Goal: Each GPU should get unique samples
GPU 0: [0, 1, 2]
GPU 1: [3, 4, 5]
GPU 2: [6, 7, 8]
GPU 3: [9, 0, 1]  <- Note: padding needed!
```

#### Implementation Hints

1. **Calculate samples per replica**:
```python
# Need to pad so all ranks have equal samples
total_samples = len(dataset)
samples_per_replica = (total_samples + num_replicas - 1) // num_replicas
total_size = samples_per_replica * num_replicas
```

2. **Generate and distribute indices**:
```python
# Create indices for all data
indices = list(range(len(dataset)))

# Optionally shuffle
if shuffle:
    g = torch.Generator()
    g.manual_seed(seed)
    indices = torch.randperm(len(dataset), generator=g).tolist()

# Pad indices to make even distribution
indices += indices[:(total_size - len(indices))]

# Select indices for this rank
start_idx = rank * samples_per_replica
end_idx = start_idx + samples_per_replica
rank_indices = indices[start_idx:end_idx]
```

3. **Why padding?**
- All GPUs must process the same number of batches
- Otherwise, some GPUs will wait for others (deadlock in collective operations)

### Step 2: Training Loop (template_trainer.py)

#### Understanding All-Reduce

All-reduce is a collective operation where:
1. Each process contributes a tensor
2. An operation (sum, max, min, etc.) is applied element-wise
3. The result is available on all processes

Example:
```
GPU 0 gradient: [1.0, 2.0, 3.0]
GPU 1 gradient: [2.0, 3.0, 4.0]

After all_reduce(SUM):
Both GPUs have: [3.0, 5.0, 7.0]

After dividing by 2:
Both GPUs have: [1.5, 2.5, 3.5]  <- Average gradient!
```

#### Implementation Hints

1. **Setup distributed process group**:
```python
import torch.distributed as dist
import os

# These environment variables are set by torchrun/torch.distributed.launch
# MASTER_ADDR: IP address of rank 0
# MASTER_PORT: Port for communication
# WORLD_SIZE: Total number of processes
# RANK: Current process rank

dist.init_process_group(
    backend='nccl',  # Use 'nccl' for GPU, 'gloo' for CPU
    init_method='env://'  # Read from environment variables
)
```

2. **Gradient averaging**:
```python
for param in model.parameters():
    if param.grad is not None:
        # Sum gradients across all processes
        dist.all_reduce(param.grad.data, op=dist.ReduceOp.SUM)
        # Average by dividing by world size
        param.grad.data /= world_size
```

3. **Model broadcasting**:
```python
for param in model.parameters():
    # Broadcast from rank 0 to all other ranks
    dist.broadcast(param.data, src=0)
```

## Testing Your Implementation

### Test 1: Data Distribution
```bash
python template_data_loader.py
```
Expected output:
- Each rank should have equal number of samples
- No overlap between ranks (except for padding)
- Total samples across all ranks should cover entire dataset

### Test 2: Gradient Synchronization
Create a simple test:
```python
# On each GPU, compute different gradients
# After all_reduce, all GPUs should have the average
```

## Common Pitfalls

1. **Forgetting to average after all_reduce**
   - `all_reduce(SUM)` gives the sum, not average
   - Must divide by world_size

2. **Not handling uneven dataset sizes**
   - If dataset size is not divisible by num_GPUs, some ranks will have fewer samples
   - Must pad to ensure all ranks have equal samples

3. **Device placement errors**
   - Model must be on correct GPU (e.g., `model.to(f'cuda:{rank}'`)
   - Data must be on same device as model

4. **Deadlocks in collective operations**
   - All processes must participate in collective ops (all_reduce, broadcast)
   - If one process skips, others will hang waiting

## Performance Considerations

1. **Communication overhead**
   - Each all_reduce requires network communication
   - Overhead increases with model size and number of GPUs
   - Rule of thumb: Keep batch size large enough to amortize communication

2. **Optimal batch size**
   - Effective batch size = batch_size_per_gpu * num_gpus
   - Too small: Underutilize GPUs
   - Too large: May not fit in memory or hurt convergence

## Next Steps

Once you can:
- Distribute data across GPUs
- Synchronize gradients
- Train a simple model (e.g., small CNN on MNIST)

You're ready for Phase 2: Advanced techniques like gradient accumulation and model parallelism!

## Resources

- [PyTorch Distributed Tutorial](https://pytorch.org/tutorials/intermediate/dist_tuto.html)
- [All-Reduce Visualization](https://tech.preferred.jp/en/blog/technologies-behind-distributed-deep-learning-allreduce/)
- [NCCL Documentation](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)

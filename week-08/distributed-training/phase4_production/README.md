# Phase 4: Production-Ready Large-Scale Image Classification

This is the culmination of the distributed training learning path - a complete, production-ready training system for ImageNet-scale datasets.

## Project Overview

Train a ResNet-50 or Vision Transformer (ViT) model on ImageNet (or similar large dataset) using:
- 8+ GPUs across multiple nodes
- Advanced distributed techniques (Ring-AllReduce, gradient compression)
- Fault tolerance and checkpointing
- Complete monitoring and profiling
- Cloud deployment (AWS/GCP)

## Target Metrics

- **Training Time**: <24 hours for 90 epochs on ImageNet
- **Accuracy**: Top-1 >76% (ResNet-50), >80% (ViT-B/16)
- **Scaling Efficiency**: >85% with 8 GPUs
- **Fault Recovery**: Automatic recovery from node failures <5 minutes
- **Resource Utilization**: >90% GPU utilization

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Master Node                         │
│  - Monitoring Dashboard (Grafana)                       │
│  - Metrics Collection (Prometheus)                      │
│  - Training Coordinator                                 │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
   │ Node 0  │       │ Node 1  │      │ Node N  │
   │ 8x GPU  │       │ 8x GPU  │      │ 8x GPU  │
   └─────────┘       └─────────┘      └─────────┘
```

## Features Implemented

### 1. Distributed Training
- **Data Parallel**: Each GPU processes different data
- **Ring-AllReduce**: Efficient gradient synchronization
- **Gradient Compression**: Reduce communication overhead (1-bit SGD)
- **Mixed Precision**: FP16 training with loss scaling
- **Gradient Accumulation**: Simulate larger batch sizes

### 2. Fault Tolerance
- **Automatic Checkpointing**: Save state every N minutes
- **Node Failure Detection**: Detect and handle node failures
- **Elastic Training**: Add/remove nodes dynamically
- **Recovery**: Resume from last checkpoint automatically

### 3. Performance Optimization
- **Data Loading**: Multi-process data loading with prefetching
- **GPU Memory**: Activation checkpointing for large models
- **Communication**: Overlapping communication with computation
- **Batch Size Tuning**: Automatic batch size finder

### 4. Monitoring & Observability
- **Real-time Metrics**: Training loss, learning rate, GPU utilization
- **Distributed Profiling**: Identify communication bottlenecks
- **Alerts**: Slack/email alerts for failures or anomalies
- **Logging**: Centralized logging with ELK stack

## Directory Structure

```
phase4_production/
├── README.md (this file)
├── config/
│   ├── imagenet_resnet50.yaml
│   ├── imagenet_vit.yaml
│   └── distributed_config.yaml
├── src/
│   ├── trainer.py              # Main training script
│   ├── distributed_trainer.py  # Distributed training logic
│   ├── data_loader.py          # Efficient data loading
│   ├── models.py               # Model definitions
│   ├── optimization.py         # Optimizers and schedulers
│   └── utils.py
├── monitoring/
│   ├── prometheus_exporter.py  # Export metrics
│   ├── grafana_dashboard.json  # Dashboard config
│   └── profiler.py             # Performance profiling
├── fault_tolerance/
│   ├── checkpoint_manager.py   # Checkpointing logic
│   ├── fault_detector.py       # Node failure detection
│   └── recovery.py             # Recovery logic
├── deployment/
│   ├── kubernetes/
│   │   ├── training-job.yaml
│   │   ├── monitoring.yaml
│   │   └── storage.yaml
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── gpu_nodes.tf
│   │   └── storage.tf
│   └── docker/
│       ├── Dockerfile
│       └── docker-compose.yml
└── scripts/
    ├── launch_training.sh
    ├── monitor.sh
    └── cleanup.sh
```

## Quick Start

### Local Testing (Single Node, Multiple GPUs)

```bash
# Install dependencies
pip install -r requirements.txt

# Train on 4 GPUs
torchrun --nproc_per_node=4 src/trainer.py \
    --config config/imagenet_resnet50.yaml \
    --data_path /path/to/imagenet

# Monitor training
python monitoring/dashboard.py
```

### Multi-Node Training (Kubernetes)

```bash
# Deploy to Kubernetes cluster
kubectl apply -f deployment/kubernetes/

# Check status
kubectl get pods -l job=imagenet-training

# View logs
kubectl logs -f imagenet-training-worker-0

# Access monitoring
kubectl port-forward svc/grafana 3000:3000
```

### Cloud Deployment (AWS)

```bash
# Provision infrastructure
cd deployment/terraform
terraform init
terraform apply

# Launch training
./scripts/launch_training.sh \
    --nodes 4 \
    --gpus-per-node 8 \
    --config config/imagenet_resnet50.yaml
```

## Configuration

### Training Configuration (imagenet_resnet50.yaml)

```yaml
# Model
model:
  name: resnet50
  pretrained: false

# Data
data:
  dataset: imagenet
  train_path: /data/imagenet/train
  val_path: /data/imagenet/val
  workers: 8
  prefetch_factor: 2

# Training
training:
  epochs: 90
  batch_size: 32  # Per GPU
  base_lr: 0.1
  warmup_epochs: 5
  lr_schedule: cosine
  
# Optimization
optimization:
  optimizer: sgd
  momentum: 0.9
  weight_decay: 1e-4
  mixed_precision: true
  gradient_clip: 1.0
  
# Distributed
distributed:
  backend: nccl
  gradient_compression: true
  bucket_cap_mb: 25
  
# Checkpointing
checkpoint:
  save_interval: 3600  # seconds
  keep_last_n: 3
  async_save: true
```

## Performance Tuning Guide

### 1. Batch Size Selection
```python
# Use batch size finder to maximize throughput
python scripts/find_optimal_batch_size.py --model resnet50
```

### 2. Communication Optimization
- **Gradient Bucketing**: Group small gradients into buckets
- **Compression**: Use 1-bit SGD for large models
- **Overlap**: Start communication before backward pass completes

### 3. Data Loading
- Use DALI (NVIDIA Data Loading Library) for fastest data loading
- NVMe SSDs for local data caching
- Prefetch data to GPU memory

### 4. Mixed Precision
- Use automatic mixed precision (AMP)
- Dynamic loss scaling to prevent underflow
- ~2x speedup with minimal accuracy loss

## Monitoring

### Metrics Tracked
- **Training**: Loss, accuracy, learning rate
- **Performance**: Throughput (images/sec), GPU utilization, memory usage
- **Distributed**: Communication time, all-reduce time, load imbalance
- **System**: CPU usage, network bandwidth, disk I/O

### Grafana Dashboard
Access at `http://localhost:3000` (default credentials: admin/admin)

Panels include:
- Training loss and accuracy curves
- GPU utilization across all nodes
- Communication overhead
- Data loading bottlenecks
- System resource usage

## Troubleshooting

### Common Issues

1. **Out of Memory (OOM)**
   - Reduce batch size
   - Enable gradient checkpointing
   - Use gradient accumulation

2. **Low GPU Utilization**
   - Increase data loading workers
   - Check for data loading bottleneck
   - Reduce communication frequency

3. **Training Hangs**
   - Check all nodes can communicate
   - Verify firewall rules
   - Check for deadlock in collective operations

4. **Poor Scaling**
   - Profile communication overhead
   - Increase batch size per GPU
   - Enable gradient compression

## Results

Expected results on ImageNet with ResNet-50:

| GPUs | Batch Size | Training Time | Top-1 Acc | Scaling Efficiency |
|------|------------|---------------|-----------|-------------------|
| 1    | 256        | 14 days       | 76.2%     | 100%              |
| 8    | 2048       | 48 hours      | 76.5%     | 87%               |
| 32   | 8192       | 14 hours      | 76.1%     | 81%               |
| 64   | 16384      | 8 hours       | 75.8%     | 75%               |

## What You'll Learn

By completing this project, you'll understand:
1. How to scale training to multiple nodes and dozens of GPUs
2. How to implement and debug distributed training systems
3. How to optimize for performance (latency, throughput, scaling)
4. How to build production-grade ML infrastructure
5. How to monitor and troubleshoot distributed systems
6. How to deploy on cloud platforms

## Next Steps

After mastering this system:
- Experiment with larger models (ViT-L, ResNet-152)
- Try different distributed strategies (model parallelism, pipeline parallelism)
- Optimize for different hardware (TPUs, AMD GPUs)
- Implement advanced features (elastic training, spot instance handling)
- Build a training platform for your organization

## References

- [PyTorch Distributed](https://pytorch.org/tutorials/intermediate/ddp_tutorial.html)
- [Horovod](https://github.com/horovod/horovod)
- [DeepSpeed](https://github.com/microsoft/DeepSpeed)
- [ImageNet Training in PyTorch](https://github.com/pytorch/examples/tree/master/imagenet)

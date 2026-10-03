# vLLM Engine Implementation Guide

This guide provides detailed, step-by-step instructions for implementing a vLLM-style LLM serving engine from scratch.

## Overview

You will build a complete LLM serving system with:
1. **PagedAttention**: Block-based KV cache management
2. **Continuous Batching**: Dynamic request scheduling
3. **Tensor Parallelism**: Multi-GPU distribution
4. **Quantization**: GPTQ, AWQ support
5. **Serving**: Production API server

## Phase 1: Core PagedAttention

### Step 1: Understand PagedAttention Concept

**Traditional KV Cache Problems**:
- Pre-allocated contiguous memory for max_seq_len
- Cannot share cache between sequences
- Internal fragmentation (~50% wasted)
- External fragmentation when sequences complete

**PagedAttention Solution**:
- Fixed-size blocks (e.g., 16 tokens)
- Logical-to-physical block mapping
- Share blocks via copy-on-write
- Allocate on-demand

**Analogy to Virtual Memory**:
```
Traditional:     [████████████████████░░░░░░░░] (pre-allocated)
PagedAttention:  Block 0: [████████████████]
                 Block 1: [████████████████]
                 Block 2: [████░░░░░░░░░░░░] (partially filled)
```

---

### Step 2: Implement Block Manager

**Goal**: Manage KV cache blocks

**Core data structures**:
```python
@dataclass
class Block:
    """Physical memory block"""
    block_id: int
    ref_count: int
    data: Optional[torch.Tensor]  # Actual KV cache data

class BlockTable:
    """Logical-to-physical block mapping"""
    def __init__(self, block_size: int = 16):
        self.block_size = block_size
        self.blocks = []  # List of Block IDs
    
    def append_block(self, block_id: int):
        """Add block to table"""
        self.blocks.append(block_id)
    
    def get_physical_blocks(self) -> List[int]:
        """Get list of physical block IDs"""
        return self.blocks

class BlockAllocator:
    """Allocates and manages blocks"""
    def __init__(self, num_blocks: int, block_size: int):
        self.num_blocks = num_blocks
        self.block_size = block_size
        self.free_blocks = list(range(num_blocks))
        self.blocks = [Block(i, 0, None) for i in range(num_blocks)]
    
    def allocate(self) -> Optional[int]:
        """Allocate a free block"""
        if not self.free_blocks:
            return None
        block_id = self.free_blocks.pop(0)
        self.blocks[block_id].ref_count = 1
        return block_id
    
    def free(self, block_id: int):
        """Free a block"""
        block = self.blocks[block_id]
        block.ref_count -= 1
        if block.ref_count == 0:
            self.free_blocks.append(block_id)
    
    def fork(self, src_block_id: int) -> int:
        """Copy-on-write fork of a block"""
        # Increment ref count for sharing
        self.blocks[src_block_id].ref_count += 1
        return src_block_id
```

**Implementation tasks**:
- [ ] Implement Block class
- [ ] Implement BlockTable for mapping
- [ ] Implement BlockAllocator with free list
- [ ] Add reference counting for sharing
- [ ] Test: Allocate, free, and fork blocks

**Testing**:
```python
# Test block allocation
allocator = BlockAllocator(num_blocks=100, block_size=16)

# Allocate blocks
block1 = allocator.allocate()
block2 = allocator.allocate()
assert block1 != block2

# Free block
allocator.free(block1)
assert block1 in allocator.free_blocks

# Test forking (COW)
block3 = allocator.allocate()
block4 = allocator.fork(block3)
assert block3 == block4  # Same physical block
assert allocator.blocks[block3].ref_count == 2
```

---

### Step 3: PagedAttention CUDA Kernel

**Goal**: Implement attention with non-contiguous KV cache

**Kernel overview**:
```
Input:
  - Q: Query tensor [batch, heads, 1, head_dim]
  - K blocks: [num_blocks, block_size, num_heads, head_dim]
  - V blocks: [num_blocks, block_size, num_heads, head_dim]
  - Block tables: [batch, max_blocks]
  
Algorithm:
  1. For each query position:
  2. For each block in block table:
  3.   Load K from block
  4.   Compute attention scores
  5.   Load V from block
  6.   Accumulate weighted values
```

**CUDA implementation**:
```cpp
// paged_attention_kernel.cu

__global__ void paged_attention_kernel(
    float* out,              // [batch, num_heads, head_dim]
    const float* query,      // [batch, num_heads, head_dim]
    const float* key_cache,  // [num_blocks, block_size, num_heads, head_dim]
    const float* value_cache,// [num_blocks, block_size, num_heads, head_dim]
    const int* block_tables, // [batch, max_num_blocks]
    const int* seq_lens,     // [batch]
    int num_heads,
    int head_dim,
    int block_size,
    int max_num_blocks,
    float scale
) {
    int batch_idx = blockIdx.x;
    int head_idx = blockIdx.y;
    
    // Each thread processes one head dimension
    int dim_idx = threadIdx.x;
    
    if (dim_idx >= head_dim) return;
    
    int seq_len = seq_lens[batch_idx];
    int num_blocks = (seq_len + block_size - 1) / block_size;
    
    float q_val = query[batch_idx * num_heads * head_dim + 
                       head_idx * head_dim + dim_idx];
    
    // Compute attention scores and accumulate
    float out_val = 0.0f;
    float sum_scores = 0.0f;
    
    for (int block_idx = 0; block_idx < num_blocks; block_idx++) {
        int physical_block = block_tables[batch_idx * max_num_blocks + block_idx];
        
        int tokens_in_block = min(block_size, seq_len - block_idx * block_size);
        
        for (int token_idx = 0; token_idx < tokens_in_block; token_idx++) {
            // Load K
            int k_offset = physical_block * block_size * num_heads * head_dim +
                          token_idx * num_heads * head_dim +
                          head_idx * head_dim + dim_idx;
            float k_val = key_cache[k_offset];
            
            // Compute attention score
            float score = q_val * k_val * scale;  // Simplified, need full dot product
            score = expf(score);
            
            // Load V
            int v_offset = physical_block * block_size * num_heads * head_dim +
                          token_idx * num_heads * head_dim +
                          head_idx * head_dim + dim_idx;
            float v_val = value_cache[v_offset];
            
            // Accumulate
            out_val += score * v_val;
            sum_scores += score;
        }
    }
    
    // Normalize
    out[batch_idx * num_heads * head_dim + head_idx * head_dim + dim_idx] = 
        out_val / sum_scores;
}
```

**Implementation tasks**:
- [ ] Write basic paged attention kernel
- [ ] Optimize with shared memory
- [ ] Handle block boundaries correctly
- [ ] Add numerical stability (softmax tricks)
- [ ] Test: Compare with standard attention

**Testing**:
```python
# Test paged attention correctness
seq_len = 100
block_size = 16
num_blocks = (seq_len + block_size - 1) // block_size

# Create standard attention inputs
Q = torch.randn(1, 8, 1, 64)
K = torch.randn(1, 8, seq_len, 64)
V = torch.randn(1, 8, seq_len, 64)

# Standard attention
standard_output = torch.nn.functional.scaled_dot_product_attention(Q, K, V)

# Paged attention (need to create blocks)
blocks = create_blocks(K, V, block_size)
block_table = list(range(num_blocks))
paged_output = paged_attention(Q, blocks, block_table, seq_len)

# Compare
error = (standard_output - paged_output).abs().mean()
assert error < 1e-5
```

---

### Step 4: CacheEngine Integration

**Goal**: Integrate block management with attention

**Implementation**:
```python
class CacheEngine:
    """Manages KV cache with PagedAttention"""
    def __init__(self, num_blocks: int, block_size: int, 
                 num_layers: int, num_heads: int, head_dim: int):
        self.block_size = block_size
        self.num_layers = num_layers
        
        # Allocate physical memory for all blocks
        self.key_cache = [
            torch.zeros(num_blocks, block_size, num_heads, head_dim)
            for _ in range(num_layers)
        ]
        self.value_cache = [
            torch.zeros(num_blocks, block_size, num_heads, head_dim)
            for _ in range(num_layers)
        ]
        
        # Block allocator
        self.allocator = BlockAllocator(num_blocks, block_size)
    
    def allocate_sequence(self, seq_len: int) -> BlockTable:
        """Allocate blocks for new sequence"""
        num_blocks = (seq_len + self.block_size - 1) // self.block_size
        block_table = BlockTable(self.block_size)
        
        for _ in range(num_blocks):
            block_id = self.allocator.allocate()
            if block_id is None:
                raise RuntimeError("Out of memory")
            block_table.append_block(block_id)
        
        return block_table
    
    def free_sequence(self, block_table: BlockTable):
        """Free blocks for completed sequence"""
        for block_id in block_table.blocks:
            self.allocator.free(block_id)
    
    def append_slot(self, block_table: BlockTable) -> Optional[int]:
        """Append a new token slot, allocating new block if needed"""
        num_tokens = len(block_table.blocks) * self.block_size
        slot_in_block = num_tokens % self.block_size
        
        if slot_in_block == 0:
            # Need new block
            block_id = self.allocator.allocate()
            if block_id is None:
                return None
            block_table.append_block(block_id)
        
        return len(block_table.blocks) - 1  # Return block index
```

**Implementation tasks**:
- [ ] Implement CacheEngine class
- [ ] Add sequence allocation/deallocation
- [ ] Handle token appending with new blocks
- [ ] Integrate with attention layer
- [ ] Test: Manage multiple sequences

---

## Phase 2: Continuous Batching

### Step 5: Sequence State Management

**Goal**: Track generation state for each request

**Implementation**:
```python
class SequenceStatus(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SWAPPED = "swapped"
    FINISHED_STOPPED = "finished_stopped"
    FINISHED_LENGTH = "finished_length"

@dataclass
class Sequence:
    """Represents a generation request"""
    seq_id: int
    prompt: str
    prompt_tokens: List[int]
    output_tokens: List[int]
    block_table: BlockTable
    status: SequenceStatus
    
    # Sampling parameters
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int = 100
    
    # State
    num_computed_tokens: int = 0  # Tokens already processed
    
    def append_token(self, token: int):
        """Add generated token"""
        self.output_tokens.append(token)
    
    def get_len(self) -> int:
        """Total sequence length"""
        return len(self.prompt_tokens) + len(self.output_tokens)
    
    def is_finished(self) -> bool:
        """Check if generation is complete"""
        if len(self.output_tokens) >= self.max_tokens:
            self.status = SequenceStatus.FINISHED_LENGTH
            return True
        if self.output_tokens and self.output_tokens[-1] == EOS_TOKEN:
            self.status = SequenceStatus.FINISHED_STOPPED
            return True
        return False

@dataclass
class SequenceGroup:
    """Group of sequences (for beam search, etc.)"""
    request_id: str
    sequences: List[Sequence]
    arrival_time: float
```

**Implementation tasks**:
- [ ] Implement Sequence class
- [ ] Add token tracking
- [ ] Implement completion detection
- [ ] Add SequenceGroup for batching
- [ ] Test: Create and update sequences

---

### Step 6: Scheduler

**Goal**: Dynamically batch requests

**Scheduler algorithm**:
```python
class Scheduler:
    """Continuous batching scheduler"""
    def __init__(self, max_num_seqs: int, max_num_batched_tokens: int):
        self.max_num_seqs = max_num_seqs
        self.max_num_batched_tokens = max_num_batched_tokens
        
        self.waiting: List[SequenceGroup] = []
        self.running: List[SequenceGroup] = []
        self.swapped: List[SequenceGroup] = []
    
    def add_request(self, request: SequenceGroup):
        """Add new request"""
        self.waiting.append(request)
    
    def schedule(self) -> SchedulerOutput:
        """Schedule next batch"""
        # 1. Handle finished sequences
        self._remove_finished()
        
        # 2. Try to swap in swapped sequences
        self._swap_in()
        
        # 3. Check if need to preempt (out of memory)
        if self._out_of_memory():
            self._preempt()
        
        # 4. Add new sequences from waiting queue
        self._add_new_sequences()
        
        # 5. Create batch
        return self._create_batch()
    
    def _remove_finished(self):
        """Remove completed sequences"""
        self.running = [
            sg for sg in self.running 
            if not all(seq.is_finished() for seq in sg.sequences)
        ]
    
    def _add_new_sequences(self):
        """Add waiting sequences to running"""
        while self.waiting and len(self.running) < self.max_num_seqs:
            # Check if we have enough blocks
            seq_group = self.waiting[0]
            if not self._can_allocate(seq_group):
                break
            
            seq_group = self.waiting.pop(0)
            self._allocate_blocks(seq_group)
            self.running.append(seq_group)
    
    def _preempt(self):
        """Preempt sequences to free memory"""
        # Preempt lowest priority sequences
        # In simple version, preempt newest
        while self._out_of_memory() and self.running:
            seq_group = self.running.pop()
            self._swap_out(seq_group)
    
    def _create_batch(self) -> SchedulerOutput:
        """Create batch from running sequences"""
        seq_ids = []
        block_tables = []
        input_tokens = []
        
        for seq_group in self.running:
            for seq in seq_group.sequences:
                seq_ids.append(seq.seq_id)
                block_tables.append(seq.block_table.get_physical_blocks())
                
                # For prefill, use all prompt tokens
                # For decode, use only last token
                if seq.num_computed_tokens == 0:
                    input_tokens.append(seq.prompt_tokens)
                else:
                    input_tokens.append([seq.output_tokens[-1]])
        
        return SchedulerOutput(
            seq_ids=seq_ids,
            block_tables=block_tables,
            input_tokens=input_tokens
        )
```

**Implementation tasks**:
- [ ] Implement scheduler with queues
- [ ] Add request admission logic
- [ ] Implement preemption
- [ ] Add swapping support
- [ ] Test: Schedule various workloads

**Testing**:
```python
# Test scheduler
scheduler = Scheduler(max_num_seqs=32, max_num_batched_tokens=8192)

# Add requests
for i in range(100):
    request = create_request(prompt=f"Request {i}")
    scheduler.add_request(request)

# Schedule steps
for _ in range(50):
    batch = scheduler.schedule()
    print(f"Batch size: {len(batch.seq_ids)}")
    
    # Simulate generation
    for seq_id in batch.seq_ids:
        seq = scheduler.get_sequence(seq_id)
        seq.append_token(random.randint(0, 10000))
```

---

## Phase 3: Model Parallelism

### Step 7: Tensor Parallelism

**Goal**: Distribute model across GPUs

**Tensor parallel strategies**:
1. **Column-parallel**: Split output dimension
2. **Row-parallel**: Split input dimension
3. **All-reduce**: Aggregate results

**Implementation**:
```python
class ColumnParallelLinear(nn.Module):
    """Column-parallel linear layer"""
    def __init__(self, in_features: int, out_features: int, world_size: int):
        super().__init__()
        self.world_size = world_size
        self.rank = torch.distributed.get_rank()
        
        # Each GPU gets out_features // world_size columns
        self.out_features_per_partition = out_features // world_size
        
        self.weight = nn.Parameter(
            torch.randn(self.out_features_per_partition, in_features)
        )
    
    def forward(self, x):
        # Each GPU computes its partition
        output = F.linear(x, self.weight)
        # No all-reduce needed, each GPU keeps its partition
        return output

class RowParallelLinear(nn.Module):
    """Row-parallel linear layer"""
    def __init__(self, in_features: int, out_features: int, world_size: int):
        super().__init__()
        self.world_size = world_size
        
        # Each GPU gets in_features // world_size rows
        self.in_features_per_partition = in_features // world_size
        
        self.weight = nn.Parameter(
            torch.randn(out_features, self.in_features_per_partition)
        )
    
    def forward(self, x):
        # Each GPU computes partial result
        output_parallel = F.linear(x, self.weight)
        
        # All-reduce to get full output
        output = tensor_parallel_all_reduce(output_parallel)
        return output

def tensor_parallel_all_reduce(tensor):
    """All-reduce across tensor parallel group"""
    torch.distributed.all_reduce(tensor, group=tensor_parallel_group)
    return tensor
```

**Attention head parallelism**:
```python
class TensorParallelAttention(nn.Module):
    """Attention with tensor parallelism"""
    def __init__(self, num_heads: int, head_dim: int, world_size: int):
        super().__init__()
        self.world_size = world_size
        self.num_heads_per_partition = num_heads // world_size
        
        # Q, K, V projections (column parallel)
        self.qkv_proj = ColumnParallelLinear(
            hidden_size,
            3 * num_heads * head_dim,
            world_size
        )
        
        # Output projection (row parallel)
        self.out_proj = RowParallelLinear(
            num_heads * head_dim,
            hidden_size,
            world_size
        )
    
    def forward(self, x):
        # Each GPU computes attention for its heads
        qkv = self.qkv_proj(x)
        q, k, v = qkv.split(self.num_heads_per_partition * head_dim, dim=-1)
        
        attn_output = paged_attention(q, k, v, ...)
        
        output = self.out_proj(attn_output)
        return output
```

**Implementation tasks**:
- [ ] Implement column-parallel linear
- [ ] Implement row-parallel linear
- [ ] Add NCCL communication
- [ ] Partition model weights
- [ ] Test: Verify multi-GPU correctness

---

### Step 8: Distributed Executor

**Goal**: Coordinate multi-GPU execution

**Implementation**:
```python
class Worker:
    """GPU worker process"""
    def __init__(self, rank: int, model_config, parallel_config):
        self.rank = rank
        self.device = f"cuda:{rank}"
        
        # Initialize distributed
        torch.distributed.init_process_group(
            backend="nccl",
            rank=rank,
            world_size=parallel_config.tensor_parallel_size
        )
        
        # Load model partition
        self.model = self._load_model_partition(model_config, parallel_config)
        self.cache_engine = CacheEngine(...)
    
    def execute_model(self, scheduler_output):
        """Execute model forward pass"""
        input_ids = scheduler_output.input_tokens
        block_tables = scheduler_output.block_tables
        
        # Forward pass
        logits = self.model(input_ids, block_tables, self.cache_engine)
        
        return logits
    
    def _load_model_partition(self, model_config, parallel_config):
        """Load model shard for this rank"""
        # TODO: Load appropriate weights for this GPU
        pass

class Executor:
    """Manages workers"""
    def __init__(self, model_config, parallel_config):
        self.workers = []
        self.tensor_parallel_size = parallel_config.tensor_parallel_size
        
        # Start worker processes
        for rank in range(self.tensor_parallel_size):
            worker = Worker(rank, model_config, parallel_config)
            self.workers.append(worker)
    
    def execute_model(self, scheduler_output):
        """Execute on all workers"""
        # Broadcast input to all workers
        futures = []
        for worker in self.workers:
            future = worker.execute_model(scheduler_output)
            futures.append(future)
        
        # Wait for completion
        results = [f.result() for f in futures]
        
        # Results are already synchronized via all-reduce
        return results[0]  # All workers have same result
```

**Implementation tasks**:
- [ ] Implement worker process
- [ ] Add distributed initialization
- [ ] Implement model partitioning
- [ ] Coordinate execution
- [ ] Test: Run on multiple GPUs

---

## Phase 4: Quantization

### Step 9: GPTQ Quantization

**Goal**: Support GPTQ 4-bit quantization

**GPTQ format**:
- Weights quantized to 4-bit integers
- Group-wise quantization (group_size = 128)
- Scales stored as FP16

**Implementation**:
```python
class GPTQLinear(nn.Module):
    """GPTQ quantized linear layer"""
    def __init__(self, in_features: int, out_features: int, 
                 group_size: int = 128):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.group_size = group_size
        
        # Quantized weights (4-bit packed into int32)
        # Each int32 holds 8 4-bit weights
        self.qweight = nn.Parameter(
            torch.zeros(out_features, in_features // 8, dtype=torch.int32)
        )
        
        # Scales (FP16)
        num_groups = in_features // group_size
        self.scales = nn.Parameter(
            torch.zeros(out_features, num_groups, dtype=torch.float16)
        )
        
        # Zero points (4-bit)
        self.qzeros = nn.Parameter(
            torch.zeros(out_features, num_groups // 8, dtype=torch.int32)
        )
    
    def forward(self, x):
        """Forward pass with dequantization"""
        # Dequantize weights on-the-fly
        weight_fp16 = dequantize_gptq(
            self.qweight, self.scales, self.qzeros, self.group_size
        )
        
        # Standard matrix multiplication
        output = F.linear(x, weight_fp16)
        return output

def dequantize_gptq(qweight, scales, qzeros, group_size):
    """Dequantize GPTQ weights"""
    # Unpack 4-bit values
    weight_int4 = unpack_int4(qweight)
    
    # Apply scales and zero points
    weight_fp16 = (weight_int4 - qzeros) * scales
    
    return weight_fp16

# Optimized CUDA kernel version
def gptq_gemm_cuda(x, qweight, scales, qzeros):
    """Fused GPTQ dequantize + GEMM kernel"""
    # TODO: Implement CUDA kernel that dequantizes
    # and multiplies in a single fused operation
    pass
```

**Implementation tasks**:
- [ ] Implement GPTQ weight loading
- [ ] Add dequantization logic
- [ ] Write fused CUDA kernel
- [ ] Test: Compare with FP16

---

## Phase 5: Production Serving

### Step 10: API Server

**Goal**: Build FastAPI server

**Implementation**:
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class CompletionRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 1.0
    top_p: float = 1.0

class CompletionResponse(BaseModel):
    text: str
    finish_reason: str

@app.post("/v1/completions")
async def create_completion(request: CompletionRequest):
    """OpenAI-compatible completion endpoint"""
    # Create sequence
    seq = Sequence(
        seq_id=generate_id(),
        prompt=request.prompt,
        prompt_tokens=tokenize(request.prompt),
        output_tokens=[],
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
    
    # Add to scheduler
    engine.scheduler.add_request(SequenceGroup([seq]))
    
    # Wait for completion
    while not seq.is_finished():
        await asyncio.sleep(0.01)
    
    return CompletionResponse(
        text=detokenize(seq.output_tokens),
        finish_reason=seq.status.value
    )

@app.post("/v1/completions/stream")
async def create_completion_stream(request: CompletionRequest):
    """Streaming completion"""
    async def generate():
        seq = create_sequence(request)
        engine.scheduler.add_request(SequenceGroup([seq]))
        
        prev_len = 0
        while not seq.is_finished():
            await asyncio.sleep(0.01)
            
            # Send new tokens
            if len(seq.output_tokens) > prev_len:
                new_tokens = seq.output_tokens[prev_len:]
                yield detokenize(new_tokens)
                prev_len = len(seq.output_tokens)
    
    return StreamingResponse(generate())
```

**Implementation tasks**:
- [ ] Create FastAPI server
- [ ] Implement completion endpoint
- [ ] Add streaming support
- [ ] Handle errors
- [ ] Test: Send requests via HTTP

---

## Testing and Benchmarking

### Unit Tests

```python
def test_block_allocation():
    allocator = BlockAllocator(100, 16)
    blocks = [allocator.allocate() for _ in range(50)]
    assert len(allocator.free_blocks) == 50

def test_paged_attention():
    # Compare with standard attention
    pass

def test_scheduler():
    scheduler = Scheduler(32, 8192)
    # Test various scenarios
    pass
```

### Integration Tests

```python
def test_end_to_end():
    # Start engine
    engine = Engine(model="llama-7b")
    
    # Generate
    output = engine.generate("Hello", max_tokens=10)
    assert len(output) > 0

def test_multi_gpu():
    engine = Engine(model="llama-70b", tensor_parallel_size=4)
    # Test generation
    pass
```

### Benchmarks

```python
def benchmark_throughput():
    """Measure requests per second"""
    engine = Engine(model="llama-7b")
    
    start = time.time()
    for _ in range(1000):
        engine.generate("Test", max_tokens=100)
    duration = time.time() - start
    
    throughput = 1000 / duration
    print(f"Throughput: {throughput:.1f} req/sec")

def benchmark_latency():
    """Measure time to first token"""
    times = []
    for _ in range(100):
        start = time.time()
        first_token = engine.generate_first_token("Test")
        times.append(time.time() - start)
    
    print(f"TTFT p50: {np.percentile(times, 50)*1000:.1f}ms")
    print(f"TTFT p99: {np.percentile(times, 99)*1000:.1f}ms")
```

---

## Performance Goals

Your implementation should achieve:

### Memory Efficiency
- ✅ 3-5x more sequences vs traditional caching
- ✅ <5% memory fragmentation
- ✅ 80%+ KV cache utilization

### Throughput
- ✅ >2000 tokens/sec (LLaMA-7B, A100)
- ✅ 10-24x improvement over HuggingFace

### Latency
- ✅ TTFT <100ms
- ✅ TPOT <20ms
- ✅ P99 <500ms

---

## Debug Tips

```python
# Visualize block allocation
def visualize_blocks():
    for seq in scheduler.running:
        print(f"Seq {seq.seq_id}: blocks={seq.block_table.blocks}")

# Profile attention kernel
nvprof python inference.py

# Check memory usage
nvidia-smi dmon -s m
```

---

## Next Steps

1. Add more optimization passes
2. Implement pipeline parallelism
3. Add more quantization methods
4. Optimize CUDA kernels
5. Add monitoring and logging

## Resources

- [vLLM Paper](https://arxiv.org/abs/2309.06180)
- [PagedAttention Blog](https://blog.vllm.ai/2023/06/20/vllm.html)
- [Flash Attention](https://github.com/Dao-AILab/flash-attention)
- [NCCL Documentation](https://docs.nvidia.com/deeplearning/nccl/)

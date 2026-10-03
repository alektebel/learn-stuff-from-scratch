# Phase 3: Advanced GPU Inference - Implementation Guide

This guide covers advanced GPU optimization techniques for high-performance inference including dynamic batching, multi-GPU inference, and memory management.

## Table of Contents
1. [Overview](#overview)
2. [Dynamic Batching](#dynamic-batching)
3. [Multi-GPU Inference](#multi-gpu-inference)
4. [GPU Memory Optimization](#gpu-memory-optimization)
5. [Concurrent Model Execution](#concurrent-model-execution)
6. [CUDA Optimization](#cuda-optimization)

## Overview

### What You'll Learn

Advanced techniques to maximize GPU utilization:
- **Dynamic Batching**: Combine requests for throughput
- **Multi-GPU**: Scale across multiple GPUs
- **Memory Management**: Optimize VRAM usage
- **Concurrency**: Run multiple models simultaneously
- **CUDA Optimization**: Low-level performance tuning

### Prerequisites

- Completed Phases 1 and 2
- NVIDIA GPU with CUDA support
- Understanding of GPU architecture
- Python async/await knowledge helpful

### Performance Goals

- **Throughput**: 5-10x improvement with batching
- **GPU Utilization**: >90% during inference
- **Multi-GPU Scaling**: 90%+ efficiency
- **Latency**: Maintain <100ms for interactive apps

## Dynamic Batching

### 2.1 Basic Dynamic Batching

**Concept**: Collect multiple requests and process them together in a batch for better throughput.

```python
import asyncio
import torch
from collections import deque
from typing import List, Tuple
import time

class DynamicBatcher:
    """
    Implement dynamic batching for inference requests.
    
    Collects requests for a short period and batches them together
    to maximize GPU utilization and throughput.
    """
    
    def __init__(
        self,
        model,
        max_batch_size=32,
        max_wait_time=0.01,  # 10ms
        device='cuda'
    ):
        """
        Initialize dynamic batcher.
        
        Args:
            model: Model for inference
            max_batch_size: Maximum batch size
            max_wait_time: Maximum time to wait for requests (seconds)
            device: Device to run on
        """
        self.model = model.to(device).eval()
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.device = device
        
        # Request queue
        self.request_queue = deque()
        self.results = {}
        
        # Background processing
        self.processing_task = None
        self.running = False
    
    async def predict(self, input_data):
        """
        Submit prediction request.
        
        This is the user-facing API. Requests are queued
        and processed in batches automatically.
        
        Args:
            input_data: Single input tensor
        
        Returns:
            Prediction result
        
        Implementation:
        1. Generate unique request ID
        2. Add to queue with Future
        3. Wait for result asynchronously
        4. Return result when ready
        """
        # Create request with unique ID
        request_id = id(input_data)
        future = asyncio.Future()
        
        # Add to queue
        self.request_queue.append((request_id, input_data, future))
        
        # Wait for result
        result = await future
        
        return result
    
    async def _process_loop(self):
        """
        Background loop that processes batches.
        
        Steps:
        1. Wait for requests or timeout
        2. Collect batch of requests
        3. Run batch inference
        4. Distribute results to futures
        5. Repeat
        """
        while self.running:
            # Wait for requests
            batch_start = time.time()
            
            # Collect requests
            batch = []
            futures = []
            
            while len(batch) < self.max_batch_size:
                # Check timeout
                if time.time() - batch_start > self.max_wait_time:
                    break
                
                # Get request if available
                if self.request_queue:
                    req_id, data, future = self.request_queue.popleft()
                    batch.append(data)
                    futures.append(future)
                else:
                    # Small sleep to avoid busy waiting
                    await asyncio.sleep(0.001)
            
            # Process batch if we have requests
            if batch:
                await self._process_batch(batch, futures)
    
    async def _process_batch(self, batch, futures):
        """
        Process a batch of requests.
        
        Args:
            batch: List of input tensors
            futures: List of futures to fulfill
        
        Steps:
        1. Stack inputs into batch tensor
        2. Run inference (in thread pool to not block)
        3. Split outputs
        4. Set futures with results
        """
        # Stack into batch
        batch_tensor = torch.stack(batch).to(self.device)
        
        # Inference (run in executor to not block event loop)
        loop = asyncio.get_event_loop()
        outputs = await loop.run_in_executor(
            None,
            self._run_inference,
            batch_tensor
        )
        
        # Distribute results
        for i, future in enumerate(futures):
            if not future.done():
                future.set_result(outputs[i])
    
    def _run_inference(self, batch_tensor):
        """Run synchronous inference."""
        with torch.no_grad():
            return self.model(batch_tensor)
    
    def start(self):
        """Start background processing."""
        self.running = True
        self.processing_task = asyncio.create_task(self._process_loop())
    
    async def stop(self):
        """Stop background processing."""
        self.running = False
        if self.processing_task:
            await self.processing_task
```

**Usage Example:**

```python
async def main():
    # Create batcher
    model = load_model()
    batcher = DynamicBatcher(
        model,
        max_batch_size=32,
        max_wait_time=0.01  # 10ms
    )
    
    # Start background processing
    batcher.start()
    
    # Submit requests concurrently
    tasks = []
    for i in range(100):
        input_data = torch.randn(3, 224, 224)
        task = batcher.predict(input_data)
        tasks.append(task)
    
    # Wait for all results
    results = await asyncio.gather(*tasks)
    
    # Stop batcher
    await batcher.stop()
    
    print(f"Processed {len(results)} requests")

# Run
asyncio.run(main())
```

### 2.2 Advanced Batching Strategies

**Adaptive Batch Size:**

```python
class AdaptiveBatcher(DynamicBatcher):
    """
    Batcher that adapts batch size based on latency requirements.
    
    Increases batch size when latency target is met,
    decreases when latency is too high.
    """
    
    def __init__(self, *args, target_latency=50, **kwargs):
        """
        Initialize adaptive batcher.
        
        Args:
            target_latency: Target latency in milliseconds
        """
        super().__init__(*args, **kwargs)
        self.target_latency = target_latency / 1000  # Convert to seconds
        
        # Adaptive parameters
        self.current_batch_size = 1
        self.min_batch_size = 1
        self.latency_history = deque(maxlen=100)
    
    def _adjust_batch_size(self, actual_latency):
        """
        Adjust batch size based on latency.
        
        Strategy:
        - If latency < target: Increase batch size
        - If latency > target: Decrease batch size
        """
        self.latency_history.append(actual_latency)
        
        # Need enough samples
        if len(self.latency_history) < 10:
            return
        
        avg_latency = sum(self.latency_history) / len(self.latency_history)
        
        if avg_latency < self.target_latency * 0.8:
            # Room to increase
            self.current_batch_size = min(
                self.current_batch_size + 4,
                self.max_batch_size
            )
        elif avg_latency > self.target_latency * 1.2:
            # Need to decrease
            self.current_batch_size = max(
                self.current_batch_size - 4,
                self.min_batch_size
            )
```

**Priority-Based Batching:**

```python
class PriorityBatcher:
    """
    Batcher that prioritizes requests based on deadline or importance.
    
    Useful for multi-tenant systems or SLA-based serving.
    """
    
    def __init__(self, model, max_batch_size=32):
        self.model = model
        self.max_batch_size = max_batch_size
        
        # Priority queues (high, medium, low)
        self.queues = {
            'high': deque(),
            'medium': deque(),
            'low': deque()
        }
    
    async def predict(self, input_data, priority='medium'):
        """
        Submit request with priority.
        
        Args:
            input_data: Input tensor
            priority: 'high', 'medium', or 'low'
        """
        future = asyncio.Future()
        self.queues[priority].append((input_data, future))
        return await future
    
    def _collect_batch(self):
        """
        Collect batch respecting priorities.
        
        Strategy:
        - Fill 50% from high priority
        - Fill 30% from medium priority
        - Fill 20% from low priority
        """
        batch = []
        
        # High priority (50%)
        high_count = int(self.max_batch_size * 0.5)
        batch.extend(self._take_from_queue('high', high_count))
        
        # Medium priority (30%)
        medium_count = int(self.max_batch_size * 0.3)
        batch.extend(self._take_from_queue('medium', medium_count))
        
        # Low priority (remaining)
        low_count = self.max_batch_size - len(batch)
        batch.extend(self._take_from_queue('low', low_count))
        
        return batch
```

## Multi-GPU Inference

### 3.1 Data Parallel Inference

**Distribute Inference Across GPUs:**

```python
class MultiGPUInference:
    """
    Distribute inference across multiple GPUs.
    
    Each GPU processes a portion of the batch independently.
    """
    
    def __init__(self, model, device_ids=None):
        """
        Initialize multi-GPU inference.
        
        Args:
            model: Model to replicate
            device_ids: List of GPU IDs (e.g., [0, 1, 2, 3])
        """
        if device_ids is None:
            device_ids = list(range(torch.cuda.device_count()))
        
        self.device_ids = device_ids
        self.num_gpus = len(device_ids)
        
        # Replicate model to each GPU
        self.models = []
        for device_id in device_ids:
            device = torch.device(f'cuda:{device_id}')
            model_copy = copy.deepcopy(model).to(device).eval()
            self.models.append(model_copy)
        
        print(f"Initialized inference on {self.num_gpus} GPUs")
    
    def predict_batch(self, batch_input):
        """
        Distribute batch across GPUs.
        
        Steps:
        1. Split batch into chunks (one per GPU)
        2. Process each chunk on its GPU
        3. Gather results back
        
        Args:
            batch_input: Batch tensor
        
        Returns:
            Combined outputs from all GPUs
        """
        batch_size = batch_input.size(0)
        
        # Split batch
        chunk_size = (batch_size + self.num_gpus - 1) // self.num_gpus
        chunks = []
        
        for i in range(self.num_gpus):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, batch_size)
            
            if start_idx < batch_size:
                chunk = batch_input[start_idx:end_idx]
                device = torch.device(f'cuda:{self.device_ids[i]}')
                chunks.append(chunk.to(device))
            else:
                chunks.append(None)
        
        # Process in parallel
        outputs = []
        threads = []
        
        def process_chunk(model, chunk):
            if chunk is not None:
                with torch.no_grad():
                    return model(chunk)
            return None
        
        # Launch inference on each GPU
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for model, chunk in zip(self.models, chunks):
                if chunk is not None:
                    future = executor.submit(process_chunk, model, chunk)
                    futures.append(future)
            
            # Gather results
            for future in concurrent.futures.as_completed(futures):
                output = future.result()
                if output is not None:
                    outputs.append(output.cpu())
        
        # Concatenate outputs
        combined_output = torch.cat(outputs, dim=0)
        
        return combined_output
```

### 3.2 Model Parallel Inference

**Split Large Models Across GPUs:**

```python
class ModelParallelInference:
    """
    Split large model across multiple GPUs.
    
    Useful when model doesn't fit on a single GPU.
    Different layers on different GPUs.
    """
    
    def __init__(self, model, split_points):
        """
        Initialize model parallel inference.
        
        Args:
            model: Model to split
            split_points: List of (layer_name, device_id) tuples
        
        Example:
            split_points = [
                ('layer1', 0),
                ('layer2', 0),
                ('layer3', 1),
                ('layer4', 1)
            ]
        """
        self.model = model
        self.split_points = split_points
        
        # Move layers to specified devices
        self._distribute_layers()
    
    def _distribute_layers(self):
        """Move model layers to specified GPUs."""
        for layer_name, device_id in self.split_points:
            device = torch.device(f'cuda:{device_id}')
            layer = getattr(self.model, layer_name)
            layer.to(device)
    
    def predict(self, input_data):
        """
        Run inference with model parallelism.
        
        Data flows through GPUs as it passes through layers.
        """
        x = input_data
        
        with torch.no_grad():
            for layer_name, device_id in self.split_points:
                # Move data to current layer's device
                device = torch.device(f'cuda:{device_id}')
                x = x.to(device)
                
                # Forward through layer
                layer = getattr(self.model, layer_name)
                x = layer(x)
        
        return x
```

### 3.3 Pipeline Parallelism

**Overlap Computation Across GPUs:**

```python
class PipelineParallelInference:
    """
    Pipeline model across GPUs for higher throughput.
    
    While GPU 0 processes batch N in layer 1,
    GPU 1 processes batch N-1 in layer 2.
    """
    
    def __init__(self, model, num_stages=4):
        """
        Initialize pipeline parallel inference.
        
        Args:
            model: Model to pipeline
            num_stages: Number of pipeline stages (GPUs)
        """
        self.num_stages = num_stages
        self.stages = self._split_model(model)
    
    def _split_model(self, model):
        """
        Split model into pipeline stages.
        
        Each stage runs on a different GPU.
        """
        stages = []
        layers_per_stage = len(model.layers) // self.num_stages
        
        for stage_id in range(self.num_stages):
            start_idx = stage_id * layers_per_stage
            end_idx = (stage_id + 1) * layers_per_stage
            
            stage_layers = model.layers[start_idx:end_idx]
            stage_model = nn.Sequential(*stage_layers)
            
            device = torch.device(f'cuda:{stage_id}')
            stage_model = stage_model.to(device)
            
            stages.append(stage_model)
        
        return stages
    
    def predict_batches(self, batches):
        """
        Process multiple batches with pipeline parallelism.
        
        Batches flow through stages like an assembly line.
        """
        # Queue for each stage
        stage_queues = [deque() for _ in range(self.num_stages)]
        
        # Add batches to first stage
        for batch in batches:
            stage_queues[0].append(batch)
        
        results = []
        
        # Process pipeline
        while any(queue for queue in stage_queues):
            for stage_id in range(self.num_stages):
                if stage_queues[stage_id]:
                    batch = stage_queues[stage_id].popleft()
                    
                    # Process on this stage
                    device = torch.device(f'cuda:{stage_id}')
                    batch = batch.to(device)
                    output = self.stages[stage_id](batch)
                    
                    # Send to next stage or collect result
                    if stage_id < self.num_stages - 1:
                        stage_queues[stage_id + 1].append(output)
                    else:
                        results.append(output.cpu())
        
        return results
```

## GPU Memory Optimization

### 4.1 Memory Management

**Optimize VRAM Usage:**

```python
class GPUMemoryManager:
    """
    Manage GPU memory efficiently for inference.
    
    Techniques:
    - Memory pooling
    - Garbage collection
    - Activation checkpointing
    """
    
    def __init__(self, device='cuda'):
        self.device = device
    
    def clear_cache(self):
        """
        Clear GPU cache.
        
        Useful between large operations.
        """
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    def get_memory_stats(self):
        """
        Get current memory usage.
        
        Returns:
            Dictionary with memory statistics
        """
        allocated = torch.cuda.memory_allocated() / (1024 ** 3)  # GB
        reserved = torch.cuda.memory_reserved() / (1024 ** 3)
        max_allocated = torch.cuda.max_memory_allocated() / (1024 ** 3)
        
        return {
            'allocated_gb': allocated,
            'reserved_gb': reserved,
            'max_allocated_gb': max_allocated,
            'free_gb': reserved - allocated
        }
    
    def optimize_batch_size(self, model, input_shape, start_size=128):
        """
        Find optimal batch size that fits in memory.
        
        Uses binary search to find maximum batch size.
        """
        max_batch = start_size
        min_batch = 1
        optimal_batch = 1
        
        while min_batch <= max_batch:
            batch_size = (min_batch + max_batch) // 2
            
            try:
                # Try this batch size
                self.clear_cache()
                dummy_input = torch.randn(batch_size, *input_shape).to(self.device)
                
                with torch.no_grad():
                    _ = model(dummy_input)
                
                # Success - try larger
                optimal_batch = batch_size
                min_batch = batch_size + 1
                
            except RuntimeError as e:
                if 'out of memory' in str(e):
                    # OOM - try smaller
                    max_batch = batch_size - 1
                    self.clear_cache()
                else:
                    raise e
        
        return optimal_batch
```

### 4.2 Activation Checkpointing

**Trade Compute for Memory:**

```python
from torch.utils.checkpoint import checkpoint

class CheckpointedModel(nn.Module):
    """
    Model with activation checkpointing.
    
    Recomputes activations instead of storing them,
    saving memory at the cost of compute.
    """
    
    def __init__(self, model, checkpoint_segments=4):
        super().__init__()
        self.model = model
        self.checkpoint_segments = checkpoint_segments
    
    def forward(self, x):
        """
        Forward pass with checkpointing.
        
        Only stores activations at segment boundaries,
        recomputes intermediate activations when needed.
        """
        # Split model into segments
        layers_per_segment = len(self.model.layers) // self.checkpoint_segments
        
        for i in range(self.checkpoint_segments):
            start_idx = i * layers_per_segment
            end_idx = (i + 1) * layers_per_segment
            segment = self.model.layers[start_idx:end_idx]
            
            # Use checkpointing for this segment
            x = checkpoint(
                self._segment_forward,
                segment,
                x
            )
        
        return x
    
    def _segment_forward(self, layers, x):
        """Forward through a segment of layers."""
        for layer in layers:
            x = layer(x)
        return x
```

## Concurrent Model Execution

### 5.1 Multi-Model Server

**Run Multiple Models Concurrently:**

```python
class MultiModelServer:
    """
    Serve multiple models concurrently on GPU.
    
    Uses CUDA streams for concurrent execution.
    """
    
    def __init__(self, models, device='cuda'):
        """
        Initialize multi-model server.
        
        Args:
            models: Dictionary of {model_name: model}
            device: GPU device
        """
        self.device = device
        self.models = {}
        self.streams = {}
        
        # Load models and create streams
        for name, model in models.items():
            self.models[name] = model.to(device).eval()
            self.streams[name] = torch.cuda.Stream()
    
    async def predict(self, model_name, input_data):
        """
        Run inference on specified model.
        
        Uses dedicated CUDA stream for concurrency.
        """
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")
        
        model = self.models[model_name]
        stream = self.streams[model_name]
        
        # Run inference in dedicated stream
        with torch.cuda.stream(stream):
            input_tensor = input_data.to(self.device)
            
            with torch.no_grad():
                output = model(input_tensor)
            
            # Synchronize stream
            stream.synchronize()
        
        return output.cpu()
    
    async def predict_multiple(self, requests):
        """
        Process multiple model requests concurrently.
        
        Args:
            requests: List of (model_name, input_data) tuples
        
        Returns:
            List of outputs in same order
        """
        tasks = []
        for model_name, input_data in requests:
            task = self.predict(model_name, input_data)
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        return results
```

## CUDA Optimization

### 6.1 CUDA Streams

**Overlap Operations:**

```python
class CUDAStreamOptimizer:
    """
    Optimize inference using CUDA streams.
    
    Overlaps data transfer and computation.
    """
    
    def __init__(self, model, device='cuda', num_streams=4):
        self.model = model.to(device).eval()
        self.device = device
        
        # Create multiple streams
        self.streams = [torch.cuda.Stream() for _ in range(num_streams)]
        self.current_stream = 0
    
    def predict_async(self, input_data):
        """
        Asynchronous inference using streams.
        
        Allows overlap of multiple inferences.
        """
        stream = self.streams[self.current_stream]
        self.current_stream = (self.current_stream + 1) % len(self.streams)
        
        with torch.cuda.stream(stream):
            input_tensor = input_data.to(self.device, non_blocking=True)
            
            with torch.no_grad():
                output = self.model(input_tensor)
            
            # Don't sync here - allows overlap
            return stream, output
    
    def predict_overlapped(self, batches):
        """
        Process multiple batches with overlapped execution.
        
        Overlaps:
        - Data transfer to GPU
        - Inference computation
        - Data transfer from GPU
        """
        results = []
        pending = []
        
        for batch in batches:
            # Launch inference
            stream, output = self.predict_async(batch)
            pending.append((stream, output))
            
            # Sync oldest streams (limit concurrent operations)
            if len(pending) >= len(self.streams):
                stream, output = pending.pop(0)
                stream.synchronize()
                results.append(output.cpu())
        
        # Sync remaining
        for stream, output in pending:
            stream.synchronize()
            results.append(output.cpu())
        
        return results
```

## Expected Outcomes

After completing Phase 3, you should achieve:

### Performance Targets
- **Dynamic Batching**: 5-10x throughput improvement
- **GPU Utilization**: >90% during inference
- **Multi-GPU Scaling**: 90%+ efficiency (linear scaling)
- **Memory Optimization**: Fit 2-3x larger batches

### Understanding
- ✅ Implement dynamic batching systems
- ✅ Distribute inference across GPUs
- ✅ Optimize GPU memory usage
- ✅ Use CUDA streams for concurrency
- ✅ Debug GPU performance issues

## Next Steps

Phase 4 covers production deployment:
- End-to-end video analysis system
- Edge device deployment (Jetson, RPi)
- GPU server deployment (Triton)
- Monitoring and scaling

# Phase 1: Expected Outcomes

This document describes what your implementation should achieve after completing Phase 1.

## Functional Requirements

### ✅ Model Loading Capabilities

Your implementation should successfully load:

1. **PyTorch Models**
   - `.pth` checkpoint files
   - `.pt` saved models
   - TorchScript models (`.pt` compiled)
   - Handle different checkpoint formats (state_dict, full model, etc.)

2. **ONNX Models**
   - `.onnx` format
   - Support CPU and GPU execution providers
   - Handle dynamic input shapes

3. **TensorFlow Models**
   - SavedModel format
   - Keras `.h5` format
   - TensorFlow Lite (optional)

### ✅ Inference Execution

Your inference engine should:

1. **Single Input Processing**
   - Process one image/input at a time
   - Handle preprocessing (resize, normalize, transpose)
   - Return predictions in correct format

2. **Batch Processing**
   - Process multiple inputs simultaneously
   - Optimize batch size for hardware
   - Handle variable batch sizes
   - Process datasets efficiently

3. **Error Handling**
   - Validate input shapes
   - Handle OOM errors gracefully
   - Provide clear error messages

### ✅ Performance Profiling

Your profiler should measure:

1. **Latency Metrics**
   - Mean latency
   - Median (p50)
   - 95th percentile (p95)
   - 99th percentile (p99)
   - Min/Max latency

2. **Throughput Metrics**
   - Frames per second (FPS)
   - Requests per second
   - Throughput vs batch size curves

3. **Memory Metrics**
   - Model parameter memory
   - Peak activation memory
   - GPU memory usage (allocated/reserved)

## Performance Benchmarks

### ResNet50 (Image Classification)

**CPU (Intel i7-10700K, 8 cores)**
```
Model Format    │ Latency (ms) │ Throughput (FPS) │ Memory (MB)
────────────────┼──────────────┼──────────────────┼────────────
PyTorch (FP32)  │    42.5      │       23.5       │    102
ONNX (FP32)     │    35.8      │       27.9       │     97
TorchScript     │    38.2      │       26.2       │    102
```

**GPU (NVIDIA V100, 32GB)**
```
Model Format    │ Latency (ms) │ Throughput (FPS) │ Memory (MB)
────────────────┼──────────────┼──────────────────┼────────────
PyTorch (FP32)  │     4.2      │      238         │    350
ONNX (FP32)     │     3.8      │      263         │    320
TorchScript     │     3.9      │      256         │    350
```

**Batch Processing (GPU V100, batch size 16)**
```
Batch Size │ Latency (ms) │ Throughput (FPS) │ Images/Batch
───────────┼──────────────┼──────────────────┼─────────────
    1      │     4.2      │      238         │     238
    2      │     5.1      │      392         │     784
    4      │     7.3      │      548         │    2192
    8      │    11.8      │      678         │    5424
   16      │    20.5      │      780         │   12480
   32      │    38.2      │      837         │   26784
```

### BERT-Base (Text Classification)

**CPU (Intel i7-10700K)**
```
Sequence Length │ Latency (ms) │ Throughput (seq/s)
────────────────┼──────────────┼───────────────────
     128        │    85.3      │      11.7
     256        │   142.8      │       7.0
     512        │   268.5      │       3.7
```

**GPU (NVIDIA V100)**
```
Sequence Length │ Latency (ms) │ Throughput (seq/s)
────────────────┼──────────────┼───────────────────
     128        │    12.5      │      80.0
     256        │    18.3      │      54.6
     512        │    32.7      │      30.6
```

### MobileNetV2 (Lightweight Model)

**CPU (Intel i7-10700K)**
```
Input Size     │ Latency (ms) │ Throughput (FPS)
───────────────┼──────────────┼─────────────────
  224x224      │     8.5      │     117.6
  320x320      │    14.2      │      70.4
```

**Edge Device (Raspberry Pi 4)**
```
Input Size     │ Latency (ms) │ Throughput (FPS)
───────────────┼──────────────┼─────────────────
  224x224      │    145       │       6.9
  320x320      │    285       │       3.5
```

## Measurement Accuracy

Your measurements should be:

### Precision
- **Latency variance**: < 5% standard deviation
- **Reproducibility**: Within 10% across runs
- **GPU timing**: Use CUDA events, not CPU time

### Methodology
- ✅ Proper warmup (10-50 iterations)
- ✅ Sufficient iterations (100-1000 for latency)
- ✅ GPU synchronization before timing
- ✅ Statistical reporting (not just mean)

### Reporting Format

```python
Profiling Results:
==================
Model: ResNet50
Device: CUDA (Tesla V100-SXM2-32GB)
Input Shape: (1, 3, 224, 224)
Iterations: 1000 (100 warmup)

Latency Statistics:
  Mean:   4.23 ms
  Median: 4.18 ms
  Std:    0.21 ms (4.9%)
  Min:    3.95 ms
  Max:    5.87 ms
  P95:    4.52 ms
  P99:    4.89 ms

Memory Usage:
  Model Parameters: 97.5 MB
  Peak Activation:  125.3 MB
  Total GPU:        350.8 MB
  
Throughput: 236.4 FPS
```

## Code Quality Standards

### Structure
```
phase1_basics/
├── model_loader.py          # Model loading classes
│   ├── PyTorchModelLoader
│   ├── ONNXModelLoader
│   └── TensorFlowModelLoader
├── inference_engine.py       # Inference execution
│   └── InferenceEngine
├── profiler.py              # Performance profiling
│   └── PerformanceProfiler
├── preprocessors.py         # Data preprocessing
├── utils.py                 # Helper functions
└── tests/
    ├── test_loaders.py
    ├── test_inference.py
    └── test_profiler.py
```

### Code Style
- ✅ Type hints for all functions
- ✅ Docstrings (Google or NumPy style)
- ✅ Clear variable names
- ✅ Error handling with try/except
- ✅ Logging instead of print statements

### Example Well-Written Function
```python
def measure_latency(
    model: torch.nn.Module,
    input_shape: Tuple[int, ...],
    num_iterations: int = 100,
    warmup: int = 10,
    device: str = 'cpu'
) -> Dict[str, float]:
    """
    Measure model inference latency with proper methodology.
    
    Args:
        model: PyTorch model to benchmark
        input_shape: Shape of input tensor (C, H, W)
        num_iterations: Number of measurements to collect
        warmup: Number of warmup iterations before measurement
        device: Device to run on ('cpu' or 'cuda')
    
    Returns:
        Dictionary containing latency statistics:
            - mean: Average latency in milliseconds
            - median: Median latency
            - std: Standard deviation
            - p95, p99: 95th and 99th percentiles
    
    Raises:
        ValueError: If device is 'cuda' but CUDA is unavailable
        RuntimeError: If model inference fails
    
    Example:
        >>> model = torchvision.models.resnet50()
        >>> stats = measure_latency(model, (3, 224, 224), device='cuda')
        >>> print(f"Mean latency: {stats['mean']:.2f}ms")
    """
    # Implementation...
```

### Testing Requirements

**Unit Tests (>80% coverage)**
```python
# Test model loading
def test_load_pytorch_model()
def test_load_onnx_model()
def test_load_with_invalid_path()

# Test inference
def test_single_inference()
def test_batch_inference()
def test_variable_batch_sizes()

# Test profiling
def test_latency_measurement()
def test_throughput_measurement()
def test_memory_profiling()
```

**Integration Tests**
```python
def test_end_to_end_inference_pipeline()
def test_multiple_model_formats()
def test_cpu_gpu_parity()
```

## Common Issues and Solutions

### Issue 1: Inconsistent Timing
**Problem**: Latency varies widely between runs
**Solutions**:
- ✅ Add proper warmup iterations
- ✅ Use CUDA events instead of `time.time()`
- ✅ Disable CPU frequency scaling
- ✅ Close other applications
- ✅ Run multiple times and report statistics

### Issue 2: OOM Errors
**Problem**: Out of memory when running inference
**Solutions**:
- ✅ Reduce batch size
- ✅ Clear CUDA cache between runs
- ✅ Use `torch.no_grad()` context
- ✅ Enable memory growth (TensorFlow)
- ✅ Move data to GPU incrementally

### Issue 3: Slow First Inference
**Problem**: First inference much slower than subsequent ones
**Explanation**: This is expected due to:
- CUDA kernel compilation
- GPU initialization
- CPU cache warming
**Solution**: Always include warmup iterations

### Issue 4: CPU vs GPU Timing Confusion
**Problem**: GPU timing seems wrong
**Solution**: Remember GPU operations are asynchronous:
```python
# WRONG
start = time.time()
output = model(input)
end = time.time()  # This is wrong!

# CORRECT
start_event = torch.cuda.Event(enable_timing=True)
end_event = torch.cuda.Event(enable_timing=True)
start_event.record()
output = model(input)
end_event.record()
torch.cuda.synchronize()
latency = start_event.elapsed_time(end_event)
```

## Validation Checklist

Before moving to Phase 2, verify:

### Functionality
- [ ] Can load PyTorch models successfully
- [ ] Can load ONNX models successfully
- [ ] Can run single input inference
- [ ] Can run batch inference
- [ ] Preprocessing pipeline works correctly
- [ ] Outputs are correct (verify on known test cases)

### Performance
- [ ] Latency measurements within 5% variance
- [ ] Throughput measurements are consistent
- [ ] Batch processing faster than single inference
- [ ] GPU utilization >80% during inference
- [ ] Memory profiling shows expected usage

### Code Quality
- [ ] All tests pass
- [ ] Test coverage >80%
- [ ] Type hints added
- [ ] Documentation complete
- [ ] No linter errors
- [ ] Code follows style guide

### Understanding
- [ ] Understand why warmup is necessary
- [ ] Know the difference between latency and throughput
- [ ] Understand batch size tradeoffs
- [ ] Can explain GPU synchronization
- [ ] Know when to use CPU vs GPU

## Self-Assessment Questions

Test your understanding:

1. **Why is the first inference always slower?**
   - GPU needs to compile kernels
   - CPU caches need to warm up
   - Memory allocation happens
   
2. **What's the difference between `torch.no_grad()` and `model.eval()`?**
   - `no_grad()`: Disables gradient computation
   - `eval()`: Changes behavior of BatchNorm/Dropout
   - Both are needed for inference

3. **Why use p99 latency instead of mean?**
   - p99 represents worst-case performance
   - Critical for user experience
   - Mean can hide outliers

4. **When to use batch inference?**
   - Higher throughput needed
   - Multiple requests available
   - GPU utilization is low
   - Latency not critical

5. **How to choose batch size?**
   - Start with what fits in memory
   - Measure throughput at different sizes
   - Consider latency requirements
   - Monitor GPU utilization

## Next Steps

You're ready for Phase 2 if you can:
1. ✅ Reliably load and run models
2. ✅ Measure performance accurately
3. ✅ Understand your measurements
4. ✅ Debug performance issues
5. ✅ Write production-quality code

**Phase 2 Preview**: Learn to optimize models with:
- Quantization (INT8, FP16)
- Model compilation (TensorRT)
- Graph optimizations
- Accuracy preservation techniques

# TensorRT Inference Engine from Scratch

A from-scratch implementation of a TensorRT-style inference engine. Learn how NVIDIA TensorRT optimizes neural networks for maximum inference performance on GPUs.

## Goal

Build a deep understanding of inference optimization by implementing:
- **Network optimizer**: Graph optimization, layer fusion, precision calibration
- **Engine builder**: Convert optimized graphs to efficient execution plans
- **Runtime engine**: Execute inference with minimal overhead
- **Plugin system**: Custom layer implementations
- **Memory management**: Efficient tensor allocation and reuse
- **Multi-precision support**: FP32, FP16, INT8 quantization

## What is TensorRT?

TensorRT is NVIDIA's high-performance deep learning inference SDK. It:
- Optimizes trained neural networks for inference
- Fuses layers and eliminates dead code
- Performs kernel auto-tuning for target GPU
- Supports mixed precision (FP16, INT8)
- Reduces memory footprint and latency
- Provides C++ and Python APIs

Typical speedup: 2-10x faster than framework inference (PyTorch, TensorFlow)

## Project Structure

```
tensorrt-inference/
├── README.md                          # This file
├── IMPLEMENTATION_GUIDE.md            # Detailed implementation guide
├── core/
│   ├── network.py                    # Network definition API
│   ├── builder.py                    # Engine builder
│   ├── engine.py                     # Runtime engine
│   └── context.py                    # Execution context
├── optimizer/
│   ├── graph_optimizer.py            # Graph-level optimizations
│   ├── layer_fusion.py               # Layer fusion passes
│   ├── precision_calibrator.py       # INT8 calibration
│   └── kernel_autotuner.py           # Kernel selection
├── layers/
│   ├── base.py                       # Layer interface
│   ├── convolution.py               # Convolution layer
│   ├── pooling.py                   # Pooling layers
│   ├── activation.py                # Activation functions
│   ├── fully_connected.py           # Dense layers
│   └── normalization.py             # BatchNorm, LayerNorm
├── plugins/
│   ├── plugin_base.py               # Plugin interface
│   ├── custom_layers.py             # Custom layer examples
│   └── plugin_registry.py           # Plugin registration
├── kernels/
│   ├── cuda_kernels.cu              # CUDA kernel implementations
│   ├── convolution_kernels.cu       # Optimized convolutions
│   ├── gemm_kernels.cu              # Matrix multiplication
│   └── reduction_kernels.cu         # Reduction operations
├── memory/
│   ├── allocator.py                 # Memory allocator
│   ├── tensor.py                    # Tensor representation
│   └── memory_pool.py               # Memory pool management
├── parsers/
│   ├── onnx_parser.py               # ONNX model parser
│   ├── pytorch_parser.py            # PyTorch model parser
│   └── tensorflow_parser.py         # TensorFlow model parser
├── calibration/
│   ├── int8_calibrator.py           # INT8 calibration
│   ├── entropy_calibrator.py        # Entropy-based calibration
│   └── minmax_calibrator.py         # Min-max calibration
├── tests/
│   ├── test_layers.py
│   ├── test_optimizer.py
│   ├── test_engine.py
│   └── benchmarks/
│       ├── inference_latency.py
│       ├── throughput.py
│       └── memory_usage.py
└── solutions/                        # Complete reference implementations
    ├── README.md
    └── ...
```

## Learning Path

### Phase 1: Core Infrastructure (10-12 hours)

**1.1 Network Definition API**

Build the network construction interface:
- Layer definitions (Conv, FC, Activation, etc.)
- Network builder pattern
- Input/output tensor specification
- Layer properties and attributes

**Implementation tasks**:
- Create `INetworkDefinition` class
- Implement layer classes (Convolution, Pooling, etc.)
- Add tensor shape inference
- Support dynamic shapes

**1.2 Basic Engine Builder**

Create the engine building pipeline:
- Parse network definition
- Allocate device memory
- Build execution graph
- Serialize engine to disk

**Implementation tasks**:
- Implement `IBuilder` class
- Create execution plan data structure
- Add layer-by-layer execution
- Implement engine serialization

**1.3 Runtime Engine**

Build the inference execution engine:
- Load serialized engine
- Create execution context
- Run inference with input tensors
- Handle multiple contexts

**Implementation tasks**:
- Implement `ICudaEngine` class
- Create `IExecutionContext` 
- Add synchronous inference
- Support batch processing

**Skills learned**:
- API design for DL frameworks
- Engine architecture
- CUDA memory management
- Serialization strategies

---

### Phase 2: Graph Optimizations (12-15 hours)

**2.1 Layer Fusion**

Implement common fusion patterns:
- Conv + Bias + ReLU → ConvBiasReLU
- BatchNorm folding into Conv
- Pointwise operation fusion
- Residual connection optimization

**Implementation tasks**:
- Create fusion pattern matching
- Implement Conv-BN fusion
- Add activation fusion
- Test performance improvement

**2.2 Dead Code Elimination**

Remove unused operations:
- Identify unreachable nodes
- Eliminate redundant operations
- Constant folding
- Common subexpression elimination

**Implementation tasks**:
- Implement graph traversal
- Add liveness analysis
- Remove dead nodes
- Fold constant operations

**2.3 Memory Optimization**

Minimize memory footprint:
- Tensor lifetime analysis
- In-place operations
- Memory reuse planning
- Scratch space allocation

**Implementation tasks**:
- Implement lifetime analysis
- Create memory reuse algorithm
- Add in-place optimization
- Measure memory savings

**2.4 Kernel Selection**

Auto-tune kernel implementations:
- Profile multiple implementations
- Select fastest kernel per layer
- Cache auto-tuning results
- Handle different tensor shapes

**Implementation tasks**:
- Implement kernel profiling
- Create kernel registry
- Add auto-tuning framework
- Cache tuning results

**Skills learned**:
- Compiler optimizations for DL
- Pattern matching in graphs
- Performance auto-tuning
- Memory optimization strategies

---

### Phase 3: Mixed Precision (15-18 hours)

**3.1 FP16 Inference**

Implement half-precision inference:
- Convert FP32 operations to FP16
- Handle mixed FP32/FP16 tensors
- Optimize memory bandwidth
- Validate numerical stability

**Implementation tasks**:
- Add FP16 layer implementations
- Implement automatic casting
- Test numerical accuracy
- Benchmark speedup

**3.2 INT8 Quantization**

Build INT8 inference pipeline:
- Symmetric and asymmetric quantization
- Per-tensor and per-channel scales
- Dynamic range calculation
- Quantization-aware layer fusion

**Implementation tasks**:
- Implement quantization operators
- Add scale calculation
- Create quantized layer kernels
- Test accuracy on models

**3.3 Calibration System**

Implement INT8 calibration:
- Collect activation statistics
- Compute optimal scales
- Entropy calibration algorithm
- Percentile-based calibration

**Implementation tasks**:
- Create calibration data loader
- Implement entropy calibrator
- Add min-max calibrator
- Compare calibration methods

**3.4 Mixed Precision Policies**

Optimize precision selection:
- Layer-wise precision selection
- Sensitivity analysis
- Automatic mixed precision
- Accuracy-latency tradeoff

**Implementation tasks**:
- Implement precision profiler
- Create policy selector
- Add sensitivity analysis
- Optimize precision per layer

**Skills learned**:
- Numerical precision tradeoffs
- Quantization techniques
- Calibration algorithms
- Mixed precision strategies

---

### Phase 4: Advanced Features (12-15 hours)

**4.1 Plugin System**

Build custom layer support:
- Plugin interface definition
- Plugin registration system
- Custom kernel integration
- Dynamic plugin loading

**Implementation tasks**:
- Define `IPluginV2` interface
- Implement plugin registry
- Add plugin factory
- Create example plugins

**4.2 Dynamic Shapes**

Support variable input sizes:
- Optimization profiles
- Dynamic shape inference
- Memory reallocation
- Runtime shape binding

**Implementation tasks**:
- Add optimization profiles
- Implement shape inference
- Handle dynamic allocation
- Test variable batch sizes

**4.3 Multi-Stream Execution**

Concurrent inference streams:
- Stream management
- Async execution
- Inter-stream synchronization
- Throughput optimization

**Implementation tasks**:
- Implement stream pool
- Add async inference API
- Handle stream dependencies
- Benchmark throughput

**4.4 Model Parsers**

Import from frameworks:
- ONNX model parsing
- PyTorch model export
- TensorFlow model conversion
- Weight loading

**Implementation tasks**:
- Implement ONNX parser
- Add PyTorch exporter
- Support common operators
- Validate against original

**Skills learned**:
- Extensibility patterns
- Dynamic execution
- Async programming
- Model interoperability

---

**Total Time**: ~50-60 hours for complete implementation

## Features to Implement

### Core Features
- [x] Network definition API
- [x] Engine building pipeline
- [x] Runtime execution
- [x] Multi-context support
- [x] Engine serialization/deserialization

### Optimizations
- [x] Layer fusion (Conv-BN-ReLU, etc.)
- [x] Constant folding
- [x] Memory reuse
- [x] Kernel auto-tuning
- [x] Dead code elimination

### Precision Support
- [x] FP32 (full precision)
- [x] FP16 (half precision)
- [x] INT8 (quantized)
- [x] Mixed precision policies
- [x] Calibration tools

### Advanced Features
- [x] Custom plugins
- [x] Dynamic shapes
- [x] Multi-stream execution
- [x] ONNX/PyTorch/TF parsers
- [x] Profiling and benchmarking

## Testing Your Implementation

### Unit Tests

Test individual components:
```bash
# Test layers
python -m pytest tests/test_layers.py -v

# Test optimizer
python -m pytest tests/test_optimizer.py -v

# Test engine
python -m pytest tests/test_engine.py -v

# Test quantization
python -m pytest tests/test_quantization.py -v
```

### Model Tests

Test with real models:
```bash
# ResNet-50
python tests/models/test_resnet50.py

# BERT
python tests/models/test_bert.py

# YOLOv5
python tests/models/test_yolov5.py

# GPT-2
python tests/models/test_gpt2.py
```

### Benchmarks

Compare with reference implementations:
```bash
# Latency benchmark
python tests/benchmarks/inference_latency.py --model resnet50

# Throughput benchmark
python tests/benchmarks/throughput.py --batch-size 32

# Memory usage
python tests/benchmarks/memory_usage.py

# Optimization impact
python tests/benchmarks/optimization_impact.py
```

## Example Usage

### Basic Inference

```python
import tensorrt_engine as trt

# Create builder
builder = trt.Builder()
network = builder.create_network()

# Define network
input_tensor = network.add_input("input", trt.float32, (1, 3, 224, 224))
conv = network.add_convolution(input_tensor, 64, (3, 3))
relu = network.add_activation(conv, trt.ActivationType.RELU)
pool = network.add_pooling(relu, trt.PoolingType.MAX, (2, 2))
output = network.mark_output(pool)

# Build engine
config = builder.create_builder_config()
config.max_workspace_size = 1 << 30  # 1 GB
engine = builder.build_engine(network, config)

# Run inference
context = engine.create_execution_context()
input_data = load_image("image.jpg")
output_data = context.execute(input_data)
```

### INT8 Calibration

```python
# Create calibrator
calibrator = trt.EntropyCalibrator(
    calibration_dataset,
    cache_file="calibration.cache"
)

# Build INT8 engine
config.set_flag(trt.BuilderFlag.INT8)
config.int8_calibrator = calibrator
engine = builder.build_engine(network, config)

# Run INT8 inference
context = engine.create_execution_context()
output = context.execute(input_data)
```

### Custom Plugin

```python
class MyCustomLayer(trt.IPluginV2):
    def __init__(self, param):
        super().__init__()
        self.param = param
    
    def get_output_shape(self, input_shapes):
        return input_shapes[0]
    
    def execute(self, inputs, outputs, stream):
        # Custom CUDA kernel
        launch_custom_kernel(inputs, outputs, self.param, stream)

# Register plugin
trt.register_plugin("MyCustomLayer", MyCustomLayer)

# Use in network
custom = network.add_plugin_v2([input_tensor], "MyCustomLayer", param=42)
```

## Performance Goals

Your implementation should achieve:

### Latency (vs. PyTorch/TensorFlow)
- ✅ ResNet-50: 2-3x faster
- ✅ BERT-Base: 2-4x faster
- ✅ YOLOv5: 3-5x faster
- ✅ GPT-2: 2-3x faster

### Throughput
- ✅ >1000 images/sec (ResNet-50, batch=32)
- ✅ >500 sequences/sec (BERT-Base, batch=16)
- ✅ >100 FPS (YOLOv5, 1080p video)

### Memory
- ✅ <50% memory usage vs. framework
- ✅ INT8: <30% memory usage
- ✅ Efficient memory reuse (>80%)

### Precision
- ✅ FP32: Exact match with framework
- ✅ FP16: <0.1% accuracy loss
- ✅ INT8: <1% accuracy loss

## Resources

### Papers
- **TensorRT**: "GPU Inference Engine" NVIDIA (2016)
- **Quantization**: "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference" (2018)
- **Mixed Precision**: "Mixed Precision Training" (2018)
- **Graph Optimization**: "TASO: Optimizing Deep Learning Computation with Automatic Generation of Graph Substitutions" (2019)

### Official Documentation
- [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [TensorRT Developer Guide](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/)
- [TensorRT Best Practices](https://docs.nvidia.com/deeplearning/tensorrt/best-practices/)
- [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)

### Related Projects
- [TensorRT](https://github.com/NVIDIA/TensorRT) - Official TensorRT
- [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) - LLM optimization
- [ONNX Runtime](https://github.com/microsoft/onnxruntime) - Cross-platform inference
- [OpenVINO](https://github.com/openvinotoolkit/openvino) - Intel's inference toolkit

### Books & Courses
- "CUDA Programming" by Shane Cook
- "Programming Massively Parallel Processors" by Kirk & Hwu
- NVIDIA Deep Learning Institute courses
- Coursera: GPU Programming

### Video Courses
- [Deep Learning Courses](https://github.com/Developer-Y/cs-video-courses#deep-learning)
- [Computer Organization and Architecture](https://github.com/Developer-Y/cs-video-courses#computer-organization-and-architecture)
- [Systems Programming](https://github.com/Developer-Y/cs-video-courses#systems-programming)

## Common Pitfalls

1. **Incorrect tensor layout**: Use NCHW for GPU, not NHWC
2. **Memory alignment**: Align tensors to 256 bytes for optimal performance
3. **Synchronous operations**: Minimize cudaDeviceSynchronize() calls
4. **Kernel launch overhead**: Fuse operations to reduce kernel launches
5. **Poor calibration data**: Use representative dataset for INT8
6. **Ignoring dynamic shapes**: Test with variable input sizes

## Debug Tips

### Profiling

```bash
# Profile with Nsight Compute
ncu --set full python inference.py

# Profile with Nsight Systems
nsys profile -o profile python inference.py

# Analyze kernel performance
ncu --metrics sm__throughput.avg.pct_of_peak python inference.py
```

### Numerical Debugging

```python
# Compare layer outputs
def compare_outputs(trt_output, pytorch_output):
    diff = abs(trt_output - pytorch_output)
    max_diff = diff.max()
    mean_diff = diff.mean()
    print(f"Max diff: {max_diff}, Mean diff: {mean_diff}")

# Check quantization error
def check_quantization_error(fp32_engine, int8_engine, inputs):
    fp32_out = fp32_engine.execute(inputs)
    int8_out = int8_engine.execute(inputs)
    error = compute_error(fp32_out, int8_out)
    print(f"Quantization error: {error}")
```

### Memory Debugging

```bash
# Check for memory leaks
cuda-memcheck python inference.py

# Profile memory usage
nsys profile --stats=true python inference.py

# Check memory bandwidth
ncu --metrics dram__throughput.avg.pct_of_peak python inference.py
```

## Advanced Topics

After completing the core implementation, explore:

### Advanced Optimizations
- Multi-instance GPU (MIG) support
- DLA (Deep Learning Accelerator) offloading
- Graph rewriting with custom patterns
- Sparse tensor support
- Structured pruning

### Advanced Features
- Multi-model ensemble
- Online model updates
- A/B testing infrastructure
- Automatic batching
- Request scheduling

### Integration
- Triton Inference Server integration
- Kubernetes deployment
- Model versioning
- Monitoring and logging
- Load balancing

## Contributing

This is a learning project focused on understanding inference optimization. Areas for exploration:
- More optimization passes
- Additional layer types
- Better kernel implementations
- Novel quantization methods

## License

Educational purposes. Use freely for learning.

## Acknowledgments

Inspired by:
- NVIDIA TensorRT architecture
- ONNX Runtime optimization strategies
- PyTorch JIT compiler
- TensorFlow XLA compiler
- Modern inference serving systems

## Sources

**Read, do not build** — see [`../README.md`](../README.md) for why.

- The **NVIDIA TensorRT Developer Guide** — layer fusion, precision calibration, kernel auto-tuning. Vendor documentation, and the honest place for it.
- Jacob et al., **"Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference"**, CVPR 2018 — what INT8 calibration is doing.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#not-scheduled--reference)

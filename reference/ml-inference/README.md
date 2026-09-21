# ML Inference from Scratch

This directory contains from-scratch implementations of ML inference systems and optimization techniques.

## Goal
Build high-performance inference systems to understand:
- Model optimization for inference
- Hardware acceleration (GPU, TPU, specialized accelerators)
- Inference serving architectures
- Latency and throughput optimization
- Edge deployment and quantization
- Real-time inference pipelines

## Learning Path

### Phase 1: Basic Inference (Beginner)
1. **Model Loading and Inference**
   - Load different model formats (PyTorch, TensorFlow, ONNX)
   - Single prediction inference
   - Batch inference
   - Input preprocessing and output postprocessing

2. **Performance Profiling**
   - Measure inference latency
   - Identify bottlenecks
   - Memory usage analysis
   - CPU vs GPU performance

### Phase 2: Optimization Techniques (Intermediate)
3. **Model Quantization**
   - Post-training quantization (INT8, FP16)
   - Quantization-aware training
   - Dynamic quantization
   - Measure accuracy vs speed tradeoffs

4. **Model Compilation**
   - Convert to ONNX format
   - TensorRT optimization
   - TorchScript compilation
   - Graph optimization techniques

### Phase 3: Advanced Serving (Advanced)
5. **GPU Inference Optimization**
   - Dynamic batching
   - Concurrent model execution
   - Multi-GPU inference
   - Memory management

6. **Specialized Accelerators**
   - Intel Neural Compute Stick
   - AWS Inferentia
   - Google Coral TPU
   - Apple Neural Engine

### Phase 4: Production Inference System (Hero Level)
7. **Real-Life Application: Real-Time Video Analysis**
   - Deploy object detection at 30+ FPS
   - Multi-model pipeline (detection → tracking → classification)
   - Edge deployment with quantized models
   - GPU server deployment with dynamic batching
   - <50ms p99 latency on edge devices
   - Handle 100+ concurrent video streams on server
   - Adaptive model selection based on hardware

## Project Structure

```
ml-inference/
├── README.md (this file)
├── phase1_basics/
│   ├── template_model_loader.py
│   ├── template_profiler.py
│   └── guidelines.md
├── phase2_optimization/
│   ├── template_quantization.py
│   ├── template_compilation.py
│   └── guidelines.md
├── phase3_advanced/
│   ├── template_gpu_optimization.py
│   ├── template_dynamic_batching.py
│   └── guidelines.md
├── phase4_production/
│   ├── template_video_analysis/
│   └── guidelines.md
└── solutions/
    ├── phase1_basics/
    │   ├── model_loader.py
    │   ├── profiler.py
    │   └── benchmarks/
    ├── phase2_optimization/
    │   ├── quantizer.py
    │   ├── compiler.py
    │   └── performance_comparison.py
    ├── phase3_advanced/
    │   ├── gpu_optimizer.py
    │   ├── dynamic_batcher.py
    │   └── multi_model_server.py
    └── phase4_production/
        ├── video_analysis/
        │   ├── edge_inference.py (for Raspberry Pi, Jetson)
        │   ├── server_inference.py (for GPU servers)
        │   ├── model_pipeline.py
        │   └── adaptive_inference.py
        ├── deployment/
        │   ├── edge_devices/
        │   ├── triton_server/
        │   └── docker/
        └── README.md
```

## Getting Started

1. Start with Phase 1 to understand basic inference
2. Profile before optimizing - measure baseline performance
3. Apply optimizations incrementally and measure impact
4. Test on target hardware early
5. Balance accuracy, latency, and throughput

## Prerequisites

- Python 3.8+
- PyTorch or TensorFlow
- CUDA toolkit (for GPU)
- Understanding of neural network architectures
- Basic performance profiling knowledge

## Testing Your Implementation

```bash
# Phase 1: Basic inference
python template_model_loader.py --model resnet50.pth
python template_profiler.py --model resnet50.pth --iterations 100

# Phase 2: Compare optimizations
python compare_quantization.py
python benchmark_formats.py  # PyTorch vs ONNX vs TensorRT

# Phase 3: GPU optimization
python template_dynamic_batching.py --max-batch-size 32
python gpu_benchmark.py

# Phase 4: Video analysis
python video_analysis/edge_inference.py --video test.mp4 --device jetson
python video_analysis/server_inference.py --streams 100
```

## Hardware Targets

### CPU Inference
- Intel/AMD CPUs
- ARM processors (Raspberry Pi, mobile)
- Optimization: ONNX Runtime, OpenVINO

### GPU Inference
- NVIDIA GPUs
- Optimization: TensorRT, CUDA optimization

### Edge Devices
- Raspberry Pi 4
- NVIDIA Jetson (Nano, Xavier, Orin)
- Google Coral
- Intel Neural Compute Stick

## Optimization Techniques Covered

### Model-Level
- Quantization (INT8, FP16)
- Pruning and distillation
- Architecture optimization (depth, width)
- Operator fusion

### System-Level
- Batching strategies
- Caching
- Concurrent execution
- Memory optimization

### Hardware-Level
- CUDA kernels
- TensorRT optimization
- Hardware-specific compilation
- Memory layout optimization

## Performance Metrics

Key metrics you'll optimize:
- **Latency**: Time for single inference (p50, p99)
- **Throughput**: Inferences per second
- **Memory**: RAM and VRAM usage
- **Accuracy**: Model accuracy after optimization
- **Power**: Energy consumption (for edge devices)

## Resources

**Optimization & Performance**:
- [ONNX Runtime Performance Tuning](https://onnxruntime.ai/docs/performance/)
- [TensorRT Developer Guide](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/)
- [Quantization Papers and Techniques](https://arxiv.org/abs/2004.09602)
- [NVIDIA Triton Inference Server](https://github.com/triton-inference-server)
- [Model Optimization Toolkit](https://github.com/tensorflow/model-optimization)

**Video Courses**:
- [Machine Learning Courses](https://github.com/Developer-Y/cs-video-courses#machine-learning)
- [Deep Learning Courses](https://github.com/Developer-Y/cs-video-courses#deep-learning)
- [Computer Organization and Architecture](https://github.com/Developer-Y/cs-video-courses#computer-organization-and-architecture)

## Common Pitfalls

1. **Over-optimizing without profiling**: Always measure first
2. **Ignoring accuracy degradation**: Monitor model performance
3. **Not testing on target hardware**: CPU optimizations may not transfer to GPU
4. **Premature optimization**: Get it working first, then optimize
5. **Forgetting warmup**: First inference is always slower

## Benchmarking Best Practices

- Warm up the model (run several inferences first)
- Measure multiple runs and report percentiles (p50, p95, p99)
- Test with realistic data distributions
- Measure end-to-end including preprocessing
- Consider batch sizes relevant to your use case

## Note

These implementations are for educational purposes. Production inference systems may require additional optimizations and hardware-specific tuning for maximum performance.

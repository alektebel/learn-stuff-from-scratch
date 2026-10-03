# Phase 2: Model Compilation - Implementation Guide

This guide covers converting and optimizing models through compilation to ONNX, TensorRT, and other optimized formats.

## Table of Contents
1. [Overview](#overview)
2. [ONNX Conversion](#onnx-conversion)
3. [TensorRT Optimization](#tensorrt-optimization)
4. [TorchScript Compilation](#torchscript-compilation)
5. [Graph Optimizations](#graph-optimizations)
6. [Performance Comparison](#performance-comparison)

## Overview

### What is Model Compilation?

Model compilation transforms a model from a high-level framework representation (PyTorch, TensorFlow) into an optimized format for inference.

**Benefits:**
- 🚀 **Performance**: 2-10x faster than native framework
- 🔧 **Optimization**: Graph-level optimizations
- 🌐 **Portability**: Run across different frameworks
- 💻 **Hardware-specific**: Leverages specialized instructions

**Compilation Targets:**
- **ONNX**: Framework-agnostic intermediate format
- **TensorRT**: NVIDIA GPU optimization
- **TorchScript**: PyTorch's JIT compiler
- **OpenVINO**: Intel CPU/VPU optimization
- **TFLite**: Mobile/edge deployment

### Learning Objectives

1. Convert models to ONNX format
2. Optimize with TensorRT for GPU
3. Apply graph-level optimizations
4. Understand compilation tradeoffs
5. Debug compilation issues

## ONNX Conversion

### 2.1 PyTorch to ONNX

**Step-by-Step Implementation:**

```python
import torch
import torch.onnx
import onnx
import onnxruntime as ort

class ONNXConverter:
    """
    Convert PyTorch models to ONNX format.
    
    ONNX is an open format for ML models that enables
    interoperability between different frameworks.
    """
    
    def __init__(self, model, input_shape, device='cpu'):
        """
        Initialize converter.
        
        Args:
            model: PyTorch model to convert
            input_shape: Input tensor shape (batch, channels, height, width)
            device: Device for conversion ('cpu' or 'cuda')
        """
        self.model = model.to(device).eval()
        self.input_shape = input_shape
        self.device = device
    
    def export_to_onnx(
        self,
        output_path,
        opset_version=13,
        dynamic_axes=None,
        simplify=True
    ):
        """
        Export PyTorch model to ONNX.
        
        Args:
            output_path: Where to save the ONNX model
            opset_version: ONNX opset version (11-15 recommended)
            dynamic_axes: Axes with variable dimensions
            simplify: Apply ONNX simplification
        
        Implementation Steps:
        1. Create dummy input
        2. Set model to eval mode
        3. Export using torch.onnx.export()
        4. Validate ONNX model
        5. (Optional) Simplify ONNX graph
        """
        # 1. Create dummy input
        dummy_input = torch.randn(self.input_shape).to(self.device)
        
        # 2. Model should be in eval mode
        self.model.eval()
        
        # 3. Export to ONNX
        with torch.no_grad():
            torch.onnx.export(
                self.model,                      # Model
                dummy_input,                     # Example input
                output_path,                     # Output path
                export_params=True,              # Store trained weights
                opset_version=opset_version,     # ONNX version
                do_constant_folding=True,        # Optimize constants
                input_names=['input'],           # Input name
                output_names=['output'],         # Output name
                dynamic_axes=dynamic_axes        # Dynamic dimensions
            )
        
        print(f"Model exported to {output_path}")
        
        # 4. Validate ONNX model
        self._validate_onnx(output_path)
        
        # 5. Simplify if requested
        if simplify:
            self._simplify_onnx(output_path)
        
        return output_path
    
    def _validate_onnx(self, onnx_path):
        """
        Validate ONNX model.
        
        Checks:
        1. Model structure is valid
        2. All operators are supported
        3. Shapes are correct
        """
        try:
            # Load and check model
            model = onnx.load(onnx_path)
            onnx.checker.check_model(model)
            print("✓ ONNX model is valid")
            
        except Exception as e:
            print(f"✗ ONNX validation failed: {e}")
            raise
    
    def _simplify_onnx(self, onnx_path):
        """
        Simplify ONNX graph using onnx-simplifier.
        
        Benefits:
        - Remove redundant operators
        - Constant folding
        - Dead code elimination
        - Smaller model size
        
        Installation: pip install onnx-simplifier
        """
        try:
            from onnxsim import simplify
            
            # Load model
            model = onnx.load(onnx_path)
            
            # Simplify
            simplified_model, check = simplify(model)
            
            if check:
                # Save simplified model
                onnx.save(simplified_model, onnx_path)
                print("✓ ONNX model simplified")
            else:
                print("✗ Simplification check failed")
                
        except ImportError:
            print("onnx-simplifier not installed, skipping")
```

**Dynamic Axes for Variable Batch Size:**

```python
# Support variable batch size and sequence length
dynamic_axes = {
    'input': {
        0: 'batch_size',      # First dimension is batch
        1: 'sequence_length'  # Second dimension is sequence
    },
    'output': {
        0: 'batch_size'
    }
}

converter.export_to_onnx(
    'model.onnx',
    dynamic_axes=dynamic_axes
)
```

**Opset Version Selection:**

```python
"""
ONNX Opset Versions:
- Opset 9-10: Older, broader compatibility
- Opset 11-12: Good balance
- Opset 13-14: Latest operators, better optimizations
- Opset 15+: Cutting edge

Choose based on:
- Target runtime (ONNX Runtime, TensorRT)
- Required operators
- Compatibility requirements
"""

# Check which opset your operators need
torch.onnx.export(
    model,
    dummy_input,
    'model.onnx',
    opset_version=13,  # Safe default
    verbose=True       # Print operator mapping
)
```

### 2.2 ONNX Runtime Optimization

**Optimize ONNX for Inference:**

```python
class ONNXOptimizer:
    """
    Optimize ONNX models for inference.
    
    Applies graph-level optimizations and creates
    optimized ONNX Runtime sessions.
    """
    
    def __init__(self, onnx_path):
        """
        Initialize optimizer.
        
        Args:
            onnx_path: Path to ONNX model
        """
        self.onnx_path = onnx_path
        self.model = onnx.load(onnx_path)
    
    def optimize_graph(self, output_path=None):
        """
        Apply graph-level optimizations.
        
        Optimizations:
        1. Constant folding
        2. Redundant node elimination
        3. Operator fusion
        4. Layout optimization
        
        Returns:
            Path to optimized model
        """
        from onnxruntime.transformers import optimizer
        
        if output_path is None:
            output_path = self.onnx_path.replace('.onnx', '_optimized.onnx')
        
        # Apply optimizations
        optimized_model = optimizer.optimize_model(
            self.onnx_path,
            model_type='bert',  # or 'gpt2', 'bert', etc.
            num_heads=12,       # For transformer models
            hidden_size=768
        )
        
        # Save optimized model
        optimized_model.save_model_to_file(output_path)
        print(f"Optimized model saved to {output_path}")
        
        return output_path
    
    def create_inference_session(
        self,
        optimization_level='all',
        device='cpu',
        enable_profiling=False
    ):
        """
        Create optimized ONNX Runtime inference session.
        
        Args:
            optimization_level: 'none', 'basic', 'extended', 'all'
            device: 'cpu' or 'cuda'
            enable_profiling: Enable performance profiling
        
        Returns:
            Optimized InferenceSession
        """
        # Session options
        sess_options = ort.SessionOptions()
        
        # Set optimization level
        opt_levels = {
            'none': ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
            'basic': ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
            'extended': ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
            'all': ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        }
        sess_options.graph_optimization_level = opt_levels[optimization_level]
        
        # Enable profiling if requested
        if enable_profiling:
            sess_options.enable_profiling = True
        
        # Execution providers
        if device == 'cuda':
            providers = [
                ('CUDAExecutionProvider', {
                    'device_id': 0,
                    'gpu_mem_limit': 2 * 1024 * 1024 * 1024,  # 2GB
                    'arena_extend_strategy': 'kSameAsRequested',
                }),
                'CPUExecutionProvider'
            ]
        else:
            providers = ['CPUExecutionProvider']
        
        # Create session
        session = ort.InferenceSession(
            self.onnx_path,
            sess_options,
            providers=providers
        )
        
        return session
```

**Graph Optimization Levels:**

```python
"""
ONNX Runtime Optimization Levels:

1. DISABLE_ALL
   - No optimizations
   - Use for debugging only

2. ENABLE_BASIC
   - Constant folding
   - Redundant node elimination
   - Semantic rule-based optimizations
   - Fast, safe optimizations

3. ENABLE_EXTENDED
   - ENABLE_BASIC plus:
   - Node fusions (Conv+BN, etc.)
   - More aggressive optimizations
   - Some compatibility issues possible

4. ENABLE_ALL (Recommended)
   - ENABLE_EXTENDED plus:
   - Layout optimizations
   - Global optimizations
   - Maximum performance
"""
```

## TensorRT Optimization

### 3.1 ONNX to TensorRT

**High-Performance GPU Inference:**

```python
import tensorrt as trt

class TensorRTConverter:
    """
    Convert ONNX models to TensorRT engines.
    
    TensorRT provides maximum performance on NVIDIA GPUs
    through aggressive optimizations and kernel fusion.
    """
    
    def __init__(self, onnx_path, precision='fp16'):
        """
        Initialize TensorRT converter.
        
        Args:
            onnx_path: Path to ONNX model
            precision: 'fp32', 'fp16', or 'int8'
        """
        self.onnx_path = onnx_path
        self.precision = precision
        
        # Create TensorRT logger
        self.logger = trt.Logger(trt.Logger.WARNING)
    
    def build_engine(
        self,
        engine_path,
        max_batch_size=32,
        workspace_size=4,  # GB
        calibration_data=None
    ):
        """
        Build TensorRT engine from ONNX model.
        
        Args:
            engine_path: Where to save the engine
            max_batch_size: Maximum batch size for inference
            workspace_size: GPU memory for optimization (GB)
            calibration_data: Data for INT8 calibration
        
        Steps:
        1. Create builder and network
        2. Parse ONNX model
        3. Set precision mode
        4. Configure optimization
        5. Build and serialize engine
        """
        # 1. Create builder
        builder = trt.Builder(self.logger)
        network = builder.create_network(
            1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        )
        parser = trt.OnnxParser(network, self.logger)
        
        # 2. Parse ONNX
        with open(self.onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                raise RuntimeError("Failed to parse ONNX model")
        
        # 3. Configure builder
        config = builder.create_builder_config()
        
        # Workspace size (memory for optimization)
        config.max_workspace_size = workspace_size * (1 << 30)  # GB to bytes
        
        # Set precision
        if self.precision == 'fp16':
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)
                print("✓ FP16 mode enabled")
            else:
                print("✗ FP16 not supported on this GPU")
        
        elif self.precision == 'int8':
            if builder.platform_has_fast_int8:
                config.set_flag(trt.BuilderFlag.INT8)
                # INT8 requires calibration
                if calibration_data is None:
                    raise ValueError("INT8 requires calibration data")
                config.int8_calibrator = self._create_calibrator(calibration_data)
                print("✓ INT8 mode enabled")
            else:
                print("✗ INT8 not supported on this GPU")
        
        # 4. Build engine
        print("Building TensorRT engine... (this may take a while)")
        engine = builder.build_engine(network, config)
        
        if engine is None:
            raise RuntimeError("Failed to build TensorRT engine")
        
        # 5. Serialize and save
        with open(engine_path, 'wb') as f:
            f.write(engine.serialize())
        
        print(f"✓ TensorRT engine saved to {engine_path}")
        
        return engine
```

**INT8 Calibration for TensorRT:**

```python
class Int8Calibrator(trt.IInt8EntropyCalibrator2):
    """
    Calibrator for INT8 quantization in TensorRT.
    
    Collects activation statistics to determine
    optimal quantization parameters.
    """
    
    def __init__(
        self,
        calibration_loader,
        cache_file='calibration.cache'
    ):
        """
        Initialize calibrator.
        
        Args:
            calibration_loader: DataLoader with calibration data
            cache_file: Where to cache calibration results
        """
        super().__init__()
        self.calibration_loader = calibration_loader
        self.cache_file = cache_file
        self.current_index = 0
        
        # Convert calibration data to list
        self.data = [batch for batch in calibration_loader]
        
        # Allocate device memory for one batch
        self.device_input = None
    
    def get_batch_size(self):
        """Return batch size used for calibration."""
        return self.data[0].shape[0]
    
    def get_batch(self, names):
        """
        Get next calibration batch.
        
        Called by TensorRT during calibration.
        """
        if self.current_index < len(self.data):
            batch = self.data[self.current_index]
            self.current_index += 1
            
            # Allocate GPU memory if needed
            if self.device_input is None:
                import pycuda.driver as cuda
                self.device_input = cuda.mem_alloc(batch.nbytes)
            
            # Copy to GPU
            import pycuda.driver as cuda
            cuda.memcpy_htod(self.device_input, batch)
            
            return [int(self.device_input)]
        
        return None
    
    def read_calibration_cache(self):
        """
        Read cached calibration data.
        
        Allows reusing calibration results.
        """
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                return f.read()
        return None
    
    def write_calibration_cache(self, cache):
        """Write calibration cache to file."""
        with open(self.cache_file, 'wb') as f:
            f.write(cache)
```

**TensorRT Inference:**

```python
class TensorRTInference:
    """
    Run inference using TensorRT engine.
    
    Provides optimized inference with TensorRT.
    """
    
    def __init__(self, engine_path):
        """
        Load TensorRT engine.
        
        Args:
            engine_path: Path to serialized engine
        """
        self.logger = trt.Logger(trt.Logger.WARNING)
        
        # Load engine
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        # Create execution context
        self.context = self.engine.create_execution_context()
        
        # Get input/output info
        self.input_shape = self.engine.get_binding_shape(0)
        self.output_shape = self.engine.get_binding_shape(1)
    
    def infer(self, input_data):
        """
        Run inference on input data.
        
        Args:
            input_data: NumPy array or torch tensor
        
        Returns:
            Output predictions
        """
        import pycuda.driver as cuda
        import pycuda.autoinit
        
        # Convert to numpy if needed
        if torch.is_tensor(input_data):
            input_data = input_data.cpu().numpy()
        
        # Allocate GPU memory
        input_mem = cuda.mem_alloc(input_data.nbytes)
        output = np.empty(self.output_shape, dtype=np.float32)
        output_mem = cuda.mem_alloc(output.nbytes)
        
        # Copy input to GPU
        cuda.memcpy_htod(input_mem, input_data)
        
        # Run inference
        bindings = [int(input_mem), int(output_mem)]
        self.context.execute_v2(bindings)
        
        # Copy output back
        cuda.memcpy_dtoh(output, output_mem)
        
        return output
```

## TorchScript Compilation

### 4.1 Tracing vs Scripting

**Two Methods to Create TorchScript:**

```python
class TorchScriptCompiler:
    """
    Compile PyTorch models to TorchScript.
    
    TorchScript is PyTorch's JIT compiler that
    optimizes models for production deployment.
    """
    
    def __init__(self, model):
        """
        Initialize compiler.
        
        Args:
            model: PyTorch model to compile
        """
        self.model = model.eval()
    
    def trace(self, example_input):
        """
        Create TorchScript via tracing.
        
        Tracing:
        - Records operations during execution
        - Fast and simple
        - No control flow (if/for) support
        - Best for feedforward models
        
        Args:
            example_input: Example input tensor
        
        Returns:
            Traced TorchScript model
        """
        with torch.no_grad():
            traced_model = torch.jit.trace(
                self.model,
                example_input,
                strict=False  # Allow some flexibility
            )
        
        print("✓ Model traced successfully")
        return traced_model
    
    def script(self):
        """
        Create TorchScript via scripting.
        
        Scripting:
        - Analyzes Python code
        - Supports control flow
        - More complex
        - Best for models with if/for statements
        
        Returns:
            Scripted TorchScript model
        """
        scripted_model = torch.jit.script(self.model)
        
        print("✓ Model scripted successfully")
        return scripted_model
    
    def optimize_for_inference(self, scripted_model):
        """
        Apply TorchScript optimizations.
        
        Optimizations:
        - Constant folding
        - Dead code elimination
        - Operator fusion
        - Loop unrolling
        """
        # Freeze parameters (more optimizations possible)
        frozen_model = torch.jit.freeze(scripted_model)
        
        # Optimize for inference
        optimized_model = torch.jit.optimize_for_inference(frozen_model)
        
        return optimized_model
```

**When to Use Tracing vs Scripting:**

```python
# Use TRACING for:
# - Simple feedforward models
# - CNNs without dynamic behavior
# - When you want maximum speed

class SimpleCNN(nn.Module):
    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        return x

# Trace it
traced = torch.jit.trace(model, example_input)

# Use SCRIPTING for:
# - Models with if statements
# - Models with loops
# - RNNs with variable lengths

class DynamicModel(nn.Module):
    def forward(self, x):
        if x.size(0) > 1:  # Control flow!
            x = self.layer1(x)
        else:
            x = self.layer2(x)
        return x

# Script it
scripted = torch.jit.script(model)
```

## Graph Optimizations

### 5.1 Operator Fusion

**Fuse Multiple Operations:**

```python
def demonstrate_operator_fusion():
    """
    Operator fusion combines multiple operations
    into a single kernel for better performance.
    
    Common fusions:
    - Conv + BatchNorm + ReLU → Single fused operation
    - MatMul + Add → Fused GEMM
    - Multiple element-wise ops → Single kernel
    """
    
    # Before fusion (3 operations)
    x = conv(input)    # GPU kernel 1
    x = bn(x)          # GPU kernel 2
    x = relu(x)        # GPU kernel 3
    
    # After fusion (1 operation)
    x = conv_bn_relu_fused(input)  # GPU kernel 1 (fused)
    
    # Benefits:
    # - Fewer kernel launches (overhead reduction)
    # - Better memory locality
    # - Reduced intermediate storage
    # - 2-3x faster for small layers
```

**Manual Fusion in PyTorch:**

```python
def fuse_conv_bn_relu(conv, bn, relu=True):
    """
    Manually fuse Conv+BN+ReLU.
    
    Combines operations for inference efficiency.
    """
    # Fuse Conv and BN
    fused_conv = torch.nn.Conv2d(
        conv.in_channels,
        conv.out_channels,
        conv.kernel_size,
        conv.stride,
        conv.padding,
        bias=True  # Will absorb BN bias
    )
    
    # Calculate fused parameters
    bn_var_rsqrt = torch.rsqrt(bn.running_var + bn.eps)
    
    # Fuse weights: w_fused = w_conv * (gamma / sqrt(var + eps))
    fused_conv.weight.data = conv.weight * (
        (bn.weight * bn_var_rsqrt).reshape(-1, 1, 1, 1)
    )
    
    # Fuse bias: b_fused = (b_conv - mean) * gamma / sqrt(var + eps) + beta
    if conv.bias is not None:
        fused_conv.bias.data = (
            (conv.bias - bn.running_mean) * bn.weight * bn_var_rsqrt + bn.bias
        )
    else:
        fused_conv.bias.data = (
            -bn.running_mean * bn.weight * bn_var_rsqrt + bn.bias
        )
    
    return fused_conv
```

### 5.2 Constant Folding

**Precompute Constants:**

```python
# Before constant folding
def forward(self, x):
    scale = 0.5 * 2.0  # Computed every forward pass
    x = x * scale
    return x

# After constant folding
def forward(self, x):
    scale = 1.0  # Precomputed at compile time
    x = x * scale  # Or even just: return x
    return x
```

## Performance Comparison

### 6.1 Comprehensive Benchmark

**Compare All Compilation Methods:**

```python
def benchmark_compilation_methods(model, input_shape):
    """
    Compare performance across different formats.
    
    Tests:
    1. PyTorch (baseline)
    2. TorchScript (traced)
    3. ONNX Runtime
    4. TensorRT (FP32)
    5. TensorRT (FP16)
    6. TensorRT (INT8)
    """
    results = {}
    dummy_input = torch.randn(input_shape)
    
    # 1. PyTorch baseline
    results['pytorch'] = benchmark_model(model, dummy_input)
    
    # 2. TorchScript
    traced = torch.jit.trace(model, dummy_input)
    results['torchscript'] = benchmark_model(traced, dummy_input)
    
    # 3. ONNX Runtime
    onnx_path = 'model.onnx'
    torch.onnx.export(model, dummy_input, onnx_path)
    ort_session = ort.InferenceSession(onnx_path)
    results['onnx'] = benchmark_onnx(ort_session, dummy_input.numpy())
    
    # 4-6. TensorRT (if available)
    if has_tensorrt():
        # FP32
        trt_fp32 = build_tensorrt_engine(onnx_path, precision='fp32')
        results['tensorrt_fp32'] = benchmark_tensorrt(trt_fp32, dummy_input)
        
        # FP16
        trt_fp16 = build_tensorrt_engine(onnx_path, precision='fp16')
        results['tensorrt_fp16'] = benchmark_tensorrt(trt_fp16, dummy_input)
        
        # INT8 (with calibration)
        trt_int8 = build_tensorrt_engine(
            onnx_path,
            precision='int8',
            calibration_data=create_calibration_data()
        )
        results['tensorrt_int8'] = benchmark_tensorrt(trt_int8, dummy_input)
    
    return results
```

**Expected Results:**

```
Format              │ Latency  │ Speedup │ GPU Util │ Notes
────────────────────┼──────────┼─────────┼──────────┼────────────────────
PyTorch (baseline)  │  4.2 ms  │  1.0x   │   65%    │ Framework overhead
TorchScript         │  3.8 ms  │  1.1x   │   68%    │ JIT optimizations
ONNX Runtime        │  3.5 ms  │  1.2x   │   70%    │ Graph optimizations
TensorRT FP32       │  2.1 ms  │  2.0x   │   85%    │ Kernel fusion
TensorRT FP16       │  1.3 ms  │  3.2x   │   90%    │ Tensor Cores
TensorRT INT8       │  0.9 ms  │  4.7x   │   92%    │ Maximum performance
```

## Expected Outcomes

After completing Phase 2 Compilation, you should achieve:

### Performance Targets
- **ONNX Runtime**: 1.2-1.5x faster than PyTorch
- **TensorRT FP16**: 2-4x faster than PyTorch
- **TensorRT INT8**: 3-8x faster than PyTorch

### Understanding
- ✅ Convert models to different formats
- ✅ Understand compilation tradeoffs
- ✅ Debug compilation issues
- ✅ Choose appropriate format for deployment

## Next Steps

Phase 3 covers advanced GPU optimizations:
- Dynamic batching
- Multi-GPU inference
- Memory optimization
- Concurrent execution

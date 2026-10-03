# Phase 1: Basic Inference - Implementation Guide

This guide provides comprehensive instructions for implementing basic ML inference from scratch. You'll learn to load models, run inference, and measure performance.

## Table of Contents
1. [Overview](#overview)
2. [Model Loading](#model-loading)
3. [Inference Execution](#inference-execution)
4. [Performance Profiling](#performance-profiling)
5. [Testing Strategy](#testing-strategy)

## Overview

### What You'll Build

A robust inference system that can:
- Load models from multiple frameworks (PyTorch, TensorFlow, ONNX)
- Execute inference with single inputs and batches
- Measure and report performance metrics
- Profile memory usage and bottlenecks
- Compare CPU vs GPU performance

### Key Learning Objectives

1. Understand model serialization formats
2. Learn inference vs training mode differences
3. Master performance measurement techniques
4. Identify computational bottlenecks
5. Optimize data preprocessing pipelines

### Prerequisites

- Python 3.8+
- PyTorch 2.0+ or TensorFlow 2.x
- NumPy, Pillow for data handling
- Basic understanding of neural networks

## Model Loading

### 1.1 PyTorch Model Loader

**Objective**: Load PyTorch models from checkpoint files and prepare for inference.

#### Implementation Steps

```python
class PyTorchModelLoader:
    """Load and prepare PyTorch models for inference."""
    
    def __init__(self, device='cpu'):
        """
        Initialize the loader.
        
        Args:
            device: 'cpu' or 'cuda'
        """
        # TODO: Implement initialization
        # 1. Store device
        # 2. Check if CUDA is available if device='cuda'
        # 3. Set up logging
```

**Key Implementation Details:**

1. **Device Selection**
   ```python
   # Check CUDA availability
   if device == 'cuda' and not torch.cuda.is_available():
       raise ValueError("CUDA not available")
   
   # Create device object
   self.device = torch.device(device)
   ```

2. **Loading Model Weights**
   ```python
   def load_model(self, model_class, checkpoint_path):
       """
       Load model from checkpoint.
       
       Steps:
       1. Instantiate model architecture
       2. Load state dict from checkpoint
       3. Move model to device
       4. Set to evaluation mode
       5. (Optional) Disable gradient computation
       """
       # Instantiate model
       model = model_class()
       
       # Load checkpoint
       checkpoint = torch.load(checkpoint_path, map_location=self.device)
       
       # Handle different checkpoint formats
       if 'state_dict' in checkpoint:
           state_dict = checkpoint['state_dict']
       elif 'model' in checkpoint:
           state_dict = checkpoint['model']
       else:
           state_dict = checkpoint
       
       # Load weights
       model.load_state_dict(state_dict)
       
       # Prepare for inference
       model.to(self.device)
       model.eval()
       
       return model
   ```

3. **TorchScript Loading** (Optional)
   ```python
   def load_torchscript(self, model_path):
       """
       Load TorchScript optimized model.
       
       TorchScript models are pre-compiled and faster to load.
       """
       model = torch.jit.load(model_path, map_location=self.device)
       model.eval()
       return model
   ```

**Common Pitfalls:**

- ❌ Forgetting `model.eval()` → BatchNorm/Dropout behave incorrectly
- ❌ Not handling different checkpoint formats → KeyError
- ❌ Loading on GPU when CUDA unavailable → RuntimeError
- ❌ Keeping gradients enabled → Memory waste

**Testing:**

```python
def test_model_loading():
    """Test PyTorch model loading."""
    loader = PyTorchModelLoader(device='cpu')
    
    # Test 1: Load ResNet18
    from torchvision.models import resnet18
    model = loader.load_model(resnet18, 'resnet18.pth')
    assert model is not None
    assert model.training == False  # Should be in eval mode
    
    # Test 2: Verify device placement
    first_param = next(model.parameters())
    assert str(first_param.device) == 'cpu'
```

### 1.2 ONNX Model Loader

**Objective**: Load ONNX models for cross-framework inference.

#### Implementation Steps

```python
import onnxruntime as ort

class ONNXModelLoader:
    """Load and prepare ONNX models for inference."""
    
    def __init__(self, device='cpu', optimization_level='all'):
        """
        Initialize ONNX Runtime session.
        
        Args:
            device: 'cpu' or 'cuda'
            optimization_level: 'none', 'basic', 'extended', 'all'
        """
        # TODO: Set up ONNX Runtime session options
        pass
    
    def load_model(self, model_path):
        """
        Load ONNX model and create inference session.
        
        Steps:
        1. Create SessionOptions
        2. Set optimization level
        3. Configure execution providers (CPU/CUDA)
        4. Create InferenceSession
        5. Extract input/output metadata
        """
        # Session options
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = \
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Execution providers
        if self.device == 'cuda':
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        else:
            providers = ['CPUExecutionProvider']
        
        # Create session
        session = ort.InferenceSession(
            model_path,
            sess_options,
            providers=providers
        )
        
        # Get input/output info
        self.input_name = session.get_inputs()[0].name
        self.input_shape = session.get_inputs()[0].shape
        self.output_name = session.get_outputs()[0].name
        
        return session
```

**Key Concepts:**

1. **Execution Providers**: Backend engines for inference
   - CPU: Basic CPU execution
   - CUDA: NVIDIA GPU acceleration
   - TensorRT: NVIDIA optimized engine
   - OpenVINO: Intel optimization

2. **Graph Optimization**: ONNX Runtime optimizations
   - **None**: No optimization (debugging)
   - **Basic**: Constant folding, common subexpression elimination
   - **Extended**: More aggressive optimizations
   - **All**: Maximum optimization (recommended for production)

3. **Dynamic Shapes**: Handle variable batch sizes
   ```python
   # Check if input shape is dynamic
   if any(isinstance(dim, str) for dim in input_shape):
       print("Model supports dynamic batch size")
   ```

**Performance Considerations:**

- ONNX Runtime is often faster than native PyTorch/TensorFlow
- Graph optimizations can provide 10-30% speedup
- CUDAExecutionProvider requires proper CUDA installation

### 1.3 TensorFlow Model Loader

**Objective**: Load TensorFlow/Keras models.

```python
import tensorflow as tf

class TensorFlowModelLoader:
    """Load TensorFlow/Keras models."""
    
    def load_saved_model(self, model_path):
        """
        Load TensorFlow SavedModel format.
        
        Steps:
        1. Use tf.saved_model.load()
        2. Extract inference function
        3. Get input/output signatures
        """
        model = tf.saved_model.load(model_path)
        infer = model.signatures['serving_default']
        return infer
    
    def load_keras_model(self, model_path):
        """
        Load Keras .h5 or SavedModel format.
        
        Simpler than SavedModel, commonly used for Keras models.
        """
        model = tf.keras.models.load_model(model_path)
        return model
```

**TensorFlow-Specific Considerations:**

1. **Eager vs Graph Mode**
   - Eager: Easier debugging, slower
   - Graph: Faster, production-ready
   - Use `@tf.function` decorator for graph mode

2. **GPU Memory Management**
   ```python
   # Allow memory growth to avoid OOM
   gpus = tf.config.list_physical_devices('GPU')
   if gpus:
       for gpu in gpus:
           tf.config.experimental.set_memory_growth(gpu, True)
   ```

## Inference Execution

### 2.1 Single Input Inference

**Objective**: Run inference on a single image/input.

```python
class InferenceEngine:
    """Execute inference on loaded models."""
    
    def __init__(self, model, device='cpu', framework='pytorch'):
        """
        Initialize inference engine.
        
        Args:
            model: Loaded model
            device: Execution device
            framework: 'pytorch', 'onnx', or 'tensorflow'
        """
        self.model = model
        self.device = device
        self.framework = framework
    
    def predict_single(self, input_data):
        """
        Run inference on single input.
        
        Steps:
        1. Preprocess input (if needed)
        2. Convert to appropriate tensor format
        3. Move to device
        4. Run inference with no_grad()
        5. Postprocess output
        6. Return result
        """
        # Implementation depends on framework
        if self.framework == 'pytorch':
            return self._pytorch_predict(input_data)
        elif self.framework == 'onnx':
            return self._onnx_predict(input_data)
        elif self.framework == 'tensorflow':
            return self._tensorflow_predict(input_data)
    
    def _pytorch_predict(self, input_data):
        """PyTorch-specific inference."""
        with torch.no_grad():
            # Convert to tensor
            if not isinstance(input_data, torch.Tensor):
                input_tensor = torch.from_numpy(input_data)
            else:
                input_tensor = input_data
            
            # Add batch dimension if needed
            if input_tensor.ndim == 3:  # HWC or CHW
                input_tensor = input_tensor.unsqueeze(0)
            
            # Move to device
            input_tensor = input_tensor.to(self.device)
            
            # Inference
            output = self.model(input_tensor)
            
            # Move back to CPU for postprocessing
            output = output.cpu().numpy()
            
            return output
```

**Preprocessing Pipeline:**

```python
def preprocess_image(image_path, target_size=(224, 224)):
    """
    Standard image preprocessing for vision models.
    
    Steps:
    1. Load image
    2. Resize to target size
    3. Convert to RGB (if needed)
    4. Normalize (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    5. Transpose to CHW format (PyTorch convention)
    """
    from PIL import Image
    import numpy as np
    
    # Load and resize
    img = Image.open(image_path).convert('RGB')
    img = img.resize(target_size)
    
    # To numpy array (HWC format)
    img_array = np.array(img).astype(np.float32) / 255.0
    
    # Normalize (ImageNet stats)
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    img_array = (img_array - mean) / std
    
    # HWC -> CHW
    img_array = np.transpose(img_array, (2, 0, 1))
    
    return img_array
```

### 2.2 Batch Inference

**Objective**: Process multiple inputs efficiently.

```python
def predict_batch(self, input_batch):
    """
    Run inference on batch of inputs.
    
    Batch inference is more efficient than processing one-by-one
    because it amortizes overhead and utilizes hardware parallelism.
    
    Args:
        input_batch: List or array of inputs
    
    Returns:
        Batch of predictions
    """
    if self.framework == 'pytorch':
        with torch.no_grad():
            # Stack inputs into batch
            if isinstance(input_batch, list):
                batch_tensor = torch.stack([
                    torch.from_numpy(x) if isinstance(x, np.ndarray) else x
                    for x in input_batch
                ])
            else:
                batch_tensor = torch.from_numpy(input_batch)
            
            # Move to device
            batch_tensor = batch_tensor.to(self.device)
            
            # Inference
            output = self.model(batch_tensor)
            
            return output.cpu().numpy()
```

**Batch Size Selection:**

```python
def find_optimal_batch_size(model, input_shape, device='cuda'):
    """
    Find optimal batch size through binary search.
    
    Start with large batch size and decrease until it fits in memory.
    """
    max_batch_size = 256
    min_batch_size = 1
    
    while min_batch_size < max_batch_size:
        batch_size = (min_batch_size + max_batch_size + 1) // 2
        
        try:
            # Try inference with this batch size
            dummy_input = torch.randn(batch_size, *input_shape).to(device)
            with torch.no_grad():
                _ = model(dummy_input)
            
            # Success - try larger
            min_batch_size = batch_size
            
        except RuntimeError as e:
            if 'out of memory' in str(e):
                # OOM - try smaller
                max_batch_size = batch_size - 1
                torch.cuda.empty_cache()
            else:
                raise e
    
    return min_batch_size
```

**Batch Processing Best Practices:**

1. **Use DataLoader** for automatic batching:
   ```python
   from torch.utils.data import DataLoader, Dataset
   
   dataloader = DataLoader(
       dataset,
       batch_size=32,
       num_workers=4,  # Parallel data loading
       pin_memory=True  # Faster GPU transfer
   )
   ```

2. **Handle remainder** when dataset size not divisible by batch size:
   ```python
   for batch in dataloader:
       predictions = model(batch)
       # Last batch may be smaller
   ```

## Performance Profiling

### 3.1 Latency Measurement

**Objective**: Accurately measure inference time.

```python
class PerformanceProfiler:
    """Profile model inference performance."""
    
    def __init__(self, model, input_shape, device='cpu'):
        self.model = model
        self.input_shape = input_shape
        self.device = device
    
    def measure_latency(self, num_iterations=100, warmup=10):
        """
        Measure inference latency with proper methodology.
        
        Args:
            num_iterations: Number of iterations to measure
            warmup: Number of warmup iterations (discarded)
        
        Returns:
            Dictionary with latency statistics
        """
        # Create dummy input
        dummy_input = self._create_dummy_input()
        
        # Warmup phase (first few iterations are slower)
        print(f"Warming up with {warmup} iterations...")
        for _ in range(warmup):
            _ = self.model(dummy_input)
            if self.device == 'cuda':
                torch.cuda.synchronize()  # Wait for GPU
        
        # Measurement phase
        print(f"Measuring latency over {num_iterations} iterations...")
        latencies = []
        
        for _ in range(num_iterations):
            # Start timing
            if self.device == 'cuda':
                start_event = torch.cuda.Event(enable_timing=True)
                end_event = torch.cuda.Event(enable_timing=True)
                start_event.record()
            else:
                start_time = time.perf_counter()
            
            # Inference
            _ = self.model(dummy_input)
            
            # End timing
            if self.device == 'cuda':
                end_event.record()
                torch.cuda.synchronize()
                latency = start_event.elapsed_time(end_event)  # milliseconds
            else:
                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000  # convert to ms
            
            latencies.append(latency)
        
        # Calculate statistics
        return self._calculate_statistics(latencies)
    
    def _calculate_statistics(self, latencies):
        """Calculate latency statistics."""
        latencies = np.array(latencies)
        
        return {
            'mean': np.mean(latencies),
            'median': np.median(latencies),
            'std': np.std(latencies),
            'min': np.min(latencies),
            'max': np.max(latencies),
            'p50': np.percentile(latencies, 50),
            'p95': np.percentile(latencies, 95),
            'p99': np.percentile(latencies, 99),
            'all_latencies': latencies
        }
```

**Key Measurement Principles:**

1. **Warmup is Critical**
   - First inference is always slower
   - GPU needs to initialize kernels
   - CPU caches need to warm up
   - Typical warmup: 10-50 iterations

2. **Synchronization for GPU**
   - GPU operations are asynchronous
   - Must call `torch.cuda.synchronize()` before timing
   - Use CUDA Events for accurate timing

3. **Statistical Reporting**
   - Report percentiles (p50, p95, p99), not just mean
   - p99 latency critical for production systems
   - Standard deviation indicates variance

### 3.2 Throughput Measurement

**Objective**: Measure requests per second.

```python
def measure_throughput(self, batch_sizes=[1, 2, 4, 8, 16, 32], duration=10):
    """
    Measure throughput at different batch sizes.
    
    Args:
        batch_sizes: List of batch sizes to test
        duration: Measurement duration in seconds
    
    Returns:
        Dictionary mapping batch_size -> throughput (FPS)
    """
    results = {}
    
    for batch_size in batch_sizes:
        print(f"Testing batch size: {batch_size}")
        
        # Create batched input
        dummy_input = self._create_dummy_input(batch_size)
        
        # Warmup
        for _ in range(10):
            _ = self.model(dummy_input)
            if self.device == 'cuda':
                torch.cuda.synchronize()
        
        # Measure
        num_processed = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            _ = self.model(dummy_input)
            if self.device == 'cuda':
                torch.cuda.synchronize()
            num_processed += batch_size
        
        elapsed = time.time() - start_time
        throughput = num_processed / elapsed
        
        results[batch_size] = {
            'throughput_fps': throughput,
            'latency_ms': (elapsed / num_processed) * 1000
        }
    
    return results
```

**Throughput vs Latency Tradeoff:**

```
Batch Size │ Latency (ms) │ Throughput (FPS)
───────────┼──────────────┼─────────────────
    1      │     5.2      │      192
    2      │     6.1      │      328
    4      │     7.8      │      513
    8      │    11.2      │      714
   16      │    19.5      │      821
   32      │    35.8      │      894

Observation:
- Larger batches = higher throughput
- Larger batches = higher latency
- Diminishing returns at large batch sizes
```

### 3.3 Memory Profiling

**Objective**: Monitor memory usage during inference.

```python
def profile_memory(self):
    """
    Profile memory usage during inference.
    
    Measures:
    - Model parameter memory
    - Activation memory
    - Peak memory usage
    - Memory allocated vs reserved
    """
    results = {}
    
    # Model memory
    param_memory = sum(p.numel() * p.element_size() 
                      for p in self.model.parameters()) / (1024**2)
    results['model_memory_mb'] = param_memory
    
    if self.device == 'cuda':
        # Reset peak stats
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()
        
        # Initial memory
        initial_memory = torch.cuda.memory_allocated() / (1024**2)
        
        # Run inference
        dummy_input = self._create_dummy_input()
        _ = self.model(dummy_input)
        torch.cuda.synchronize()
        
        # Peak memory
        peak_memory = torch.cuda.max_memory_allocated() / (1024**2)
        current_memory = torch.cuda.memory_allocated() / (1024**2)
        reserved_memory = torch.cuda.memory_reserved() / (1024**2)
        
        results['gpu_memory'] = {
            'initial_mb': initial_memory,
            'peak_mb': peak_memory,
            'current_mb': current_memory,
            'reserved_mb': reserved_memory,
            'activation_mb': peak_memory - param_memory
        }
    
    return results
```

**Memory Optimization Tips:**

1. **Use `torch.no_grad()`**: Disables gradient computation
2. **Clear cache**: `torch.cuda.empty_cache()` between runs
3. **Use smaller batch sizes**: Reduce memory footprint
4. **Mixed precision**: Use FP16 to halve memory usage

## Testing Strategy

### Unit Tests

```python
import unittest

class TestInference(unittest.TestCase):
    """Test inference functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.model = create_test_model()
        self.engine = InferenceEngine(self.model, device='cpu')
    
    def test_single_inference(self):
        """Test single input inference."""
        input_data = np.random.randn(3, 224, 224).astype(np.float32)
        output = self.engine.predict_single(input_data)
        
        # Verify output shape
        self.assertEqual(output.shape[0], 1)
        self.assertEqual(output.shape[1], 1000)  # ImageNet classes
    
    def test_batch_inference(self):
        """Test batch inference."""
        batch = [np.random.randn(3, 224, 224).astype(np.float32) 
                for _ in range(4)]
        output = self.engine.predict_batch(batch)
        
        # Verify batch processing
        self.assertEqual(output.shape[0], 4)
    
    def test_latency_measurement(self):
        """Test latency profiling."""
        profiler = PerformanceProfiler(self.model, (3, 224, 224))
        stats = profiler.measure_latency(num_iterations=10, warmup=2)
        
        # Verify statistics
        self.assertIn('mean', stats)
        self.assertIn('p99', stats)
        self.assertGreater(stats['mean'], 0)
```

### Integration Tests

```python
def test_full_pipeline():
    """Test complete inference pipeline."""
    # 1. Load model
    loader = PyTorchModelLoader(device='cpu')
    model = loader.load_model(resnet18, 'resnet18.pth')
    
    # 2. Create engine
    engine = InferenceEngine(model, device='cpu')
    
    # 3. Preprocess image
    image = preprocess_image('test.jpg')
    
    # 4. Run inference
    output = engine.predict_single(image)
    
    # 5. Postprocess
    predicted_class = np.argmax(output)
    
    # Verify end-to-end
    assert 0 <= predicted_class < 1000
```

## Expected Outcomes

After completing Phase 1, your implementation should achieve:

### Functionality
- ✅ Load PyTorch, ONNX, and TensorFlow models
- ✅ Run single and batch inference
- ✅ Accurate latency measurements (<5% variance)
- ✅ Memory profiling on CPU and GPU

### Performance
- **ResNet50 on CPU**: 30-50ms per image
- **ResNet50 on GPU (V100)**: 3-5ms per image
- **Batch throughput**: 3-5x better than single inference

### Code Quality
- Clean, modular code structure
- Comprehensive error handling
- Unit tests with >80% coverage
- Clear documentation

## Next Steps

Move to Phase 2 to learn optimization techniques:
- Model quantization (INT8, FP16)
- Model compilation (ONNX, TensorRT)
- Graph optimizations
- Accuracy vs speed tradeoffs

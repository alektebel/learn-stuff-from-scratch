# Phase 2: Model Quantization - Implementation Guide

This guide provides comprehensive instructions for implementing model quantization techniques to optimize inference performance.

## Table of Contents
1. [Overview](#overview)
2. [Quantization Fundamentals](#quantization-fundamentals)
3. [Post-Training Quantization](#post-training-quantization)
4. [Quantization-Aware Training](#quantization-aware-training)
5. [Framework-Specific Implementation](#framework-specific-implementation)
6. [Accuracy Analysis](#accuracy-analysis)
7. [Testing Strategy](#testing-strategy)

## Overview

### What is Quantization?

Quantization is the process of reducing the precision of model weights and activations from floating-point (FP32) to lower precision formats (INT8, FP16).

**Benefits:**
- 🚀 **Speed**: 2-4x faster inference
- 💾 **Size**: 4x smaller models (FP32→INT8)
- ⚡ **Power**: Lower energy consumption
- 📱 **Deployment**: Enables edge device deployment

**Tradeoffs:**
- ⚠️ Slight accuracy degradation (typically <1%)
- 🔧 Requires calibration data
- 🎯 More complex implementation

### Learning Objectives

1. Understand quantization mathematics
2. Implement dynamic and static quantization
3. Perform calibration for optimal accuracy
4. Measure accuracy vs performance tradeoffs
5. Apply quantization to various architectures

### Prerequisites

- Completed Phase 1
- Understanding of neural network math
- Familiarity with fixed-point arithmetic
- PyTorch 2.0+ or TensorFlow 2.x

## Quantization Fundamentals

### 2.1 Mathematical Foundation

#### Quantization Formula

```
quantized = round((float_value / scale) + zero_point)
dequantized = (quantized - zero_point) * scale
```

**Key Concepts:**

1. **Scale**: Determines the range of values
   ```python
   scale = (float_max - float_min) / (quant_max - quant_min)
   ```

2. **Zero Point**: Maps float zero to integer zero
   ```python
   zero_point = quant_min - round(float_min / scale)
   ```

3. **Quantization Range**: Depends on bit-width
   - INT8: -128 to 127 (signed) or 0 to 255 (unsigned)
   - UINT8: 0 to 255
   - INT16: -32768 to 32767

#### Example: Quantize a Weight Tensor

```python
def quantize_tensor(tensor, num_bits=8, symmetric=True):
    """
    Quantize a floating-point tensor to integer representation.
    
    Args:
        tensor: Float tensor to quantize
        num_bits: Number of bits for quantization (typically 8)
        symmetric: Use symmetric or asymmetric quantization
    
    Returns:
        Tuple of (quantized_tensor, scale, zero_point)
    """
    # Find min and max values
    float_min = tensor.min()
    float_max = tensor.max()
    
    # Calculate quantization parameters
    if symmetric:
        # Symmetric: zero_point = 0
        abs_max = max(abs(float_min), abs(float_max))
        float_min = -abs_max
        float_max = abs_max
        zero_point = 0
    else:
        # Asymmetric: use full range
        zero_point = 0  # Will be calculated below
    
    # Quantization range
    if num_bits == 8:
        quant_min, quant_max = -128, 127
    else:
        quant_min = -(2 ** (num_bits - 1))
        quant_max = (2 ** (num_bits - 1)) - 1
    
    # Calculate scale
    scale = (float_max - float_min) / (quant_max - quant_min)
    
    if not symmetric:
        zero_point = quant_min - int(round(float_min / scale))
    
    # Quantize
    quantized = torch.round((tensor / scale) + zero_point)
    quantized = torch.clamp(quantized, quant_min, quant_max)
    
    return quantized.to(torch.int8), scale, zero_point
```

### 2.2 Types of Quantization

#### Dynamic Quantization (Easiest)

**What**: Weights quantized ahead of time, activations quantized at runtime
**When**: Good for models with variable input sizes (NLP)
**Pros**: Easy to apply, no calibration needed
**Cons**: Activation quantization overhead

```python
# Conceptual flow
weights = quantize(fp32_weights)  # Done once at conversion
activations = quantize(fp32_activations)  # Done at runtime
output = compute(quantized_weights, quantized_activations)
output = dequantize(output)
```

#### Static Quantization (Best Performance)

**What**: Both weights and activations quantized ahead of time
**When**: Best for production with known input distributions
**Pros**: Fastest inference, no runtime overhead
**Cons**: Requires calibration data

```python
# Conceptual flow
# During calibration:
collect_activation_statistics(model, calibration_data)
determine_activation_ranges()

# During inference:
# Everything is pre-quantized, no runtime conversion
output = compute_int8(quantized_weights, quantized_activations)
```

#### Quantization-Aware Training (Best Accuracy)

**What**: Model trained with quantization in mind
**When**: When accuracy loss is unacceptable
**Pros**: Minimal accuracy loss (<0.5%)
**Cons**: Requires retraining, more complex

```python
# Conceptual flow
for epoch in training_loop:
    forward_pass_with_fake_quantization()
    backward_pass_in_fp32()  # Gradients in FP32
    update_quantization_parameters()
```

## Post-Training Quantization

### 3.1 Dynamic Quantization (PyTorch)

**Step-by-Step Implementation:**

```python
import torch
import torch.nn as nn
from torch.quantization import quantize_dynamic

class DynamicQuantizer:
    """
    Apply dynamic quantization to PyTorch models.
    
    Best for: LSTM, Transformer models, models with dynamic shapes
    """
    
    def __init__(self, model, dtype=torch.qint8):
        """
        Initialize quantizer.
        
        Args:
            model: PyTorch model to quantize
            dtype: Target quantization type (qint8 or float16)
        """
        self.model = model
        self.dtype = dtype
        self.model.eval()  # Must be in eval mode
    
    def quantize(self, layer_types=None):
        """
        Apply dynamic quantization.
        
        Args:
            layer_types: Which layers to quantize (default: Linear, LSTM, GRU)
        
        Returns:
            Quantized model
        
        Implementation Steps:
        1. Specify which layer types to quantize
        2. Call torch.quantization.quantize_dynamic()
        3. Return quantized model
        """
        if layer_types is None:
            # Default: quantize Linear and RNN layers
            layer_types = {nn.Linear, nn.LSTM, nn.GRU}
        
        # Apply dynamic quantization
        quantized_model = quantize_dynamic(
            self.model,
            qconfig_spec=layer_types,
            dtype=self.dtype
        )
        
        return quantized_model
    
    def compare_models(self, original_model, quantized_model, test_input):
        """
        Compare original and quantized model outputs.
        
        Steps:
        1. Run inference on both models
        2. Calculate output difference
        3. Measure size reduction
        4. Measure speedup
        """
        # 1. Inference
        with torch.no_grad():
            orig_output = original_model(test_input)
            quant_output = quantized_model(test_input)
        
        # 2. Output difference
        diff = torch.abs(orig_output - quant_output).mean()
        
        # 3. Size comparison
        orig_size = self._get_model_size(original_model)
        quant_size = self._get_model_size(quantized_model)
        size_reduction = orig_size / quant_size
        
        # 4. Speed comparison
        orig_time = self._measure_inference_time(original_model, test_input)
        quant_time = self._measure_inference_time(quantized_model, test_input)
        speedup = orig_time / quant_time
        
        return {
            'output_diff': diff.item(),
            'size_reduction': size_reduction,
            'speedup': speedup,
            'original_size_mb': orig_size,
            'quantized_size_mb': quant_size
        }
```

**Detailed Implementation Example:**

```python
# Example: Quantize BERT model
from transformers import BertModel

# 1. Load original model
model = BertModel.from_pretrained('bert-base-uncased')
model.eval()

# 2. Create quantizer
quantizer = DynamicQuantizer(model)

# 3. Apply quantization
quantized_model = quantizer.quantize(
    layer_types={nn.Linear}  # Quantize all Linear layers
)

# 4. Test
dummy_input = torch.randint(0, 1000, (1, 128))  # Token IDs
results = quantizer.compare_models(model, quantized_model, dummy_input)

print(f"Size reduction: {results['size_reduction']:.2f}x")
print(f"Speedup: {results['speedup']:.2f}x")
print(f"Output difference: {results['output_diff']:.6f}")
```

### 3.2 Static Quantization (PyTorch)

**More Complex but Better Performance:**

```python
class StaticQuantizer:
    """
    Apply static quantization with calibration.
    
    Best for: CNN models, production deployment, maximum performance
    """
    
    def __init__(self, model, backend='fbgemm'):
        """
        Initialize static quantizer.
        
        Args:
            model: Model to quantize (must have QuantStub/DeQuantStub)
            backend: 'fbgemm' (x86) or 'qnnpack' (ARM)
        """
        self.model = model
        self.backend = backend
        torch.backends.quantized.engine = backend
    
    def prepare_model(self):
        """
        Prepare model for static quantization.
        
        Steps:
        1. Fuse operations (Conv+BN+ReLU)
        2. Insert QuantStub and DeQuantStub
        3. Set quantization config
        4. Prepare model for calibration
        """
        # 1. Fuse layers
        # Common patterns: conv+bn+relu, linear+relu
        self.model = torch.quantization.fuse_modules(
            self.model,
            [['conv', 'bn', 'relu']]  # Specify fusion patterns
        )
        
        # 2. Set qconfig (quantization configuration)
        self.model.qconfig = torch.quantization.get_default_qconfig(self.backend)
        
        # 3. Prepare for calibration
        torch.quantization.prepare(self.model, inplace=True)
        
        return self.model
    
    def calibrate(self, calibration_data_loader, num_batches=100):
        """
        Calibrate quantization parameters using representative data.
        
        This step determines the optimal scale and zero_point for activations.
        
        Args:
            calibration_data_loader: DataLoader with representative data
            num_batches: Number of batches to use for calibration
        
        Steps:
        1. Set model to eval mode
        2. Run forward passes to collect statistics
        3. Don't need gradients or loss computation
        """
        self.model.eval()
        
        with torch.no_grad():
            for batch_idx, (data, _) in enumerate(calibration_data_loader):
                if batch_idx >= num_batches:
                    break
                
                # Forward pass - this collects activation statistics
                _ = self.model(data)
                
                if batch_idx % 10 == 0:
                    print(f"Calibration: {batch_idx}/{num_batches}")
    
    def convert(self):
        """
        Convert to quantized model after calibration.
        
        This creates the final INT8 model.
        """
        torch.quantization.convert(self.model, inplace=True)
        return self.model
```

**Critical Implementation Details:**

#### Model Preparation with QuantStub

```python
class QuantizableModel(nn.Module):
    """
    Model prepared for static quantization.
    
    Must include QuantStub (input) and DeQuantStub (output).
    """
    
    def __init__(self, original_model):
        super().__init__()
        # Quantization stubs
        self.quant = torch.quantization.QuantStub()
        self.dequant = torch.quantization.DeQuantStub()
        
        # Original model
        self.model = original_model
    
    def forward(self, x):
        # Insert quantization at input
        x = self.quant(x)
        
        # Model computation (in INT8)
        x = self.model(x)
        
        # Dequantize at output
        x = self.dequant(x)
        
        return x
```

#### Layer Fusion for Better Performance

```python
def fuse_model(model):
    """
    Fuse consecutive operations for optimization.
    
    Common patterns:
    - Conv + BN + ReLU
    - Conv + BN
    - Linear + ReLU
    """
    # Example for ResNet-like architecture
    fusion_patterns = [
        ['conv1', 'bn1', 'relu'],
        ['layer1.0.conv1', 'layer1.0.bn1', 'layer1.0.relu'],
        # ... more patterns
    ]
    
    # Manual fusion
    torch.quantization.fuse_modules(model, fusion_patterns, inplace=True)
    
    return model
```

**Complete Static Quantization Example:**

```python
def quantize_resnet_static():
    """Complete example: Quantize ResNet with static quantization."""
    
    # 1. Load model
    model = torchvision.models.resnet18(pretrained=True)
    model.eval()
    
    # 2. Wrap with QuantStub/DeQuantStub
    class QuantizableResNet(nn.Module):
        def __init__(self, model):
            super().__init__()
            self.quant = torch.quantization.QuantStub()
            self.dequant = torch.quantization.DeQuantStub()
            self.model = model
        
        def forward(self, x):
            x = self.quant(x)
            x = self.model(x)
            x = self.dequant(x)
            return x
    
    wrapped_model = QuantizableResNet(model)
    
    # 3. Fuse layers
    # (In real code, specify exact layer names)
    
    # 4. Set qconfig
    wrapped_model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
    
    # 5. Prepare for calibration
    torch.quantization.prepare(wrapped_model, inplace=True)
    
    # 6. Calibrate (run inference on sample data)
    calibration_loader = create_calibration_loader()  # Your data
    with torch.no_grad():
        for batch_idx, (data, _) in enumerate(calibration_loader):
            if batch_idx >= 100:
                break
            _ = wrapped_model(data)
    
    # 7. Convert to quantized model
    torch.quantization.convert(wrapped_model, inplace=True)
    
    # 8. Test
    test_input = torch.randn(1, 3, 224, 224)
    output = wrapped_model(test_input)
    
    return wrapped_model
```

### 3.3 FP16 Quantization

**Half Precision on GPU:**

```python
class FP16Converter:
    """
    Convert models to FP16 (half precision).
    
    Best for: GPU inference, NVIDIA GPUs with Tensor Cores
    Speedup: 1.5-2x on modern GPUs
    """
    
    def convert_to_fp16(self, model):
        """
        Convert model to FP16.
        
        Simple conversion - just call .half()
        """
        model_fp16 = model.half()
        return model_fp16
    
    def mixed_precision_inference(self, model, input_tensor):
        """
        Use mixed precision (FP16 + FP32) for better accuracy.
        
        Some operations stay in FP32 to prevent numerical issues.
        """
        with torch.cuda.amp.autocast():
            output = model(input_tensor)
        
        return output
```

**When to Use FP16:**

✅ **Use FP16 when:**
- Running on GPU with Tensor Cores (V100, A100, etc.)
- Model has convolutions or matrix multiplications
- Accuracy degradation is acceptable (<0.5%)

❌ **Don't use FP16 when:**
- Running on CPU (no benefit)
- Model has numerical stability issues
- Need exact FP32 precision

**Implementation Example:**

```python
# Convert model to FP16
model = torchvision.models.resnet50(pretrained=True)
model = model.half().cuda()

# Input must also be FP16
input_tensor = torch.randn(1, 3, 224, 224).half().cuda()

# Inference
with torch.no_grad():
    output = model(input_tensor)

# Output is in FP16, convert back if needed
output = output.float()
```

### 3.4 Calibration Strategies

**Critical for Static Quantization:**

```python
def create_calibration_dataset(dataset, num_samples=1000):
    """
    Create representative calibration dataset.
    
    Best practices:
    1. Use samples from training set
    2. Ensure diverse representation
    3. Include edge cases
    4. Typically 100-1000 samples
    """
    indices = np.random.choice(len(dataset), num_samples, replace=False)
    subset = torch.utils.data.Subset(dataset, indices)
    
    loader = DataLoader(
        subset,
        batch_size=32,
        shuffle=True,
        num_workers=4
    )
    
    return loader
```

**Calibration Methods:**

1. **MinMax Calibration** (Default)
   - Use min/max values from activations
   - Simple, but sensitive to outliers
   
2. **Entropy Calibration** (TensorRT)
   - Minimize KL divergence between FP32 and INT8 distributions
   - Better accuracy, more computation
   
3. **Percentile Calibration**
   - Use percentiles (e.g., 99.9%) to ignore outliers
   - More robust than MinMax

## Quantization-Aware Training

### 4.1 QAT Implementation

**For Maximum Accuracy:**

```python
class QuantizationAwareTrainer:
    """
    Train model with quantization simulation.
    
    This achieves best accuracy after quantization.
    """
    
    def prepare_qat_model(self, model):
        """
        Prepare model for QAT.
        
        Steps:
        1. Fuse layers
        2. Set QAT qconfig
        3. Prepare for training
        """
        # Fuse layers
        model = fuse_model(model)
        
        # Set QAT-specific config
        model.qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')
        
        # Prepare for QAT
        torch.quantization.prepare_qat(model, inplace=True)
        
        return model
    
    def train_qat(self, model, train_loader, num_epochs=10):
        """
        Train with quantization simulation.
        
        Steps:
        1. Start in training mode
        2. Use fake quantization (simulates INT8)
        3. Gradients computed in FP32
        4. After training, freeze and convert
        """
        model.train()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        criterion = nn.CrossEntropyLoss()
        
        for epoch in range(num_epochs):
            for batch_idx, (data, target) in enumerate(train_loader):
                optimizer.zero_grad()
                
                # Forward pass with fake quantization
                output = model(data)
                loss = criterion(output, target)
                
                # Backward in FP32
                loss.backward()
                optimizer.step()
            
            # Switch to eval mode periodically to check accuracy
            if epoch % 2 == 0:
                model.eval()
                validate(model, val_loader)
                model.train()
        
        # After training, convert to actual INT8
        model.eval()
        torch.quantization.convert(model, inplace=True)
        
        return model
```

**Fake Quantization:**

```python
class FakeQuantize(nn.Module):
    """
    Simulate quantization during training.
    
    Forward pass: Quantize then dequantize (simulates INT8)
    Backward pass: Straight-through estimator (gradients flow)
    """
    
    def __init__(self, scale, zero_point):
        super().__init__()
        self.scale = scale
        self.zero_point = zero_point
    
    def forward(self, x):
        # Quantize
        x_int = torch.round(x / self.scale) + self.zero_point
        x_int = torch.clamp(x_int, -128, 127)
        
        # Dequantize (back to FP32 for training)
        x_float = (x_int - self.zero_point) * self.scale
        
        return x_float
```

## Accuracy Analysis

### 5.1 Measuring Accuracy Degradation

```python
def evaluate_quantization_accuracy(
    original_model,
    quantized_model,
    test_loader,
    device='cuda'
):
    """
    Compare accuracy of original vs quantized model.
    
    Returns:
        Dictionary with accuracy metrics and analysis
    """
    def eval_model(model):
        """Evaluate model accuracy."""
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                pred = output.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)
        
        return correct / total
    
    # Evaluate both models
    orig_acc = eval_model(original_model)
    quant_acc = eval_model(quantized_model)
    
    # Calculate degradation
    accuracy_drop = orig_acc - quant_acc
    relative_drop = (accuracy_drop / orig_acc) * 100
    
    return {
        'original_accuracy': orig_acc,
        'quantized_accuracy': quant_acc,
        'accuracy_drop': accuracy_drop,
        'relative_drop_percent': relative_drop
    }
```

### 5.2 Layer-wise Analysis

```python
def analyze_quantization_error_by_layer(model, quantized_model, test_input):
    """
    Identify which layers have the most quantization error.
    
    Useful for debugging accuracy issues.
    """
    errors = {}
    
    # Hook to capture layer outputs
    orig_activations = {}
    quant_activations = {}
    
    def hook_fn(name, activations_dict):
        def hook(module, input, output):
            activations_dict[name] = output.detach()
        return hook
    
    # Register hooks on all layers
    for name, module in model.named_modules():
        if isinstance(module, (nn.Conv2d, nn.Linear)):
            module.register_forward_hook(hook_fn(name, orig_activations))
    
    for name, module in quantized_model.named_modules():
        if isinstance(module, (nn.Conv2d, nn.Linear)):
            module.register_forward_hook(hook_fn(name, quant_activations))
    
    # Run inference
    with torch.no_grad():
        _ = model(test_input)
        _ = quantized_model(test_input)
    
    # Calculate per-layer error
    for name in orig_activations:
        if name in quant_activations:
            orig = orig_activations[name]
            quant = quant_activations[name]
            
            # Calculate error metrics
            mse = torch.mean((orig - quant) ** 2).item()
            mae = torch.mean(torch.abs(orig - quant)).item()
            max_error = torch.max(torch.abs(orig - quant)).item()
            
            errors[name] = {
                'mse': mse,
                'mae': mae,
                'max_error': max_error
            }
    
    return errors
```

## Performance Comparison

### 6.1 Comprehensive Benchmark

```python
def benchmark_quantization_methods(model, input_shape, test_loader):
    """
    Compare all quantization methods comprehensively.
    
    Measures:
    - Inference speed (latency, throughput)
    - Model size
    - Accuracy
    - Memory usage
    """
    results = {}
    
    # 1. Original FP32
    results['fp32'] = {
        'latency': measure_latency(model, input_shape),
        'size': get_model_size(model),
        'accuracy': eval_accuracy(model, test_loader),
        'memory': measure_memory(model, input_shape)
    }
    
    # 2. Dynamic INT8
    dynamic_model = apply_dynamic_quantization(model)
    results['dynamic_int8'] = {
        'latency': measure_latency(dynamic_model, input_shape),
        'size': get_model_size(dynamic_model),
        'accuracy': eval_accuracy(dynamic_model, test_loader),
        'memory': measure_memory(dynamic_model, input_shape)
    }
    
    # 3. Static INT8
    static_model = apply_static_quantization(model, create_calibration_loader())
    results['static_int8'] = {
        'latency': measure_latency(static_model, input_shape),
        'size': get_model_size(static_model),
        'accuracy': eval_accuracy(static_model, test_loader),
        'memory': measure_memory(static_model, input_shape)
    }
    
    # 4. FP16
    fp16_model = model.half().cuda()
    results['fp16_gpu'] = {
        'latency': measure_latency(fp16_model, input_shape, device='cuda'),
        'size': get_model_size(fp16_model),
        'accuracy': eval_accuracy(fp16_model, test_loader),
        'memory': measure_memory(fp16_model, input_shape, device='cuda')
    }
    
    # Generate comparison table
    print_comparison_table(results)
    
    return results
```

**Expected Results Table:**

```
Method          │ Latency  │ Speedup │ Size    │ Reduction │ Accuracy │ Drop
────────────────┼──────────┼─────────┼─────────┼───────────┼──────────┼─────
FP32 Original   │ 42.5 ms  │ 1.0x    │ 102 MB  │ 1.0x      │ 76.2%    │  -
Dynamic INT8    │ 18.3 ms  │ 2.3x    │  27 MB  │ 3.8x      │ 75.9%    │ 0.3%
Static INT8     │ 15.7 ms  │ 2.7x    │  26 MB  │ 3.9x      │ 75.8%    │ 0.4%
FP16 (GPU)      │ 22.1 ms  │ 1.9x    │  51 MB  │ 2.0x      │ 76.1%    │ 0.1%
QAT INT8        │ 15.5 ms  │ 2.7x    │  26 MB  │ 3.9x      │ 76.0%    │ 0.2%
```

## Testing Strategy

### Unit Tests

```python
class TestQuantization(unittest.TestCase):
    """Test quantization implementations."""
    
    def test_quantize_dequantize(self):
        """Test quantization round-trip."""
        tensor = torch.randn(100)
        quantized, scale, zero_point = quantize_tensor(tensor)
        dequantized = dequantize_tensor(quantized, scale, zero_point)
        
        # Should be close to original
        error = torch.abs(tensor - dequantized).mean()
        self.assertLess(error, 0.1)
    
    def test_dynamic_quantization(self):
        """Test dynamic quantization application."""
        model = nn.Linear(10, 5)
        quantized = quantize_dynamic(model, {nn.Linear})
        
        # Check model is quantized
        self.assertTrue(hasattr(quantized, '_packed_params'))
    
    def test_quantized_inference(self):
        """Test quantized model produces valid output."""
        model = create_test_model()
        quantized_model = quantize_model(model)
        
        input_tensor = torch.randn(1, 3, 224, 224)
        output = quantized_model(input_tensor)
        
        # Should produce valid probabilities
        self.assertEqual(output.shape, (1, 1000))
        self.assertTrue(torch.all(output >= 0))
```

## Expected Outcomes

After completing Phase 2, you should achieve:

### Performance Targets
- **INT8 Quantization**: 2-4x speedup on CPU
- **FP16 on GPU**: 1.5-2x speedup
- **Model Size**: 4x reduction (FP32 → INT8)
- **Accuracy Drop**: <1% for most models

### Understanding
- ✅ Explain quantization mathematics
- ✅ Choose appropriate quantization method
- ✅ Perform calibration correctly
- ✅ Debug accuracy issues
- ✅ Measure performance improvements

## Next Steps

Phase 3 covers:
- Model compilation (ONNX, TensorRT)
- GPU-specific optimizations
- Dynamic batching
- Multi-model serving

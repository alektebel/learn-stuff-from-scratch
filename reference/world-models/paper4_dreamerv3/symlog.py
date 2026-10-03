"""
Symlog Transformation Utilities for DreamerV3

Symlog is a key component of DreamerV3's robustness across domains.
It normalizes values across different scales while preserving sign.

Mathematical properties:
- symlog(0) = 0
- symlog(-x) = -symlog(x)
- symlog is monotonic
- Compresses large values logarithmically
- Linear near zero

Paper: Mastering Diverse Domains through World Models (Hafner et al., 2023)
Appendix B: Symlog Predictions
"""

import torch
import numpy as np
import matplotlib.pyplot as plt


def symlog(x):
    """
    Symmetric logarithm transformation.
    
    Formula: symlog(x) = sign(x) * log(|x| + 1)
    
    Args:
        x: Input tensor or scalar
        
    Returns:
        Transformed value
    """
    return torch.sign(x) * torch.log(torch.abs(x) + 1)


def symexp(x):
    """
    Inverse of symlog transformation.
    
    Formula: symexp(x) = sign(x) * (exp(|x|) - 1)
    
    Args:
        x: Symlog-transformed tensor or scalar
        
    Returns:
        Original scale value
    """
    return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)


def two_hot_encoding(x, num_bins=255, vmin=-20, vmax=20):
    """
    Two-hot encoding for distributional critic.
    
    Encodes a scalar value as two adjacent "hot" bins with interpolation.
    More stable than one-hot encoding.
    
    Args:
        x: Values to encode (batch,)
        num_bins: Number of bins
        vmin: Minimum value
        vmax: Maximum value
        
    Returns:
        encoding: Two-hot encoded values (batch, num_bins)
    """
    # TODO: Implement two-hot encoding
    # Guidelines:
    # 1. Normalize x to [0, num_bins-1]
    #    x_norm = (x - vmin) / (vmax - vmin) * (num_bins - 1)
    # 2. Get lower and upper bin indices
    #    lower = torch.floor(x_norm).long()
    #    upper = torch.ceil(x_norm).long()
    # 3. Compute interpolation weight
    #    weight_upper = x_norm - lower.float()
    #    weight_lower = 1 - weight_upper
    # 4. Create encoding with two hot bins
    #    encoding = torch.zeros(x.shape[0], num_bins)
    #    encoding.scatter_(1, lower.unsqueeze(1), weight_lower.unsqueeze(1))
    #    encoding.scatter_(1, upper.unsqueeze(1), weight_upper.unsqueeze(1))
    # 5. Return encoding
    pass


def from_two_hot(encoding, num_bins=255, vmin=-20, vmax=20):
    """
    Decode two-hot encoding back to scalar.
    
    Args:
        encoding: Two-hot encoded values (batch, num_bins)
        num_bins: Number of bins
        vmin: Minimum value
        vmax: Maximum value
        
    Returns:
        values: Decoded values (batch,)
    """
    # TODO: Implement decoding
    # Guidelines:
    # 1. Create bin centers
    #    bins = torch.linspace(vmin, vmax, num_bins)
    # 2. Weighted average
    #    values = (encoding * bins).sum(dim=-1)
    # 3. Return values
    pass


def visualize_symlog():
    """
    Visualize symlog transformation properties.
    """
    x = np.linspace(-100, 100, 1000)
    x_torch = torch.tensor(x, dtype=torch.float32)
    
    y = symlog(x_torch).numpy()
    
    plt.figure(figsize=(12, 4))
    
    # Plot transformation
    plt.subplot(1, 3, 1)
    plt.plot(x, y)
    plt.xlabel('Original Value')
    plt.ylabel('Symlog Value')
    plt.title('Symlog Transformation')
    plt.grid(True)
    
    # Plot around zero
    plt.subplot(1, 3, 2)
    x_zoom = np.linspace(-10, 10, 1000)
    x_zoom_torch = torch.tensor(x_zoom, dtype=torch.float32)
    y_zoom = symlog(x_zoom_torch).numpy()
    plt.plot(x_zoom, y_zoom)
    plt.xlabel('Original Value')
    plt.ylabel('Symlog Value')
    plt.title('Symlog Near Zero (Linear-like)')
    plt.grid(True)
    
    # Plot derivative
    plt.subplot(1, 3, 3)
    dx = x[1] - x[0]
    dy_dx = np.gradient(y, dx)
    plt.plot(x, dy_dx)
    plt.xlabel('Original Value')
    plt.ylabel('Derivative')
    plt.title('Symlog Derivative (Smooth)')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('symlog_visualization.png')
    print("✓ Saved symlog visualization to symlog_visualization.png")


def test_symlog():
    """Test symlog utilities."""
    print("Testing Symlog Utilities...")
    
    # Test basic symlog/symexp
    x = torch.tensor([-100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0])
    y = symlog(x)
    x_recon = symexp(y)
    
    print(f"✓ Symlog transformation:")
    print(f"  Original: {x}")
    print(f"  Symlog: {y}")
    print(f"  Reconstructed: {x_recon}")
    assert torch.allclose(x, x_recon, atol=1e-5)
    
    # Test symmetry
    assert torch.allclose(symlog(-x), -symlog(x))
    print(f"✓ Symmetry property holds")
    
    # Test monotonicity
    x_sorted = torch.sort(torch.randn(100))[0]
    y_sorted = symlog(x_sorted)
    assert torch.all(y_sorted[1:] >= y_sorted[:-1])
    print(f"✓ Monotonicity property holds")
    
    # Test near-zero linearity
    x_small = torch.linspace(-0.1, 0.1, 21)
    y_small = symlog(x_small)
    # Should be approximately linear near zero
    correlation = torch.corrcoef(torch.stack([x_small, y_small]))[0, 1]
    assert correlation > 0.99
    print(f"✓ Linear near zero (correlation: {correlation:.4f})")
    
    # Test two-hot encoding
    values = torch.tensor([-5.0, 0.0, 5.0, 10.0])
    encoding = two_hot_encoding(values)
    decoded = from_two_hot(encoding)
    assert torch.allclose(values, decoded, atol=0.1)
    print(f"✓ Two-hot encoding works")
    
    # Visualize
    try:
        visualize_symlog()
    except:
        print("⚠ Could not create visualization (matplotlib issue)")
    
    print("\n✅ All symlog tests passed!")
    print("\nKey properties:")
    print("  - Preserves sign and monotonicity")
    print("  - Compresses large values")
    print("  - Linear near zero")
    print("  - Smooth and differentiable")


if __name__ == "__main__":
    test_symlog()

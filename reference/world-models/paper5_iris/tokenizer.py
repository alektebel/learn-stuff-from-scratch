"""
VQ-VAE Tokenizer for IRIS

IRIS uses a VQ-VAE (Vector Quantized Variational Autoencoder) to tokenize
observations into discrete codes. This enables transformer-based world modeling.

Key Concepts:
- Discrete tokenization of continuous observations
- Codebook of learnable vectors
- Straight-through gradient estimator
- Enables autoregressive modeling with transformers

Architecture:
- Encoder: Image → continuous embeddings
- Quantization: Map to nearest codebook vector
- Decoder: Discrete codes → reconstructed image

Paper: Transformers are Sample Efficient World Models (Robine et al., 2023)
Section 3.1: Tokenizer
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class VectorQuantizer(nn.Module):
    """
    Vector quantization layer.
    
    Maps continuous embeddings to discrete codebook vectors using
    nearest-neighbor lookup with straight-through gradients.
    
    Args:
        num_embeddings: Size of codebook (default: 4096)
        embedding_dim: Dimension of each code (default: 256)
        commitment_cost: Weight for commitment loss (default: 0.25)
    """
    
    def __init__(
        self,
        num_embeddings=4096,
        embedding_dim=256,
        commitment_cost=0.25
    ):
        super().__init__()
        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        self.commitment_cost = commitment_cost
        
        # TODO: Initialize codebook
        # Guidelines:
        # - Create learnable embedding table
        # - Initialize with uniform distribution
        #
        # self.embedding = nn.Embedding(num_embeddings, embedding_dim)
        # self.embedding.weight.data.uniform_(-1/num_embeddings, 1/num_embeddings)
        
        pass  # Remove when implementing
    
    def forward(self, z):
        """
        Quantize continuous embeddings to discrete codes.
        
        Args:
            z: Continuous embeddings (batch, embedding_dim, H, W)
            
        Returns:
            z_q: Quantized embeddings (batch, embedding_dim, H, W)
            indices: Codebook indices (batch, H, W)
            vq_loss: Vector quantization loss
        """
        # TODO: Implement vector quantization
        # Guidelines:
        # 1. Reshape for processing
        #    z_flat = z.permute(0, 2, 3, 1).reshape(-1, self.embedding_dim)
        # 
        # 2. Compute distances to all codebook vectors
        #    distances = torch.sum(z_flat**2, dim=1, keepdim=True) + \
        #                torch.sum(self.embedding.weight**2, dim=1) - \
        #                2 * torch.matmul(z_flat, self.embedding.weight.t())
        # 
        # 3. Find nearest codebook vector
        #    indices = torch.argmin(distances, dim=1)
        #    z_q_flat = self.embedding(indices)
        # 
        # 4. Reshape back
        #    z_q = z_q_flat.reshape(z.shape[0], z.shape[2], z.shape[3], -1)
        #    z_q = z_q.permute(0, 3, 1, 2)
        # 
        # 5. Straight-through estimator
        #    z_q = z + (z_q - z).detach()
        # 
        # 6. VQ loss
        #    e_latent_loss = F.mse_loss(z_q.detach(), z)
        #    q_latent_loss = F.mse_loss(z_q, z.detach())
        #    vq_loss = q_latent_loss + self.commitment_cost * e_latent_loss
        # 
        # 7. Return z_q, indices, vq_loss
        #
        # Paper reference: Section 3.1, VQ-VAE
        pass


class Encoder(nn.Module):
    """
    Convolutional encoder for VQ-VAE.
    
    Maps images to continuous embeddings before quantization.
    
    Args:
        embedding_dim: Output embedding dimension (default: 256)
        num_channels: Input image channels (default: 3)
    """
    
    def __init__(self, embedding_dim=256, num_channels=3):
        super().__init__()
        
        # TODO: Implement encoder
        # Guidelines:
        # - Use strided convolutions to downsample
        # - 4x downsampling total (64x64 → 16x16)
        # - Use residual connections
        # - Output: (batch, embedding_dim, 16, 16)
        #
        # Architecture:
        # Conv 3 → 64, stride 2 (64x64 → 32x32)
        # Residual block 64
        # Conv 64 → 128, stride 2 (32x32 → 16x16)
        # Residual block 128
        # Conv 128 → embedding_dim
        #
        # Paper reference: Section 3.1, Encoder
        pass
    
    def forward(self, x):
        """
        Encode image to continuous embeddings.
        
        Args:
            x: Image (batch, 3, 64, 64)
            
        Returns:
            z: Embeddings (batch, embedding_dim, 16, 16)
        """
        # TODO: Implement forward pass
        pass


class Decoder(nn.Module):
    """
    Convolutional decoder for VQ-VAE.
    
    Reconstructs images from quantized embeddings.
    
    Args:
        embedding_dim: Input embedding dimension (default: 256)
        num_channels: Output image channels (default: 3)
    """
    
    def __init__(self, embedding_dim=256, num_channels=3):
        super().__init__()
        
        # TODO: Implement decoder
        # Guidelines:
        # - Mirror encoder architecture
        # - Use transposed convolutions to upsample
        # - 4x upsampling total (16x16 → 64x64)
        # - Use residual connections
        #
        # Architecture (reverse of encoder):
        # Conv embedding_dim → 128
        # Residual block 128
        # ConvTranspose 128 → 64, stride 2 (16x16 → 32x32)
        # Residual block 64
        # ConvTranspose 64 → 3, stride 2 (32x32 → 64x64)
        #
        # Paper reference: Section 3.1, Decoder
        pass
    
    def forward(self, z_q):
        """
        Decode quantized embeddings to image.
        
        Args:
            z_q: Quantized embeddings (batch, embedding_dim, 16, 16)
            
        Returns:
            x_recon: Reconstructed image (batch, 3, 64, 64)
        """
        # TODO: Implement forward pass
        pass


class VQVAETokenizer(nn.Module):
    """
    Complete VQ-VAE tokenizer for IRIS.
    
    Combines encoder, vector quantizer, and decoder into a single module.
    Converts images to discrete tokens and back.
    
    Args:
        num_embeddings: Codebook size (default: 4096)
        embedding_dim: Embedding dimension (default: 256)
        commitment_cost: VQ commitment cost (default: 0.25)
    """
    
    def __init__(
        self,
        num_embeddings=4096,
        embedding_dim=256,
        commitment_cost=0.25
    ):
        super().__init__()
        
        # TODO: Initialize components
        # self.encoder = Encoder(embedding_dim)
        # self.quantizer = VectorQuantizer(num_embeddings, embedding_dim, commitment_cost)
        # self.decoder = Decoder(embedding_dim)
        
        pass  # Remove when implementing
    
    def encode(self, x):
        """
        Encode image to discrete tokens.
        
        Args:
            x: Image (batch, 3, 64, 64)
            
        Returns:
            indices: Token indices (batch, 16, 16)
        """
        # TODO: Implement encoding
        # Guidelines:
        # 1. Pass through encoder: z = self.encoder(x)
        # 2. Quantize: z_q, indices, _ = self.quantizer(z)
        # 3. Return indices
        pass
    
    def decode(self, indices):
        """
        Decode tokens to image.
        
        Args:
            indices: Token indices (batch, 16, 16)
            
        Returns:
            x_recon: Reconstructed image (batch, 3, 64, 64)
        """
        # TODO: Implement decoding
        # Guidelines:
        # 1. Lookup embeddings: z_q = self.quantizer.embedding(indices)
        # 2. Reshape: z_q = z_q.permute(0, 3, 1, 2)
        # 3. Decode: x_recon = self.decoder(z_q)
        # 4. Return reconstruction
        pass
    
    def forward(self, x):
        """
        Full forward pass: encode → quantize → decode.
        
        Args:
            x: Image (batch, 3, 64, 64)
            
        Returns:
            x_recon: Reconstructed image
            indices: Token indices
            vq_loss: VQ loss
        """
        # TODO: Implement full forward
        # Guidelines:
        # 1. Encode: z = self.encoder(x)
        # 2. Quantize: z_q, indices, vq_loss = self.quantizer(z)
        # 3. Decode: x_recon = self.decoder(z_q)
        # 4. Return x_recon, indices, vq_loss
        pass


def test_tokenizer():
    """Test VQ-VAE tokenizer implementation."""
    print("Testing VQ-VAE Tokenizer...")
    
    # Hyperparameters
    batch_size = 4
    num_embeddings = 512  # Smaller for testing
    embedding_dim = 64
    
    # Create tokenizer
    tokenizer = VQVAETokenizer(
        num_embeddings=num_embeddings,
        embedding_dim=embedding_dim
    )
    
    print(f"✓ Created VQ-VAE tokenizer")
    print(f"  - Codebook size: {num_embeddings}")
    print(f"  - Embedding dim: {embedding_dim}")
    print(f"  - Spatial size: 16×16")
    print(f"  - Total tokens per image: 256")
    
    # Test encoding
    x = torch.randn(batch_size, 3, 64, 64)
    indices = tokenizer.encode(x)
    assert indices.shape == (batch_size, 16, 16)
    assert torch.all((indices >= 0) & (indices < num_embeddings))
    print(f"✓ Encoding works: {x.shape} → {indices.shape}")
    print(f"  - Token range: [{indices.min()}, {indices.max()}]")
    
    # Test decoding
    x_recon = tokenizer.decode(indices)
    assert x_recon.shape == (batch_size, 3, 64, 64)
    print(f"✓ Decoding works: {indices.shape} → {x_recon.shape}")
    
    # Test full forward pass
    x_recon, indices, vq_loss = tokenizer(x)
    assert x_recon.shape == x.shape
    assert vq_loss.ndim == 0  # Scalar
    print(f"✓ Full forward pass works")
    print(f"  - VQ loss: {vq_loss.item():.4f}")
    
    # Test reconstruction quality
    recon_loss = F.mse_loss(x_recon, x)
    print(f"✓ Reconstruction loss: {recon_loss.item():.4f}")
    
    # Test codebook usage
    unique_codes = torch.unique(indices)
    usage_ratio = len(unique_codes) / num_embeddings
    print(f"✓ Codebook usage: {len(unique_codes)}/{num_embeddings} ({usage_ratio:.1%})")
    
    # Test gradient flow
    total_loss = recon_loss + vq_loss
    total_loss.backward()
    print(f"✓ Gradients flow through tokenizer")
    
    print("\n✅ All tokenizer tests passed!")
    print("\nKey properties:")
    print("  - Discrete tokenization of images")
    print("  - 4× spatial downsampling (64×64 → 16×16)")
    print("  - Learnable codebook")
    print("  - Straight-through gradient estimator")
    print("  - Enables transformer-based world modeling")


if __name__ == "__main__":
    test_tokenizer()

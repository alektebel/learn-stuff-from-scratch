"""
Variational Autoencoder (VAE) for World Models

This VAE compresses high-dimensional observations (96x96x3 images) into 
compact 32-dimensional latent representations.

Architecture:
- Encoder: Conv layers → latent mean and log variance
- Decoder: Deconv layers → reconstructed image
- Loss: Reconstruction loss + KL divergence

Paper: World Models (Ha & Schmidhuber, 2018)
Section 2.1: V (Vision Model)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class VAE(nn.Module):
    """
    Variational Autoencoder for compressing observations.
    
    Args:
        latent_dim: Dimension of latent space (default: 32)
        image_channels: Number of input channels (default: 3 for RGB)
    """
    
    def __init__(self, latent_dim=32, image_channels=3):
        super().__init__()
        self.latent_dim = latent_dim
        
        # TODO: Implement encoder
        # Guidelines:
        # - Input: (batch, 3, 96, 96)
        # - Use 4 convolutional layers with stride 2
        # - Channels: 3 → 32 → 64 → 128 → 256
        # - Kernel size 4, stride 2, padding 1
        # - ReLU activation after each conv
        # - Final output should be flattened and passed to two FC layers
        #   for mu and logvar (each outputting latent_dim values)
        
        # Encoder convolutional layers
        # self.encoder_conv = nn.Sequential(...)
        
        # Encoder output layers (for mean and log variance)
        # self.fc_mu = nn.Linear(...)
        # self.fc_logvar = nn.Linear(...)
        
        # TODO: Implement decoder
        # Guidelines:
        # - Input: latent vector of size latent_dim
        # - First FC layer to expand to suitable size for deconv
        # - Use 4 transposed convolutional layers
        # - Reverse the encoder architecture
        # - Use Sigmoid activation at the end to output [0, 1] range
        
        # Decoder initial projection
        # self.decoder_fc = nn.Linear(...)
        
        # Decoder deconvolutional layers
        # self.decoder_deconv = nn.Sequential(...)
        
        pass  # Remove this when you implement the network
    
    def encode(self, x):
        """
        Encode observation to latent distribution parameters.
        
        Args:
            x: Input images (batch, channels, height, width)
            
        Returns:
            mu: Mean of latent distribution (batch, latent_dim)
            logvar: Log variance of latent distribution (batch, latent_dim)
        """
        # TODO: Implement encoding
        # Guidelines:
        # 1. Pass through convolutional encoder
        # 2. Flatten the output
        # 3. Compute mu and logvar from flattened features
        
        pass
    
    def reparameterize(self, mu, logvar):
        """
        Reparameterization trick: z = mu + sigma * epsilon
        
        Args:
            mu: Mean (batch, latent_dim)
            logvar: Log variance (batch, latent_dim)
            
        Returns:
            z: Sampled latent vector (batch, latent_dim)
        """
        # TODO: Implement reparameterization trick
        # Guidelines:
        # 1. Compute std = exp(0.5 * logvar)
        # 2. Sample epsilon from N(0, 1)
        # 3. Return z = mu + std * epsilon
        # 
        # Note: During training, we need gradients to flow through this.
        # The reparameterization trick allows backprop through random sampling.
        
        pass
    
    def decode(self, z):
        """
        Decode latent vector to reconstructed observation.
        
        Args:
            z: Latent vector (batch, latent_dim)
            
        Returns:
            reconstruction: Reconstructed image (batch, channels, height, width)
        """
        # TODO: Implement decoding
        # Guidelines:
        # 1. Pass z through initial FC layer
        # 2. Reshape to spatial dimensions (e.g., 256 channels, 6x6 spatial)
        # 3. Pass through deconvolutional layers
        # 4. Apply sigmoid to ensure output is in [0, 1]
        
        pass
    
    def forward(self, x):
        """
        Full forward pass through VAE.
        
        Args:
            x: Input images (batch, channels, height, width)
            
        Returns:
            reconstruction: Reconstructed images
            mu: Latent mean
            logvar: Latent log variance
        """
        # TODO: Implement full forward pass
        # Guidelines:
        # 1. Encode to get mu and logvar
        # 2. Sample z using reparameterization
        # 3. Decode z to get reconstruction
        # 4. Return all three: reconstruction, mu, logvar
        
        pass
    
    def loss_function(self, recon_x, x, mu, logvar, kl_weight=1.0):
        """
        VAE loss = Reconstruction loss + KL divergence
        
        Args:
            recon_x: Reconstructed images
            x: Original images
            mu: Latent mean
            logvar: Latent log variance
            kl_weight: Weight for KL term (default: 1.0)
            
        Returns:
            loss: Total loss
            recon_loss: Reconstruction loss component
            kl_loss: KL divergence component
        """
        # TODO: Implement loss function
        # Guidelines:
        # 1. Reconstruction loss: MSE between original and reconstructed
        #    recon_loss = F.mse_loss(recon_x, x, reduction='sum')
        # 
        # 2. KL divergence: KL(q(z|x) || p(z)) where p(z) = N(0, I)
        #    For Gaussian distributions:
        #    KL = -0.5 * sum(1 + logvar - mu^2 - exp(logvar))
        # 
        # 3. Total loss = recon_loss + kl_weight * kl_loss
        
        pass


def test_vae():
    """
    Test function to verify VAE implementation.
    """
    print("Testing VAE...")
    
    # Create VAE
    vae = VAE(latent_dim=32, image_channels=3)
    
    # Test with dummy input
    batch_size = 4
    x = torch.randn(batch_size, 3, 96, 96)
    
    # TODO: Uncomment when implemented
    # # Forward pass
    # recon, mu, logvar = vae(x)
    # 
    # # Check shapes
    # assert recon.shape == x.shape, f"Reconstruction shape mismatch: {recon.shape} vs {x.shape}"
    # assert mu.shape == (batch_size, 32), f"Mu shape mismatch: {mu.shape}"
    # assert logvar.shape == (batch_size, 32), f"Logvar shape mismatch: {logvar.shape}"
    # 
    # # Check loss
    # loss, recon_loss, kl_loss = vae.loss_function(recon, x, mu, logvar)
    # assert loss.item() > 0, "Loss should be positive"
    # 
    # print(f"✓ VAE test passed!")
    # print(f"  Reconstruction shape: {recon.shape}")
    # print(f"  Latent shape: {mu.shape}")
    # print(f"  Total loss: {loss.item():.4f}")
    # print(f"  Recon loss: {recon_loss.item():.4f}")
    # print(f"  KL loss: {kl_loss.item():.4f}")
    
    print("Implementation not complete yet. Uncomment test code when ready.")


if __name__ == "__main__":
    test_vae()

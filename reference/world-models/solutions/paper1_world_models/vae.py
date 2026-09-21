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
        
        # Encoder: (batch, 3, 96, 96) -> (batch, 256, 6, 6)
        self.encoder_conv = nn.Sequential(
            # Layer 1: 96x96 -> 48x48
            nn.Conv2d(image_channels, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            # Layer 2: 48x48 -> 24x24
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            # Layer 3: 24x24 -> 12x12
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            # Layer 4: 12x12 -> 6x6
            nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1),
            nn.ReLU()
        )
        
        # Calculate flattened size: 256 channels * 6 * 6 spatial
        self.flatten_size = 256 * 6 * 6
        
        # Latent distribution parameters
        self.fc_mu = nn.Linear(self.flatten_size, latent_dim)
        self.fc_logvar = nn.Linear(self.flatten_size, latent_dim)
        
        # Decoder: expand latent to spatial features
        self.decoder_fc = nn.Linear(latent_dim, self.flatten_size)
        
        # Decoder: (batch, 256, 6, 6) -> (batch, 3, 96, 96)
        self.decoder_deconv = nn.Sequential(
            # Layer 1: 6x6 -> 12x12
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            # Layer 2: 12x12 -> 24x24
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            # Layer 3: 24x24 -> 48x48
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            # Layer 4: 48x48 -> 96x96
            nn.ConvTranspose2d(32, image_channels, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()  # Output in [0, 1] range
        )
    
    def encode(self, x):
        """
        Encode observation to latent distribution parameters.
        
        Args:
            x: Input images (batch, channels, height, width)
            
        Returns:
            mu: Mean of latent distribution (batch, latent_dim)
            logvar: Log variance of latent distribution (batch, latent_dim)
        """
        # Pass through convolutional encoder
        h = self.encoder_conv(x)
        
        # Flatten
        h = h.view(h.size(0), -1)
        
        # Compute distribution parameters
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        
        return mu, logvar
    
    def reparameterize(self, mu, logvar):
        """
        Reparameterization trick: z = mu + sigma * epsilon
        
        This allows gradients to flow through the sampling operation.
        Instead of sampling z ~ N(mu, sigma^2), we sample epsilon ~ N(0, 1)
        and compute z = mu + sigma * epsilon.
        
        Args:
            mu: Mean (batch, latent_dim)
            logvar: Log variance (batch, latent_dim)
            
        Returns:
            z: Sampled latent vector (batch, latent_dim)
        """
        # Compute standard deviation from log variance
        std = torch.exp(0.5 * logvar)
        
        # Sample epsilon from standard normal distribution
        eps = torch.randn_like(std)
        
        # Reparameterization: z = mu + std * epsilon
        z = mu + std * eps
        
        return z
    
    def decode(self, z):
        """
        Decode latent vector to reconstructed observation.
        
        Args:
            z: Latent vector (batch, latent_dim)
            
        Returns:
            reconstruction: Reconstructed image (batch, channels, height, width)
        """
        # Project to flattened spatial features
        h = self.decoder_fc(z)
        
        # Reshape to spatial dimensions
        h = h.view(h.size(0), 256, 6, 6)
        
        # Pass through deconvolutional decoder
        reconstruction = self.decoder_deconv(h)
        
        return reconstruction
    
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
        # Encode to latent distribution
        mu, logvar = self.encode(x)
        
        # Sample latent vector
        z = self.reparameterize(mu, logvar)
        
        # Decode to reconstruction
        reconstruction = self.decode(z)
        
        return reconstruction, mu, logvar
    
    def loss_function(self, recon_x, x, mu, logvar, kl_weight=1.0):
        """
        VAE loss = Reconstruction loss + KL divergence
        
        The reconstruction loss measures how well we can reconstruct the input.
        The KL divergence regularizes the latent space to be close to N(0, I).
        
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
        # Reconstruction loss: Mean Squared Error
        # Sum over all dimensions, then average over batch
        recon_loss = F.mse_loss(recon_x, x, reduction='sum')
        
        # KL divergence: KL(q(z|x) || p(z)) where p(z) = N(0, I)
        # For Gaussian distributions:
        # KL = -0.5 * sum(1 + log(sigma^2) - mu^2 - sigma^2)
        #    = -0.5 * sum(1 + logvar - mu^2 - exp(logvar))
        kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        
        # Total loss (averaged over batch)
        batch_size = x.size(0)
        loss = (recon_loss + kl_weight * kl_loss) / batch_size
        
        return loss, recon_loss / batch_size, kl_loss / batch_size


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
    
    # Forward pass
    recon, mu, logvar = vae(x)
    
    # Check shapes
    assert recon.shape == x.shape, f"Reconstruction shape mismatch: {recon.shape} vs {x.shape}"
    assert mu.shape == (batch_size, 32), f"Mu shape mismatch: {mu.shape}"
    assert logvar.shape == (batch_size, 32), f"Logvar shape mismatch: {logvar.shape}"
    
    # Check loss
    loss, recon_loss, kl_loss = vae.loss_function(recon, x, mu, logvar)
    assert loss.item() > 0, "Loss should be positive"
    
    print(f"✓ VAE test passed!")
    print(f"  Reconstruction shape: {recon.shape}")
    print(f"  Latent shape: {mu.shape}")
    print(f"  Total loss: {loss.item():.4f}")
    print(f"  Recon loss: {recon_loss.item():.4f}")
    print(f"  KL loss: {kl_loss.item():.4f}")
    
    # Test encoding and decoding separately
    mu_test, logvar_test = vae.encode(x)
    z_test = vae.reparameterize(mu_test, logvar_test)
    recon_test = vae.decode(z_test)
    assert recon_test.shape == x.shape, "Separate encode/decode failed"
    
    print(f"✓ Separate encode/decode test passed!")
    
    # Test that output is in valid range
    assert recon.min() >= 0.0 and recon.max() <= 1.0, "Reconstruction should be in [0, 1]"
    print(f"✓ Output range test passed! Range: [{recon.min():.3f}, {recon.max():.3f}]")


if __name__ == "__main__":
    test_vae()

"""
Improved Encoder/Decoder Networks for DreamerV2

DreamerV2 improves the encoder and decoder architectures with:
- LayerNorm for better normalization
- ELU activations instead of ReLU
- Improved architectural choices

These networks connect observations to the discrete latent space.

Paper: Mastering Atari with Discrete World Models (Hafner et al., 2021)
Section 3.1: Model Components
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvEncoder(nn.Module):
    """
    Convolutional encoder for processing image observations.
    
    Improvements over DreamerV1:
    - LayerNorm instead of BatchNorm
    - ELU activation instead of ReLU
    - Better depth progression
    
    Args:
        embed_dim: Output embedding dimension (default: 1024)
        depth: Base channel depth (default: 32)
        activation: Activation function (default: 'elu')
    """
    
    def __init__(self, embed_dim=1024, depth=32, activation='elu'):
        super().__init__()
        self.embed_dim = embed_dim
        
        # TODO: Implement convolutional encoder
        # Guidelines:
        # - Input: (batch, 3, 64, 64) RGB images
        # - Use 4 convolutional layers with stride 2
        # - Channel progression: 3 → depth → 2*depth → 4*depth → 8*depth
        # - Kernel size: 4x4 for all layers
        # - Apply LayerNorm after each conv (not BatchNorm!)
        # - Use ELU activation
        # - Final spatial size: 4x4
        # - Flatten and project to embed_dim
        #
        # Architecture:
        # Conv1: 3 → 32 channels, 64x64 → 32x32
        # Conv2: 32 → 64 channels, 32x32 → 16x16
        # Conv3: 64 → 128 channels, 16x16 → 8x8
        # Conv4: 128 → 256 channels, 8x8 → 4x4
        # Flatten: 256*4*4 = 4096
        # Linear: 4096 → embed_dim
        #
        # Paper reference: Section 3.1, Encoder architecture
        
        # self.conv1 = nn.Conv2d(3, depth, kernel_size=4, stride=2)
        # self.norm1 = nn.LayerNorm([depth, 32, 32])
        # 
        # self.conv2 = nn.Conv2d(depth, 2*depth, kernel_size=4, stride=2)
        # self.norm2 = nn.LayerNorm([2*depth, 16, 16])
        # 
        # self.conv3 = nn.Conv2d(2*depth, 4*depth, kernel_size=4, stride=2)
        # self.norm3 = nn.LayerNorm([4*depth, 8, 8])
        # 
        # self.conv4 = nn.Conv2d(4*depth, 8*depth, kernel_size=4, stride=2)
        # self.norm4 = nn.LayerNorm([8*depth, 4, 4])
        # 
        # self.fc = nn.Linear(8*depth*4*4, embed_dim)
        # self.activation = nn.ELU()
        
        pass  # Remove when implementing
    
    def forward(self, obs):
        """
        Encode observation to embedding.
        
        Args:
            obs: Observation images (batch, 3, 64, 64)
            
        Returns:
            embed: Embedding vector (batch, embed_dim)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Apply conv1, norm1, activation
        #    x = self.activation(self.norm1(self.conv1(obs)))
        # 2. Apply conv2, norm2, activation
        # 3. Apply conv3, norm3, activation
        # 4. Apply conv4, norm4, activation
        # 5. Flatten: x = x.reshape(x.shape[0], -1)
        # 6. Apply final linear layer: embed = self.fc(x)
        # 7. Return embedding
        #
        # Note: LayerNorm expects (batch, channels, height, width)
        pass


class ConvDecoder(nn.Module):
    """
    Convolutional decoder for reconstructing observations.
    
    Improvements over DreamerV1:
    - LayerNorm in decoder path
    - ELU activation
    - Better architectural symmetry with encoder
    
    Args:
        state_dim: Dimension of stochastic state (default: 1024)
        rnn_hidden_dim: Dimension of deterministic state (default: 200)
        depth: Base channel depth (default: 32)
        activation: Activation function (default: 'elu')
    """
    
    def __init__(
        self, 
        state_dim=1024,
        rnn_hidden_dim=200,
        depth=32,
        activation='elu'
    ):
        super().__init__()
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement convolutional decoder
        # Guidelines:
        # - Input: concatenated (z, h) with dimension latent_dim
        # - Project to 8*depth*4*4 and reshape to (batch, 8*depth, 4, 4)
        # - Use 4 transposed convolutions with stride 2
        # - Channel progression: 8*depth → 4*depth → 2*depth → depth → 3
        # - Apply LayerNorm after each layer (except last)
        # - Use ELU activation (except last)
        # - Final layer: no activation (raw RGB values)
        #
        # Architecture (reverse of encoder):
        # Linear: latent_dim → 8*depth*4*4
        # Reshape: (batch, 8*depth, 4, 4)
        # ConvTranspose1: 256 → 128 channels, 4x4 → 8x8
        # ConvTranspose2: 128 → 64 channels, 8x8 → 16x16
        # ConvTranspose3: 64 → 32 channels, 16x16 → 32x32
        # ConvTranspose4: 32 → 3 channels, 32x32 → 64x64
        #
        # Paper reference: Section 3.1, Decoder architecture
        
        # self.fc = nn.Linear(latent_dim, 8*depth*4*4)
        # 
        # self.deconv1 = nn.ConvTranspose2d(8*depth, 4*depth, kernel_size=4, stride=2)
        # self.norm1 = nn.LayerNorm([4*depth, 8, 8])
        # 
        # self.deconv2 = nn.ConvTranspose2d(4*depth, 2*depth, kernel_size=4, stride=2)
        # self.norm2 = nn.LayerNorm([2*depth, 16, 16])
        # 
        # self.deconv3 = nn.ConvTranspose2d(2*depth, depth, kernel_size=4, stride=2)
        # self.norm3 = nn.LayerNorm([depth, 32, 32])
        # 
        # self.deconv4 = nn.ConvTranspose2d(depth, 3, kernel_size=4, stride=2)
        # 
        # self.activation = nn.ELU()
        # self.depth = depth
        
        pass  # Remove when implementing
    
    def forward(self, state):
        """
        Decode latent state to observation.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            
        Returns:
            obs: Reconstructed observation (batch, 3, 64, 64)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate: x = torch.cat([state['z'], state['h']], dim=-1)
        # 2. Project to feature maps: x = self.fc(x)
        # 3. Reshape: x = x.reshape(x.shape[0], 8*self.depth, 4, 4)
        # 4. Apply deconv1, norm1, activation
        # 5. Apply deconv2, norm2, activation
        # 6. Apply deconv3, norm3, activation
        # 7. Apply deconv4 (no norm, no activation)
        # 8. Return reconstructed observation
        pass


class RewardPredictor(nn.Module):
    """
    Predict rewards from latent states.
    
    Improvements over DreamerV1:
    - ELU activation
    - Deeper network (optional)
    - Better initialization
    
    Args:
        state_dim: Dimension of stochastic state (default: 1024)
        rnn_hidden_dim: Dimension of deterministic state (default: 200)
        hidden_dim: Dimension of hidden layers (default: 400)
        num_layers: Number of hidden layers (default: 4)
        activation: Activation function (default: 'elu')
    """
    
    def __init__(
        self,
        state_dim=1024,
        rnn_hidden_dim=200,
        hidden_dim=400,
        num_layers=4,
        activation='elu'
    ):
        super().__init__()
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement reward predictor
        # Guidelines:
        # - Input: concatenated (z, h)
        # - Build MLP with num_layers hidden layers
        # - Use ELU activation between layers
        # - Output: single scalar reward prediction
        #
        # Architecture:
        # latent_dim → hidden_dim → ... → hidden_dim → 1
        #
        # Paper reference: Section 3.1, Reward predictor
        
        # layers = []
        # layers.append(nn.Linear(latent_dim, hidden_dim))
        # layers.append(nn.ELU())
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.ELU())
        # layers.append(nn.Linear(hidden_dim, 1))
        # self.network = nn.Sequential(*layers)
        
        pass  # Remove when implementing
    
    def forward(self, state):
        """
        Predict reward from state.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            
        Returns:
            reward: Predicted reward (batch,) or (batch, 1)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate: x = torch.cat([state['z'], state['h']], dim=-1)
        # 2. Pass through network: reward = self.network(x)
        # 3. Squeeze last dimension: reward = reward.squeeze(-1)
        # 4. Return reward
        pass


class ContinuePredictor(nn.Module):
    """
    Predict episode continuation probability.
    
    Outputs probability that episode continues (doesn't terminate).
    
    Args:
        state_dim: Dimension of stochastic state (default: 1024)
        rnn_hidden_dim: Dimension of deterministic state (default: 200)
        hidden_dim: Dimension of hidden layers (default: 400)
        num_layers: Number of hidden layers (default: 4)
        activation: Activation function (default: 'elu')
    """
    
    def __init__(
        self,
        state_dim=1024,
        rnn_hidden_dim=200,
        hidden_dim=400,
        num_layers=4,
        activation='elu'
    ):
        super().__init__()
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement continue predictor
        # Guidelines:
        # - Similar architecture to reward predictor
        # - Output: single logit for binary classification
        # - Use sigmoid to get probability
        #
        # Architecture:
        # latent_dim → hidden_dim → ... → hidden_dim → 1
        #
        # Paper reference: Section 3.1, Continue predictor
        
        # layers = []
        # layers.append(nn.Linear(latent_dim, hidden_dim))
        # layers.append(nn.ELU())
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.ELU())
        # layers.append(nn.Linear(hidden_dim, 1))
        # self.network = nn.Sequential(*layers)
        
        pass  # Remove when implementing
    
    def forward(self, state):
        """
        Predict continuation probability from state.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            
        Returns:
            continue_prob: Probability of continuation (batch,)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate: x = torch.cat([state['z'], state['h']], dim=-1)
        # 2. Pass through network: logit = self.network(x)
        # 3. Apply sigmoid: prob = torch.sigmoid(logit)
        # 4. Squeeze: prob = prob.squeeze(-1)
        # 5. Return probability
        pass


def test_networks():
    """Test DreamerV2 network implementations."""
    print("Testing DreamerV2 Networks...")
    
    # Hyperparameters
    batch_size = 4
    state_dim = 1024  # 32 categoricals × 32 categories
    rnn_hidden_dim = 200
    embed_dim = 1024
    
    # Test encoder
    encoder = ConvEncoder(embed_dim=embed_dim)
    obs = torch.randn(batch_size, 3, 64, 64)
    embed = encoder(obs)
    assert embed.shape == (batch_size, embed_dim)
    print(f"✓ Encoder works: {obs.shape} → {embed.shape}")
    
    # Test decoder
    decoder = ConvDecoder(
        state_dim=state_dim,
        rnn_hidden_dim=rnn_hidden_dim
    )
    state = {
        'z': torch.randn(batch_size, state_dim),
        'h': torch.randn(batch_size, rnn_hidden_dim)
    }
    recon = decoder(state)
    assert recon.shape == (batch_size, 3, 64, 64)
    print(f"✓ Decoder works: latent → {recon.shape}")
    
    # Test reward predictor
    reward_pred = RewardPredictor(
        state_dim=state_dim,
        rnn_hidden_dim=rnn_hidden_dim
    )
    reward = reward_pred(state)
    assert reward.shape == (batch_size,) or reward.shape == (batch_size, 1)
    print(f"✓ Reward predictor works: {reward.shape}")
    
    # Test continue predictor
    continue_pred = ContinuePredictor(
        state_dim=state_dim,
        rnn_hidden_dim=rnn_hidden_dim
    )
    cont = continue_pred(state)
    assert cont.shape == (batch_size,) or cont.shape == (batch_size, 1)
    assert torch.all((cont >= 0) & (cont <= 1))  # Valid probabilities
    print(f"✓ Continue predictor works: {cont.shape}")
    
    # Test gradient flow
    loss = embed.sum() + recon.sum() + reward.sum() + cont.sum()
    loss.backward()
    print(f"✓ Gradients flow through all networks")
    
    print("\n✅ All network tests passed!")
    print("\nImprovements over DreamerV1:")
    print("  - LayerNorm instead of BatchNorm")
    print("  - ELU activations instead of ReLU")
    print("  - Better architectural choices")


if __name__ == "__main__":
    test_networks()

"""
Neural Networks for DreamerV1 World Model

This module contains the encoder, decoder, and prediction networks that work
with the RSSM to form the complete world model.

Components:
1. Encoder: Converts observations (images) to compact embeddings
2. Decoder: Reconstructs observations from latent states
3. Reward Predictor: Predicts rewards from latent states
4. Continue Predictor: Predicts episode termination

Paper: Dream to Control (Hafner et al., 2020)
Section 3.2: Encoding and Reconstruction
Section 3.3: Reward and Continuation Prediction
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvEncoder(nn.Module):
    """
    Convolutional encoder for processing image observations.
    
    Converts high-dimensional observations (64x64x3 images) into compact
    embeddings that the RSSM can work with.
    
    Args:
        obs_shape: Shape of observations (channels, height, width)
        embed_dim: Dimension of output embedding (default: 1024)
    """
    
    def __init__(self, obs_shape=(3, 64, 64), embed_dim=1024):
        super().__init__()
        self.obs_shape = obs_shape
        self.embed_dim = embed_dim
        
        # TODO: Implement convolutional encoder
        # Guidelines:
        # - Input: (batch, 3, 64, 64) RGB images
        # - Use 4 convolutional layers with increasing channels
        # - Typical architecture: 3 → 32 → 64 → 128 → 256
        # - Kernel size 4, stride 2, padding 1 for each conv
        # - ReLU activation after each conv
        # - Final spatial size should be 4x4 with 256 channels
        # - Flatten and project to embed_dim with a linear layer
        #
        # Architecture pattern (each conv reduces spatial dims by 2):
        # 64x64 → 32x32 → 16x16 → 8x8 → 4x4
        #
        # Paper reference: Section 3.2 (Image Encoder)
        
        # Example structure:
        # self.conv = nn.Sequential(
        #     nn.Conv2d(3, 32, kernel_size=4, stride=2, padding=1),
        #     nn.ReLU(),
        #     nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
        #     nn.ReLU(),
        #     ...
        # )
        # self.fc = nn.Linear(256 * 4 * 4, embed_dim)
        
        pass  # Remove when implementing
    
    def forward(self, obs):
        """
        Encode observation to embedding.
        
        Args:
            obs: Observations (batch, channels, height, width)
            
        Returns:
            embed: Embedding (batch, embed_dim)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Pass through convolutional layers
        # 2. Flatten: x = x.view(batch_size, -1)
        # 3. Pass through final linear layer
        # 4. Apply ReLU to final embedding
        
        pass


class ConvDecoder(nn.Module):
    """
    Convolutional decoder for reconstructing observations.
    
    Takes the latent state (h, z) and reconstructs the observation.
    
    Args:
        state_dim: Dimension of stochastic state z
        rnn_hidden_dim: Dimension of deterministic state h
        obs_shape: Shape of output observations (channels, height, width)
    """
    
    def __init__(self, state_dim=30, rnn_hidden_dim=200, obs_shape=(3, 64, 64)):
        super().__init__()
        self.state_dim = state_dim
        self.rnn_hidden_dim = rnn_hidden_dim
        self.obs_shape = obs_shape
        
        # Total latent dimension
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement decoder
        # Guidelines:
        # - Input: concatenation of z and h (state_dim + rnn_hidden_dim)
        # - First project to spatial features: latent_dim → 256 * 4 * 4
        # - Reshape to (batch, 256, 4, 4)
        # - Use 4 transposed convolutions (reverse of encoder)
        # - Architecture: 256 → 128 → 64 → 32 → 3
        # - ConvTranspose2d with kernel=4, stride=2, padding=1
        # - ReLU after each layer except last
        # - Sigmoid at the end to ensure [0, 1] range
        #
        # Paper reference: Section 3.2 (Image Decoder)
        
        # self.fc = nn.Linear(latent_dim, 256 * 4 * 4)
        # self.deconv = nn.Sequential(
        #     nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
        #     nn.ReLU(),
        #     ...
        #     nn.ConvTranspose2d(32, 3, kernel_size=4, stride=2, padding=1),
        #     nn.Sigmoid()
        # )
        
        pass  # Remove when implementing
    
    def forward(self, state):
        """
        Decode latent state to observation.
        
        Args:
            state: Dict with 'z' (batch, state_dim) and 'h' (batch, rnn_hidden_dim)
                   OR tensor (batch, state_dim + rnn_hidden_dim)
            
        Returns:
            obs: Reconstructed observation (batch, channels, height, width)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate z and h
        # 2. Pass through initial FC layer
        # 3. Reshape to (batch, 256, 4, 4)
        # 4. Pass through deconvolutional layers
        
        pass


class DenseDecoder(nn.Module):
    """
    Dense decoder for scalar predictions (rewards, continues, values).
    
    A simple MLP that takes latent states and outputs scalar predictions.
    
    Args:
        state_dim: Dimension of stochastic state z
        rnn_hidden_dim: Dimension of deterministic state h
        hidden_dim: Dimension of hidden layers (default: 400)
        num_layers: Number of hidden layers (default: 4)
        output_dim: Output dimension (default: 1 for scalars)
        output_activation: Activation for output (None, 'sigmoid', 'tanh')
    """
    
    def __init__(
        self,
        state_dim=30,
        rnn_hidden_dim=200,
        hidden_dim=400,
        num_layers=4,
        output_dim=1,
        output_activation=None
    ):
        super().__init__()
        self.output_activation = output_activation
        
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement dense decoder
        # Guidelines:
        # - Input: concatenation of z and h
        # - Build MLP with num_layers hidden layers
        # - Each hidden layer: Linear + ReLU
        # - Hidden dimension: hidden_dim
        # - Output layer: Linear to output_dim
        # - Apply output_activation if specified
        #
        # Architecture:
        # latent_dim → hidden_dim → ... → hidden_dim → output_dim
        #
        # Paper reference: Section 3.3 (Reward and Continuation Predictors)
        
        # Example structure:
        # layers = []
        # layers.append(nn.Linear(latent_dim, hidden_dim))
        # layers.append(nn.ReLU())
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.ReLU())
        # layers.append(nn.Linear(hidden_dim, output_dim))
        # self.model = nn.Sequential(*layers)
        
        pass  # Remove when implementing
    
    def forward(self, state):
        """
        Predict scalar value from latent state.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            
        Returns:
            output: Predicted value (batch, output_dim)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate z and h
        # 2. Pass through MLP
        # 3. Apply output activation if specified:
        #    - 'sigmoid': torch.sigmoid(x)
        #    - 'tanh': torch.tanh(x)
        #    - None: no activation
        
        pass


class RewardPredictor(nn.Module):
    """
    Predict rewards from latent states.
    
    This is a wrapper around DenseDecoder specifically for reward prediction.
    """
    
    def __init__(self, state_dim=30, rnn_hidden_dim=200, hidden_dim=400, num_layers=4):
        super().__init__()
        # TODO: Create DenseDecoder for reward prediction
        # Guidelines:
        # - output_dim = 1 (scalar reward)
        # - No output activation (rewards can be any real value)
        #
        # self.decoder = DenseDecoder(
        #     state_dim=state_dim,
        #     rnn_hidden_dim=rnn_hidden_dim,
        #     hidden_dim=hidden_dim,
        #     num_layers=num_layers,
        #     output_dim=1,
        #     output_activation=None
        # )
        pass
    
    def forward(self, state):
        """Predict reward from state."""
        # return self.decoder(state)
        pass


class ContinuePredictor(nn.Module):
    """
    Predict episode continuation probability from latent states.
    
    Outputs probability that episode continues (1 - done).
    """
    
    def __init__(self, state_dim=30, rnn_hidden_dim=200, hidden_dim=400, num_layers=4):
        super().__init__()
        # TODO: Create DenseDecoder for continuation prediction
        # Guidelines:
        # - output_dim = 1 (probability)
        # - Use 'sigmoid' output activation for [0, 1] probability
        #
        # self.decoder = DenseDecoder(
        #     state_dim=state_dim,
        #     rnn_hidden_dim=rnn_hidden_dim,
        #     hidden_dim=hidden_dim,
        #     num_layers=num_layers,
        #     output_dim=1,
        #     output_activation='sigmoid'
        # )
        pass
    
    def forward(self, state):
        """Predict continuation probability from state."""
        # return self.decoder(state)
        pass


def test_networks():
    """
    Test function to verify network implementations.
    """
    print("Testing DreamerV1 Networks...")
    
    batch_size = 4
    seq_len = 10
    state_dim = 30
    rnn_hidden_dim = 200
    obs_shape = (3, 64, 64)
    
    print("\nTest 1: ConvEncoder")
    # TODO: Uncomment when implemented
    # encoder = ConvEncoder(obs_shape=obs_shape, embed_dim=1024)
    # obs = torch.randn(batch_size, *obs_shape)
    # embed = encoder(obs)
    # assert embed.shape == (batch_size, 1024), f"Encoder output shape: {embed.shape}"
    # print(f"✓ Encoder: {obs.shape} → {embed.shape}")
    
    print("\nTest 2: ConvDecoder")
    # TODO: Uncomment when implemented
    # decoder = ConvDecoder(state_dim=state_dim, rnn_hidden_dim=rnn_hidden_dim, obs_shape=obs_shape)
    # state = {
    #     'z': torch.randn(batch_size, state_dim),
    #     'h': torch.randn(batch_size, rnn_hidden_dim)
    # }
    # recon = decoder(state)
    # assert recon.shape == (batch_size, *obs_shape), f"Decoder output shape: {recon.shape}"
    # assert recon.min() >= 0 and recon.max() <= 1, "Decoder output should be in [0, 1]"
    # print(f"✓ Decoder: latent → {recon.shape}")
    
    print("\nTest 3: RewardPredictor")
    # TODO: Uncomment when implemented
    # reward_predictor = RewardPredictor(state_dim=state_dim, rnn_hidden_dim=rnn_hidden_dim)
    # reward = reward_predictor(state)
    # assert reward.shape == (batch_size, 1), f"Reward shape: {reward.shape}"
    # print(f"✓ Reward Predictor: {reward.shape}")
    
    print("\nTest 4: ContinuePredictor")
    # TODO: Uncomment when implemented
    # continue_predictor = ContinuePredictor(state_dim=state_dim, rnn_hidden_dim=rnn_hidden_dim)
    # cont = continue_predictor(state)
    # assert cont.shape == (batch_size, 1), f"Continue shape: {cont.shape}"
    # assert cont.min() >= 0 and cont.max() <= 1, "Continue should be in [0, 1]"
    # print(f"✓ Continue Predictor: {cont.shape}")
    
    print("\nTest 5: Full pipeline")
    # TODO: Uncomment when implemented
    # # Encode observation
    # obs = torch.randn(batch_size, *obs_shape)
    # embed = encoder(obs)
    # 
    # # Create state
    # state = {
    #     'z': torch.randn(batch_size, state_dim),
    #     'h': torch.randn(batch_size, rnn_hidden_dim)
    # }
    # 
    # # Decode, predict reward and continuation
    # recon = decoder(state)
    # reward = reward_predictor(state)
    # cont = continue_predictor(state)
    # 
    # print(f"✓ Full pipeline:")
    # print(f"  Observation: {obs.shape} → Embedding: {embed.shape}")
    # print(f"  State → Reconstruction: {recon.shape}")
    # print(f"  State → Reward: {reward.shape}")
    # print(f"  State → Continue: {cont.shape}")
    
    print("\nImplementation not complete yet. Uncomment tests when ready.")


if __name__ == "__main__":
    test_networks()

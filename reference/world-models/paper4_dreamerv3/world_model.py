"""
Unified World Model for DreamerV3

DreamerV3 simplifies DreamerV2 while improving robustness and generalization.
The world model is a single unified component with consistent processing.

Key Simplifications:
- Single normalization strategy (symlog)
- Consistent network architecture
- Simplified hyperparameters
- Robust to different domains without tuning

Architecture:
- Deterministic state (h): Recurrent processing
- Stochastic state (z): Categorical distributions (like DreamerV2)
- All predictions use symlog transformation
- Consistent MLP architecture throughout

Paper: Mastering Diverse Domains through World Models (Hafner et al., 2023)
Section 3: Method
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import OneHotCategorical


def symlog(x):
    """Symmetric log transformation."""
    return torch.sign(x) * torch.log(torch.abs(x) + 1)


def symexp(x):
    """Inverse of symlog."""
    return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)


class MLP(nn.Module):
    """
    Standardized MLP used throughout DreamerV3.
    
    All MLPs in DreamerV3 use the same architecture:
    - LayerNorm for normalization
    - SiLU (Swish) activation
    - Consistent initialization
    
    Args:
        input_dim: Input dimension
        output_dim: Output dimension
        hidden_dim: Hidden layer dimension (default: 640)
        num_layers: Number of hidden layers (default: 3)
        layer_norm: Use LayerNorm (default: True)
    """
    
    def __init__(
        self,
        input_dim,
        output_dim,
        hidden_dim=640,
        num_layers=3,
        layer_norm=True
    ):
        super().__init__()
        
        # TODO: Implement standardized MLP
        # Guidelines:
        # - Build layers list
        # - First layer: Linear(input_dim, hidden_dim)
        # - For each hidden layer:
        #   * Apply LayerNorm if enabled
        #   * Apply SiLU activation
        #   * Linear(hidden_dim, hidden_dim)
        # - Final layer: Linear(hidden_dim, output_dim)
        #
        # Paper reference: Section 3, Architecture simplification
        
        # layers = []
        # layers.append(nn.Linear(input_dim, hidden_dim))
        # layers.append(nn.LayerNorm(hidden_dim) if layer_norm else nn.Identity())
        # layers.append(nn.SiLU())
        # 
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.LayerNorm(hidden_dim) if layer_norm else nn.Identity())
        #     layers.append(nn.SiLU())
        # 
        # layers.append(nn.Linear(hidden_dim, output_dim))
        # self.network = nn.Sequential(*layers)
        
        pass  # Remove when implementing
    
    def forward(self, x):
        """Forward pass through MLP."""
        # TODO: Simply pass through network
        # return self.network(x)
        pass


class WorldModel(nn.Module):
    """
    Simplified unified world model for DreamerV3.
    
    Combines all world model components into a single cohesive module:
    - Encoder (CNN to embeddings)
    - RSSM (recurrent + stochastic states)
    - Decoder (embeddings to observations)
    - Reward predictor (with symlog)
    - Continue predictor
    
    All components use consistent architecture and normalization.
    
    Args:
        num_categories: Number of classes per categorical (default: 32)
        num_categoricals: Number of independent categoricals (default: 32)
        rnn_hidden_dim: Dimension of deterministic state (default: 512)
        hidden_dim: Dimension of hidden layers (default: 640)
        mlp_layers: Number of MLP layers (default: 3)
    """
    
    def __init__(
        self,
        num_categories=32,
        num_categoricals=32,
        rnn_hidden_dim=512,
        hidden_dim=640,
        mlp_layers=3
    ):
        super().__init__()
        self.num_categories = num_categories
        self.num_categoricals = num_categoricals
        self.state_dim = num_categories * num_categoricals
        self.rnn_hidden_dim = rnn_hidden_dim
        
        # TODO: Implement unified world model
        # Guidelines:
        # 1. Encoder (CNN): Uses same conv architecture but consistent init
        # 2. RSSM components:
        #    - GRU for recurrence
        #    - MLP for prior: h → categorical logits
        #    - MLP for posterior: (h, obs_embed) → categorical logits
        # 3. Decoder (CNN transpose)
        # 4. Reward predictor (MLP with symlog output)
        # 5. Continue predictor (MLP with sigmoid output)
        #
        # All MLPs use standardized architecture
        #
        # Paper reference: Section 3.1, Unified architecture
        pass
    
    def encode(self, obs):
        """
        Encode observations to embeddings.
        
        Args:
            obs: Observations (batch, 3, 64, 64)
            
        Returns:
            embed: Embeddings (batch, embed_dim)
        """
        # TODO: Implement encoder
        pass
    
    def decode(self, z, h):
        """
        Decode latent state to observation.
        
        Args:
            z: Stochastic state (batch, state_dim)
            h: Deterministic state (batch, rnn_hidden_dim)
            
        Returns:
            obs: Reconstructed observation (batch, 3, 64, 64)
        """
        # TODO: Implement decoder
        pass
    
    def predict_reward(self, z, h):
        """
        Predict reward in symlog space.
        
        Args:
            z: Stochastic state
            h: Deterministic state
            
        Returns:
            reward_symlog: Predicted reward in symlog space
        """
        # TODO: Implement reward prediction
        # Guidelines:
        # - Concatenate z and h
        # - Pass through reward MLP
        # - Output is already in symlog space
        # - Use symexp() to convert back if needed
        pass
    
    def predict_continue(self, z, h):
        """
        Predict episode continuation probability.
        
        Args:
            z: Stochastic state
            h: Deterministic state
            
        Returns:
            continue_prob: Probability of continuation
        """
        # TODO: Implement continue prediction
        pass
    
    def prior(self, h):
        """
        Compute prior p(z | h).
        
        Args:
            h: Deterministic state (batch, rnn_hidden_dim)
            
        Returns:
            z: Sampled stochastic state (batch, state_dim)
            logits: Categorical logits (batch, num_categoricals, num_categories)
        """
        # TODO: Implement prior
        # - Use standardized MLP
        # - Categorical distribution with straight-through gradients
        pass
    
    def posterior(self, h, obs_embed):
        """
        Compute posterior q(z | h, obs).
        
        Args:
            h: Deterministic state
            obs_embed: Observation embedding
            
        Returns:
            z: Sampled stochastic state
            logits: Categorical logits
        """
        # TODO: Implement posterior
        pass
    
    def dynamics_step(self, z_prev, h_prev, action):
        """
        Single step of dynamics: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
        
        Args:
            z_prev: Previous stochastic state
            h_prev: Previous deterministic state
            action: Action
            
        Returns:
            h: New deterministic state
        """
        # TODO: Implement dynamics step
        # - Concatenate z_prev and action
        # - Pass through GRU
        pass
    
    def imagine(self, initial_z, initial_h, policy, horizon):
        """
        Imagine future trajectories using the policy.
        
        Args:
            initial_z: Starting stochastic state
            initial_h: Starting deterministic state
            policy: Policy network
            horizon: Number of steps to imagine
            
        Returns:
            trajectories: Dict with states, actions, rewards, continues
        """
        # TODO: Implement imagination
        # Guidelines:
        # 1. Initialize lists for storage
        # 2. Loop over horizon:
        #    a. Get action from policy
        #    b. Update h using dynamics_step
        #    c. Sample z from prior
        #    d. Predict reward and continue
        #    e. Store everything
        # 3. Return as dict
        pass


def test_world_model():
    """Test unified world model implementation."""
    print("Testing DreamerV3 World Model...")
    
    # Hyperparameters
    batch_size = 4
    horizon = 10
    
    # Create world model
    world_model = WorldModel(
        num_categories=16,  # Smaller for testing
        num_categoricals=16,
        rnn_hidden_dim=256,
        hidden_dim=320
    )
    
    print(f"✓ Created unified world model")
    print(f"  - State dim: {world_model.state_dim}")
    print(f"  - RNN hidden dim: {world_model.rnn_hidden_dim}")
    
    # Test encoder
    obs = torch.randn(batch_size, 3, 64, 64)
    embed = world_model.encode(obs)
    print(f"✓ Encoder works: {obs.shape} → {embed.shape}")
    
    # Test prior/posterior
    h = torch.randn(batch_size, world_model.rnn_hidden_dim)
    z, logits = world_model.prior(h)
    assert z.shape == (batch_size, world_model.state_dim)
    print(f"✓ Prior works: {z.shape}")
    
    z, logits = world_model.posterior(h, embed)
    assert z.shape == (batch_size, world_model.state_dim)
    print(f"✓ Posterior works: {z.shape}")
    
    # Test dynamics
    action = torch.randn(batch_size, 6)
    h_next = world_model.dynamics_step(z, h, action)
    assert h_next.shape == (batch_size, world_model.rnn_hidden_dim)
    print(f"✓ Dynamics step works: {h_next.shape}")
    
    # Test decoder
    obs_recon = world_model.decode(z, h)
    assert obs_recon.shape == (batch_size, 3, 64, 64)
    print(f"✓ Decoder works: {obs_recon.shape}")
    
    # Test reward prediction
    reward = world_model.predict_reward(z, h)
    print(f"✓ Reward prediction works: {reward.shape}")
    
    # Test continue prediction
    cont = world_model.predict_continue(z, h)
    assert torch.all((cont >= 0) & (cont <= 1))
    print(f"✓ Continue prediction works: {cont.shape}")
    
    # Test imagination
    class DummyPolicy:
        def __call__(self, z, h):
            return torch.randn(z.shape[0], 6)
    
    policy = DummyPolicy()
    trajectories = world_model.imagine(z, h, policy, horizon)
    print(f"✓ Imagination works")
    
    print("\n✅ All world model tests passed!")
    print("\nSimplifications in DreamerV3:")
    print("  - Single unified world model class")
    print("  - Standardized MLP architecture")
    print("  - Consistent symlog transformation")
    print("  - Simplified hyperparameters")


if __name__ == "__main__":
    test_world_model()

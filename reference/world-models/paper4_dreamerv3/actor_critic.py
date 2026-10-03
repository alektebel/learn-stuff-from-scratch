"""
Robust Actor-Critic for DreamerV3

DreamerV3 uses simplified and robust actor-critic learning that works
across diverse domains without hyperparameter tuning.

Key Features:
- Symlog value predictions for robustness
- Percentile normalization for returns
- Simplified loss functions
- Consistent architecture

Paper: Mastering Diverse Domains through World Models (Hafner et al., 2023)
Section 3.2: Behavior Learning
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, Independent, TanhTransform, TransformedDistribution


def symlog(x):
    """Symmetric log transformation."""
    return torch.sign(x) * torch.log(torch.abs(x) + 1)


def symexp(x):
    """Inverse of symlog."""
    return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)


class Actor(nn.Module):
    """
    Robust actor network with symlog support.
    
    Uses standardized MLP architecture and outputs tanh-transformed Gaussian.
    
    Args:
        state_dim: Stochastic state dimension (default: 1024)
        rnn_hidden_dim: Deterministic state dimension (default: 512)
        action_dim: Action space dimension
        hidden_dim: Hidden layer dimension (default: 640)
        num_layers: Number of layers (default: 3)
        min_std: Minimum standard deviation (default: 0.1)
        max_std: Maximum standard deviation (default: 1.0)
    """
    
    def __init__(
        self,
        state_dim=1024,
        rnn_hidden_dim=512,
        action_dim=None,
        hidden_dim=640,
        num_layers=3,
        min_std=0.1,
        max_std=1.0
    ):
        super().__init__()
        self.action_dim = action_dim
        self.min_std = min_std
        self.max_std = max_std
        
        input_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement robust actor
        # Guidelines:
        # - Use standardized MLP (LayerNorm + SiLU)
        # - Output mean and std for Gaussian
        # - Apply tanh transform to bound actions
        #
        # from world_model import MLP
        # self.trunk = MLP(input_dim, hidden_dim, hidden_dim, num_layers)
        # self.mean_head = nn.Linear(hidden_dim, action_dim)
        # self.std_head = nn.Linear(hidden_dim, action_dim)
        
        pass  # Remove when implementing
    
    def forward(self, z, h, deterministic=False):
        """
        Compute action distribution.
        
        Args:
            z: Stochastic state
            h: Deterministic state
            deterministic: If True, return mean action
            
        Returns:
            action: Sampled action
            action_dist: Distribution over actions
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Concatenate z and h
        # 2. Pass through trunk
        # 3. Compute mean and std
        # 4. Create TanhNormal distribution
        # 5. Sample or return mean
        pass


class Critic(nn.Module):
    """
    Robust critic network with symlog predictions.
    
    Predicts values in symlog space for numerical stability.
    
    Args:
        state_dim: Stochastic state dimension (default: 1024)
        rnn_hidden_dim: Deterministic state dimension (default: 512)
        hidden_dim: Hidden layer dimension (default: 640)
        num_layers: Number of layers (default: 3)
        num_bins: Number of bins for distributional critic (default: 255)
    """
    
    def __init__(
        self,
        state_dim=1024,
        rnn_hidden_dim=512,
        hidden_dim=640,
        num_layers=3,
        num_bins=255
    ):
        super().__init__()
        self.num_bins = num_bins
        
        input_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement robust critic
        # Guidelines:
        # - Use standardized MLP
        # - Output value in symlog space
        # - Optionally: use distributional critic with bins
        #
        # from world_model import MLP
        # self.network = MLP(input_dim, 1, hidden_dim, num_layers)
        
        pass  # Remove when implementing
    
    def forward(self, z, h):
        """
        Predict value in symlog space.
        
        Args:
            z: Stochastic state
            h: Deterministic state
            
        Returns:
            value_symlog: Value in symlog space
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Concatenate z and h
        # 2. Pass through network
        # 3. Output is in symlog space
        pass


def compute_returns(
    rewards,
    values,
    continues,
    gamma=0.997,
    lambda_=0.95
):
    """
    Compute lambda returns with symlog normalization.
    
    DreamerV3 computes returns in the original scale (not symlog).
    
    Args:
        rewards: Predicted rewards (already in original scale)
        values: Predicted values (in symlog space)
        continues: Continuation probabilities
        gamma: Discount factor (default: 0.997, slightly higher than V2)
        lambda_: Lambda parameter
        
    Returns:
        returns: Lambda returns (in original scale)
    """
    # TODO: Implement return computation
    # Guidelines:
    # 1. Convert values from symlog to original scale
    #    values_orig = symexp(values)
    # 
    # 2. Compute lambda returns (same as DreamerV2)
    #    Use backward iteration
    # 
    # 3. Returns are in original scale
    #
    # Paper reference: Section 3.2
    pass


def percentile_normalize(returns, percentile=95):
    """
    Normalize returns using percentile for robustness.
    
    DreamerV3 uses percentile normalization instead of mean/std
    to be robust to outliers.
    
    Args:
        returns: Returns to normalize
        percentile: Percentile to use (default: 95)
        
    Returns:
        normalized: Normalized returns
    """
    # TODO: Implement percentile normalization
    # Guidelines:
    # 1. Compute percentile: scale = torch.quantile(torch.abs(returns), percentile/100.0)
    # 2. Normalize: normalized = returns / torch.maximum(scale, torch.tensor(1.0))
    # 3. Return normalized returns
    #
    # This is more robust than mean/std normalization
    pass


def compute_actor_loss(
    actor,
    trajectories,
    returns,
    entropy_coef=3e-4
):
    """
    Compute robust actor loss.
    
    Args:
        actor: Actor network
        trajectories: Dict with z, h sequences
        returns: Target returns (percentile normalized)
        entropy_coef: Entropy regularization coefficient
        
    Returns:
        loss: Actor loss
        info: Logging dict
    """
    # TODO: Implement actor loss
    # Guidelines:
    # - Similar to DreamerV2 but with percentile-normalized returns
    # - Use reinforce-style policy gradient
    pass


def compute_critic_loss(
    critic,
    trajectories,
    returns
):
    """
    Compute robust critic loss.
    
    Critic predicts values in symlog space.
    
    Args:
        critic: Critic network
        trajectories: Dict with z, h sequences
        returns: Target returns (in original scale)
        
    Returns:
        loss: Critic loss
        info: Logging dict
    """
    # TODO: Implement critic loss
    # Guidelines:
    # 1. Get value predictions in symlog space
    # 2. Convert returns to symlog space
    # 3. Compute MSE in symlog space
    # 4. This provides better numerical stability
    pass


def test_actor_critic():
    """Test DreamerV3 actor-critic."""
    print("Testing DreamerV3 Actor-Critic...")
    
    batch_size = 4
    horizon = 15
    state_dim = 1024
    rnn_hidden_dim = 512
    action_dim = 6
    
    # Create networks
    actor = Actor(state_dim, rnn_hidden_dim, action_dim)
    critic = Critic(state_dim, rnn_hidden_dim)
    
    print(f"✓ Created robust actor and critic")
    
    # Test actor
    z = torch.randn(batch_size, state_dim)
    h = torch.randn(batch_size, rnn_hidden_dim)
    action, dist = actor(z, h)
    assert action.shape == (batch_size, action_dim)
    print(f"✓ Actor works: {action.shape}")
    
    # Test critic
    value_symlog = critic(z, h)
    print(f"✓ Critic works: {value_symlog.shape}")
    
    # Test returns computation
    rewards = torch.randn(batch_size, horizon)
    values = torch.randn(batch_size, horizon + 1)
    continues = torch.ones(batch_size, horizon)
    returns = compute_returns(rewards, values, continues)
    print(f"✓ Returns computed: {returns.shape}")
    
    # Test percentile normalization
    normalized = percentile_normalize(returns)
    print(f"✓ Percentile normalization works")
    print(f"  Original range: [{returns.min():.2f}, {returns.max():.2f}]")
    print(f"  Normalized range: [{normalized.min():.2f}, {normalized.max():.2f}]")
    
    # Test symlog/symexp
    x = torch.tensor([-100.0, -1.0, 0.0, 1.0, 100.0])
    y = symlog(x)
    x_recon = symexp(y)
    assert torch.allclose(x, x_recon, atol=1e-5)
    print(f"✓ Symlog transformation works")
    
    print("\n✅ All actor-critic tests passed!")
    print("\nRobustness improvements:")
    print("  - Symlog value predictions")
    print("  - Percentile normalization")
    print("  - Simplified architecture")


if __name__ == "__main__":
    test_actor_critic()

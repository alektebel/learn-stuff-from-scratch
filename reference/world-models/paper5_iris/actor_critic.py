"""
Transformer-based Policy for IRIS

IRIS uses transformers not just for world modeling but also for the policy.
This enables better credit assignment and long-term planning.

Architecture:
- Processes history of observations and actions
- Outputs action distribution
- Can attend to long context

Paper: Transformers are Sample Efficient World Models (Robine et al., 2023)
Section 3.3: Actor-Critic
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, Independent


class TransformerActor(nn.Module):
    """
    Transformer-based actor network.
    
    Uses transformer to process observation history and output actions.
    
    Args:
        num_obs_tokens: Size of observation vocabulary
        num_actions: Dimension of action space
        embed_dim: Embedding dimension (default: 256)
        num_layers: Number of transformer layers (default: 4)
        num_heads: Number of attention heads (default: 4)
        max_seq_len: Maximum sequence length (default: 100)
    """
    
    def __init__(
        self,
        num_obs_tokens=4096,
        num_actions=6,
        embed_dim=256,
        num_layers=4,
        num_heads=4,
        max_seq_len=100
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_actions = num_actions
        
        # TODO: Implement transformer actor
        # Guidelines:
        # - Similar to world model transformer
        # - Embed observation tokens
        # - Process with transformer
        # - Output mean and std for Gaussian policy
        #
        # from transformer import TransformerBlock
        # 
        # self.obs_embedding = nn.Embedding(num_obs_tokens, embed_dim)
        # self.pos_embedding = nn.Parameter(torch.zeros(1, max_seq_len, embed_dim))
        # 
        # self.blocks = nn.ModuleList([
        #     TransformerBlock(embed_dim, num_heads)
        #     for _ in range(num_layers)
        # ])
        # 
        # self.ln_f = nn.LayerNorm(embed_dim)
        # self.mean_head = nn.Linear(embed_dim, num_actions)
        # self.std_head = nn.Linear(embed_dim, num_actions)
        
        pass  # Remove when implementing
    
    def forward(self, obs_tokens, deterministic=False):
        """
        Compute action distribution from observation history.
        
        Args:
            obs_tokens: Observation tokens (batch, seq_len, 16, 16)
            deterministic: If True, return mean action
            
        Returns:
            action: Sampled action (batch, num_actions)
            action_dist: Distribution over actions
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Embed observations (flatten spatial dimensions)
        # 2. Add positional encoding
        # 3. Pass through transformer blocks
        # 4. Take last position output
        # 5. Compute mean and std
        # 6. Create and sample from distribution
        pass


class TransformerCritic(nn.Module):
    """
    Transformer-based critic network.
    
    Estimates value of observation history using transformer.
    
    Args:
        num_obs_tokens: Size of observation vocabulary
        embed_dim: Embedding dimension (default: 256)
        num_layers: Number of transformer layers (default: 4)
        num_heads: Number of attention heads (default: 4)
        max_seq_len: Maximum sequence length (default: 100)
    """
    
    def __init__(
        self,
        num_obs_tokens=4096,
        embed_dim=256,
        num_layers=4,
        num_heads=4,
        max_seq_len=100
    ):
        super().__init__()
        self.embed_dim = embed_dim
        
        # TODO: Implement transformer critic
        # Guidelines:
        # - Similar to actor but output single value
        # - Process observation history
        # - Output value estimate
        #
        # from transformer import TransformerBlock
        # 
        # self.obs_embedding = nn.Embedding(num_obs_tokens, embed_dim)
        # self.pos_embedding = nn.Parameter(torch.zeros(1, max_seq_len, embed_dim))
        # 
        # self.blocks = nn.ModuleList([
        #     TransformerBlock(embed_dim, num_heads)
        #     for _ in range(num_layers)
        # ])
        # 
        # self.ln_f = nn.LayerNorm(embed_dim)
        # self.value_head = nn.Linear(embed_dim, 1)
        
        pass  # Remove when implementing
    
    def forward(self, obs_tokens):
        """
        Estimate value of observation history.
        
        Args:
            obs_tokens: Observation tokens (batch, seq_len, 16, 16)
            
        Returns:
            value: Value estimate (batch,)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Embed observations
        # 2. Add positional encoding
        # 3. Pass through transformer
        # 4. Take last position
        # 5. Compute value
        pass


def compute_actor_loss(
    actor,
    obs_tokens,
    returns,
    entropy_coef=1e-4
):
    """
    Compute actor loss for transformer policy.
    
    Args:
        actor: Transformer actor
        obs_tokens: Observation token sequences
        returns: Target returns
        entropy_coef: Entropy regularization
        
    Returns:
        loss: Actor loss
        info: Logging dict
    """
    # TODO: Implement actor loss
    # Guidelines:
    # - Similar to DreamerV3 but with transformer
    # - Policy gradient with entropy regularization
    pass


def compute_critic_loss(
    critic,
    obs_tokens,
    returns
):
    """
    Compute critic loss for transformer value network.
    
    Args:
        critic: Transformer critic
        obs_tokens: Observation token sequences
        returns: Target returns
        
    Returns:
        loss: Critic loss
        info: Logging dict
    """
    # TODO: Implement critic loss
    # Guidelines:
    # - MSE between predicted and target values
    pass


def test_transformer_actor_critic():
    """Test transformer-based actor-critic."""
    print("Testing Transformer Actor-Critic...")
    
    batch_size = 2
    seq_len = 10
    num_obs_tokens = 512
    num_actions = 6
    embed_dim = 128
    
    # Create networks
    actor = TransformerActor(
        num_obs_tokens=num_obs_tokens,
        num_actions=num_actions,
        embed_dim=embed_dim,
        num_layers=2,
        num_heads=4
    )
    
    critic = TransformerCritic(
        num_obs_tokens=num_obs_tokens,
        embed_dim=embed_dim,
        num_layers=2,
        num_heads=4
    )
    
    print(f"✓ Created transformer actor and critic")
    
    # Test actor
    obs_tokens = torch.randint(0, num_obs_tokens, (batch_size, seq_len, 16, 16))
    action, dist = actor(obs_tokens)
    assert action.shape == (batch_size, num_actions)
    print(f"✓ Transformer actor works: {action.shape}")
    
    # Test critic
    value = critic(obs_tokens)
    assert value.shape == (batch_size,) or value.shape == (batch_size, 1)
    print(f"✓ Transformer critic works: {value.shape}")
    
    # Test with different sequence lengths
    obs_tokens_short = torch.randint(0, num_obs_tokens, (batch_size, 5, 16, 16))
    action_short, _ = actor(obs_tokens_short)
    value_short = critic(obs_tokens_short)
    print(f"✓ Works with variable sequence lengths")
    
    # Test gradients
    loss = action.sum() + value.sum()
    loss.backward()
    print(f"✓ Gradients flow through transformer actor-critic")
    
    print("\n✅ All transformer actor-critic tests passed!")
    print("\nAdvantages of transformer policy:")
    print("  - Can attend to long history")
    print("  - Better credit assignment")
    print("  - Parallel training")
    print("  - State-of-the-art in many domains")


if __name__ == "__main__":
    test_transformer_actor_critic()

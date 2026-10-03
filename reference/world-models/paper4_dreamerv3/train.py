"""
DreamerV3 Training Script

Simplified and robust training across diverse domains.

Key features:
- Single set of hyperparameters works everywhere
- Symlog predictions for all scales
- Percentile normalization
- Robust optimization

Paper: Mastering Diverse Domains through World Models (Hafner et al., 2023)
Section 3: Method
"""

import torch
import torch.nn as nn
import torch.optim as optim

from world_model import WorldModel
from actor_critic import Actor, Critic, compute_returns, percentile_normalize
from symlog import symlog, symexp


class DreamerV3:
    """
    Complete DreamerV3 implementation.
    
    Simplifications over DreamerV2:
    - Unified world model
    - Single set of hyperparameters
    - Consistent symlog usage
    - Robust to different domains
    
    Args:
        action_dim: Dimension of action space
        num_categories: Categories per categorical (default: 32)
        num_categoricals: Number of categoricals (default: 32)
        rnn_hidden_dim: Deterministic state dim (default: 512)
        hidden_dim: MLP hidden dim (default: 640)
        learning_rate: Single LR for all components (default: 1e-4)
        gamma: Discount factor (default: 0.997)
        lambda_: Lambda for returns (default: 0.95)
        imagination_horizon: Steps to imagine (default: 15)
        entropy_coef: Entropy regularization (default: 3e-4)
        kl_coef: KL regularization (default: 1.0)
        free_nats: Free nats (default: 1.0)
    """
    
    def __init__(
        self,
        action_dim,
        num_categories=32,
        num_categoricals=32,
        rnn_hidden_dim=512,
        hidden_dim=640,
        learning_rate=1e-4,
        gamma=0.997,
        lambda_=0.95,
        imagination_horizon=15,
        entropy_coef=3e-4,
        kl_coef=1.0,
        free_nats=1.0
    ):
        self.action_dim = action_dim
        self.gamma = gamma
        self.lambda_ = lambda_
        self.imagination_horizon = imagination_horizon
        self.entropy_coef = entropy_coef
        self.kl_coef = kl_coef
        self.free_nats = free_nats
        
        # TODO: Initialize components
        # Guidelines:
        # 1. Create world model
        # 2. Create actor
        # 3. Create critic
        # 4. Create single optimizer for all parameters (simplification!)
        #
        # self.world_model = WorldModel(...)
        # self.actor = Actor(...)
        # self.critic = Critic(...)
        # 
        # all_params = (
        #     list(self.world_model.parameters()) +
        #     list(self.actor.parameters()) +
        #     list(self.critic.parameters())
        # )
        # self.optimizer = optim.Adam(all_params, lr=learning_rate)
        
        pass  # Remove when implementing
    
    def train_step(self, observations, actions, rewards, terminals):
        """
        Single training step on batch of sequences.
        
        DreamerV3 trains world model and behavior jointly in one step.
        
        Args:
            observations: (batch, seq_len, 3, 64, 64)
            actions: (batch, seq_len, action_dim)
            rewards: (batch, seq_len)
            terminals: (batch, seq_len)
            
        Returns:
            losses: Dict of all loss components
        """
        # TODO: Implement unified training step
        # Guidelines:
        # 1. Encode observations
        # 2. Rollout world model through sequence
        # 3. Compute world model losses:
        #    - Reconstruction loss
        #    - Reward loss (with symlog)
        #    - Continue loss
        #    - KL loss (with free nats)
        # 4. Imagine trajectories for actor-critic
        # 5. Compute returns with percentile normalization
        # 6. Compute actor loss
        # 7. Compute critic loss (with symlog predictions)
        # 8. Total loss and single optimization step
        # 9. Return all losses for logging
        #
        # Paper reference: Section 3, Algorithm
        pass
    
    def select_action(self, observation, state=None, deterministic=False):
        """
        Select action for environment interaction.
        
        Args:
            observation: Current observation (3, 64, 64)
            state: Previous state dict {'z': z, 'h': h}
            deterministic: If True, use mean action
            
        Returns:
            action: Selected action
            new_state: Updated state dict
        """
        # TODO: Implement action selection
        # Guidelines:
        # 1. Encode observation
        # 2. Update state (posterior if first step, prior otherwise)
        # 3. Get action from actor
        # 4. Return action and new state
        pass
    
    def save(self, path):
        """Save model checkpoint."""
        torch.save({
            'world_model': self.world_model.state_dict(),
            'actor': self.actor.state_dict(),
            'critic': self.critic.state_dict(),
            'optimizer': self.optimizer.state_dict()
        }, path)
    
    def load(self, path):
        """Load model checkpoint."""
        checkpoint = torch.load(path)
        self.world_model.load_state_dict(checkpoint['world_model'])
        self.actor.load_state_dict(checkpoint['actor'])
        self.critic.load_state_dict(checkpoint['critic'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])


def test_dreamerv3():
    """Test DreamerV3 implementation."""
    print("Testing DreamerV3...")
    
    # Hyperparameters
    batch_size = 2
    seq_len = 10
    action_dim = 6
    
    # Create agent
    agent = DreamerV3(
        action_dim=action_dim,
        num_categories=8,  # Smaller for testing
        num_categoricals=8,
        hidden_dim=128
    )
    
    print(f"✓ Created DreamerV3 agent")
    
    # Test training step
    observations = torch.randn(batch_size, seq_len, 3, 64, 64)
    actions = torch.randn(batch_size, seq_len, action_dim)
    rewards = torch.randn(batch_size, seq_len)
    terminals = torch.zeros(batch_size, seq_len)
    
    losses = agent.train_step(observations, actions, rewards, terminals)
    print(f"✓ Training step works")
    print(f"  Losses: {losses}")
    
    # Test action selection
    observation = torch.randn(3, 64, 64)
    action, state = agent.select_action(observation)
    print(f"✓ Action selection works: {action.shape}")
    
    # Test continued action selection
    observation2 = torch.randn(3, 64, 64)
    action2, state2 = agent.select_action(observation2, state)
    print(f"✓ Continued action selection works")
    
    # Test save/load
    agent.save('/tmp/dreamerv3_test.pt')
    agent.load('/tmp/dreamerv3_test.pt')
    print(f"✓ Save/load works")
    
    print("\n✅ All DreamerV3 tests passed!")
    print("\nKey simplifications:")
    print("  - Single optimizer for all components")
    print("  - Single learning rate")
    print("  - Unified world model")
    print("  - Works across domains without tuning")


if __name__ == "__main__":
    test_dreamerv3()

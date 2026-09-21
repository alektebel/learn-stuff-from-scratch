"""
IRIS Training Script

Integrates tokenizer, transformer world model, and transformer policy
for complete training loop.

Key features:
- Autoregressive world modeling
- Transformer-based policy
- Efficient token-based training

Paper: Transformers are Sample Efficient World Models (Robine et al., 2023)
Section 3: Method
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

from tokenizer import VQVAETokenizer
from transformer import WorldModelTransformer
from actor_critic import TransformerActor, TransformerCritic


class IRIS:
    """
    Complete IRIS implementation.
    
    Combines VQ-VAE tokenizer, transformer world model, and transformer policy.
    
    Args:
        action_dim: Dimension of action space
        num_embeddings: VQ-VAE codebook size (default: 4096)
        embedding_dim: VQ-VAE embedding dim (default: 256)
        model_embed_dim: World model embedding dim (default: 512)
        policy_embed_dim: Policy embedding dim (default: 256)
        model_layers: World model transformer layers (default: 6)
        policy_layers: Policy transformer layers (default: 4)
        tokenizer_lr: Tokenizer learning rate (default: 3e-4)
        model_lr: World model learning rate (default: 1e-4)
        policy_lr: Policy learning rate (default: 3e-4)
        gamma: Discount factor (default: 0.99)
        lambda_: Lambda for returns (default: 0.95)
        imagination_horizon: Steps to imagine (default: 15)
    """
    
    def __init__(
        self,
        action_dim,
        num_embeddings=4096,
        embedding_dim=256,
        model_embed_dim=512,
        policy_embed_dim=256,
        model_layers=6,
        policy_layers=4,
        tokenizer_lr=3e-4,
        model_lr=1e-4,
        policy_lr=3e-4,
        gamma=0.99,
        lambda_=0.95,
        imagination_horizon=15
    ):
        self.action_dim = action_dim
        self.gamma = gamma
        self.lambda_ = lambda_
        self.imagination_horizon = imagination_horizon
        
        # TODO: Initialize components
        # Guidelines:
        # 1. Create tokenizer
        # 2. Create world model transformer
        # 3. Create actor transformer
        # 4. Create critic transformer
        # 5. Create separate optimizers for each component
        #
        # self.tokenizer = VQVAETokenizer(num_embeddings, embedding_dim)
        # self.world_model = WorldModelTransformer(
        #     num_obs_tokens=num_embeddings,
        #     num_actions=action_dim,
        #     embed_dim=model_embed_dim,
        #     num_layers=model_layers
        # )
        # self.actor = TransformerActor(
        #     num_obs_tokens=num_embeddings,
        #     num_actions=action_dim,
        #     embed_dim=policy_embed_dim,
        #     num_layers=policy_layers
        # )
        # self.critic = TransformerCritic(
        #     num_obs_tokens=num_embeddings,
        #     embed_dim=policy_embed_dim,
        #     num_layers=policy_layers
        # )
        # 
        # self.tokenizer_optimizer = optim.Adam(self.tokenizer.parameters(), lr=tokenizer_lr)
        # self.model_optimizer = optim.Adam(self.world_model.parameters(), lr=model_lr)
        # self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=policy_lr)
        # self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=policy_lr)
        
        pass  # Remove when implementing
    
    def train_tokenizer(self, observations):
        """
        Train VQ-VAE tokenizer on observations.
        
        Args:
            observations: (batch, seq_len, 3, 64, 64)
            
        Returns:
            losses: Dict of loss values
        """
        # TODO: Implement tokenizer training
        # Guidelines:
        # 1. Flatten sequence dimension
        # 2. Pass through tokenizer
        # 3. Compute reconstruction loss + VQ loss
        # 4. Backprop and update
        # 5. Return losses
        pass
    
    def train_world_model(self, observations, actions, rewards):
        """
        Train world model transformer on sequences.
        
        Args:
            observations: (batch, seq_len, 3, 64, 64)
            actions: (batch, seq_len, action_dim)
            rewards: (batch, seq_len)
            
        Returns:
            losses: Dict of loss values
        """
        # TODO: Implement world model training
        # Guidelines:
        # 1. Tokenize observations (detach from tokenizer gradients)
        # 2. Pass through world model
        # 3. Compute observation prediction loss (cross-entropy)
        # 4. Compute reward prediction loss (MSE)
        # 5. Total loss and backprop
        # 6. Return losses
        pass
    
    def train_actor_critic(self, initial_obs):
        """
        Train actor-critic on imagined trajectories.
        
        Args:
            initial_obs: Starting observations (batch, 3, 64, 64)
            
        Returns:
            losses: Dict of loss values
        """
        # TODO: Implement actor-critic training
        # Guidelines:
        # 1. Tokenize initial observations
        # 2. Imagine trajectories using world model and current policy
        # 3. Decode imagined tokens to compute rewards
        # 4. Compute lambda returns
        # 5. Train actor with policy gradient
        # 6. Train critic with value regression
        # 7. Return losses
        pass
    
    def select_action(self, observation, obs_history=None):
        """
        Select action for environment interaction.
        
        Args:
            observation: Current observation (3, 64, 64)
            obs_history: Previous observation tokens (seq_len, 16, 16)
            
        Returns:
            action: Selected action
            new_obs_history: Updated observation history
        """
        # TODO: Implement action selection
        # Guidelines:
        # 1. Tokenize observation
        # 2. Append to history (or create new history)
        # 3. Get action from transformer actor
        # 4. Return action and updated history
        pass
    
    def save(self, path):
        """Save model checkpoint."""
        torch.save({
            'tokenizer': self.tokenizer.state_dict(),
            'world_model': self.world_model.state_dict(),
            'actor': self.actor.state_dict(),
            'critic': self.critic.state_dict(),
            'tokenizer_optimizer': self.tokenizer_optimizer.state_dict(),
            'model_optimizer': self.model_optimizer.state_dict(),
            'actor_optimizer': self.actor_optimizer.state_dict(),
            'critic_optimizer': self.critic_optimizer.state_dict()
        }, path)
    
    def load(self, path):
        """Load model checkpoint."""
        checkpoint = torch.load(path)
        self.tokenizer.load_state_dict(checkpoint['tokenizer'])
        self.world_model.load_state_dict(checkpoint['world_model'])
        self.actor.load_state_dict(checkpoint['actor'])
        self.critic.load_state_dict(checkpoint['critic'])
        self.tokenizer_optimizer.load_state_dict(checkpoint['tokenizer_optimizer'])
        self.model_optimizer.load_state_dict(checkpoint['model_optimizer'])
        self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer'])
        self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer'])


def test_iris():
    """Test IRIS implementation."""
    print("Testing IRIS...")
    
    # Hyperparameters
    batch_size = 2
    seq_len = 5
    action_dim = 6
    
    # Create agent
    agent = IRIS(
        action_dim=action_dim,
        num_embeddings=512,  # Smaller for testing
        model_layers=2,
        policy_layers=2
    )
    
    print(f"✓ Created IRIS agent")
    
    # Test tokenizer training
    observations = torch.randn(batch_size, seq_len, 3, 64, 64)
    tok_losses = agent.train_tokenizer(observations)
    print(f"✓ Tokenizer training works")
    print(f"  Losses: {tok_losses}")
    
    # Test world model training
    actions = torch.randn(batch_size, seq_len, action_dim)
    rewards = torch.randn(batch_size, seq_len)
    wm_losses = agent.train_world_model(observations, actions, rewards)
    print(f"✓ World model training works")
    print(f"  Losses: {wm_losses}")
    
    # Test actor-critic training
    initial_obs = observations[:, 0]
    ac_losses = agent.train_actor_critic(initial_obs)
    print(f"✓ Actor-critic training works")
    print(f"  Losses: {ac_losses}")
    
    # Test action selection
    observation = torch.randn(3, 64, 64)
    action, history = agent.select_action(observation)
    print(f"✓ Action selection works: {action.shape}")
    
    # Test continued action selection
    observation2 = torch.randn(3, 64, 64)
    action2, history2 = agent.select_action(observation2, history)
    print(f"✓ Continued action selection works")
    
    # Test save/load
    agent.save('/tmp/iris_test.pt')
    agent.load('/tmp/iris_test.pt')
    print(f"✓ Save/load works")
    
    print("\n✅ All IRIS tests passed!")
    print("\nKey components:")
    print("  - VQ-VAE tokenizer for discrete observations")
    print("  - Transformer world model for dynamics")
    print("  - Transformer policy for actions")
    print("  - Autoregressive training")


if __name__ == "__main__":
    test_iris()

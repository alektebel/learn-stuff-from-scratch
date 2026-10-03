"""
DreamerV2 Training Script

Integrates all components for end-to-end training with:
- KL balancing for stable discrete representations
- Symlog predictions for reward normalization
- Improved training dynamics

Paper: Mastering Atari with Discrete World Models (Hafner et al., 2021)
Section 3: Algorithm
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from collections import deque

from rssm import DiscreteRSSM
from networks import ConvEncoder, ConvDecoder, RewardPredictor, ContinuePredictor
from actor_critic import Actor, Critic, compute_lambda_returns, compute_actor_loss, compute_critic_loss


def symlog(x):
    """
    Symmetric logarithm transformation for reward normalization.
    
    symlog(x) = sign(x) * log(|x| + 1)
    
    Benefits:
    - Normalizes rewards across different scales
    - Preserves sign (unlike log)
    - Smooth around zero
    
    Args:
        x: Input tensor
        
    Returns:
        transformed: Symlog-transformed tensor
    """
    # TODO: Implement symlog
    # Guidelines:
    # - return torch.sign(x) * torch.log(torch.abs(x) + 1)
    pass


def symexp(x):
    """
    Inverse of symlog transformation.
    
    symexp(x) = sign(x) * (exp(|x|) - 1)
    
    Args:
        x: Symlog-transformed tensor
        
    Returns:
        original: Original scale tensor
    """
    # TODO: Implement symexp
    # Guidelines:
    # - return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)
    pass


class DreamerV2:
    """
    Complete DreamerV2 implementation.
    
    Key improvements over DreamerV1:
    - Discrete RSSM with categorical distributions
    - KL balancing for stable training
    - Symlog predictions for reward normalization
    - Improved network architectures
    
    Args:
        action_dim: Dimension of action space
        num_categories: Number of classes per categorical (default: 32)
        num_categoricals: Number of independent categoricals (default: 32)
        rnn_hidden_dim: Dimension of deterministic state (default: 200)
        embed_dim: Dimension of observation embedding (default: 1024)
        hidden_dim: Dimension of hidden layers (default: 400)
        actor_layers: Number of actor layers (default: 4)
        critic_layers: Number of critic layers (default: 4)
        world_model_lr: Learning rate for world model (default: 3e-4)
        actor_lr: Learning rate for actor (default: 8e-5)
        critic_lr: Learning rate for critic (default: 8e-5)
        kl_balance: KL balancing coefficient (default: 0.8)
        free_nats: Free nats for KL loss (default: 1.0)
        gamma: Discount factor (default: 0.99)
        lambda_: Lambda for returns (default: 0.95)
        imagination_horizon: Steps to imagine (default: 15)
        use_symlog: Use symlog for rewards (default: True)
    """
    
    def __init__(
        self,
        action_dim,
        num_categories=32,
        num_categoricals=32,
        rnn_hidden_dim=200,
        embed_dim=1024,
        hidden_dim=400,
        actor_layers=4,
        critic_layers=4,
        world_model_lr=3e-4,
        actor_lr=8e-5,
        critic_lr=8e-5,
        kl_balance=0.8,
        free_nats=1.0,
        gamma=0.99,
        lambda_=0.95,
        imagination_horizon=15,
        use_symlog=True
    ):
        self.action_dim = action_dim
        self.gamma = gamma
        self.lambda_ = lambda_
        self.imagination_horizon = imagination_horizon
        self.use_symlog = use_symlog
        self.kl_balance = kl_balance
        self.free_nats = free_nats
        
        # TODO: Initialize networks
        # Guidelines:
        # 1. Create RSSM: self.rssm = DiscreteRSSM(...)
        # 2. Create encoder: self.encoder = ConvEncoder(...)
        # 3. Create decoder: self.decoder = ConvDecoder(...)
        # 4. Create reward predictor: self.reward_predictor = RewardPredictor(...)
        # 5. Create continue predictor: self.continue_predictor = ContinuePredictor(...)
        # 6. Create actor: self.actor = Actor(...)
        # 7. Create critic: self.critic = Critic(...)
        pass
        
        # TODO: Initialize optimizers
        # Guidelines:
        # 1. World model parameters include: encoder, decoder, rssm, reward_predictor, continue_predictor
        # 2. Create world_model_optimizer with world_model_lr
        # 3. Create actor_optimizer with actor_lr
        # 4. Create critic_optimizer with critic_lr
        #
        # world_model_params = (
        #     list(self.encoder.parameters()) +
        #     list(self.decoder.parameters()) +
        #     list(self.rssm.parameters()) +
        #     list(self.reward_predictor.parameters()) +
        #     list(self.continue_predictor.parameters())
        # )
        # self.world_model_optimizer = optim.Adam(world_model_params, lr=world_model_lr)
        # self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=actor_lr)
        # self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=critic_lr)
        pass
    
    def train_world_model(self, observations, actions):
        """
        Train world model on batch of sequences.
        
        Args:
            observations: (batch, seq_len, 3, 64, 64)
            actions: (batch, seq_len, action_dim)
            
        Returns:
            losses: Dict of loss values
        """
        # TODO: Implement world model training
        # Guidelines:
        # 1. Encode observations:
        #    batch_size, seq_len = observations.shape[:2]
        #    obs_flat = observations.reshape(-1, 3, 64, 64)
        #    embed_flat = self.encoder(obs_flat)
        #    obs_embed = embed_flat.reshape(batch_size, seq_len, -1)
        # 
        # 2. Rollout through observations:
        #    states, prior_dists, post_dists = self.rssm.rollout_observation(
        #        seq_len, obs_embed, actions
        #    )
        # 
        # 3. Decode observations:
        #    Reconstruct all timesteps
        # 
        # 4. Predict rewards:
        #    Use symlog if enabled
        # 
        # 5. Predict continues:
        #    Binary cross-entropy loss
        # 
        # 6. Compute KL loss with balancing:
        #    kl_loss, kl_value = self.rssm.kl_loss(
        #        post_dists, prior_dists,
        #        kl_balance=self.kl_balance,
        #        free_nats=self.free_nats
        #    )
        # 
        # 7. Total loss and backprop:
        #    total_loss = recon_loss + reward_loss + continue_loss + kl_loss
        #    self.world_model_optimizer.zero_grad()
        #    total_loss.backward()
        #    self.world_model_optimizer.step()
        # 
        # 8. Return losses dict
        pass
    
    def train_actor_critic(self, initial_states):
        """
        Train actor and critic on imagined trajectories.
        
        Args:
            initial_states: Starting states for imagination (list of dicts)
            
        Returns:
            losses: Dict of loss values
        """
        # TODO: Implement actor-critic training
        # Guidelines:
        # 1. Imagine trajectories:
        #    with torch.no_grad():
        #        # Flatten initial states
        #        # Run imagination rollout
        # 
        # 2. Predict rewards and continues for imagined states:
        #    Use reward_predictor and continue_predictor
        #    Apply symlog if enabled
        # 
        # 3. Compute values:
        #    Use critic to estimate values
        # 
        # 4. Compute lambda returns:
        #    lambda_returns = compute_lambda_returns(...)
        # 
        # 5. Update actor:
        #    actor_loss, actor_info = compute_actor_loss(...)
        #    self.actor_optimizer.zero_grad()
        #    actor_loss.backward()
        #    self.actor_optimizer.step()
        # 
        # 6. Update critic:
        #    critic_loss, critic_info = compute_critic_loss(...)
        #    self.critic_optimizer.zero_grad()
        #    critic_loss.backward()
        #    self.critic_optimizer.step()
        # 
        # 7. Return combined losses dict
        pass
    
    def select_action(self, observation, state=None):
        """
        Select action for environment interaction.
        
        Args:
            observation: Current observation (3, 64, 64)
            state: Previous RSSM state (or None for initial)
            
        Returns:
            action: Selected action
            new_state: Updated RSSM state
        """
        # TODO: Implement action selection
        # Guidelines:
        # 1. Encode observation
        # 2. Update RSSM state using posterior
        # 3. Get action from actor
        # 4. Return action and new state
        pass


def test_dreamerv2():
    """Test DreamerV2 implementation."""
    print("Testing DreamerV2...")
    
    # Hyperparameters
    batch_size = 2
    seq_len = 10
    action_dim = 6
    
    # Create agent
    agent = DreamerV2(
        action_dim=action_dim,
        num_categories=8,  # Smaller for testing
        num_categoricals=8
    )
    
    print(f"✓ Created DreamerV2 agent")
    
    # Test world model training
    observations = torch.randn(batch_size, seq_len, 3, 64, 64)
    actions = torch.randn(batch_size, seq_len, action_dim)
    
    wm_losses = agent.train_world_model(observations, actions)
    print(f"✓ World model training works")
    print(f"  Losses: {wm_losses}")
    
    # Test actor-critic training
    # Extract states from world model for imagination
    with torch.no_grad():
        obs_embed = agent.encoder(observations[:, 0].reshape(-1, 3, 64, 64))
        initial_state = agent.rssm.get_initial_state(batch_size, observations.device)
    
    ac_losses = agent.train_actor_critic([initial_state])
    print(f"✓ Actor-critic training works")
    print(f"  Losses: {ac_losses}")
    
    # Test action selection
    observation = torch.randn(3, 64, 64)
    action, state = agent.select_action(observation)
    print(f"✓ Action selection works: {action.shape}")
    
    # Test symlog
    x = torch.tensor([-100.0, -1.0, 0.0, 1.0, 100.0])
    y = symlog(x)
    x_recon = symexp(y)
    assert torch.allclose(x, x_recon, atol=1e-5)
    print(f"✓ Symlog transformation works")
    print(f"  Original: {x}")
    print(f"  Symlog: {y}")
    
    print("\n✅ All DreamerV2 tests passed!")


if __name__ == "__main__":
    test_dreamerv2()

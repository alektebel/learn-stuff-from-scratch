"""
Actor-Critic with Lambda Returns for DreamerV2

Improvements over DreamerV1:
- Lambda returns (TD(λ)) for better value estimation
- Improved value learning with target networks (optional)
- Better normalization strategies
- Robust policy optimization

Paper: Mastering Atari with Discrete World Models (Hafner et al., 2021)
Section 3.2: Behavior Learning
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, Independent


class Actor(nn.Module):
    """
    Actor network with improved architecture.
    
    Similar to DreamerV1 but with:
    - ELU activations
    - Better initialization
    - Optional LayerNorm
    
    Args:
        state_dim: Dimension of stochastic state (default: 1024)
        rnn_hidden_dim: Dimension of deterministic state (default: 200)
        action_dim: Dimension of action space
        hidden_dim: Dimension of hidden layers (default: 400)
        num_layers: Number of hidden layers (default: 4)
        activation: Activation function (default: 'elu')
        min_std: Minimum standard deviation (default: 1e-4)
        max_std: Maximum standard deviation (default: 1.0)
        init_std: Initial standard deviation (default: 5.0)
    """
    
    def __init__(
        self,
        state_dim=1024,
        rnn_hidden_dim=200,
        action_dim=None,
        hidden_dim=400,
        num_layers=4,
        activation='elu',
        min_std=1e-4,
        max_std=1.0,
        init_std=5.0
    ):
        super().__init__()
        self.action_dim = action_dim
        self.min_std = min_std
        self.max_std = max_std
        self.init_std = init_std
        
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement actor network
        # Guidelines:
        # - Input: concatenation of z and h
        # - Build MLP with num_layers hidden layers
        # - Use ELU activation
        # - Split output into mean and std heads
        #
        # Architecture (similar to DreamerV1 but with ELU):
        # latent_dim → hidden_dim → ... → hidden_dim → (mean, std)
        #
        # Paper reference: Section 3.2, Actor network
        
        # layers = []
        # layers.append(nn.Linear(latent_dim, hidden_dim))
        # layers.append(nn.ELU())
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.ELU())
        # self.shared = nn.Sequential(*layers)
        # 
        # self.mean_layer = nn.Linear(hidden_dim, action_dim)
        # self.std_layer = nn.Linear(hidden_dim, action_dim)
        
        pass  # Remove when implementing
    
    def forward(self, state, deterministic=False):
        """
        Compute action distribution and sample action.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            deterministic: If True, return mean action
            
        Returns:
            action: Sampled action (batch, action_dim)
            action_dist: Normal distribution over actions
        """
        # TODO: Implement forward pass
        # Guidelines:
        # - Same as DreamerV1 but ensure compatibility with discrete states
        # 1. Concatenate state if dict
        # 2. Pass through shared layers
        # 3. Compute mean with tanh
        # 4. Compute std with softplus
        # 5. Create Independent Normal distribution
        # 6. Sample or return mean
        pass


class Critic(nn.Module):
    """
    Critic network for value estimation.
    
    Similar to DreamerV1 but with:
    - ELU activations
    - Optional LayerNorm
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
        
        # TODO: Implement critic network
        # Guidelines:
        # - Input: concatenation of z and h
        # - Build MLP with num_layers hidden layers
        # - Use ELU activation
        # - Output: single value estimate
        #
        # Architecture:
        # latent_dim → hidden_dim → ... → hidden_dim → 1
        #
        # Paper reference: Section 3.2, Critic network
        
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
        Estimate value of state.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            
        Returns:
            value: Value estimate (batch,)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Concatenate state if dict
        # 2. Pass through network
        # 3. Squeeze last dimension
        # 4. Return value
        pass


def compute_lambda_returns(
    rewards,
    values,
    continues,
    gamma=0.99,
    lambda_=0.95
):
    """
    Compute lambda returns (TD(λ)) for value learning.
    
    Lambda returns interpolate between TD(0) and Monte Carlo returns:
    G^λ_t = r_t + γ * c_t * ((1-λ) * V(s_{t+1}) + λ * G^λ_{t+1})
    
    This provides better bias-variance tradeoff than pure TD or MC.
    
    Args:
        rewards: Predicted rewards (batch, horizon)
        values: Predicted values (batch, horizon+1)
        continues: Episode continuation flags (batch, horizon)
        gamma: Discount factor (default: 0.99)
        lambda_: Lambda parameter (default: 0.95)
        
    Returns:
        lambda_returns: Target returns (batch, horizon)
    """
    # TODO: Implement lambda returns
    # Guidelines:
    # 1. Initialize returns with final value
    #    returns = torch.zeros_like(rewards)
    #    last_return = values[:, -1]  # V(s_T)
    # 
    # 2. Backward iteration from T-1 to 0:
    #    for t in reversed(range(horizon)):
    #        # TD target: r_t + γ * c_t * V(s_{t+1})
    #        td_target = rewards[:, t] + gamma * continues[:, t] * values[:, t+1]
    #        
    #        # Lambda return: (1-λ) * TD + λ * G_{t+1}
    #        lambda_return = td_target + gamma * continues[:, t] * lambda_ * (last_return - values[:, t+1])
    #        
    #        # Store and update
    #        returns[:, t] = lambda_return
    #        last_return = lambda_return
    # 
    # 3. Return lambda returns
    #
    # Alternative (vectorized):
    # Use the recursive formula with scan operations
    #
    # Paper reference: Section 3.2, Lambda returns
    # Also see: https://arxiv.org/abs/1506.02438 (GAE paper)
    pass


def compute_actor_loss(
    actor,
    states,
    lambda_returns,
    old_actions=None,
    entropy_coef=1e-4
):
    """
    Compute actor loss from imagined trajectories.
    
    DreamerV2 uses reinforce-style policy gradient:
    L_actor = -E[G^λ] + entropy_regularization
    
    Args:
        actor: Actor network
        states: List of state dicts from imagination
        lambda_returns: Target returns (batch, horizon)
        old_actions: Optional actions for importance sampling
        entropy_coef: Entropy regularization coefficient
        
    Returns:
        actor_loss: Scalar loss value
        info: Dict with logging information
    """
    # TODO: Implement actor loss
    # Guidelines:
    # 1. Compute actions and distributions for each state:
    #    actions = []
    #    log_probs = []
    #    entropies = []
    #    for t, state in enumerate(states[:-1]):  # Exclude last state
    #        action, action_dist = actor(state)
    #        actions.append(action)
    #        log_probs.append(action_dist.log_prob(action))
    #        entropies.append(action_dist.entropy())
    # 
    # 2. Stack tensors:
    #    log_probs = torch.stack(log_probs, dim=1)  # (batch, horizon)
    #    entropies = torch.stack(entropies, dim=1)  # (batch, horizon)
    # 
    # 3. Compute policy gradient loss:
    #    # Detach lambda returns (don't backprop through critic)
    #    targets = lambda_returns.detach()
    #    
    #    # Reinforce: maximize expected return
    #    policy_loss = -(log_probs * targets).mean()
    # 
    # 4. Add entropy regularization:
    #    entropy_loss = -entropy_coef * entropies.mean()
    # 
    # 5. Total actor loss:
    #    actor_loss = policy_loss + entropy_loss
    # 
    # 6. Return loss and info dict
    #    info = {
    #        'actor_loss': actor_loss.item(),
    #        'policy_loss': policy_loss.item(),
    #        'entropy': entropies.mean().item(),
    #        'mean_return': lambda_returns.mean().item()
    #    }
    #
    # Paper reference: Section 3.2, Policy gradient
    pass


def compute_critic_loss(
    critic,
    states,
    lambda_returns
):
    """
    Compute critic loss for value learning.
    
    Learns to predict lambda returns:
    L_critic = MSE(V(s), G^λ)
    
    Args:
        critic: Critic network
        states: List of state dicts from imagination
        lambda_returns: Target returns (batch, horizon)
        
    Returns:
        critic_loss: Scalar loss value
        info: Dict with logging information
    """
    # TODO: Implement critic loss
    # Guidelines:
    # 1. Compute value predictions for each state:
    #    values = []
    #    for state in states[:-1]:  # Exclude last state
    #        value = critic(state)
    #        values.append(value)
    # 
    # 2. Stack values: values = torch.stack(values, dim=1)  # (batch, horizon)
    # 
    # 3. Compute MSE loss:
    #    # Detach targets (already detached but be explicit)
    #    targets = lambda_returns.detach()
    #    critic_loss = F.mse_loss(values, targets)
    # 
    # 4. Return loss and info
    #    info = {
    #        'critic_loss': critic_loss.item(),
    #        'mean_value': values.mean().item(),
    #        'value_std': values.std().item()
    #    }
    #
    # Paper reference: Section 3.2, Value learning
    pass


def test_actor_critic():
    """Test Actor-Critic implementation."""
    print("Testing DreamerV2 Actor-Critic...")
    
    # Hyperparameters
    batch_size = 4
    horizon = 15
    state_dim = 1024
    rnn_hidden_dim = 200
    action_dim = 6
    
    # Create networks
    actor = Actor(
        state_dim=state_dim,
        rnn_hidden_dim=rnn_hidden_dim,
        action_dim=action_dim
    )
    critic = Critic(
        state_dim=state_dim,
        rnn_hidden_dim=rnn_hidden_dim
    )
    
    print(f"✓ Created Actor and Critic networks")
    
    # Test actor
    state = {
        'z': torch.randn(batch_size, state_dim),
        'h': torch.randn(batch_size, rnn_hidden_dim)
    }
    action, action_dist = actor(state)
    assert action.shape == (batch_size, action_dim)
    assert torch.all((action >= -1) & (action <= 1))  # Bounded actions
    print(f"✓ Actor outputs bounded actions: {action.shape}")
    
    # Test critic
    value = critic(state)
    assert value.shape == (batch_size,) or value.shape == (batch_size, 1)
    print(f"✓ Critic outputs values: {value.shape}")
    
    # Test lambda returns
    rewards = torch.randn(batch_size, horizon)
    values = torch.randn(batch_size, horizon + 1)
    continues = torch.ones(batch_size, horizon)
    
    lambda_returns = compute_lambda_returns(
        rewards, values, continues,
        gamma=0.99, lambda_=0.95
    )
    assert lambda_returns.shape == (batch_size, horizon)
    print(f"✓ Lambda returns computed: {lambda_returns.shape}")
    
    # Test actor loss
    states = [state for _ in range(horizon + 1)]
    actor_loss, actor_info = compute_actor_loss(
        actor, states, lambda_returns
    )
    assert actor_loss.ndim == 0  # Scalar
    print(f"✓ Actor loss computed: {actor_loss:.4f}")
    print(f"  Info: {actor_info}")
    
    # Test critic loss
    critic_loss, critic_info = compute_critic_loss(
        critic, states, lambda_returns
    )
    assert critic_loss.ndim == 0  # Scalar
    print(f"✓ Critic loss computed: {critic_loss:.4f}")
    print(f"  Info: {critic_info}")
    
    # Test gradients
    total_loss = actor_loss + critic_loss
    total_loss.backward()
    print(f"✓ Gradients flow through actor and critic")
    
    print("\n✅ All Actor-Critic tests passed!")
    print("\nImprovements over DreamerV1:")
    print("  - Lambda returns for better value estimation")
    print("  - ELU activations")
    print("  - Improved architecture choices")


if __name__ == "__main__":
    test_actor_critic()

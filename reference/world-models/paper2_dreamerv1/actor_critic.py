"""
Actor-Critic Networks for DreamerV1

Implements the policy (actor) and value function (critic) that learn behaviors
by imagining trajectories in the learned world model.

Key Concepts:
- Actor: Learns policy π(a | z, h) in latent space
- Critic: Estimates value V(z, h) for imagined states
- Learning happens entirely in imagination using the world model

Paper: Dream to Control (Hafner et al., 2020)
Section 4: Behavior Learning from Imagined Trajectories
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, Independent


class Actor(nn.Module):
    """
    Actor network that outputs a stochastic policy.
    
    The actor learns a policy π(a | z, h) that operates in the latent space
    of the world model. It outputs a Gaussian distribution over actions.
    
    Args:
        state_dim: Dimension of stochastic state z
        rnn_hidden_dim: Dimension of deterministic state h
        action_dim: Dimension of action space
        hidden_dim: Dimension of hidden layers (default: 400)
        num_layers: Number of hidden layers (default: 4)
        min_std: Minimum standard deviation (default: 1e-4)
        max_std: Maximum standard deviation (default: 1.0)
        init_std: Initial standard deviation (default: 5.0)
    """
    
    def __init__(
        self,
        state_dim=30,
        rnn_hidden_dim=200,
        action_dim=None,
        hidden_dim=400,
        num_layers=4,
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
        # - Input: concatenation of z and h (latent_dim)
        # - Build MLP with num_layers hidden layers
        # - Hidden layers: Linear + ReLU, dimension hidden_dim
        # - Output layer splits into mean and std
        # - Mean: Linear to action_dim, then tanh to bound actions in [-1, 1]
        # - Std: Linear to action_dim, then softplus + scaling
        #
        # Architecture:
        # latent_dim → hidden_dim → ... → hidden_dim → (mean, std)
        #
        # Paper reference: Section 4 (Actor-Critic Algorithm)
        
        # Build shared layers
        # layers = []
        # layers.append(nn.Linear(latent_dim, hidden_dim))
        # layers.append(nn.ReLU())
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.ReLU())
        # self.shared = nn.Sequential(*layers)
        
        # Output heads
        # self.mean_layer = nn.Linear(hidden_dim, action_dim)
        # self.std_layer = nn.Linear(hidden_dim, action_dim)
        
        pass  # Remove when implementing
    
    def forward(self, state, deterministic=False):
        """
        Compute action distribution (and optionally sample).
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            deterministic: If True, return mean action without sampling
            
        Returns:
            action: Sampled action (or mean if deterministic)
            action_dist: Normal distribution over actions
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate: x = torch.cat([state['z'], state['h']], dim=-1)
        # 2. Pass through shared layers
        # 3. Compute mean: mean = torch.tanh(self.mean_layer(x))
        #    This bounds actions to [-1, 1]
        # 4. Compute std:
        #    - Raw std: std = self.std_layer(x)
        #    - Apply softplus: std = F.softplus(std) + self.min_std
        #    - Clip to max_std: std = torch.clamp(std, max=self.max_std)
        # 5. Create distribution: action_dist = Normal(mean, std)
        #    Use Independent wrapper for multi-dimensional actions:
        #    action_dist = Independent(Normal(mean, std), 1)
        # 6. Sample action:
        #    - If deterministic: action = mean
        #    - Else: action = action_dist.rsample() (reparameterization trick)
        # 7. Return action and distribution
        #
        # Note: Independent wrapper treats the last dimension as independent
        # event dimensions, which is correct for multi-dimensional actions.
        
        pass
    
    def get_action(self, state, deterministic=False):
        """
        Sample action from policy (convenience method).
        
        Args:
            state: Latent state
            deterministic: Whether to use mean action
            
        Returns:
            action: Sampled action
        """
        action, _ = self.forward(state, deterministic)
        return action


class Critic(nn.Module):
    """
    Critic network that estimates state values.
    
    The critic learns a value function V(z, h) that estimates the expected
    return from a given latent state when following the current policy.
    
    Args:
        state_dim: Dimension of stochastic state z
        rnn_hidden_dim: Dimension of deterministic state h
        hidden_dim: Dimension of hidden layers (default: 400)
        num_layers: Number of hidden layers (default: 4)
    """
    
    def __init__(
        self,
        state_dim=30,
        rnn_hidden_dim=200,
        hidden_dim=400,
        num_layers=4
    ):
        super().__init__()
        
        latent_dim = state_dim + rnn_hidden_dim
        
        # TODO: Implement critic network
        # Guidelines:
        # - Similar to Actor but outputs a single scalar (value)
        # - Input: concatenation of z and h
        # - MLP with num_layers hidden layers (hidden_dim, ReLU)
        # - Output: Single value (no activation)
        #
        # Architecture:
        # latent_dim → hidden_dim → ... → hidden_dim → 1
        #
        # Paper reference: Section 4 (Value Learning)
        
        # layers = []
        # layers.append(nn.Linear(latent_dim, hidden_dim))
        # layers.append(nn.ReLU())
        # for _ in range(num_layers - 1):
        #     layers.append(nn.Linear(hidden_dim, hidden_dim))
        #     layers.append(nn.ReLU())
        # layers.append(nn.Linear(hidden_dim, 1))
        # self.model = nn.Sequential(*layers)
        
        pass  # Remove when implementing
    
    def forward(self, state):
        """
        Estimate value of latent state.
        
        Args:
            state: Dict with 'z' and 'h' OR concatenated tensor
            
        Returns:
            value: Estimated value (batch, 1)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. If state is dict, concatenate z and h
        # 2. Pass through MLP
        # 3. Return value
        
        pass


def compute_lambda_returns(rewards, values, continues, gamma=0.99, lambda_=0.95):
    """
    Compute lambda returns for value learning.
    
    Lambda returns blend n-step returns of different horizons, providing
    a bias-variance tradeoff controlled by lambda.
    
    Args:
        rewards: Predicted rewards (batch, horizon, 1)
        values: Predicted values (batch, horizon + 1, 1)
        continues: Continuation probabilities (batch, horizon, 1)
        gamma: Discount factor (default: 0.99)
        lambda_: Lambda parameter (default: 0.95)
        
    Returns:
        lambda_returns: Target values for critic (batch, horizon, 1)
    """
    # TODO: Implement lambda returns
    # Guidelines:
    # 1. Lambda returns are computed backwards from the end of trajectory
    # 2. The recursive formula:
    #    V^λ_t = r_t + γ * c_t * ((1 - λ) * V(s_{t+1}) + λ * V^λ_{t+1})
    #    where:
    #    - r_t is the reward at time t
    #    - c_t is the continuation probability (1 - done)
    #    - V(s_{t+1}) is the value estimate
    #    - V^λ_{t+1} is the lambda return of next step
    # 3. Initialize the last lambda return as the last value
    # 4. Iterate backwards to compute all lambda returns
    #
    # Pseudocode:
    # lambda_return = values[:, -1]  # Start with final value
    # lambda_returns = []
    # for t in reversed(range(horizon)):
    #     lambda_return = rewards[:, t] + gamma * continues[:, t] * (
    #         (1 - lambda_) * values[:, t + 1] + lambda_ * lambda_return
    #     )
    #     lambda_returns.insert(0, lambda_return)
    # return torch.stack(lambda_returns, dim=1)
    #
    # Paper reference: Section 4, Equation 4 (similar to TD(λ))
    
    pass


def compute_actor_loss(
    imagined_states,
    actor,
    critic,
    reward_predictor,
    continue_predictor,
    gamma=0.99,
    lambda_=0.95
):
    """
    Compute actor loss from imagined trajectories.
    
    The actor is trained to maximize the expected lambda returns of
    imagined trajectories.
    
    Args:
        imagined_states: Dict with 'z' and 'h' over imagined trajectory
        actor: Actor network
        critic: Critic network
        reward_predictor: Reward prediction network
        continue_predictor: Continue prediction network
        gamma: Discount factor
        lambda_: Lambda parameter for returns
        
    Returns:
        actor_loss: Policy gradient loss
        metrics: Dict with additional metrics for logging
    """
    # TODO: Implement actor loss
    # Guidelines:
    # 1. Extract imagined trajectory
    #    - Shape: (batch, horizon, state_dim) for z and h
    # 2. Predict rewards and continues for imagined states
    # 3. Compute values for imagined states
    # 4. Compute lambda returns using rewards, values, continues
    # 5. Actor loss = -mean(lambda_returns)
    #    The negative is because we want to maximize returns (minimize -returns)
    # 6. Detach lambda returns before computing loss (don't backprop through critic)
    #
    # Paper reference: Section 4, Equation 5 (Policy Learning)
    
    pass


def compute_critic_loss(
    imagined_states,
    critic,
    reward_predictor,
    continue_predictor,
    gamma=0.99,
    lambda_=0.95
):
    """
    Compute critic loss from imagined trajectories.
    
    The critic learns to predict the lambda returns.
    
    Args:
        imagined_states: Dict with 'z' and 'h' over imagined trajectory
        critic: Critic network
        reward_predictor: Reward prediction network
        continue_predictor: Continue prediction network
        gamma: Discount factor
        lambda_: Lambda parameter for returns
        
    Returns:
        critic_loss: MSE loss between predicted values and lambda returns
        metrics: Dict with additional metrics
    """
    # TODO: Implement critic loss
    # Guidelines:
    # 1. Similar to actor loss, compute lambda returns
    # 2. Compute predicted values for imagined states
    # 3. Critic loss = MSE(predicted_values, lambda_returns.detach())
    #    Detach targets to avoid backprop through them
    # 4. Return loss and metrics (e.g., mean value, mean return)
    #
    # Paper reference: Section 4, Equation 6 (Value Learning)
    
    pass


def test_actor_critic():
    """
    Test function to verify Actor-Critic implementation.
    """
    print("Testing Actor-Critic...")
    
    batch_size = 4
    seq_len = 10
    state_dim = 30
    rnn_hidden_dim = 200
    action_dim = 6
    
    print("\nTest 1: Actor")
    # TODO: Uncomment when implemented
    # actor = Actor(
    #     state_dim=state_dim,
    #     rnn_hidden_dim=rnn_hidden_dim,
    #     action_dim=action_dim
    # )
    # state = {
    #     'z': torch.randn(batch_size, state_dim),
    #     'h': torch.randn(batch_size, rnn_hidden_dim)
    # }
    # action, action_dist = actor(state)
    # assert action.shape == (batch_size, action_dim), f"Action shape: {action.shape}"
    # assert action.min() >= -1 and action.max() <= 1, "Actions should be in [-1, 1]"
    # print(f"✓ Actor outputs actions: {action.shape}")
    
    print("\nTest 2: Critic")
    # TODO: Uncomment when implemented
    # critic = Critic(state_dim=state_dim, rnn_hidden_dim=rnn_hidden_dim)
    # value = critic(state)
    # assert value.shape == (batch_size, 1), f"Value shape: {value.shape}"
    # print(f"✓ Critic outputs values: {value.shape}")
    
    print("\nTest 3: Lambda returns")
    # TODO: Uncomment when implemented
    # rewards = torch.randn(batch_size, seq_len, 1)
    # values = torch.randn(batch_size, seq_len + 1, 1)
    # continues = torch.ones(batch_size, seq_len, 1) * 0.99
    # lambda_returns = compute_lambda_returns(rewards, values, continues)
    # assert lambda_returns.shape == (batch_size, seq_len, 1)
    # print(f"✓ Lambda returns computed: {lambda_returns.shape}")
    
    print("\nTest 4: Action sampling")
    # TODO: Uncomment when implemented
    # # Test deterministic and stochastic actions
    # action_det, _ = actor(state, deterministic=True)
    # action_sto, _ = actor(state, deterministic=False)
    # 
    # # Deterministic should be the same when called multiple times
    # action_det2, _ = actor(state, deterministic=True)
    # assert torch.allclose(action_det, action_det2), "Deterministic actions should match"
    # 
    # # Stochastic might differ (with high probability)
    # action_sto2, _ = actor(state, deterministic=False)
    # # Note: They could match by chance, so we won't assert they're different
    # 
    # print(f"✓ Deterministic and stochastic sampling works")
    
    print("\nImplementation not complete yet. Uncomment tests when ready.")


if __name__ == "__main__":
    test_actor_critic()

"""
Recurrent State-Space Model (RSSM) for DreamerV1

The RSSM is the core of DreamerV1's world model, maintaining both deterministic 
and stochastic states to model environment dynamics.

Architecture:
- Deterministic state (h): GRU/LSTM capturing temporal dependencies
- Stochastic state (z): Gaussian latent capturing uncertainty
- Transition: h_{t+1} = f(h_t, z_t, a_t)
- Prior: p(z_t | h_t) - imagination without observations
- Posterior: q(z_t | h_t, o_t) - inference from observations

Paper: Dream to Control (Hafner et al., 2020)
Section 3: Recurrent State-Space Model
Equations 1-3
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal


class RSSM(nn.Module):
    """
    Recurrent State-Space Model combining deterministic and stochastic states.
    
    The RSSM maintains two types of states:
    - h (deterministic): Captures temporal dependencies via recurrence
    - z (stochastic): Captures uncertainty via probabilistic transitions
    
    Args:
        state_dim: Dimension of stochastic state z (default: 30)
        rnn_hidden_dim: Dimension of deterministic state h (default: 200)
        action_dim: Dimension of action space
        hidden_dim: Dimension of hidden layers (default: 200)
        embed_dim: Dimension of observation embedding (default: 1024)
    """
    
    def __init__(
        self, 
        state_dim=30,
        rnn_hidden_dim=200,
        action_dim=None,
        hidden_dim=200,
        embed_dim=1024
    ):
        super().__init__()
        self.state_dim = state_dim
        self.rnn_hidden_dim = rnn_hidden_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        
        # TODO: Implement recurrent model (deterministic path)
        # Guidelines:
        # - Use GRU or LSTM for recurrence
        # - Input: concatenation of previous stochastic state z and action
        # - Input dimension: state_dim + action_dim
        # - Hidden dimension: rnn_hidden_dim
        # - This captures h_{t+1} = f(h_t, z_t, a_t)
        #
        # Paper reference: Section 3, Equation 1
        # self.rnn = nn.GRU(
        #     input_size=state_dim + action_dim,
        #     hidden_size=rnn_hidden_dim,
        #     batch_first=True
        # )
        
        # TODO: Implement prior network p(z_t | h_t)
        # Guidelines:
        # - Maps deterministic state h_t to stochastic state distribution
        # - Input: h_t (rnn_hidden_dim)
        # - Hidden layer: hidden_dim with ReLU
        # - Output: mean and std for z_t distribution
        # - Two separate heads for mean and std
        #
        # Paper reference: Section 3, Prior distribution
        # self.fc_prior = nn.Sequential(
        #     nn.Linear(rnn_hidden_dim, hidden_dim),
        #     nn.ReLU()
        # )
        # self.fc_prior_mean = nn.Linear(hidden_dim, state_dim)
        # self.fc_prior_std = nn.Linear(hidden_dim, state_dim)
        
        # TODO: Implement posterior network q(z_t | h_t, o_t)
        # Guidelines:
        # - Maps deterministic state h_t AND observation embedding to z_t
        # - Input: concatenation of h_t and embedded observation
        # - Input dimension: rnn_hidden_dim + embed_dim
        # - Hidden layer: hidden_dim with ReLU
        # - Output: mean and std for z_t distribution
        #
        # Paper reference: Section 3, Posterior distribution
        # self.fc_posterior = nn.Sequential(
        #     nn.Linear(rnn_hidden_dim + embed_dim, hidden_dim),
        #     nn.ReLU()
        # )
        # self.fc_posterior_mean = nn.Linear(hidden_dim, state_dim)
        # self.fc_posterior_std = nn.Linear(hidden_dim, state_dim)
        
        # Minimum standard deviation to prevent collapse
        self.min_std = 0.1
        
        pass  # Remove when implementing
    
    def get_initial_state(self, batch_size, device):
        """
        Initialize RSSM state at the start of a sequence.
        
        Args:
            batch_size: Number of parallel sequences
            device: torch device
            
        Returns:
            state: Dict containing 'h' (deterministic) and 'z' (stochastic)
        """
        # TODO: Implement initial state
        # Guidelines:
        # - Initialize h as zeros of shape (1, batch_size, rnn_hidden_dim)
        #   Note: First dimension is for num_layers in GRU/LSTM
        # - Initialize z as zeros of shape (batch_size, state_dim)
        # - Return as dictionary: {'h': h, 'z': z}
        
        pass
    
    def prior(self, h):
        """
        Compute prior distribution p(z_t | h_t) for imagination.
        
        Used when imagining trajectories without observations.
        
        Args:
            h: Deterministic state (batch, rnn_hidden_dim)
            
        Returns:
            mean: Prior mean (batch, state_dim)
            std: Prior standard deviation (batch, state_dim)
        """
        # TODO: Implement prior
        # Guidelines:
        # 1. Pass h through fc_prior network
        # 2. Compute mean from fc_prior_mean
        # 3. Compute std from fc_prior_std
        # 4. Apply softplus to std and add min_std: std = F.softplus(std) + min_std
        #    This ensures std is always positive and bounded below
        #
        # Paper reference: Equation 2 (prior)
        
        pass
    
    def posterior(self, h, embed):
        """
        Compute posterior distribution q(z_t | h_t, o_t) from observations.
        
        Used during training to infer states from actual observations.
        
        Args:
            h: Deterministic state (batch, rnn_hidden_dim)
            embed: Observation embedding (batch, embed_dim)
            
        Returns:
            mean: Posterior mean (batch, state_dim)
            std: Posterior standard deviation (batch, state_dim)
        """
        # TODO: Implement posterior
        # Guidelines:
        # 1. Concatenate h and embed: x = torch.cat([h, embed], dim=-1)
        # 2. Pass through fc_posterior network
        # 3. Compute mean from fc_posterior_mean
        # 4. Compute std from fc_posterior_std
        # 5. Apply softplus to std and add min_std
        #
        # Paper reference: Equation 3 (posterior)
        
        pass
    
    def recurrent_step(self, prev_state, prev_action):
        """
        Single recurrent step: update deterministic state h.
        
        Transition model: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
        
        Args:
            prev_state: Dict with 'h' (1, batch, rnn_hidden) and 'z' (batch, state_dim)
            prev_action: Previous action (batch, action_dim)
            
        Returns:
            h: New deterministic state (batch, rnn_hidden_dim)
            h_hidden: New hidden state for RNN (1, batch, rnn_hidden_dim)
        """
        # TODO: Implement recurrent step
        # Guidelines:
        # 1. Extract h and z from prev_state
        # 2. Concatenate z and prev_action: x = torch.cat([z, prev_action], dim=-1)
        # 3. Add sequence dimension: x = x.unsqueeze(1) (batch, 1, input_dim)
        # 4. Pass through RNN: output, h_new = self.rnn(x, h)
        # 5. Remove sequence dimension from output: h_out = output.squeeze(1)
        # 6. Return h_out and h_new
        #
        # Paper reference: Equation 1 (recurrent model)
        
        pass
    
    def rollout_imagination(self, initial_state, actions):
        """
        Roll out imagined trajectories using the prior (without observations).
        
        Used for planning and actor-critic learning in imagination.
        
        Args:
            initial_state: Initial RSSM state dict
            actions: Sequence of actions (batch, seq_len, action_dim)
            
        Returns:
            states: Dict of 'h' and 'z' over trajectory
                h: (batch, seq_len, rnn_hidden_dim)
                z: (batch, seq_len, state_dim)
            prior_means: Means of prior distributions (batch, seq_len, state_dim)
            prior_stds: Stds of prior distributions (batch, seq_len, state_dim)
        """
        # TODO: Implement imagination rollout
        # Guidelines:
        # 1. Initialize lists to store h, z, means, stds
        # 2. Set current state = initial_state
        # 3. Loop over time steps:
        #    a. Perform recurrent_step with current state and action
        #    b. Compute prior distribution from new h
        #    c. Sample z from prior: z = Normal(mean, std).rsample()
        #    d. Update current state: {'h': h_hidden, 'z': z}
        #    e. Append h, z, mean, std to lists
        # 4. Stack lists into tensors along time dimension
        # 5. Return as dictionary
        #
        # Note: Use rsample() for reparameterization trick (differentiable)
        #
        # Paper reference: Section 4 (Behavior Learning from Imagined Trajectories)
        
        pass
    
    def rollout_observation(self, observations, actions, initial_state=None):
        """
        Roll out using observations to compute posterior states.
        
        Used during training to learn the world model.
        
        Args:
            observations: Embedded observations (batch, seq_len, embed_dim)
            actions: Actions taken (batch, seq_len, action_dim)
            initial_state: Initial RSSM state dict (optional)
            
        Returns:
            states: Dict of posterior states over trajectory
            priors: Dict of prior means and stds
            posteriors: Dict of posterior means and stds
        """
        # TODO: Implement observation rollout
        # Guidelines:
        # 1. If initial_state is None, create one
        # 2. Initialize storage for h, z, prior/posterior means and stds
        # 3. Loop over time steps:
        #    a. Perform recurrent_step with current state and action[t]
        #    b. Compute prior p(z_t | h_t)
        #    c. Compute posterior q(z_t | h_t, o_t) using observation[t]
        #    d. Sample z from posterior
        #    e. Update current state
        #    f. Store all values
        # 4. Stack into tensors
        # 5. Return three dicts: states, priors, posteriors
        #
        # Paper reference: Section 3 (Model Learning)
        
        pass
    
    def kl_loss(self, prior_mean, prior_std, posterior_mean, posterior_std, free_nats=3.0):
        """
        Compute KL divergence between posterior and prior.
        
        KL[q(z|h,o) || p(z|h)] with free nats to prevent posterior collapse.
        
        Args:
            prior_mean: Prior means (batch, seq_len, state_dim)
            prior_std: Prior stds (batch, seq_len, state_dim)
            posterior_mean: Posterior means (batch, seq_len, state_dim)
            posterior_std: Posterior stds (batch, seq_len, state_dim)
            free_nats: Free nats threshold (default: 3.0)
            
        Returns:
            kl_loss: KL divergence loss
        """
        # TODO: Implement KL loss
        # Guidelines:
        # 1. Create Normal distributions for prior and posterior
        #    prior_dist = Normal(prior_mean, prior_std)
        #    posterior_dist = Normal(posterior_mean, posterior_std)
        # 
        # 2. Compute KL divergence:
        #    kl = torch.distributions.kl_divergence(posterior_dist, prior_dist)
        # 
        # 3. Apply free nats: kl = torch.maximum(kl, torch.tensor(free_nats))
        #    This prevents the posterior from collapsing to the prior too much
        # 
        # 4. Average over all dimensions: kl_loss = kl.mean()
        #
        # Paper reference: Section 3 (KL balancing, though DreamerV1 uses free nats)
        
        pass
    
    def forward(self, observations, actions, initial_state=None):
        """
        Full forward pass for training.
        
        Args:
            observations: Embedded observations (batch, seq_len, embed_dim)
            actions: Actions (batch, seq_len, action_dim)
            initial_state: Initial state (optional)
            
        Returns:
            states: Posterior states
            priors: Prior distributions
            posteriors: Posterior distributions
        """
        return self.rollout_observation(observations, actions, initial_state)


def test_rssm():
    """
    Test function to verify RSSM implementation.
    """
    print("Testing RSSM...")
    
    # Hyperparameters
    batch_size = 4
    seq_len = 10
    state_dim = 30
    rnn_hidden_dim = 200
    action_dim = 6
    embed_dim = 1024
    
    # Create RSSM
    rssm = RSSM(
        state_dim=state_dim,
        rnn_hidden_dim=rnn_hidden_dim,
        action_dim=action_dim,
        embed_dim=embed_dim
    )
    
    # Test data
    observations = torch.randn(batch_size, seq_len, embed_dim)
    actions = torch.randn(batch_size, seq_len, action_dim)
    
    print("\nTest 1: Initial state")
    # TODO: Uncomment when implemented
    # initial_state = rssm.get_initial_state(batch_size, observations.device)
    # assert 'h' in initial_state and 'z' in initial_state
    # assert initial_state['h'].shape == (1, batch_size, rnn_hidden_dim)
    # assert initial_state['z'].shape == (batch_size, state_dim)
    # print("✓ Initial state correct")
    
    print("\nTest 2: Observation rollout")
    # TODO: Uncomment when implemented
    # states, priors, posteriors = rssm(observations, actions)
    # assert states['h'].shape == (batch_size, seq_len, rnn_hidden_dim)
    # assert states['z'].shape == (batch_size, seq_len, state_dim)
    # assert priors['mean'].shape == (batch_size, seq_len, state_dim)
    # assert posteriors['mean'].shape == (batch_size, seq_len, state_dim)
    # print("✓ Observation rollout shapes correct")
    
    print("\nTest 3: Imagination rollout")
    # TODO: Uncomment when implemented
    # initial_state = rssm.get_initial_state(batch_size, observations.device)
    # imagined_states, prior_means, prior_stds = rssm.rollout_imagination(
    #     initial_state, actions
    # )
    # assert imagined_states['h'].shape == (batch_size, seq_len, rnn_hidden_dim)
    # assert imagined_states['z'].shape == (batch_size, seq_len, state_dim)
    # print("✓ Imagination rollout shapes correct")
    
    print("\nTest 4: KL loss")
    # TODO: Uncomment when implemented
    # kl_loss = rssm.kl_loss(
    #     priors['mean'], priors['std'],
    #     posteriors['mean'], posteriors['std']
    # )
    # assert kl_loss.item() >= 0, "KL should be non-negative"
    # print(f"✓ KL loss computed: {kl_loss.item():.4f}")
    
    print("\nImplementation not complete yet. Uncomment tests when ready.")


if __name__ == "__main__":
    test_rssm()

"""
Discrete RSSM for DreamerV2

DreamerV2 improves upon DreamerV1 by using discrete (categorical) representations
for the stochastic state instead of continuous Gaussian distributions.

Key Improvements:
- Discrete latent variables with straight-through gradients
- Multiple categorical distributions (32 classes × 32 categoricals)
- Better representation learning and sample efficiency
- KL balancing to prevent posterior collapse

Architecture:
- Deterministic state (h): GRU capturing temporal dependencies
- Stochastic state (z): Categorical distribution over discrete codes
- Transition: h_{t+1} = f(h_t, z_t, a_t)
- Prior: p(z_t | h_t) - categorical distribution for imagination
- Posterior: q(z_t | h_t, o_t) - categorical distribution from observations

Paper: Mastering Atari with Discrete World Models (Hafner et al., 2021)
Section 3.1: Recurrent State-Space Model
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import OneHotCategorical, Categorical


class DiscreteRSSM(nn.Module):
    """
    Discrete Recurrent State-Space Model with categorical distributions.
    
    Key differences from DreamerV1:
    - Uses categorical distributions instead of Gaussian
    - Stochastic state is one-hot encoded
    - Straight-through estimator for gradients
    - Multiple independent categoricals for capacity
    
    Args:
        num_categories: Number of classes per categorical (default: 32)
        num_categoricals: Number of independent categoricals (default: 32)
        rnn_hidden_dim: Dimension of deterministic state h (default: 200)
        action_dim: Dimension of action space
        hidden_dim: Dimension of hidden layers (default: 200)
        embed_dim: Dimension of observation embedding (default: 1024)
        unimix: Uniform mixing coefficient for KL loss (default: 0.01)
    """
    
    def __init__(
        self,
        num_categories=32,
        num_categoricals=32,
        rnn_hidden_dim=200,
        action_dim=None,
        hidden_dim=200,
        embed_dim=1024,
        unimix=0.01
    ):
        super().__init__()
        self.num_categories = num_categories
        self.num_categoricals = num_categoricals
        self.state_dim = num_categories * num_categoricals
        self.rnn_hidden_dim = rnn_hidden_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.unimix = unimix
        
        # TODO: Implement recurrent model (deterministic path)
        # Guidelines:
        # - Use GRU for recurrence (like DreamerV1)
        # - Input: concatenation of previous stochastic state z and action
        # - Note: z is now one-hot encoded, so input_size = state_dim + action_dim
        # - Hidden dimension: rnn_hidden_dim
        # - This captures h_{t+1} = f(h_t, z_t, a_t)
        #
        # Paper reference: Section 3.1, Equation 1
        # self.rnn = nn.GRUCell(
        #     input_size=self.state_dim + action_dim,
        #     hidden_size=rnn_hidden_dim
        # )
        
        # TODO: Implement prior network p(z_t | h_t)
        # Guidelines:
        # - Maps deterministic state h_t to categorical distribution
        # - Input: h_t (rnn_hidden_dim)
        # - Hidden layer: hidden_dim with ELU activation
        # - Output: logits for each categorical distribution
        # - Output shape: (batch, num_categoricals, num_categories)
        #
        # Architecture:
        # h_t → hidden_dim (ELU) → num_categoricals * num_categories
        #
        # Paper reference: Section 3.1, Prior p(z_t | h_t)
        # self.fc_prior = nn.Sequential(
        #     nn.Linear(rnn_hidden_dim, hidden_dim),
        #     nn.ELU()
        # )
        # self.fc_prior_logits = nn.Linear(hidden_dim, num_categoricals * num_categories)
        
        # TODO: Implement posterior network q(z_t | h_t, o_t)
        # Guidelines:
        # - Maps h_t AND observation embedding to categorical distribution
        # - Input: concatenation of h_t and embedded observation
        # - Input dimension: rnn_hidden_dim + embed_dim
        # - Hidden layer: hidden_dim with ELU activation
        # - Output: logits for each categorical distribution
        #
        # Paper reference: Section 3.1, Posterior q(z_t | h_t, o_t)
        # self.fc_posterior = nn.Sequential(
        #     nn.Linear(rnn_hidden_dim + embed_dim, hidden_dim),
        #     nn.ELU()
        # )
        # self.fc_posterior_logits = nn.Linear(hidden_dim, num_categoricals * num_categories)
        
        pass  # Remove when implementing
    
    def get_initial_state(self, batch_size, device):
        """
        Initialize RSSM state (h and z).
        
        Returns:
            state: Dict with 'h' and 'z'
                - h: (batch_size, rnn_hidden_dim) - deterministic state
                - z: (batch_size, state_dim) - one-hot stochastic state
        """
        # TODO: Implement initial state
        # Guidelines:
        # - h starts as zeros: torch.zeros(batch_size, rnn_hidden_dim, device=device)
        # - z starts as zeros: torch.zeros(batch_size, state_dim, device=device)
        # - Return as dict: {'h': h, 'z': z}
        pass
    
    def prior(self, h):
        """
        Compute prior distribution p(z_t | h_t) for imagination.
        
        Args:
            h: Deterministic state (batch_size, rnn_hidden_dim)
            
        Returns:
            z: Sampled one-hot stochastic state (batch_size, state_dim)
            z_dist: Categorical distribution for each categorical variable
            z_logits: Raw logits (batch_size, num_categoricals, num_categories)
        """
        # TODO: Implement prior
        # Guidelines:
        # 1. Pass h through prior network to get logits
        #    x = self.fc_prior(h)
        #    logits = self.fc_prior_logits(x)
        # 
        # 2. Reshape logits to (batch, num_categoricals, num_categories)
        #    logits = logits.reshape(-1, self.num_categoricals, self.num_categories)
        # 
        # 3. Create categorical distribution for each categorical
        #    z_dist = OneHotCategorical(logits=logits)
        # 
        # 4. Sample from each categorical (with straight-through gradient)
        #    z_sample = z_dist.sample()  # (batch, num_categoricals, num_categories)
        # 
        # 5. Use straight-through estimator:
        #    z_one_hot = z_sample + z_dist.probs - z_dist.probs.detach()
        #    This allows gradients to flow through discrete sampling
        # 
        # 6. Flatten to one-hot vector: (batch, state_dim)
        #    z = z_one_hot.reshape(-1, self.state_dim)
        # 
        # 7. Return z, z_dist, and logits
        #
        # Paper reference: Section 3.1, Straight-through gradients
        pass
    
    def posterior(self, h, obs_embed):
        """
        Compute posterior distribution q(z_t | h_t, o_t) from observations.
        
        Args:
            h: Deterministic state (batch_size, rnn_hidden_dim)
            obs_embed: Observation embedding (batch_size, embed_dim)
            
        Returns:
            z: Sampled one-hot stochastic state (batch_size, state_dim)
            z_dist: Categorical distribution for each categorical variable
            z_logits: Raw logits (batch_size, num_categoricals, num_categories)
        """
        # TODO: Implement posterior
        # Guidelines:
        # 1. Concatenate h and obs_embed: x = torch.cat([h, obs_embed], dim=-1)
        # 2. Pass through posterior network to get logits
        # 3. Reshape logits to (batch, num_categoricals, num_categories)
        # 4. Create categorical distribution
        # 5. Sample with straight-through gradient (same as prior)
        # 6. Return z, z_dist, and logits
        #
        # Paper reference: Section 3.1
        pass
    
    def recurrent_step(self, prev_state, action):
        """
        Update deterministic state: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
        
        Args:
            prev_state: Previous RSSM state dict {'h': h, 'z': z}
            action: Action tensor (batch_size, action_dim)
            
        Returns:
            h: New deterministic state (batch_size, rnn_hidden_dim)
        """
        # TODO: Implement recurrent step
        # Guidelines:
        # 1. Extract previous z and h from state dict
        #    prev_z = prev_state['z']
        #    prev_h = prev_state['h']
        # 
        # 2. Concatenate prev_z and action as input
        #    x = torch.cat([prev_z, action], dim=-1)
        # 
        # 3. Update h using GRU cell
        #    h = self.rnn(x, prev_h)
        # 
        # 4. Return new h
        #
        # Paper reference: Section 3.1, Equation 1
        pass
    
    def rollout_observation(self, seq_len, obs_embed, actions, initial_state=None):
        """
        Process sequence of observations to learn state representations.
        
        This is used during training to learn the world model from real data.
        Uses posterior q(z_t | h_t, o_t) since we have observations.
        
        Args:
            seq_len: Length of sequence
            obs_embed: Observation embeddings (batch, seq_len, embed_dim)
            actions: Actions (batch, seq_len, action_dim)
            initial_state: Optional initial state dict
            
        Returns:
            states: List of state dicts, one per timestep
            prior_dists: List of prior distributions
            post_dists: List of posterior distributions
        """
        # TODO: Implement observation rollout
        # Guidelines:
        # 1. Initialize lists to store outputs
        #    states = []
        #    prior_dists = []
        #    post_dists = []
        # 
        # 2. Get or create initial state
        #    if initial_state is None:
        #        state = self.get_initial_state(obs_embed.shape[0], obs_embed.device)
        # 
        # 3. Loop over sequence:
        #    for t in range(seq_len):
        #        a. Compute prior: z_prior, prior_dist, _ = self.prior(state['h'])
        #        b. Compute posterior: z_post, post_dist, _ = self.posterior(state['h'], obs_embed[:, t])
        #        c. Update state with posterior z: state = {'h': state['h'], 'z': z_post}
        #        d. Store state and distributions
        #        e. If not last step, update h: h_next = self.recurrent_step(state, actions[:, t])
        #           state = {'h': h_next, 'z': z_post}
        # 
        # 4. Return states, prior_dists, post_dists
        #
        # Paper reference: Section 3.1, Training procedure
        pass
    
    def rollout_imagination(self, horizon, policy, initial_state):
        """
        Imagine trajectories using prior p(z_t | h_t) without observations.
        
        This is used for training the actor-critic in imagination.
        
        Args:
            horizon: Number of steps to imagine
            policy: Policy network that takes state and returns action
            initial_state: Starting state dict
            
        Returns:
            states: List of imagined state dicts
            actions: List of imagined actions
        """
        # TODO: Implement imagination rollout
        # Guidelines:
        # 1. Initialize lists to store outputs
        #    states = [initial_state]
        #    actions = []
        # 
        # 2. Set current state to initial_state
        # 
        # 3. Loop over horizon:
        #    for t in range(horizon):
        #        a. Get action from policy: action, _ = policy(state)
        #        b. Update deterministic state: h_next = self.recurrent_step(state, action)
        #        c. Sample from prior: z_next, _, _ = self.prior(h_next)
        #        d. Create next state: next_state = {'h': h_next, 'z': z_next}
        #        e. Store state and action
        #        f. Update current state
        # 
        # 4. Return states and actions
        #
        # Paper reference: Section 3.2, Behavior learning
        pass
    
    def kl_loss(self, post_dist, prior_dist, kl_balance=0.8, free_nats=1.0):
        """
        Compute KL divergence loss with balancing and free nats.
        
        DreamerV2 uses KL balancing to prevent posterior collapse:
        - Mix between KL(post || prior) and KL(prior || post)
        - This helps maintain informative priors
        
        Args:
            post_dist: Posterior distributions (list of OneHotCategorical)
            prior_dist: Prior distributions (list of OneHotCategorical)
            kl_balance: Balance coefficient (default: 0.8)
            free_nats: Minimum KL in nats (default: 1.0)
            
        Returns:
            kl_loss: Scalar loss value
            kl_value: Actual KL divergence (for logging)
        """
        # TODO: Implement KL loss with balancing
        # Guidelines:
        # 1. Compute KL(post || prior) for each timestep
        #    kl_post_prior = []
        #    for t in range(len(post_dist)):
        #        kl = torch.distributions.kl_divergence(post_dist[t], prior_dist[t])
        #        kl = kl.sum(dim=-1)  # Sum over categoricals
        #        kl_post_prior.append(kl)
        #    kl_post_prior = torch.stack(kl_post_prior).mean()
        # 
        # 2. Compute KL(prior || post) similarly
        #    (Use same loop but swap order)
        # 
        # 3. Balance the two KL terms:
        #    kl_loss = kl_balance * kl_post_prior + (1 - kl_balance) * kl_prior_post
        # 
        # 4. Apply free nats (minimum KL):
        #    kl_loss = torch.maximum(kl_loss, torch.tensor(free_nats))
        # 
        # 5. For logging, also return unbalanced KL:
        #    kl_value = kl_post_prior
        # 
        # 6. Return kl_loss, kl_value
        #
        # Paper reference: Section 3.1, KL balancing
        pass
    
    def get_latent_state(self, state):
        """
        Get concatenated latent state for policy/value networks.
        
        Args:
            state: RSSM state dict {'h': h, 'z': z}
            
        Returns:
            latent: Concatenated (h, z) tensor
        """
        # TODO: Implement state concatenation
        # Guidelines:
        # - Simply concatenate h and z along last dimension
        # - return torch.cat([state['h'], state['z']], dim=-1)
        pass


def test_discrete_rssm():
    """Test Discrete RSSM implementation."""
    print("Testing Discrete RSSM...")
    
    # Hyperparameters
    batch_size = 4
    seq_len = 10
    num_categories = 32
    num_categoricals = 32
    rnn_hidden_dim = 200
    action_dim = 6
    embed_dim = 1024
    
    # Create model
    rssm = DiscreteRSSM(
        num_categories=num_categories,
        num_categoricals=num_categoricals,
        rnn_hidden_dim=rnn_hidden_dim,
        action_dim=action_dim,
        embed_dim=embed_dim
    )
    
    print(f"✓ Created Discrete RSSM")
    print(f"  - Stochastic state dim: {rssm.state_dim}")
    print(f"  - Deterministic state dim: {rnn_hidden_dim}")
    print(f"  - Num categoricals: {num_categoricals}")
    print(f"  - Num categories: {num_categories}")
    
    # Test initial state
    state = rssm.get_initial_state(batch_size, 'cpu')
    assert state['h'].shape == (batch_size, rnn_hidden_dim)
    assert state['z'].shape == (batch_size, rssm.state_dim)
    print(f"✓ Initial state shapes correct")
    
    # Test prior
    z, z_dist, z_logits = rssm.prior(state['h'])
    assert z.shape == (batch_size, rssm.state_dim)
    assert z_logits.shape == (batch_size, num_categoricals, num_categories)
    print(f"✓ Prior distribution works")
    print(f"  - z is one-hot: {torch.allclose(z.sum(-1), torch.ones(batch_size))}")
    
    # Test posterior
    obs_embed = torch.randn(batch_size, embed_dim)
    z, z_dist, z_logits = rssm.posterior(state['h'], obs_embed)
    assert z.shape == (batch_size, rssm.state_dim)
    print(f"✓ Posterior distribution works")
    
    # Test recurrent step
    action = torch.randn(batch_size, action_dim)
    h_next = rssm.recurrent_step(state, action)
    assert h_next.shape == (batch_size, rnn_hidden_dim)
    print(f"✓ Recurrent step works")
    
    # Test observation rollout
    obs_embeds = torch.randn(batch_size, seq_len, embed_dim)
    actions = torch.randn(batch_size, seq_len, action_dim)
    states, prior_dists, post_dists = rssm.rollout_observation(
        seq_len, obs_embeds, actions
    )
    assert len(states) == seq_len
    assert len(prior_dists) == seq_len
    assert len(post_dists) == seq_len
    print(f"✓ Observation rollout works")
    
    # Test KL loss
    kl_loss, kl_value = rssm.kl_loss(post_dists, prior_dists)
    assert kl_loss.ndim == 0  # Scalar
    print(f"✓ KL loss computation works")
    print(f"  - KL value: {kl_value:.4f}")
    
    # Test imagination rollout
    class DummyPolicy:
        def __call__(self, state):
            batch = state['h'].shape[0]
            return torch.randn(batch, action_dim), None
    
    policy = DummyPolicy()
    horizon = 15
    imag_states, imag_actions = rssm.rollout_imagination(horizon, policy, state)
    assert len(imag_states) == horizon + 1  # Including initial state
    assert len(imag_actions) == horizon
    print(f"✓ Imagination rollout works")
    
    print("\n✅ All Discrete RSSM tests passed!")
    print("\nKey differences from DreamerV1:")
    print("  - Categorical distributions instead of Gaussian")
    print("  - Straight-through gradient estimator")
    print("  - KL balancing for stable training")
    print("  - Multiple independent categoricals for capacity")


if __name__ == "__main__":
    test_discrete_rssm()

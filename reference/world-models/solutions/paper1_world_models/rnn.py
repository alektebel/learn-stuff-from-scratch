"""
MDN-RNN: Mixture Density Network + Recurrent Neural Network

The MDN-RNN learns a predictive model of the environment. Given the current
latent state z_t and action a_t, it predicts the next latent state z_{t+1},
reward r_t, and done flag d_t.

Key concepts:
- LSTM captures temporal dynamics
- Mixture Density Network (MDN) models uncertainty with multiple Gaussians
- Predicts distribution over next states (not just point estimates)

Paper: World Models (Ha & Schmidhuber, 2018)
Section 2.2: M (Memory Model)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class MDNRNN(nn.Module):
    """
    MDN-RNN for learning world model dynamics.
    
    The model takes as input a sequence of (z_t, a_t) pairs and predicts:
    - z_{t+1} as a mixture of Gaussians (MDN)
    - reward r_t
    - done flag d_t
    
    Args:
        latent_dim: Dimension of latent vector z (default: 32)
        action_dim: Dimension of action vector (default: 3)
        hidden_dim: LSTM hidden state dimension (default: 256)
        num_gaussians: Number of Gaussian components in mixture (default: 5)
    """
    
    def __init__(self, latent_dim=32, action_dim=3, hidden_dim=256, num_gaussians=5):
        super().__init__()
        self.latent_dim = latent_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.num_gaussians = num_gaussians
        
        # Input dimension: latent + action
        input_dim = latent_dim + action_dim
        
        # LSTM for temporal modeling
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        
        # MDN output layers for predicting next latent state
        # Pi: mixture weights (K values that sum to 1)
        self.fc_mdn_pi = nn.Linear(hidden_dim, num_gaussians)
        # Mu: means (K * latent_dim values)
        self.fc_mdn_mu = nn.Linear(hidden_dim, num_gaussians * latent_dim)
        # Logsigma: log standard deviations (K * latent_dim values)
        self.fc_mdn_logsigma = nn.Linear(hidden_dim, num_gaussians * latent_dim)
        
        # Auxiliary prediction heads
        self.fc_reward = nn.Linear(hidden_dim, 1)
        self.fc_done = nn.Linear(hidden_dim, 1)
    
    def forward(self, z, action, hidden=None):
        """
        Forward pass through MDN-RNN.
        
        Args:
            z: Latent vectors (batch, seq_len, latent_dim) or (batch, latent_dim)
            action: Actions (batch, seq_len, action_dim) or (batch, action_dim)
            hidden: Optional LSTM hidden state (h, c) tuple
            
        Returns:
            Dictionary containing:
                - pi: Mixture weights (batch, seq_len, num_gaussians)
                - mu: Means (batch, seq_len, num_gaussians, latent_dim)
                - sigma: Std devs (batch, seq_len, num_gaussians, latent_dim)
                - reward: Predicted rewards (batch, seq_len, 1)
                - done: Predicted done flags (batch, seq_len, 1)
                - hidden: Final LSTM hidden state
        """
        # Handle single timestep input by expanding to sequence
        if z.dim() == 2:
            z = z.unsqueeze(1)  # (batch, latent_dim) -> (batch, 1, latent_dim)
            action = action.unsqueeze(1)  # (batch, action_dim) -> (batch, 1, action_dim)
            squeeze_output = True
        else:
            squeeze_output = False
        
        batch_size, seq_len, _ = z.shape
        
        # Concatenate z and action
        x = torch.cat([z, action], dim=-1)
        
        # Pass through LSTM
        lstm_out, hidden = self.lstm(x, hidden)
        
        # Compute MDN outputs
        # Pi: mixture weights
        pi_logits = self.fc_mdn_pi(lstm_out)
        pi = F.softmax(pi_logits, dim=-1)  # (batch, seq_len, num_gaussians)
        
        # Mu: means
        mu = self.fc_mdn_mu(lstm_out)
        mu = mu.view(batch_size, seq_len, self.num_gaussians, self.latent_dim)
        
        # Sigma: standard deviations
        logsigma = self.fc_mdn_logsigma(lstm_out)
        logsigma = logsigma.view(batch_size, seq_len, self.num_gaussians, self.latent_dim)
        sigma = torch.exp(logsigma)  # Convert from log space
        
        # Auxiliary predictions
        reward = self.fc_reward(lstm_out)  # (batch, seq_len, 1)
        done_logits = self.fc_done(lstm_out)
        done = torch.sigmoid(done_logits)  # (batch, seq_len, 1)
        
        # Optionally squeeze if single timestep
        if squeeze_output:
            pi = pi.squeeze(1)
            mu = mu.squeeze(1)
            sigma = sigma.squeeze(1)
            reward = reward.squeeze(1)
            done = done.squeeze(1)
        
        return {
            'pi': pi,
            'mu': mu,
            'sigma': sigma,
            'reward': reward,
            'done': done,
            'hidden': hidden
        }
    
    def loss_function(self, z_next, pi, mu, sigma, reward_pred, reward_true, 
                     done_pred, done_true):
        """
        Compute MDN-RNN loss.
        
        The loss has three components:
        1. MDN loss: Negative log-likelihood of z_next under the mixture
        2. Reward loss: MSE between predicted and actual reward
        3. Done loss: Binary cross-entropy for done prediction
        
        Args:
            z_next: True next latent states (batch, seq_len, latent_dim)
            pi: Predicted mixture weights (batch, seq_len, num_gaussians)
            mu: Predicted means (batch, seq_len, num_gaussians, latent_dim)
            sigma: Predicted std devs (batch, seq_len, num_gaussians, latent_dim)
            reward_pred: Predicted rewards (batch, seq_len, 1)
            reward_true: True rewards (batch, seq_len, 1)
            done_pred: Predicted done probs (batch, seq_len, 1)
            done_true: True done flags (batch, seq_len, 1)
            
        Returns:
            loss: Total loss
            mdn_loss: MDN component
            reward_loss: Reward prediction component
            done_loss: Done prediction component
        """
        # Reshape z_next for broadcasting with mixture components
        # (batch, seq_len, latent_dim) -> (batch, seq_len, 1, latent_dim)
        z_next_expanded = z_next.unsqueeze(2)
        
        # Compute log probability for each Gaussian component
        # For multivariate Gaussian with diagonal covariance:
        # log p(x|mu,sigma) = -0.5 * sum((x-mu)^2/sigma^2 + log(sigma^2) + log(2π))
        
        # Normalized squared error term
        diff = z_next_expanded - mu  # (batch, seq_len, num_gaussians, latent_dim)
        squared_diff = diff ** 2
        
        # Log probability computation
        log_probs = -0.5 * (
            squared_diff / (sigma ** 2 + 1e-8) +  # Normalized squared error
            torch.log(sigma ** 2 + 1e-8) +         # Log variance term
            np.log(2 * np.pi)                      # Constant term
        )
        
        # Sum over latent dimensions
        log_probs = log_probs.sum(dim=-1)  # (batch, seq_len, num_gaussians)
        
        # Add log mixture weights
        log_pi = torch.log(pi + 1e-8)
        weighted_log_probs = log_pi + log_probs
        
        # Log-sum-exp trick for numerical stability
        # log(sum(pi_k * p_k)) = logsumexp(log(pi_k) + log(p_k))
        log_likelihood = torch.logsumexp(weighted_log_probs, dim=-1)
        
        # MDN loss: negative log-likelihood (averaged)
        mdn_loss = -log_likelihood.mean()
        
        # Reward loss: Mean Squared Error
        reward_loss = F.mse_loss(reward_pred, reward_true)
        
        # Done loss: Binary Cross Entropy
        done_loss = F.binary_cross_entropy(done_pred, done_true)
        
        # Total loss
        loss = mdn_loss + reward_loss + done_loss
        
        return loss, mdn_loss, reward_loss, done_loss
    
    def sample(self, pi, mu, sigma):
        """
        Sample from the mixture of Gaussians.
        
        This allows us to generate diverse predictions rather than always
        selecting the most likely outcome.
        
        Args:
            pi: Mixture weights (batch, num_gaussians)
            mu: Means (batch, num_gaussians, latent_dim)
            sigma: Std devs (batch, num_gaussians, latent_dim)
            
        Returns:
            z_next: Sampled next latent state (batch, latent_dim)
        """
        batch_size = pi.size(0)
        
        # Sample which Gaussian component to use for each batch element
        # Use multinomial sampling based on mixture weights
        component_indices = torch.multinomial(pi, num_samples=1).squeeze(1)
        
        # Gather the selected mu and sigma for each batch element
        # component_indices: (batch,)
        # We need to select mu[b, component_indices[b], :] for each b
        
        batch_indices = torch.arange(batch_size, device=pi.device)
        selected_mu = mu[batch_indices, component_indices, :]  # (batch, latent_dim)
        selected_sigma = sigma[batch_indices, component_indices, :]  # (batch, latent_dim)
        
        # Sample from the selected Gaussian
        eps = torch.randn_like(selected_mu)
        z_next = selected_mu + selected_sigma * eps
        
        return z_next


def train_rnn_on_batch(model, optimizer, z_seq, action_seq, reward_seq, done_seq):
    """
    Training loop for a single batch of sequences.
    
    Args:
        model: MDNRNN model
        optimizer: PyTorch optimizer
        z_seq: Latent sequence (batch, seq_len, latent_dim)
        action_seq: Action sequence (batch, seq_len, action_dim)
        reward_seq: Reward sequence (batch, seq_len, 1)
        done_seq: Done sequence (batch, seq_len, 1)
        
    Returns:
        Dictionary with loss components
    """
    model.train()
    optimizer.zero_grad()
    
    # Get current states and actions (all but last timestep)
    z_curr = z_seq[:, :-1, :]
    action_curr = action_seq[:, :-1, :]
    
    # Get next states and current rewards/dones (all but first timestep)
    z_next = z_seq[:, 1:, :]
    reward_curr = reward_seq[:, :-1, :]
    done_curr = done_seq[:, :-1, :]
    
    # Forward pass
    outputs = model(z_curr, action_curr)
    
    # Compute loss
    loss, mdn_loss, reward_loss, done_loss = model.loss_function(
        z_next, 
        outputs['pi'], 
        outputs['mu'], 
        outputs['sigma'],
        outputs['reward'], 
        reward_curr,
        outputs['done'], 
        done_curr
    )
    
    # Backward pass
    loss.backward()
    
    # Gradient clipping to prevent exploding gradients
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    
    # Optimizer step
    optimizer.step()
    
    return {
        'loss': loss.item(),
        'mdn_loss': mdn_loss.item(),
        'reward_loss': reward_loss.item(),
        'done_loss': done_loss.item()
    }


def test_mdnrnn():
    """
    Test function to verify MDN-RNN implementation.
    """
    print("Testing MDN-RNN...")
    
    # Create model
    model = MDNRNN(latent_dim=32, action_dim=3, hidden_dim=256, num_gaussians=5)
    
    # Test with dummy sequences
    batch_size = 4
    seq_len = 10
    z = torch.randn(batch_size, seq_len, 32)
    action = torch.randn(batch_size, seq_len, 3)
    
    # Forward pass
    outputs = model(z, action)
    
    # Check shapes
    assert outputs['pi'].shape == (batch_size, seq_len, 5), f"Pi shape: {outputs['pi'].shape}"
    assert outputs['mu'].shape == (batch_size, seq_len, 5, 32), f"Mu shape: {outputs['mu'].shape}"
    assert outputs['sigma'].shape == (batch_size, seq_len, 5, 32), f"Sigma shape: {outputs['sigma'].shape}"
    assert outputs['reward'].shape == (batch_size, seq_len, 1), f"Reward shape: {outputs['reward'].shape}"
    assert outputs['done'].shape == (batch_size, seq_len, 1), f"Done shape: {outputs['done'].shape}"
    
    # Test single timestep
    z_single = torch.randn(batch_size, 32)
    action_single = torch.randn(batch_size, 3)
    outputs_single = model(z_single, action_single)
    assert outputs_single['pi'].shape == (batch_size, 5)
    
    # Test sampling
    pi_sample = outputs['pi'][:, 0, :]  # First timestep
    mu_sample = outputs['mu'][:, 0, :, :]
    sigma_sample = outputs['sigma'][:, 0, :, :]
    z_next_sample = model.sample(pi_sample, mu_sample, sigma_sample)
    assert z_next_sample.shape == (batch_size, 32)
    
    # Test loss
    z_next = torch.randn(batch_size, seq_len, 32)
    reward = torch.randn(batch_size, seq_len, 1)
    done = torch.randint(0, 2, (batch_size, seq_len, 1)).float()
    
    loss, mdn_loss, reward_loss, done_loss = model.loss_function(
        z_next, outputs['pi'], outputs['mu'], outputs['sigma'],
        outputs['reward'], reward, outputs['done'], done
    )
    
    assert loss.item() > 0, "Loss should be positive"
    
    # Test training step
    optimizer = torch.optim.Adam(model.parameters())
    z_seq = torch.randn(batch_size, seq_len, 32)
    action_seq = torch.randn(batch_size, seq_len, 3)
    reward_seq = torch.randn(batch_size, seq_len, 1)
    done_seq = torch.randint(0, 2, (batch_size, seq_len, 1)).float()
    
    loss_dict = train_rnn_on_batch(model, optimizer, z_seq, action_seq, reward_seq, done_seq)
    assert 'loss' in loss_dict
    
    print(f"✓ MDN-RNN test passed!")
    print(f"  Pi shape: {outputs['pi'].shape}")
    print(f"  Mu shape: {outputs['mu'].shape}")
    print(f"  Sigma shape: {outputs['sigma'].shape}")
    print(f"  Total loss: {loss.item():.4f}")
    print(f"  MDN loss: {mdn_loss.item():.4f}")
    print(f"  Reward loss: {reward_loss.item():.4f}")
    print(f"  Done loss: {done_loss.item():.4f}")
    print(f"✓ Training step test passed!")


if __name__ == "__main__":
    test_mdnrnn()

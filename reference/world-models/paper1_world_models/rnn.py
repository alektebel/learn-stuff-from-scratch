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
        
        # TODO: Implement LSTM layer
        # Guidelines:
        # - Input: concatenated [z_t, a_t] of size (latent_dim + action_dim)
        # - Hidden state size: hidden_dim
        # - Single layer LSTM is sufficient (can experiment with more)
        # - Use batch_first=True for easier handling
        
        # self.lstm = nn.LSTM(...)
        
        # TODO: Implement MDN output layers
        # Guidelines:
        # The MDN predicts a mixture of Gaussians for next latent state.
        # For K Gaussians in latent_dim dimensions, we need:
        # 
        # 1. Mixture weights (pi): K values (probabilities that sum to 1)
        #    Output size: num_gaussians
        # 
        # 2. Means (mu): K vectors of size latent_dim
        #    Output size: num_gaussians * latent_dim
        # 
        # 3. Log standard deviations (logsigma): K vectors of size latent_dim
        #    Output size: num_gaussians * latent_dim
        #    (We predict log(sigma) for numerical stability)
        
        # self.fc_mdn_pi = nn.Linear(hidden_dim, num_gaussians)
        # self.fc_mdn_mu = nn.Linear(hidden_dim, num_gaussians * latent_dim)
        # self.fc_mdn_logsigma = nn.Linear(hidden_dim, num_gaussians * latent_dim)
        
        # TODO: Implement auxiliary prediction heads
        # Guidelines:
        # - Reward prediction: single scalar value
        # - Done prediction: single probability (0 = not done, 1 = done)
        
        # self.fc_reward = nn.Linear(hidden_dim, 1)
        # self.fc_done = nn.Linear(hidden_dim, 1)
        
        pass  # Remove when implemented
    
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
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Handle both batched sequences and single timesteps
        #    If z is 2D, expand to 3D: (batch, latent_dim) → (batch, 1, latent_dim)
        # 
        # 2. Concatenate z and action: x = torch.cat([z, action], dim=-1)
        # 
        # 3. Pass through LSTM: lstm_out, hidden = self.lstm(x, hidden)
        # 
        # 4. From LSTM output, compute all predictions:
        #    - pi: Apply softmax to mixture weights
        #    - mu: Reshape to (batch, seq_len, num_gaussians, latent_dim)
        #    - sigma: Apply exp to logsigma, then reshape
        #    - reward: Direct prediction from fc_reward
        #    - done: Apply sigmoid to get probability
        # 
        # 5. Return dictionary with all outputs
        
        pass
    
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
        # TODO: Implement loss function
        # Guidelines:
        # 
        # 1. MDN Loss (Negative Log-Likelihood):
        #    For each Gaussian k in the mixture:
        #    a) Compute log probability: log p_k(z_next | mu_k, sigma_k)
        #       For multivariate Gaussian with diagonal covariance:
        #       log_prob = -0.5 * sum((z_next - mu_k)^2 / sigma_k^2 + log(sigma_k^2) + log(2π))
        #    
        #    b) Weight by mixture coefficient: log(pi_k) + log_prob_k
        #    
        #    c) Compute log-sum-exp over all K Gaussians:
        #       log_likelihood = log(sum_k pi_k * p_k(z_next))
        #                      = logsumexp_k(log(pi_k) + log(p_k(z_next)))
        #    
        #    d) MDN loss = -mean(log_likelihood) over batch and sequence
        #    
        #    Hint: Use torch.logsumexp for numerical stability
        # 
        # 2. Reward Loss:
        #    Simple MSE: F.mse_loss(reward_pred, reward_true)
        # 
        # 3. Done Loss:
        #    Binary cross-entropy: F.binary_cross_entropy(done_pred, done_true)
        # 
        # 4. Total Loss:
        #    loss = mdn_loss + reward_loss + done_loss
        #    (You can weight these differently if needed)
        
        pass
    
    def sample(self, pi, mu, sigma):
        """
        Sample from the mixture of Gaussians.
        
        Args:
            pi: Mixture weights (batch, num_gaussians)
            mu: Means (batch, num_gaussians, latent_dim)
            sigma: Std devs (batch, num_gaussians, latent_dim)
            
        Returns:
            z_next: Sampled next latent state (batch, latent_dim)
        """
        # TODO: Implement sampling from MDN
        # Guidelines:
        # 1. Sample which Gaussian to use: k ~ Categorical(pi)
        #    Use torch.multinomial or similar
        # 
        # 2. For each sample in batch, select the corresponding mu_k and sigma_k
        # 
        # 3. Sample from that Gaussian: z = mu_k + sigma_k * epsilon
        #    where epsilon ~ N(0, I)
        # 
        # This gives us a diverse set of predictions rather than
        # always picking the most likely outcome.
        
        pass


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
    # TODO: Implement training loop
    # Guidelines:
    # 1. Get current z and actions (all but last timestep)
    #    z_curr = z_seq[:, :-1, :]
    #    action_curr = action_seq[:, :-1, :]
    # 
    # 2. Get next z and actual rewards/dones (all but first timestep)
    #    z_next = z_seq[:, 1:, :]
    #    reward_curr = reward_seq[:, :-1, :]
    #    done_curr = done_seq[:, :-1, :]
    # 
    # 3. Forward pass: outputs = model(z_curr, action_curr)
    # 
    # 4. Compute loss using model.loss_function(...)
    # 
    # 5. Backprop: loss.backward()
    # 
    # 6. Optimizer step: optimizer.step(), optimizer.zero_grad()
    # 
    # 7. Return loss dictionary for logging
    
    pass


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
    
    # TODO: Uncomment when implemented
    # # Forward pass
    # outputs = model(z, action)
    # 
    # # Check shapes
    # assert outputs['pi'].shape == (batch_size, seq_len, 5)
    # assert outputs['mu'].shape == (batch_size, seq_len, 5, 32)
    # assert outputs['sigma'].shape == (batch_size, seq_len, 5, 32)
    # assert outputs['reward'].shape == (batch_size, seq_len, 1)
    # assert outputs['done'].shape == (batch_size, seq_len, 1)
    # 
    # # Test sampling
    # pi_sample = outputs['pi'][:, 0, :]  # First timestep
    # mu_sample = outputs['mu'][:, 0, :, :]
    # sigma_sample = outputs['sigma'][:, 0, :, :]
    # z_next_sample = model.sample(pi_sample, mu_sample, sigma_sample)
    # assert z_next_sample.shape == (batch_size, 32)
    # 
    # # Test loss
    # z_next = torch.randn(batch_size, seq_len, 32)
    # reward = torch.randn(batch_size, seq_len, 1)
    # done = torch.randint(0, 2, (batch_size, seq_len, 1)).float()
    # 
    # loss, mdn_loss, reward_loss, done_loss = model.loss_function(
    #     z_next, outputs['pi'], outputs['mu'], outputs['sigma'],
    #     outputs['reward'], reward, outputs['done'], done
    # )
    # 
    # assert loss.item() > 0, "Loss should be positive"
    # 
    # print(f"✓ MDN-RNN test passed!")
    # print(f"  Pi shape: {outputs['pi'].shape}")
    # print(f"  Mu shape: {outputs['mu'].shape}")
    # print(f"  Sigma shape: {outputs['sigma'].shape}")
    # print(f"  Total loss: {loss.item():.4f}")
    # print(f"  MDN loss: {mdn_loss.item():.4f}")
    # print(f"  Reward loss: {reward_loss.item():.4f}")
    # print(f"  Done loss: {done_loss.item():.4f}")
    
    print("Implementation not complete yet. Uncomment test code when ready.")


if __name__ == "__main__":
    test_mdnrnn()

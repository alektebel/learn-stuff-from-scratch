"""
Controller: Linear mapping from latent state to action

The controller is a simple linear model that maps the concatenated
[z_t, h_t] (latent state and RNN hidden state) directly to actions.
Despite its simplicity, it can learn effective policies when optimized
with evolutionary strategies like CMA-ES.

Key concepts:
- Compact representation: Only ~800 parameters for CarRacing
- Trained with CMA-ES (derivative-free optimization)
- Can be evaluated entirely in the learned world model (dream)

Paper: World Models (Ha & Schmidhuber, 2018)
Section 2.3: C (Controller)
"""

import torch
import torch.nn as nn
import numpy as np


class Controller(nn.Module):
    """
    Linear controller that maps [z, h] → action.
    
    This is intentionally kept simple to reduce the number of parameters
    that need to be optimized. The world model (V + M) provides rich
    representations, so a linear controller is often sufficient.
    
    Args:
        input_dim: Dimension of input [z + h] (default: 32 + 256 = 288)
        action_dim: Dimension of action space (default: 3)
        use_bias: Whether to use bias term (default: True)
    """
    
    def __init__(self, input_dim=288, action_dim=3, use_bias=True):
        super().__init__()
        self.input_dim = input_dim
        self.action_dim = action_dim
        
        # Single linear layer for action prediction
        self.fc = nn.Linear(input_dim, action_dim, bias=use_bias)
    
    def forward(self, z, h):
        """
        Compute action from latent state and hidden state.
        
        Args:
            z: Latent vector from VAE (batch, latent_dim)
            h: Hidden state from RNN (batch, hidden_dim)
            
        Returns:
            action: Continuous action values (batch, action_dim)
        """
        # Concatenate latent state and hidden state
        x = torch.cat([z, h], dim=-1)
        
        # Linear transformation
        out = self.fc(x)
        
        # Tanh activation to bound actions to [-1, 1]
        action = torch.tanh(out)
        
        return action
    
    def get_parameters_as_vector(self):
        """
        Flatten all parameters into a single vector.
        
        This is used by CMA-ES to represent the controller as a point
        in parameter space.
        
        Returns:
            params: Flattened parameter vector (numpy array)
        """
        params = []
        for param in self.parameters():
            params.append(param.data.cpu().numpy().flatten())
        return np.concatenate(params)
    
    def set_parameters_from_vector(self, params):
        """
        Set all parameters from a flattened vector.
        
        This is used by CMA-ES to update the controller parameters
        during optimization.
        
        Args:
            params: Flattened parameter vector (numpy array)
        """
        params_tensor = torch.from_numpy(params).float()
        offset = 0
        
        for param in self.parameters():
            param_size = param.numel()
            param_slice = params_tensor[offset:offset + param_size]
            param.data = param_slice.view_as(param)
            offset += param_size
    
    def num_parameters(self):
        """
        Count total number of parameters.
        
        Returns:
            count: Total number of parameters
        """
        return sum(p.numel() for p in self.parameters())


class CMAESOptimizer:
    """
    Wrapper for CMA-ES optimization of the controller.
    
    CMA-ES (Covariance Matrix Adaptation Evolution Strategy) is a
    derivative-free optimization algorithm that's particularly effective
    for optimizing neural network policies in RL.
    
    Why CMA-ES for World Models?
    - No need for backpropagation through environment
    - Robust to local minima
    - Works well with small parameter spaces (~1000 params)
    - Can train entirely in the learned world model
    
    Args:
        controller: Controller instance to optimize
        population_size: Number of candidate solutions per generation
        sigma: Initial standard deviation for sampling
    """
    
    def __init__(self, controller, population_size=64, sigma=0.5):
        self.controller = controller
        self.population_size = population_size
        self.sigma = sigma
        
        # Get initial parameters
        self.num_params = controller.num_parameters()
        self.mean = controller.get_parameters_as_vector()
        
        # Initialize CMA-ES
        try:
            import cma
            self.es = cma.CMAEvolutionStrategy(
                self.mean,
                self.sigma,
                {'popsize': population_size}
            )
            self.use_cma = True
        except ImportError:
            print("Warning: CMA library not found. Install with: pip install cma")
            print("Falling back to simple evolution strategy.")
            self.use_cma = False
            # Simple evolution strategy fallback
            self.cov = np.eye(self.num_params) * sigma ** 2
            self.best_fitness = -np.inf
            self.best_params = self.mean.copy()
    
    def ask(self):
        """
        Sample candidate solutions from current distribution.
        
        Returns:
            candidates: List of parameter vectors (population_size, num_params)
        """
        if self.use_cma:
            return self.es.ask()
        else:
            # Simple sampling from multivariate Gaussian
            candidates = []
            for _ in range(self.population_size):
                candidate = np.random.multivariate_normal(self.mean, self.cov)
                candidates.append(candidate)
            return candidates
    
    def tell(self, candidates, fitnesses):
        """
        Update distribution based on fitness of candidates.
        
        Args:
            candidates: List of parameter vectors
            fitnesses: Fitness scores (higher is better)
        """
        if self.use_cma:
            # CMA library expects costs (lower is better), so negate fitnesses
            self.es.tell(candidates, [-f for f in fitnesses])
        else:
            # Simple evolution strategy: update mean toward best performers
            sorted_indices = np.argsort(fitnesses)[::-1]
            elite_size = self.population_size // 4
            elite_indices = sorted_indices[:elite_size]
            
            # Update mean
            elite_candidates = [candidates[i] for i in elite_indices]
            self.mean = np.mean(elite_candidates, axis=0)
            
            # Track best
            best_idx = sorted_indices[0]
            if fitnesses[best_idx] > self.best_fitness:
                self.best_fitness = fitnesses[best_idx]
                self.best_params = candidates[best_idx].copy()
    
    def should_stop(self):
        """
        Check if optimization should terminate.
        
        Returns:
            stop: Boolean indicating whether to stop
        """
        if self.use_cma:
            return self.es.stop()
        else:
            # Simple stopping criterion: sigma too small
            return np.linalg.norm(self.cov) < 1e-10
    
    def result(self):
        """
        Get the best solution found so far.
        
        Returns:
            best_params: Best parameter vector
            best_fitness: Fitness of best solution
        """
        if self.use_cma:
            return self.es.result.xbest, -self.es.result.fbest
        else:
            return self.best_params, self.best_fitness


def evaluate_controller(controller, vae, rnn, env, num_episodes=5, max_steps=1000):
    """
    Evaluate controller performance in the actual environment.
    
    This runs the full pipeline: observation → VAE → RNN → Controller → action
    
    Args:
        controller: Controller model
        vae: VAE model for encoding observations
        rnn: MDN-RNN model for temporal dynamics
        env: Gym environment
        num_episodes: Number of episodes to average over
        max_steps: Maximum steps per episode
        
    Returns:
        avg_reward: Average total reward over episodes
        avg_steps: Average episode length
    """
    controller.eval()
    vae.eval()
    rnn.eval()
    
    total_rewards = []
    total_steps = []
    
    with torch.no_grad():
        for episode in range(num_episodes):
            obs = env.reset()
            if isinstance(obs, tuple):
                obs = obs[0]  # Handle new gym API
            
            hidden = None
            episode_reward = 0
            steps = 0
            
            for step in range(max_steps):
                # Preprocess observation
                if isinstance(obs, np.ndarray):
                    obs_tensor = torch.FloatTensor(obs).permute(2, 0, 1).unsqueeze(0) / 255.0
                else:
                    obs_tensor = obs.unsqueeze(0)
                
                # Encode observation
                mu, _ = vae.encode(obs_tensor)
                z = mu  # Use mean for deterministic encoding
                
                # Get RNN hidden state
                if hidden is not None:
                    h = hidden[0].squeeze(0)  # Extract h from (h, c) tuple
                else:
                    h = torch.zeros(1, rnn.hidden_dim)
                
                # Get action from controller
                action = controller(z, h)
                action_np = action.squeeze(0).cpu().numpy()
                
                # Step environment
                result = env.step(action_np)
                if len(result) == 5:
                    obs, reward, terminated, truncated, info = result
                    done = terminated or truncated
                else:
                    obs, reward, done, info = result
                
                # Update RNN hidden state
                action_tensor = torch.FloatTensor(action_np).unsqueeze(0).unsqueeze(0)
                z_expanded = z.unsqueeze(1)
                outputs = rnn(z_expanded, action_tensor, hidden)
                hidden = outputs['hidden']
                
                episode_reward += reward
                steps += 1
                
                if done:
                    break
            
            total_rewards.append(episode_reward)
            total_steps.append(steps)
    
    avg_reward = np.mean(total_rewards)
    avg_steps = np.mean(total_steps)
    
    return avg_reward, avg_steps


def evaluate_in_dream(controller, rnn, num_rollouts=100, max_steps=1000, initial_z=None):
    """
    Evaluate controller in the learned world model (dream).
    
    This is much faster than real environment evaluation and is the
    key insight of World Models - we can train entirely in imagination!
    
    Args:
        controller: Controller model
        rnn: MDN-RNN model (world model)
        num_rollouts: Number of dream rollouts
        max_steps: Maximum steps per rollout
        initial_z: Initial latent states (num_rollouts, latent_dim)
                  If None, sample randomly
        
    Returns:
        avg_reward: Average total reward over rollouts
    """
    controller.eval()
    rnn.eval()
    
    total_rewards = []
    
    with torch.no_grad():
        # Initialize latent states
        if initial_z is None:
            z = torch.randn(num_rollouts, rnn.latent_dim)
        else:
            z = initial_z
        
        # Initialize hidden states
        hidden = None
        
        # Rollout in dream
        for step in range(max_steps):
            # Get hidden state
            if hidden is not None:
                h = hidden[0].squeeze(0)  # (1, batch, hidden_dim) -> (batch, hidden_dim)
            else:
                h = torch.zeros(num_rollouts, rnn.hidden_dim)
            
            # Get actions
            actions = controller(z, h)
            
            # Predict next state with RNN
            z_expanded = z.unsqueeze(1)  # (batch, latent_dim) -> (batch, 1, latent_dim)
            actions_expanded = actions.unsqueeze(1)  # (batch, action_dim) -> (batch, 1, action_dim)
            
            outputs = rnn(z_expanded, actions_expanded, hidden)
            
            # Sample next latent state
            pi = outputs['pi'].squeeze(1)  # (batch, 1, num_gaussians) -> (batch, num_gaussians)
            mu = outputs['mu'].squeeze(1)  # (batch, 1, num_gaussians, latent_dim) -> (batch, num_gaussians, latent_dim)
            sigma = outputs['sigma'].squeeze(1)
            
            z_next = rnn.sample(pi, mu, sigma)
            
            # Get reward and done predictions
            reward = outputs['reward'].squeeze(1).squeeze(1)  # (batch, 1, 1) -> (batch,)
            done = outputs['done'].squeeze(1).squeeze(1) > 0.5  # (batch, 1, 1) -> (batch,)
            
            # Update hidden state
            hidden = outputs['hidden']
            
            # Accumulate rewards (only for non-done episodes)
            if step == 0:
                episode_rewards = reward.cpu().numpy()
            else:
                episode_rewards += reward.cpu().numpy() * (~done_mask)
            
            # Update done mask
            if step == 0:
                done_mask = done.cpu().numpy()
            else:
                done_mask = done_mask | done.cpu().numpy()
            
            # Update z
            z = z_next
            
            # If all episodes are done, break
            if done_mask.all():
                break
    
    avg_reward = np.mean(episode_rewards)
    return avg_reward


def test_controller():
    """
    Test function to verify Controller implementation.
    """
    print("Testing Controller...")
    
    # Create controller
    controller = Controller(input_dim=288, action_dim=3)
    
    # Test with dummy input
    batch_size = 4
    z = torch.randn(batch_size, 32)
    h = torch.randn(batch_size, 256)
    
    # Forward pass
    action = controller(z, h)
    
    # Check shape and range
    assert action.shape == (batch_size, 3), f"Action shape: {action.shape}"
    assert action.min() >= -1.0 and action.max() <= 1.0, "Actions should be in [-1, 1]"
    
    # Test parameter extraction/setting
    params = controller.get_parameters_as_vector()
    print(f"  Number of parameters: {len(params)}")
    
    # Set parameters and verify
    new_params = np.random.randn(len(params)) * 0.1
    controller.set_parameters_from_vector(new_params)
    retrieved_params = controller.get_parameters_as_vector()
    np.testing.assert_allclose(new_params, retrieved_params, rtol=1e-5)
    
    print(f"✓ Controller test passed!")
    print(f"  Action shape: {action.shape}")
    print(f"  Action range: [{action.min():.3f}, {action.max():.3f}]")
    print(f"  Total parameters: {controller.num_parameters()}")
    
    # Test CMA-ES optimizer
    print("\nTesting CMA-ES Optimizer...")
    try:
        optimizer = CMAESOptimizer(controller, population_size=8, sigma=0.5)
        
        # Test ask/tell cycle
        candidates = optimizer.ask()
        assert len(candidates) == 8, f"Wrong number of candidates: {len(candidates)}"
        
        # Dummy fitness evaluation
        fitnesses = np.random.randn(8)
        optimizer.tell(candidates, fitnesses)
        
        # Get result
        best_params, best_fitness = optimizer.result()
        assert len(best_params) == len(params), "Best params wrong size"
        
        print(f"✓ CMA-ES Optimizer test passed!")
        print(f"  Population size: 8")
        print(f"  Best fitness: {best_fitness:.4f}")
    except Exception as e:
        print(f"  CMA-ES test skipped or failed: {e}")


if __name__ == "__main__":
    test_controller()

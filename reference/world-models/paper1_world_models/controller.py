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
        
        # TODO: Implement linear controller
        # Guidelines:
        # - Single linear layer: [z, h] → action
        # - Apply tanh activation to bound actions to [-1, 1]
        # - That's it! Simplicity is key here.
        
        # self.fc = nn.Linear(input_dim, action_dim, bias=use_bias)
        
        pass  # Remove when implemented
    
    def forward(self, z, h):
        """
        Compute action from latent state and hidden state.
        
        Args:
            z: Latent vector from VAE (batch, latent_dim)
            h: Hidden state from RNN (batch, hidden_dim)
            
        Returns:
            action: Continuous action values (batch, action_dim)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Concatenate z and h: x = torch.cat([z, h], dim=-1)
        # 2. Pass through linear layer: out = self.fc(x)
        # 3. Apply tanh activation: action = torch.tanh(out)
        # 
        # Note: tanh bounds actions to [-1, 1], which is standard
        # for continuous control environments.
        
        pass
    
    def get_parameters_as_vector(self):
        """
        Flatten all parameters into a single vector.
        
        This is used by CMA-ES to represent the controller as a point
        in parameter space.
        
        Returns:
            params: Flattened parameter vector (numpy array)
        """
        # TODO: Implement parameter extraction
        # Guidelines:
        # 1. Iterate through all parameters: self.parameters()
        # 2. Flatten each parameter and concatenate
        # 3. Convert to numpy array
        # 
        # Example:
        # params = []
        # for param in self.parameters():
        #     params.append(param.data.cpu().numpy().flatten())
        # return np.concatenate(params)
        
        pass
    
    def set_parameters_from_vector(self, params):
        """
        Set all parameters from a flattened vector.
        
        This is used by CMA-ES to update the controller parameters
        during optimization.
        
        Args:
            params: Flattened parameter vector (numpy array)
        """
        # TODO: Implement parameter setting
        # Guidelines:
        # 1. Convert params to torch tensor
        # 2. Iterate through model parameters
        # 3. Extract the correct slice for each parameter
        # 4. Reshape and assign to parameter.data
        # 
        # Example structure:
        # params_tensor = torch.from_numpy(params).float()
        # offset = 0
        # for param in self.parameters():
        #     param_size = param.numel()
        #     param_slice = params_tensor[offset:offset+param_size]
        #     param.data = param_slice.view_as(param)
        #     offset += param_size
        
        pass
    
    def num_parameters(self):
        """
        Count total number of parameters.
        
        Returns:
            count: Total number of parameters
        """
        # TODO: Implement parameter counting
        # Guidelines:
        # Sum up param.numel() for all parameters
        
        pass


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
        
        # TODO: Initialize CMA-ES state
        # Guidelines:
        # You can either:
        # 1. Use a library like 'cma' (pip install cma)
        #    import cma
        #    self.es = cma.CMAEvolutionStrategy(self.mean, self.sigma, {...})
        # 
        # 2. Or implement a simple evolution strategy:
        #    - Track population mean and covariance
        #    - Sample candidates from multivariate Gaussian
        #    - Update mean toward high-fitness solutions
        #    - Update covariance based on successful directions
        # 
        # For this template, we'll use the 'cma' library approach.
        
        # try:
        #     import cma
        #     self.es = cma.CMAEvolutionStrategy(
        #         self.mean,
        #         self.sigma,
        #         {'popsize': population_size}
        #     )
        # except ImportError:
        #     raise ImportError("Please install cma: pip install cma")
        
        pass  # Remove when implemented
    
    def ask(self):
        """
        Sample candidate solutions from current distribution.
        
        Returns:
            candidates: List of parameter vectors (population_size, num_params)
        """
        # TODO: Implement candidate sampling
        # Guidelines:
        # If using cma library:
        #   return self.es.ask()
        # 
        # If implementing manually:
        #   Sample from N(mean, covariance) population_size times
        
        pass
    
    def tell(self, candidates, fitnesses):
        """
        Update distribution based on fitness of candidates.
        
        Args:
            candidates: List of parameter vectors
            fitnesses: Fitness scores (higher is better)
        """
        # TODO: Implement distribution update
        # Guidelines:
        # If using cma library:
        #   The library expects costs (lower is better), so negate fitnesses:
        #   self.es.tell(candidates, [-f for f in fitnesses])
        # 
        # If implementing manually:
        #   1. Rank candidates by fitness
        #   2. Update mean toward top performers
        #   3. Update covariance based on successful steps
        
        pass
    
    def should_stop(self):
        """
        Check if optimization should terminate.
        
        Returns:
            stop: Boolean indicating whether to stop
        """
        # TODO: Implement stopping criteria
        # Guidelines:
        # If using cma library:
        #   return self.es.stop()
        # 
        # If implementing manually:
        #   Check for convergence (e.g., sigma too small, fitness plateau)
        
        pass
    
    def result(self):
        """
        Get the best solution found so far.
        
        Returns:
            best_params: Best parameter vector
            best_fitness: Fitness of best solution
        """
        # TODO: Implement result retrieval
        # Guidelines:
        # If using cma library:
        #   return self.es.result.xbest, -self.es.result.fbest
        # 
        # If implementing manually:
        #   Return the best parameters and fitness seen during optimization
        
        pass


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
    # TODO: Implement evaluation
    # Guidelines:
    # 1. Set all models to eval mode
    # 2. For each episode:
    #    a) Reset environment: obs = env.reset()
    #    b) Initialize RNN hidden state: hidden = None
    #    c) For each step:
    #       - Encode observation: z = vae.encode(obs)[0]  # Use mean
    #       - Get RNN hidden state: h = hidden[0] if hidden else zeros
    #       - Compute action: action = controller(z, h)
    #       - Step environment: obs, reward, done, info = env.step(action)
    #       - Update RNN hidden state with (z, action)
    #       - Accumulate reward
    #       - Break if done
    # 3. Return average reward and steps
    # 
    # Note: This is for real environment evaluation. For training,
    # we can evaluate in the learned world model (dream environment).
    
    pass


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
    # TODO: Implement dream evaluation
    # Guidelines:
    # 1. Initialize:
    #    - Sample or use provided initial_z
    #    - Initialize RNN hidden states
    # 
    # 2. For each step:
    #    a) Get action from controller(z, h)
    #    b) Predict next state with RNN: outputs = rnn(z, action, hidden)
    #    c) Sample next z from MDN: z_next = rnn.sample(pi, mu, sigma)
    #    d) Get predicted reward: reward = outputs['reward']
    #    e) Check done flag: done = outputs['done'] > 0.5
    #    f) Accumulate reward, update hidden state
    #    g) Continue until done or max_steps
    # 
    # 3. Return average reward
    # 
    # This allows us to evaluate millions of steps quickly without
    # interacting with the real environment!
    
    pass


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
    
    # TODO: Uncomment when implemented
    # # Forward pass
    # action = controller(z, h)
    # 
    # # Check shape and range
    # assert action.shape == (batch_size, 3)
    # assert action.min() >= -1.0 and action.max() <= 1.0, "Actions should be in [-1, 1]"
    # 
    # # Test parameter extraction/setting
    # params = controller.get_parameters_as_vector()
    # print(f"  Number of parameters: {len(params)}")
    # 
    # # Set parameters and verify
    # new_params = np.random.randn(len(params)) * 0.1
    # controller.set_parameters_from_vector(new_params)
    # retrieved_params = controller.get_parameters_as_vector()
    # np.testing.assert_allclose(new_params, retrieved_params, rtol=1e-5)
    # 
    # print(f"✓ Controller test passed!")
    # print(f"  Action shape: {action.shape}")
    # print(f"  Action range: [{action.min():.3f}, {action.max():.3f}]")
    # print(f"  Total parameters: {controller.num_parameters()}")
    
    print("Implementation not complete yet. Uncomment test code when ready.")


if __name__ == "__main__":
    test_controller()

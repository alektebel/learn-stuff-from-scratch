"""
Replay Buffer for World Models

This module provides efficient replay buffer implementations for storing and
sampling experience data. Unlike standard RL buffers that sample individual
transitions, these buffers handle sequential data for training recurrent models.

Key Features:
- Store complete episodes with variable lengths
- Sample sequences of fixed length for training
- Efficient memory management
- Support for both online and offline learning

Buffer Types:
1. ReplayBuffer: Standard sequence buffer for online RL
2. EpisodeBuffer: Stores complete episodes, samples subsequences
3. UniformBuffer: Simple FIFO buffer with uniform sampling

Example:
    >>> buffer = EpisodeBuffer(capacity=100000, obs_shape=(3, 64, 64))
    >>> for episode in range(100):
    ...     obs = env.reset()
    ...     for step in range(episode_length):
    ...         action = agent.act(obs)
    ...         obs, reward, done, _ = env.step(action)
    ...         buffer.add(obs, action, reward, done)
    >>> batch = buffer.sample()  # Sample training batch

References:
- World Models (Ha & Schmidhuber, 2018)
- Dream to Control (Hafner et al., 2020)
- Mastering Diverse Domains through World Models (Hafner et al., 2021)
"""

import numpy as np
from collections import deque
import pickle
import os


class EpisodeBuffer:
    """
    Replay buffer that stores complete episodes and samples subsequences.
    
    This is the most common buffer type for world model training. Episodes
    are stored in full, and training batches consist of subsequences sampled
    uniformly from across all stored episodes.
    
    Args:
        capacity: Maximum number of time steps to store (not episodes)
        obs_shape: Shape of observations, e.g., (3, 64, 64)
        action_shape: Shape of actions, e.g., (2,) for continuous or () for discrete
        seq_len: Length of sequences to sample for training (default: 50)
        batch_size: Number of sequences in a training batch (default: 50)
    """
    
    def __init__(
        self,
        capacity=1000000,
        obs_shape=(3, 64, 64),
        action_shape=(),
        seq_len=50,
        batch_size=50
    ):
        self.capacity = capacity
        self.obs_shape = obs_shape
        self.action_shape = action_shape
        self.seq_len = seq_len
        self.batch_size = batch_size
        
        # Storage for episodes
        self.episodes = deque()
        self.total_steps = 0
        
        # Current episode being collected
        self.current_episode = {
            'observations': [],
            'actions': [],
            'rewards': [],
            'dones': [],
        }
    
    def add(self, obs, action, reward, done):
        """
        Add a single transition to the buffer.
        
        Transitions are accumulated into episodes. When done=True,
        the episode is stored and a new one begins.
        
        Args:
            obs: Observation (numpy array)
            action: Action (numpy array or scalar)
            reward: Reward (float)
            done: Whether episode ended (bool)
        """
        # TODO: Implement adding transition
        # Guidelines:
        # 1. Append transition to current episode
        # 2. If done=True, store the complete episode
        # 3. Handle capacity management (remove old episodes if needed)
        # 4. Reset current_episode after storing
        
        self.current_episode['observations'].append(obs)
        self.current_episode['actions'].append(action)
        self.current_episode['rewards'].append(reward)
        self.current_episode['dones'].append(done)
        
        if done:
            # Store complete episode
            episode_len = len(self.current_episode['observations'])
            
            if episode_len > 0:
                # Convert lists to numpy arrays
                stored_episode = {
                    'observations': np.array(self.current_episode['observations']),
                    'actions': np.array(self.current_episode['actions']),
                    'rewards': np.array(self.current_episode['rewards']),
                    'dones': np.array(self.current_episode['dones']),
                    'length': episode_len
                }
                
                self.episodes.append(stored_episode)
                self.total_steps += episode_len
                
                # Remove old episodes if over capacity
                while self.total_steps > self.capacity and len(self.episodes) > 1:
                    removed_episode = self.episodes.popleft()
                    self.total_steps -= removed_episode['length']
            
            # Reset current episode
            self.current_episode = {
                'observations': [],
                'actions': [],
                'rewards': [],
                'dones': [],
            }
    
    def sample(self):
        """
        Sample a batch of sequences from stored episodes.
        
        Each sequence has length seq_len and is sampled uniformly from
        the available episodes. Sequences can wrap around episode boundaries
        or be padded if needed (implementation choice).
        
        Returns:
            batch: Dictionary containing:
                - observations: (batch_size, seq_len, *obs_shape)
                - actions: (batch_size, seq_len, *action_shape)
                - rewards: (batch_size, seq_len)
                - dones: (batch_size, seq_len)
        """
        # TODO: Implement sequence sampling
        # Guidelines:
        # 1. Check if buffer has enough data (at least seq_len steps)
        # 2. For each sequence in batch:
        #    a. Randomly select an episode
        #    b. Randomly select a starting position
        #    c. Extract sequence of length seq_len
        #    d. Handle edge cases (sequence extends beyond episode)
        # 3. Stack sequences into batch arrays
        # 4. Return as dictionary
        
        if len(self.episodes) == 0 or self.total_steps < self.seq_len:
            raise ValueError("Not enough data in buffer to sample")
        
        batch = {
            'observations': [],
            'actions': [],
            'rewards': [],
            'dones': [],
        }
        
        for _ in range(self.batch_size):
            # Select random episode (weighted by length for uniform sampling)
            episode = np.random.choice(self.episodes)
            episode_len = episode['length']
            
            # Select random starting position
            # Ensure we can sample seq_len steps
            if episode_len >= self.seq_len:
                start_idx = np.random.randint(0, episode_len - self.seq_len + 1)
                end_idx = start_idx + self.seq_len
                
                batch['observations'].append(episode['observations'][start_idx:end_idx])
                batch['actions'].append(episode['actions'][start_idx:end_idx])
                batch['rewards'].append(episode['rewards'][start_idx:end_idx])
                batch['dones'].append(episode['dones'][start_idx:end_idx])
            else:
                # Episode too short, pad with zeros
                obs_seq = np.zeros((self.seq_len, *self.obs_shape), dtype=np.float32)
                act_seq = np.zeros((self.seq_len, *self.action_shape), dtype=np.float32)
                rew_seq = np.zeros(self.seq_len, dtype=np.float32)
                done_seq = np.ones(self.seq_len, dtype=bool)  # Mark as done
                
                obs_seq[:episode_len] = episode['observations']
                act_seq[:episode_len] = episode['actions']
                rew_seq[:episode_len] = episode['rewards']
                done_seq[:episode_len] = episode['dones']
                
                batch['observations'].append(obs_seq)
                batch['actions'].append(act_seq)
                batch['rewards'].append(rew_seq)
                batch['dones'].append(done_seq)
        
        # Stack into numpy arrays
        batch['observations'] = np.array(batch['observations'])
        batch['actions'] = np.array(batch['actions'])
        batch['rewards'] = np.array(batch['rewards'])
        batch['dones'] = np.array(batch['dones'])
        
        return batch
    
    def __len__(self):
        """Return total number of steps stored."""
        return self.total_steps
    
    def save(self, path):
        """
        Save buffer to disk.
        
        Args:
            path: File path to save buffer
        """
        # TODO: Implement saving
        # Guidelines:
        # 1. Convert deque to list for serialization
        # 2. Use pickle or numpy to save
        # 3. Handle file creation and errors
        
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        
        save_data = {
            'episodes': list(self.episodes),
            'total_steps': self.total_steps,
            'capacity': self.capacity,
            'obs_shape': self.obs_shape,
            'action_shape': self.action_shape,
            'seq_len': self.seq_len,
            'batch_size': self.batch_size,
        }
        
        with open(path, 'wb') as f:
            pickle.dump(save_data, f)
        
        print(f"Buffer saved to {path} ({self.total_steps} steps, {len(self.episodes)} episodes)")
    
    def load(self, path):
        """
        Load buffer from disk.
        
        Args:
            path: File path to load buffer from
        """
        # TODO: Implement loading
        # Guidelines:
        # 1. Load data from file
        # 2. Restore episodes deque
        # 3. Restore all metadata
        # 4. Handle errors gracefully
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Buffer file not found: {path}")
        
        with open(path, 'rb') as f:
            save_data = pickle.load(f)
        
        self.episodes = deque(save_data['episodes'])
        self.total_steps = save_data['total_steps']
        self.capacity = save_data['capacity']
        self.obs_shape = save_data['obs_shape']
        self.action_shape = save_data['action_shape']
        self.seq_len = save_data['seq_len']
        self.batch_size = save_data['batch_size']
        
        print(f"Buffer loaded from {path} ({self.total_steps} steps, {len(self.episodes)} episodes)")


class UniformBuffer:
    """
    Simple uniform replay buffer with FIFO replacement.
    
    Stores individual transitions in a circular buffer. Simpler than
    EpisodeBuffer but doesn't maintain episode structure.
    
    Args:
        capacity: Maximum number of transitions to store
        obs_shape: Shape of observations
        action_shape: Shape of actions
    """
    
    def __init__(self, capacity=1000000, obs_shape=(3, 64, 64), action_shape=()):
        self.capacity = capacity
        self.obs_shape = obs_shape
        self.action_shape = action_shape
        
        # Pre-allocate arrays for efficiency
        self.observations = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self.actions = np.zeros((capacity, *action_shape), dtype=np.float32)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_observations = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=bool)
        
        self.position = 0
        self.size = 0
    
    def add(self, obs, action, reward, next_obs, done):
        """
        Add a transition to the buffer.
        
        Args:
            obs: Current observation
            action: Action taken
            reward: Reward received
            next_obs: Next observation
            done: Whether episode ended
        """
        # TODO: Implement adding transition
        # Guidelines:
        # 1. Store transition at current position
        # 2. Update position (circular buffer)
        # 3. Update size (up to capacity)
        
        self.observations[self.position] = obs
        self.actions[self.position] = action
        self.rewards[self.position] = reward
        self.next_observations[self.position] = next_obs
        self.dones[self.position] = done
        
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
    
    def sample(self, batch_size):
        """
        Sample a batch of transitions.
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            Dictionary containing sampled transitions
        """
        # TODO: Implement sampling
        # Guidelines:
        # 1. Sample random indices from [0, size)
        # 2. Return transitions at those indices
        # 3. Handle case where buffer is not full
        
        if self.size < batch_size:
            raise ValueError(f"Not enough samples in buffer ({self.size} < {batch_size})")
        
        indices = np.random.randint(0, self.size, size=batch_size)
        
        return {
            'observations': self.observations[indices],
            'actions': self.actions[indices],
            'rewards': self.rewards[indices],
            'next_observations': self.next_observations[indices],
            'dones': self.dones[indices],
        }
    
    def __len__(self):
        """Return number of transitions stored."""
        return self.size


class PrioritizedBuffer:
    """
    Prioritized replay buffer for importance sampling.
    
    Samples transitions with probability proportional to their TD error
    or other priority metric. More complex but can improve learning efficiency.
    
    Args:
        capacity: Maximum number of transitions
        obs_shape: Shape of observations
        action_shape: Shape of actions
        alpha: Priority exponent (0 = uniform, 1 = fully prioritized)
        beta: Importance sampling exponent (0 = no correction, 1 = full correction)
    """
    
    def __init__(
        self,
        capacity=1000000,
        obs_shape=(3, 64, 64),
        action_shape=(),
        alpha=0.6,
        beta=0.4
    ):
        self.capacity = capacity
        self.obs_shape = obs_shape
        self.action_shape = action_shape
        self.alpha = alpha
        self.beta = beta
        
        # Storage
        self.observations = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self.actions = np.zeros((capacity, *action_shape), dtype=np.float32)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_observations = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=bool)
        
        # Priority storage
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.max_priority = 1.0
        
        self.position = 0
        self.size = 0
    
    def add(self, obs, action, reward, next_obs, done):
        """
        Add transition with maximum priority.
        
        New transitions get max priority to ensure they're sampled.
        
        Args:
            obs: Current observation
            action: Action taken
            reward: Reward received
            next_obs: Next observation
            done: Whether episode ended
        """
        # TODO: Implement adding with priority
        # Guidelines:
        # 1. Store transition like UniformBuffer
        # 2. Set priority to max_priority for new experiences
        # 3. Update position and size
        
        self.observations[self.position] = obs
        self.actions[self.position] = action
        self.rewards[self.position] = reward
        self.next_observations[self.position] = next_obs
        self.dones[self.position] = done
        
        self.priorities[self.position] = self.max_priority
        
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
    
    def sample(self, batch_size):
        """
        Sample batch with prioritized sampling.
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            Dictionary with sampled transitions, indices, and weights
        """
        # TODO: Implement prioritized sampling
        # Guidelines:
        # 1. Calculate sampling probabilities from priorities
        # 2. Sample indices based on probabilities
        # 3. Calculate importance sampling weights
        # 4. Return transitions, indices, and weights
        
        if self.size < batch_size:
            raise ValueError(f"Not enough samples in buffer ({self.size} < {batch_size})")
        
        # Get priorities for valid range
        priorities = self.priorities[:self.size] ** self.alpha
        probabilities = priorities / priorities.sum()
        
        # Sample indices
        indices = np.random.choice(self.size, size=batch_size, p=probabilities, replace=False)
        
        # Calculate importance sampling weights
        weights = (self.size * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()  # Normalize for stability
        
        return {
            'observations': self.observations[indices],
            'actions': self.actions[indices],
            'rewards': self.rewards[indices],
            'next_observations': self.next_observations[indices],
            'dones': self.dones[indices],
            'indices': indices,
            'weights': weights,
        }
    
    def update_priorities(self, indices, priorities):
        """
        Update priorities for sampled transitions.
        
        Called after computing TD errors or other priority metrics.
        
        Args:
            indices: Indices of transitions to update
            priorities: New priority values
        """
        # TODO: Implement priority update
        # Guidelines:
        # 1. Update priorities at given indices
        # 2. Update max_priority if needed
        # 3. Add small epsilon to avoid zero priorities
        
        priorities = np.abs(priorities) + 1e-6  # Avoid zero priorities
        self.priorities[indices] = priorities
        self.max_priority = max(self.max_priority, priorities.max())
    
    def __len__(self):
        """Return number of transitions stored."""
        return self.size


# Example usage and testing
if __name__ == "__main__":
    print("Testing replay buffers...")
    
    # Test EpisodeBuffer
    print("\n=== Testing EpisodeBuffer ===")
    buffer = EpisodeBuffer(
        capacity=1000,
        obs_shape=(3, 64, 64),
        action_shape=(2,),
        seq_len=10,
        batch_size=4
    )
    
    # Simulate episode
    for episode_idx in range(3):
        episode_len = np.random.randint(20, 50)
        for step in range(episode_len):
            obs = np.random.randn(3, 64, 64).astype(np.float32)
            action = np.random.randn(2).astype(np.float32)
            reward = np.random.randn()
            done = (step == episode_len - 1)
            
            buffer.add(obs, action, reward, done)
    
    print(f"✓ Added 3 episodes, total steps: {len(buffer)}")
    
    # Test sampling
    try:
        batch = buffer.sample()
        print(f"✓ Sampled batch:")
        print(f"  Observations: {batch['observations'].shape}")
        print(f"  Actions: {batch['actions'].shape}")
        print(f"  Rewards: {batch['rewards'].shape}")
        print(f"  Dones: {batch['dones'].shape}")
    except Exception as e:
        print(f"✗ Sampling error: {e}")
    
    # Test save/load
    try:
        buffer.save('/tmp/test_buffer.pkl')
        buffer2 = EpisodeBuffer(capacity=1000, obs_shape=(3, 64, 64), action_shape=(2,))
        buffer2.load('/tmp/test_buffer.pkl')
        print(f"✓ Save/load works: {len(buffer2)} steps")
    except Exception as e:
        print(f"✗ Save/load error: {e}")
    
    # Test UniformBuffer
    print("\n=== Testing UniformBuffer ===")
    uniform_buffer = UniformBuffer(capacity=100, obs_shape=(4,), action_shape=())
    
    for i in range(50):
        obs = np.random.randn(4).astype(np.float32)
        action = np.random.randint(0, 4)
        reward = np.random.randn()
        next_obs = np.random.randn(4).astype(np.float32)
        done = (i % 10 == 9)
        
        uniform_buffer.add(obs, action, reward, next_obs, done)
    
    print(f"✓ Added 50 transitions to UniformBuffer")
    
    try:
        batch = uniform_buffer.sample(16)
        print(f"✓ Sampled batch of size {len(batch['observations'])}")
    except Exception as e:
        print(f"✗ Sampling error: {e}")
    
    # Test PrioritizedBuffer
    print("\n=== Testing PrioritizedBuffer ===")
    prior_buffer = PrioritizedBuffer(capacity=100, obs_shape=(4,), action_shape=())
    
    for i in range(50):
        obs = np.random.randn(4).astype(np.float32)
        action = np.random.randint(0, 4)
        reward = np.random.randn()
        next_obs = np.random.randn(4).astype(np.float32)
        done = (i % 10 == 9)
        
        prior_buffer.add(obs, action, reward, next_obs, done)
    
    print(f"✓ Added 50 transitions to PrioritizedBuffer")
    
    try:
        batch = prior_buffer.sample(16)
        print(f"✓ Sampled prioritized batch:")
        print(f"  Batch size: {len(batch['observations'])}")
        print(f"  Weights range: [{batch['weights'].min():.3f}, {batch['weights'].max():.3f}]")
        
        # Update priorities
        new_priorities = np.random.rand(16)
        prior_buffer.update_priorities(batch['indices'], new_priorities)
        print(f"✓ Updated priorities")
    except Exception as e:
        print(f"✗ Prioritized sampling error: {e}")
    
    print("\nAll tests completed!")

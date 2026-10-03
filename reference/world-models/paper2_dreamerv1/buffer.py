"""
Replay Buffer for DreamerV1

Stores experience sequences and provides batches for training the world model
and actor-critic. Unlike typical RL buffers that store individual transitions,
this buffer stores and samples sequences for recurrent training.

Key Features:
- Store episodes as sequences
- Sample subsequences of fixed length
- Handle variable-length episodes
- Efficient batching for training

Paper: Dream to Control (Hafner et al., 2020)
Section 5: Implementation Details
"""

import numpy as np
import torch
from collections import deque


class ReplayBuffer:
    """
    Replay buffer for storing and sampling sequential experience.
    
    Stores complete episodes and samples subsequences for training recurrent models.
    
    Args:
        capacity: Maximum number of time steps to store
        obs_shape: Shape of observations (channels, height, width)
        action_dim: Dimension of action space
        seq_len: Length of sequences to sample (default: 50)
        batch_size: Batch size for sampling (default: 50)
    """
    
    def __init__(
        self,
        capacity=1000000,
        obs_shape=(3, 64, 64),
        action_dim=None,
        seq_len=50,
        batch_size=50
    ):
        self.capacity = capacity
        self.obs_shape = obs_shape
        self.action_dim = action_dim
        self.seq_len = seq_len
        self.batch_size = batch_size
        
        # TODO: Initialize storage
        # Guidelines:
        # - Use deque for efficient FIFO behavior when at capacity
        # - Store episodes as dictionaries containing:
        #   - observations: list of observations
        #   - actions: list of actions
        #   - rewards: list of rewards
        #   - dones: list of done flags
        # - Keep track of total steps stored
        # - Keep track of current episode being filled
        
        # self.episodes = deque(maxlen=None)  # Will manage capacity manually
        # self.current_episode = {
        #     'observations': [],
        #     'actions': [],
        #     'rewards': [],
        #     'dones': []
        # }
        # self.total_steps = 0
        
        pass  # Remove when implementing
    
    def add(self, obs, action, reward, done):
        """
        Add a single transition to the buffer.
        
        Args:
            obs: Observation (channels, height, width) as numpy array
            action: Action as numpy array
            reward: Reward as float
            done: Done flag as bool
        """
        # TODO: Implement add
        # Guidelines:
        # 1. Add transition to current_episode
        # 2. Increment total_steps
        # 3. If done=True or episode is too long:
        #    a. Finalize current episode (convert lists to numpy arrays)
        #    b. Add to episodes deque
        #    c. Start new episode
        # 4. Manage capacity:
        #    a. If total_steps > capacity:
        #       - Remove oldest episodes until under capacity
        #       - Update total_steps
        #
        # Note: Store observations as uint8 to save memory, convert to float during sampling
        
        pass
    
    def sample(self):
        """
        Sample a batch of sequences.
        
        Returns:
            batch: Dict containing:
                observations: (batch_size, seq_len, *obs_shape)
                actions: (batch_size, seq_len, action_dim)
                rewards: (batch_size, seq_len)
                dones: (batch_size, seq_len)
        """
        # TODO: Implement sampling
        # Guidelines:
        # 1. Check if buffer has enough data (need at least batch_size sequences)
        # 2. For each sample in batch:
        #    a. Randomly select an episode
        #    b. If episode length <= seq_len: use entire episode and pad
        #    c. If episode length > seq_len: randomly select a starting point
        #       and extract seq_len steps
        #    d. Handle padding for shorter sequences (pad with zeros and done=True)
        # 3. Stack into batch tensors
        # 4. Convert observations to float and normalize to [0, 1]
        # 5. Return as dictionary
        #
        # Note: Make sure to sample episodes with probability proportional to their length
        # to ensure all time steps have equal probability of being sampled.
        
        pass
    
    def _sample_episode(self):
        """
        Sample a random episode with probability proportional to length.
        
        Returns:
            episode: Randomly selected episode dict
        """
        # TODO: Implement episode sampling
        # Guidelines:
        # - Weight episodes by their length
        # - Use numpy.random.choice with weights
        # - Return selected episode
        
        pass
    
    def _extract_sequence(self, episode):
        """
        Extract a sequence from an episode.
        
        Args:
            episode: Episode dict
            
        Returns:
            sequence: Dict with extracted sequence of length seq_len
        """
        # TODO: Implement sequence extraction
        # Guidelines:
        # 1. Get episode length
        # 2. If episode_len <= seq_len:
        #    - Use entire episode
        #    - Pad to seq_len with zeros
        #    - Set done=True for padded steps
        # 3. If episode_len > seq_len:
        #    - Randomly select start index: max is episode_len - seq_len
        #    - Extract seq_len consecutive steps
        # 4. Return as dict
        
        pass
    
    def __len__(self):
        """Return total number of steps in buffer."""
        return self.total_steps
    
    def num_episodes(self):
        """Return number of episodes in buffer."""
        # return len(self.episodes)
        pass


class SimpleBuffer:
    """
    Simplified buffer for debugging and testing.
    
    This is a minimal implementation that stores fixed-length sequences
    directly without episode boundaries.
    """
    
    def __init__(self, capacity=10000, obs_shape=(3, 64, 64), action_dim=6, seq_len=50):
        self.capacity = capacity
        self.obs_shape = obs_shape
        self.action_dim = action_dim
        self.seq_len = seq_len
        
        # TODO: Initialize simple storage
        # Guidelines:
        # - Pre-allocate arrays for efficiency
        # - Store observations, actions, rewards, dones
        # - Use circular buffer (wrap around when full)
        
        # self.observations = np.zeros((capacity,) + obs_shape, dtype=np.uint8)
        # self.actions = np.zeros((capacity, action_dim), dtype=np.float32)
        # self.rewards = np.zeros(capacity, dtype=np.float32)
        # self.dones = np.zeros(capacity, dtype=np.bool_)
        # self.idx = 0
        # self.full = False
        
        pass
    
    def add(self, obs, action, reward, done):
        """Add single transition."""
        # TODO: Implement simple add
        # Guidelines:
        # 1. Store at current index
        # 2. Increment index
        # 3. Wrap around if at capacity
        # 4. Mark as full if wrapped
        pass
    
    def sample(self, batch_size):
        """Sample batch of sequences."""
        # TODO: Implement simple sampling
        # Guidelines:
        # 1. Determine valid range (0 to idx if not full, else full buffer)
        # 2. Sample batch_size starting indices
        # 3. Extract seq_len steps from each starting index
        # 4. Handle boundary wrapping carefully
        # 5. Convert to tensors and return
        pass
    
    def __len__(self):
        """Return number of valid samples."""
        return self.idx if not self.full else self.capacity


def test_buffer():
    """
    Test function to verify buffer implementation.
    """
    print("Testing Replay Buffer...")
    
    obs_shape = (3, 64, 64)
    action_dim = 6
    seq_len = 10
    batch_size = 4
    
    print("\nTest 1: Basic buffer operations")
    # TODO: Uncomment when implemented
    # buffer = ReplayBuffer(
    #     capacity=1000,
    #     obs_shape=obs_shape,
    #     action_dim=action_dim,
    #     seq_len=seq_len,
    #     batch_size=batch_size
    # )
    # 
    # # Add some transitions
    # for episode in range(3):
    #     for step in range(20):
    #         obs = np.random.randint(0, 256, obs_shape, dtype=np.uint8)
    #         action = np.random.randn(action_dim).astype(np.float32)
    #         reward = np.random.randn()
    #         done = (step == 19)
    #         buffer.add(obs, action, reward, done)
    # 
    # print(f"✓ Added 3 episodes (60 steps)")
    # print(f"  Total steps: {len(buffer)}")
    # print(f"  Num episodes: {buffer.num_episodes()}")
    
    print("\nTest 2: Sampling")
    # TODO: Uncomment when implemented
    # batch = buffer.sample()
    # 
    # assert 'observations' in batch
    # assert 'actions' in batch
    # assert 'rewards' in batch
    # assert 'dones' in batch
    # 
    # assert batch['observations'].shape == (batch_size, seq_len, *obs_shape)
    # assert batch['actions'].shape == (batch_size, seq_len, action_dim)
    # assert batch['rewards'].shape == (batch_size, seq_len)
    # assert batch['dones'].shape == (batch_size, seq_len)
    # 
    # # Check data types
    # assert batch['observations'].dtype == torch.float32
    # assert batch['actions'].dtype == torch.float32
    # assert batch['rewards'].dtype == torch.float32
    # 
    # # Check value ranges
    # assert batch['observations'].min() >= 0 and batch['observations'].max() <= 1
    # 
    # print(f"✓ Sampling works correctly")
    # print(f"  Batch shapes:")
    # print(f"    Observations: {batch['observations'].shape}")
    # print(f"    Actions: {batch['actions'].shape}")
    # print(f"    Rewards: {batch['rewards'].shape}")
    # print(f"    Dones: {batch['dones'].shape}")
    
    print("\nTest 3: Capacity management")
    # TODO: Uncomment when implemented
    # small_buffer = ReplayBuffer(capacity=100, obs_shape=obs_shape, action_dim=action_dim)
    # 
    # # Add more than capacity
    # for episode in range(10):
    #     for step in range(20):
    #         obs = np.random.randint(0, 256, obs_shape, dtype=np.uint8)
    #         action = np.random.randn(action_dim).astype(np.float32)
    #         reward = np.random.randn()
    #         done = (step == 19)
    #         small_buffer.add(obs, action, reward, done)
    # 
    # assert len(small_buffer) <= 100, "Buffer should respect capacity"
    # print(f"✓ Capacity management works: {len(small_buffer)} steps")
    
    print("\nImplementation not complete yet. Uncomment tests when ready.")


if __name__ == "__main__":
    test_buffer()

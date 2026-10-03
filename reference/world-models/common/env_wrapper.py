"""
Environment Wrappers for World Models

This module provides preprocessing wrappers for gym environments commonly used
in world model research. These wrappers handle observation preprocessing,
action space modifications, and episode management.

Key Features:
- Image resizing and normalization
- Frame stacking for temporal information
- Action repeat for faster learning
- Grayscale conversion (optional)
- Episode statistics tracking

Common usage in papers:
- World Models: 64x64 RGB, action repeat 4
- DreamerV1/V2/V3: 64x64 RGB, action repeat 2-4
- IRIS: Variable sizes, typically 64x64 or 128x128

References:
- World Models (Ha & Schmidhuber, 2018)
- Dream to Control (Hafner et al., 2020)
- Mastering Diverse Domains through World Models (Hafner et al., 2021)
"""

import numpy as np
import gym
from gym import spaces
from collections import deque
import cv2


class ResizeObservation(gym.ObservationWrapper):
    """
    Resize image observations to a specified size.
    
    This is crucial for world models as:
    - Reduces computational cost for VAE/encoder
    - Standardizes input size across environments
    - Focuses on essential visual features
    
    Args:
        env: Gym environment to wrap
        size: Tuple (height, width) for output size
        interpolation: CV2 interpolation method (default: INTER_AREA)
    """
    
    def __init__(self, env, size=(64, 64), interpolation=cv2.INTER_AREA):
        super().__init__(env)
        self.size = size  # (height, width)
        self.interpolation = interpolation
        
        # TODO: Update observation space
        # Guidelines:
        # - Get the original observation space shape
        # - Determine if observations are (H, W, C) or (C, H, W)
        # - Create new space with resized dimensions
        # - Preserve the dtype and bounds (min/max values)
        
        old_space = env.observation_space
        if isinstance(old_space, spaces.Box):
            # Assuming observations are images with shape (H, W, C) or (C, H, W)
            old_shape = old_space.shape
            
            # Detect format: channels-last (H,W,C) or channels-first (C,H,W)
            if len(old_shape) == 3:
                if old_shape[0] in [1, 3, 4]:  # Likely channels-first
                    self.channels_first = True
                    channels = old_shape[0]
                    new_shape = (channels, size[0], size[1])
                else:  # Likely channels-last
                    self.channels_first = False
                    channels = old_shape[2]
                    new_shape = (size[0], size[1], channels)
            else:
                # Grayscale image (H, W)
                self.channels_first = False
                new_shape = size
            
            self.observation_space = spaces.Box(
                low=old_space.low.flat[0],
                high=old_space.high.flat[0],
                shape=new_shape,
                dtype=old_space.dtype
            )
        else:
            raise ValueError(f"Unsupported observation space type: {type(old_space)}")
    
    def observation(self, obs):
        """
        Resize the observation.
        
        Args:
            obs: Original observation
            
        Returns:
            Resized observation
        """
        # TODO: Implement observation resizing
        # Guidelines:
        # 1. Handle both channels-first and channels-last formats
        # 2. Use cv2.resize with the specified interpolation
        # 3. Ensure output format matches the observation space
        # 4. Handle grayscale and RGB images
        
        # Convert to channels-last for cv2 if needed
        if len(obs.shape) == 3 and self.channels_first:
            obs = np.transpose(obs, (1, 2, 0))
        
        # Resize using cv2 (expects H, W, C format)
        resized = cv2.resize(obs, (self.size[1], self.size[0]), 
                            interpolation=self.interpolation)
        
        # Handle case where cv2 drops channel dimension for grayscale
        if len(obs.shape) == 3 and len(resized.shape) == 2:
            resized = np.expand_dims(resized, axis=-1)
        
        # Convert back to channels-first if needed
        if len(resized.shape) == 3 and self.channels_first:
            resized = np.transpose(resized, (2, 0, 1))
        
        return resized


class NormalizeObservation(gym.ObservationWrapper):
    """
    Normalize observations to [0, 1] or [-1, 1] range.
    
    Neural networks typically perform better with normalized inputs.
    This wrapper handles uint8 images and float arrays.
    
    Args:
        env: Gym environment to wrap
        scale_range: Output range, either '01' for [0, 1] or '11' for [-1, 1]
    """
    
    def __init__(self, env, scale_range='01'):
        super().__init__(env)
        self.scale_range = scale_range
        
        # Update observation space bounds
        old_space = env.observation_space
        if isinstance(old_space, spaces.Box):
            if scale_range == '01':
                low, high = 0.0, 1.0
            elif scale_range == '11':
                low, high = -1.0, 1.0
            else:
                raise ValueError(f"scale_range must be '01' or '11', got {scale_range}")
            
            self.observation_space = spaces.Box(
                low=low,
                high=high,
                shape=old_space.shape,
                dtype=np.float32
            )
    
    def observation(self, obs):
        """
        Normalize the observation.
        
        Args:
            obs: Original observation
            
        Returns:
            Normalized observation
        """
        # TODO: Implement normalization
        # Guidelines:
        # 1. Convert to float32 if not already
        # 2. If uint8 (0-255), divide by 255.0
        # 3. If scale_range is '11', scale from [0,1] to [-1,1]
        # 4. Handle edge cases where obs is already normalized
        
        obs = obs.astype(np.float32)
        
        # Normalize to [0, 1] if needed
        if obs.max() > 1.0:
            obs = obs / 255.0
        
        # Scale to [-1, 1] if requested
        if self.scale_range == '11':
            obs = obs * 2.0 - 1.0
        
        return obs


class GrayScaleObservation(gym.ObservationWrapper):
    """
    Convert RGB observations to grayscale.
    
    Some world models use grayscale to reduce dimensionality and
    focus on structure rather than color. Used in original World Models paper.
    
    Args:
        env: Gym environment to wrap
        keep_dim: If True, output shape is (H, W, 1), else (H, W)
    """
    
    def __init__(self, env, keep_dim=True):
        super().__init__(env)
        self.keep_dim = keep_dim
        
        # TODO: Update observation space
        # Guidelines:
        # - Reduce color channels from 3 to 1
        # - Handle both channels-first and channels-last formats
        # - Preserve height, width, and dtype
        
        old_space = env.observation_space
        if isinstance(old_space, spaces.Box):
            old_shape = old_space.shape
            
            # Detect format
            if len(old_shape) == 3:
                if old_shape[0] == 3:  # Channels-first (3, H, W)
                    self.channels_first = True
                    if keep_dim:
                        new_shape = (1, old_shape[1], old_shape[2])
                    else:
                        new_shape = (old_shape[1], old_shape[2])
                elif old_shape[2] == 3:  # Channels-last (H, W, 3)
                    self.channels_first = False
                    if keep_dim:
                        new_shape = (old_shape[0], old_shape[1], 1)
                    else:
                        new_shape = (old_shape[0], old_shape[1])
                else:
                    raise ValueError(f"Expected 3 color channels, got shape {old_shape}")
            else:
                raise ValueError(f"Expected 3D observation, got shape {old_shape}")
            
            self.observation_space = spaces.Box(
                low=old_space.low.flat[0],
                high=old_space.high.flat[0],
                shape=new_shape,
                dtype=old_space.dtype
            )
    
    def observation(self, obs):
        """
        Convert observation to grayscale.
        
        Args:
            obs: RGB observation
            
        Returns:
            Grayscale observation
        """
        # TODO: Implement RGB to grayscale conversion
        # Guidelines:
        # 1. Handle both channels-first and channels-last
        # 2. Use standard RGB to grayscale formula or cv2.cvtColor
        # 3. Maintain dtype
        # 4. Add or remove channel dimension based on keep_dim
        
        # Convert to channels-last for processing
        if self.channels_first:
            obs = np.transpose(obs, (1, 2, 0))
        
        # Convert to grayscale using OpenCV
        if obs.dtype == np.uint8:
            gray = cv2.cvtColor(obs, cv2.COLOR_RGB2GRAY)
        else:
            # For float observations, use weighted average
            gray = np.dot(obs[..., :3], [0.299, 0.587, 0.114])
        
        # Add channel dimension if needed
        if self.keep_dim:
            gray = np.expand_dims(gray, axis=-1)
            if self.channels_first:
                gray = np.transpose(gray, (2, 0, 1))
        
        return gray.astype(obs.dtype)


class FrameStack(gym.Wrapper):
    """
    Stack multiple consecutive frames as observation.
    
    Provides temporal information to the agent, allowing it to infer
    velocity and other dynamics from static frames.
    
    Args:
        env: Gym environment to wrap
        num_stack: Number of frames to stack (default: 4)
        channels_first: If True, stack along channel dimension (C, H, W)
    """
    
    def __init__(self, env, num_stack=4, channels_first=False):
        super().__init__(env)
        self.num_stack = num_stack
        self.channels_first = channels_first
        self.frames = deque(maxlen=num_stack)
        
        # TODO: Update observation space
        # Guidelines:
        # - Multiply channel dimension by num_stack
        # - Preserve other dimensions and properties
        # - Handle both channels-first and channels-last formats
        
        old_space = env.observation_space
        if isinstance(old_space, spaces.Box):
            old_shape = old_space.shape
            
            if channels_first:
                # Shape: (C, H, W) -> (C*num_stack, H, W)
                new_shape = (old_shape[0] * num_stack, *old_shape[1:])
            else:
                # Shape: (H, W, C) -> (H, W, C*num_stack)
                new_shape = (*old_shape[:-1], old_shape[-1] * num_stack)
            
            self.observation_space = spaces.Box(
                low=np.repeat(old_space.low, num_stack, axis=0 if channels_first else -1),
                high=np.repeat(old_space.high, num_stack, axis=0 if channels_first else -1),
                shape=new_shape,
                dtype=old_space.dtype
            )
    
    def reset(self, **kwargs):
        """Reset environment and initialize frame stack."""
        obs = self.env.reset(**kwargs)
        
        # TODO: Initialize frame stack
        # Guidelines:
        # - Clear the deque
        # - Fill with num_stack copies of the initial observation
        
        self.frames.clear()
        for _ in range(self.num_stack):
            self.frames.append(obs)
        
        return self._get_observation()
    
    def step(self, action):
        """Take step and update frame stack."""
        obs, reward, done, info = self.env.step(action)
        
        # TODO: Update frame stack
        # Guidelines:
        # - Append new observation to deque
        # - deque automatically removes oldest frame when full
        
        self.frames.append(obs)
        
        return self._get_observation(), reward, done, info
    
    def _get_observation(self):
        """
        Stack frames into single observation.
        
        Returns:
            Stacked observation
        """
        # TODO: Stack frames
        # Guidelines:
        # - Concatenate along appropriate axis
        # - Use axis=0 for channels-first, axis=-1 for channels-last
        
        if self.channels_first:
            return np.concatenate(list(self.frames), axis=0)
        else:
            return np.concatenate(list(self.frames), axis=-1)


class ActionRepeat(gym.Wrapper):
    """
    Repeat each action for multiple steps.
    
    Reduces the effective episode length and allows the agent to operate
    at a lower frequency, which is useful for:
    - Faster learning (fewer decisions needed)
    - More temporally consistent actions
    - Reduced computational cost
    
    Args:
        env: Gym environment to wrap
        repeat: Number of times to repeat each action (default: 4)
        aggregate_rewards: If True, sum rewards over repeated steps
    """
    
    def __init__(self, env, repeat=4, aggregate_rewards=True):
        super().__init__(env)
        self.repeat = repeat
        self.aggregate_rewards = aggregate_rewards
    
    def step(self, action):
        """
        Repeat action for multiple steps.
        
        Args:
            action: Action to repeat
            
        Returns:
            obs: Final observation after all repeats
            total_reward: Sum or final reward based on aggregate_rewards
            done: True if episode ended during any repeat
            info: Info dict from final step
        """
        # TODO: Implement action repeat
        # Guidelines:
        # 1. Execute action 'repeat' times
        # 2. Accumulate or keep final reward based on aggregate_rewards
        # 3. Stop early if episode ends (done=True)
        # 4. Return final observation and accumulated reward
        
        total_reward = 0.0
        for i in range(self.repeat):
            obs, reward, done, info = self.env.step(action)
            
            if self.aggregate_rewards:
                total_reward += reward
            else:
                total_reward = reward  # Keep only last reward
            
            if done:
                break
        
        return obs, total_reward, done, info


class EpisodeStatistics(gym.Wrapper):
    """
    Track episode statistics (return, length, success).
    
    Automatically computes and logs episode-level metrics.
    Useful for monitoring training progress.
    
    Args:
        env: Gym environment to wrap
    """
    
    def __init__(self, env):
        super().__init__(env)
        self.episode_return = 0.0
        self.episode_length = 0
    
    def reset(self, **kwargs):
        """Reset environment and statistics."""
        self.episode_return = 0.0
        self.episode_length = 0
        return self.env.reset(**kwargs)
    
    def step(self, action):
        """
        Take step and update statistics.
        
        Args:
            action: Action to take
            
        Returns:
            obs, reward, done, info (with episode stats added to info)
        """
        # TODO: Implement statistics tracking
        # Guidelines:
        # 1. Take step in environment
        # 2. Accumulate reward to episode_return
        # 3. Increment episode_length
        # 4. If done, add 'episode' dict to info with return and length
        # 5. Reset statistics after episode ends
        
        obs, reward, done, info = self.env.step(action)
        
        self.episode_return += reward
        self.episode_length += 1
        
        if done:
            info['episode'] = {
                'r': self.episode_return,
                'l': self.episode_length,
            }
            # Note: Statistics will be reset on next reset() call
        
        return obs, reward, done, info


def make_env(
    env_id,
    size=(64, 64),
    grayscale=False,
    frame_stack=1,
    action_repeat=1,
    normalize=True,
    normalize_range='01',
    seed=None
):
    """
    Create and wrap environment with standard preprocessing.
    
    This is a convenience function that applies common world model
    preprocessing steps in the correct order.
    
    Args:
        env_id: Gym environment ID (e.g., 'CarRacing-v2')
        size: Tuple (height, width) for resizing (default: (64, 64))
        grayscale: Whether to convert to grayscale (default: False)
        frame_stack: Number of frames to stack (default: 1, no stacking)
        action_repeat: Number of times to repeat each action (default: 1)
        normalize: Whether to normalize observations (default: True)
        normalize_range: '01' for [0,1] or '11' for [-1,1] (default: '01')
        seed: Random seed for reproducibility
        
    Returns:
        Wrapped gym environment
        
    Example:
        >>> env = make_env('CarRacing-v2', size=(64, 64), action_repeat=4)
        >>> obs = env.reset()
        >>> obs.shape  # (3, 64, 64) - channels first, normalized
    """
    # TODO: Implement environment creation and wrapping
    # Guidelines:
    # 1. Create base environment
    # 2. Apply wrappers in appropriate order:
    #    - ActionRepeat (affects episode length)
    #    - EpisodeStatistics (tracks full episodes)
    #    - ResizeObservation (before frame stacking)
    #    - GrayScaleObservation (if needed)
    #    - NormalizeObservation (after resizing)
    #    - FrameStack (last, operates on processed frames)
    # 3. Set seed if provided
    # 4. Return wrapped environment
    
    # Create base environment
    env = gym.make(env_id)
    
    if seed is not None:
        env.seed(seed)
    
    # Apply wrappers in order
    if action_repeat > 1:
        env = ActionRepeat(env, repeat=action_repeat)
    
    env = EpisodeStatistics(env)
    
    if size is not None:
        env = ResizeObservation(env, size=size)
    
    if grayscale:
        env = GrayScaleObservation(env, keep_dim=True)
    
    if normalize:
        env = NormalizeObservation(env, scale_range=normalize_range)
    
    if frame_stack > 1:
        env = FrameStack(env, num_stack=frame_stack)
    
    return env


# Example usage and testing
if __name__ == "__main__":
    print("Testing environment wrappers...")
    
    # Test basic wrapping
    try:
        env = make_env('CarRacing-v2', size=(64, 64), action_repeat=2)
        obs = env.reset()
        print(f"✓ Basic wrapping works. Obs shape: {obs.shape}, dtype: {obs.dtype}")
        print(f"  Obs range: [{obs.min():.3f}, {obs.max():.3f}]")
        
        # Test step
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        print(f"✓ Step works. Reward: {reward:.3f}, Done: {done}")
        
        env.close()
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test frame stacking
    try:
        env = make_env('CarRacing-v2', size=(32, 32), frame_stack=4)
        obs = env.reset()
        print(f"✓ Frame stacking works. Obs shape: {obs.shape}")
        env.close()
    except Exception as e:
        print(f"✗ Frame stacking error: {e}")
    
    # Test grayscale
    try:
        env = make_env('CarRacing-v2', size=(32, 32), grayscale=True)
        obs = env.reset()
        print(f"✓ Grayscale works. Obs shape: {obs.shape}")
        env.close()
    except Exception as e:
        print(f"✗ Grayscale error: {e}")
    
    print("\nAll tests completed!")

"""
Common Utilities for World Models

This package provides shared utilities for implementing world models including
environment preprocessing, replay buffers, video generation, and metrics.

Modules:
- env_wrapper: Environment preprocessing wrappers (resize, normalize, frame stack, etc.)
- replay_buffer: Efficient replay buffer implementations for sequence data
- video: Video generation utilities for visualizations and rollouts
- metrics: Evaluation metrics for tracking training progress

Quick Start:
    >>> from world_models.common import make_env, EpisodeBuffer, save_video
    >>> 
    >>> # Create preprocessed environment
    >>> env = make_env('CarRacing-v2', size=(64, 64), action_repeat=4)
    >>> 
    >>> # Create replay buffer
    >>> buffer = EpisodeBuffer(capacity=100000, obs_shape=(3, 64, 64))
    >>> 
    >>> # Collect experience
    >>> obs = env.reset()
    >>> for _ in range(1000):
    ...     action = env.action_space.sample()
    ...     next_obs, reward, done, info = env.step(action)
    ...     buffer.add(obs, action, reward, done)
    ...     if done:
    ...         obs = env.reset()
    ...     else:
    ...         obs = next_obs

Educational Design:
- All modules include detailed docstrings with paper references
- TODO comments guide implementation of key functions
- Example usage and testing code at the bottom of each file
- Error handling and edge case considerations
- Clear separation of concerns between modules

References:
- World Models (Ha & Schmidhuber, 2018)
- Dream to Control: DreamerV1 (Hafner et al., 2020)
- Mastering Diverse Domains: DreamerV2 (Hafner et al., 2021)
- Mastering Atari: DreamerV3 (Hafner et al., 2023)
- IRIS (Micheli et al., 2023)
"""

# Environment wrappers
from .env_wrapper import (
    ResizeObservation,
    NormalizeObservation,
    GrayScaleObservation,
    FrameStack,
    ActionRepeat,
    EpisodeStatistics,
    make_env,
)

# Replay buffers
from .replay_buffer import (
    EpisodeBuffer,
    UniformBuffer,
    PrioritizedBuffer,
)

# Video utilities
from .video import (
    VideoRecorder,
    save_video,
    save_comparison_video,
    save_grid_video,
    record_episode,
    visualize_reconstructions,
)

# Metrics
from .metrics import (
    MetricTracker,
    EpisodeMetrics,
    compute_reconstruction_error,
    compute_prediction_accuracy,
    compute_latent_statistics,
    compute_kl_divergence,
    Timer,
    format_metrics,
)

__all__ = [
    # Environment wrappers
    'ResizeObservation',
    'NormalizeObservation',
    'GrayScaleObservation',
    'FrameStack',
    'ActionRepeat',
    'EpisodeStatistics',
    'make_env',
    
    # Replay buffers
    'EpisodeBuffer',
    'UniformBuffer',
    'PrioritizedBuffer',
    
    # Video utilities
    'VideoRecorder',
    'save_video',
    'save_comparison_video',
    'save_grid_video',
    'record_episode',
    'visualize_reconstructions',
    
    # Metrics
    'MetricTracker',
    'EpisodeMetrics',
    'compute_reconstruction_error',
    'compute_prediction_accuracy',
    'compute_latent_statistics',
    'compute_kl_divergence',
    'Timer',
    'format_metrics',
]

__version__ = '1.0.0'

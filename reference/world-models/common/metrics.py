"""
Evaluation Metrics for World Models

This module provides standardized metrics for evaluating world models and
agents. Metrics help track training progress, compare models, and diagnose issues.

Key Metric Categories:
1. Episode Metrics: Return, length, success rate
2. Model Metrics: Reconstruction error, prediction accuracy
3. Latent Metrics: Latent space statistics, information content
4. Computational Metrics: FPS, memory usage, training time

Common usage patterns:
- Track episode returns during RL training
- Monitor reconstruction quality during VAE training
- Measure prediction horizon for world models
- Compute success rates for goal-based tasks

References:
- World Models (Ha & Schmidhuber, 2018): Episode returns, reconstruction MSE
- DreamerV1/V2/V3: Episode return, prediction RMSE, latent divergence
"""

import numpy as np
from collections import deque
from typing import Dict, List, Optional, Union
import time


class MetricTracker:
    """
    Track and aggregate metrics over time.
    
    Supports running averages, summaries, and history tracking.
    
    Args:
        window_size: Size of rolling window for statistics (default: 100)
        track_history: Whether to keep full history (default: False)
    """
    
    def __init__(self, window_size: int = 100, track_history: bool = False):
        self.window_size = window_size
        self.track_history = track_history
        
        self.metrics = {}  # metric_name -> deque of recent values
        self.history = {}  # metric_name -> full history (if track_history=True)
        self.counts = {}   # metric_name -> total count
    
    def update(self, **metrics: Union[float, int]):
        """
        Update metrics with new values.
        
        Args:
            **metrics: Keyword arguments of metric_name=value
            
        Example:
            >>> tracker.update(reward=10.5, loss=0.23, accuracy=0.95)
        """
        # TODO: Implement metric update
        # Guidelines:
        # 1. For each metric:
        #    a. Initialize deque and history if needed
        #    b. Append value to deque (with maxlen=window_size)
        #    c. Append to history if track_history=True
        #    d. Increment count
        
        for name, value in metrics.items():
            # Initialize if needed
            if name not in self.metrics:
                self.metrics[name] = deque(maxlen=self.window_size)
                self.counts[name] = 0
                if self.track_history:
                    self.history[name] = []
            
            # Update
            self.metrics[name].append(value)
            self.counts[name] += 1
            
            if self.track_history:
                self.history[name].append(value)
    
    def get(self, metric_name: str, aggregation: str = 'mean') -> Optional[float]:
        """
        Get aggregated metric value.
        
        Args:
            metric_name: Name of metric
            aggregation: How to aggregate ('mean', 'sum', 'max', 'min', 'last')
            
        Returns:
            Aggregated value or None if metric doesn't exist
        """
        # TODO: Implement metric aggregation
        # Guidelines:
        # 1. Check if metric exists
        # 2. Apply requested aggregation to recent values
        # 3. Return result or None
        
        if metric_name not in self.metrics or len(self.metrics[metric_name]) == 0:
            return None
        
        values = list(self.metrics[metric_name])
        
        if aggregation == 'mean':
            return np.mean(values)
        elif aggregation == 'sum':
            return np.sum(values)
        elif aggregation == 'max':
            return np.max(values)
        elif aggregation == 'min':
            return np.min(values)
        elif aggregation == 'last':
            return values[-1]
        elif aggregation == 'std':
            return np.std(values)
        else:
            raise ValueError(f"Unknown aggregation: {aggregation}")
    
    def get_summary(self, metric_name: str) -> Dict[str, float]:
        """
        Get summary statistics for a metric.
        
        Args:
            metric_name: Name of metric
            
        Returns:
            Dictionary with mean, std, min, max, count
        """
        # TODO: Implement summary statistics
        # Guidelines:
        # 1. Check if metric exists
        # 2. Compute mean, std, min, max from recent values
        # 3. Include total count
        # 4. Return as dictionary
        
        if metric_name not in self.metrics:
            return {}
        
        values = list(self.metrics[metric_name])
        
        if len(values) == 0:
            return {'count': 0}
        
        return {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'count': self.counts[metric_name],
            'recent_count': len(values),
        }
    
    def get_all(self, aggregation: str = 'mean') -> Dict[str, float]:
        """
        Get all metrics with specified aggregation.
        
        Args:
            aggregation: How to aggregate each metric
            
        Returns:
            Dictionary of metric_name -> aggregated_value
        """
        return {name: self.get(name, aggregation) 
                for name in self.metrics.keys()}
    
    def reset(self, metric_name: Optional[str] = None):
        """
        Reset metrics.
        
        Args:
            metric_name: Specific metric to reset, or None for all
        """
        if metric_name is None:
            self.metrics.clear()
            self.history.clear()
            self.counts.clear()
        else:
            if metric_name in self.metrics:
                self.metrics[metric_name].clear()
                self.counts[metric_name] = 0
                if self.track_history:
                    self.history[metric_name].clear()


class EpisodeMetrics:
    """
    Track episode-level metrics for RL training.
    
    Automatically computes statistics like mean return, success rate,
    episode length distribution, etc.
    
    Args:
        window_size: Number of recent episodes to track (default: 100)
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.returns = deque(maxlen=window_size)
        self.lengths = deque(maxlen=window_size)
        self.successes = deque(maxlen=window_size)  # 1 for success, 0 for failure
        
        self.total_episodes = 0
        self.total_steps = 0
    
    def add_episode(self, episode_return: float, episode_length: int, 
                   success: Optional[bool] = None):
        """
        Add completed episode statistics.
        
        Args:
            episode_return: Total return for episode
            episode_length: Number of steps in episode
            success: Whether episode was successful (optional)
        """
        # TODO: Implement episode tracking
        # Guidelines:
        # 1. Add to deques
        # 2. Update totals
        # 3. Handle optional success flag
        
        self.returns.append(episode_return)
        self.lengths.append(episode_length)
        
        if success is not None:
            self.successes.append(1 if success else 0)
        
        self.total_episodes += 1
        self.total_steps += episode_length
    
    def get_statistics(self) -> Dict[str, float]:
        """
        Get summary statistics for recent episodes.
        
        Returns:
            Dictionary with mean/std return, mean length, success rate, etc.
        """
        # TODO: Implement statistics computation
        # Guidelines:
        # 1. Compute return statistics (mean, std, min, max)
        # 2. Compute length statistics
        # 3. Compute success rate if available
        # 4. Return as dictionary
        
        stats = {
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
        }
        
        if len(self.returns) > 0:
            stats['mean_return'] = np.mean(self.returns)
            stats['std_return'] = np.std(self.returns)
            stats['min_return'] = np.min(self.returns)
            stats['max_return'] = np.max(self.returns)
        
        if len(self.lengths) > 0:
            stats['mean_length'] = np.mean(self.lengths)
            stats['std_length'] = np.std(self.lengths)
        
        if len(self.successes) > 0:
            stats['success_rate'] = np.mean(self.successes)
        
        return stats
    
    def __repr__(self):
        stats = self.get_statistics()
        return (f"EpisodeMetrics(episodes={stats.get('total_episodes', 0)}, "
                f"mean_return={stats.get('mean_return', 0):.2f}±{stats.get('std_return', 0):.2f})")


def compute_reconstruction_error(
    original: np.ndarray,
    reconstructed: np.ndarray,
    metric: str = 'mse'
) -> float:
    """
    Compute reconstruction error between original and reconstructed observations.
    
    Args:
        original: Original observations (B, ...)
        reconstructed: Reconstructed observations (same shape)
        metric: Error metric ('mse', 'mae', 'rmse', 'psnr')
        
    Returns:
        Reconstruction error (lower is better, except PSNR where higher is better)
        
    Example:
        >>> error = compute_reconstruction_error(obs, vae_output, metric='mse')
    """
    # TODO: Implement reconstruction error
    # Guidelines:
    # 1. Ensure arrays have same shape
    # 2. Compute requested metric
    # 3. Handle edge cases (division by zero for PSNR)
    
    if original.shape != reconstructed.shape:
        raise ValueError(f"Shape mismatch: {original.shape} vs {reconstructed.shape}")
    
    if metric == 'mse':
        # Mean Squared Error
        return np.mean((original - reconstructed) ** 2)
    
    elif metric == 'mae':
        # Mean Absolute Error
        return np.mean(np.abs(original - reconstructed))
    
    elif metric == 'rmse':
        # Root Mean Squared Error
        return np.sqrt(np.mean((original - reconstructed) ** 2))
    
    elif metric == 'psnr':
        # Peak Signal-to-Noise Ratio
        mse = np.mean((original - reconstructed) ** 2)
        if mse == 0:
            return float('inf')
        
        # Assume pixel values in [0, 1] or [0, 255]
        max_pixel = 1.0 if original.max() <= 1.0 else 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
        return psnr
    
    else:
        raise ValueError(f"Unknown metric: {metric}")


def compute_prediction_accuracy(
    true_next_obs: np.ndarray,
    predicted_obs: np.ndarray,
    metric: str = 'mse',
    horizon: Optional[int] = None
) -> Union[float, List[float]]:
    """
    Compute prediction accuracy for world model.
    
    Measures how well the model predicts future observations.
    
    Args:
        true_next_obs: True next observations (B, T, ...)
        predicted_obs: Predicted observations (B, T, ...)
        metric: Error metric ('mse', 'mae', 'rmse')
        horizon: If specified, return per-timestep errors
        
    Returns:
        Error value or list of errors per timestep
        
    Example:
        >>> errors = compute_prediction_accuracy(true_obs, pred_obs, horizon=10)
    """
    # TODO: Implement prediction accuracy
    # Guidelines:
    # 1. Handle batched temporal data (B, T, ...)
    # 2. If horizon specified, compute error for each timestep
    # 3. Otherwise, compute overall error
    
    if true_next_obs.shape != predicted_obs.shape:
        raise ValueError(f"Shape mismatch: {true_next_obs.shape} vs {predicted_obs.shape}")
    
    if horizon is not None:
        # Compute per-timestep errors
        errors = []
        for t in range(min(horizon, true_next_obs.shape[1])):
            true_t = true_next_obs[:, t]
            pred_t = predicted_obs[:, t]
            error = compute_reconstruction_error(true_t, pred_t, metric=metric)
            errors.append(error)
        return errors
    else:
        # Compute overall error
        return compute_reconstruction_error(true_next_obs, predicted_obs, metric=metric)


def compute_latent_statistics(latents: np.ndarray) -> Dict[str, float]:
    """
    Compute statistics of latent representations.
    
    Useful for monitoring latent space quality and detecting issues
    like posterior collapse or mode collapse.
    
    Args:
        latents: Latent vectors (B, latent_dim)
        
    Returns:
        Dictionary with mean, std, sparsity, etc.
        
    Example:
        >>> stats = compute_latent_statistics(latent_vectors)
        >>> print(f"Latent space utilization: {stats['active_dims']}/{latent_dim}")
    """
    # TODO: Implement latent statistics
    # Guidelines:
    # 1. Compute mean and std per dimension
    # 2. Compute sparsity (fraction of near-zero activations)
    # 3. Compute active dimensions (non-zero variance)
    # 4. Compute norm statistics
    
    stats = {}
    
    # Basic statistics
    stats['mean_activation'] = np.mean(np.abs(latents))
    stats['std_activation'] = np.std(latents)
    stats['max_activation'] = np.max(np.abs(latents))
    
    # Per-dimension statistics
    dim_means = np.mean(latents, axis=0)
    dim_stds = np.std(latents, axis=0)
    
    stats['mean_dim_mean'] = np.mean(dim_means)
    stats['mean_dim_std'] = np.mean(dim_stds)
    
    # Active dimensions (dimensions with non-trivial variance)
    active_threshold = 0.01
    active_dims = np.sum(dim_stds > active_threshold)
    stats['active_dims'] = active_dims
    stats['active_fraction'] = active_dims / latents.shape[1]
    
    # Sparsity (fraction of near-zero activations)
    sparsity_threshold = 0.01
    sparse_count = np.sum(np.abs(latents) < sparsity_threshold)
    stats['sparsity'] = sparse_count / latents.size
    
    # Norm statistics
    norms = np.linalg.norm(latents, axis=1)
    stats['mean_norm'] = np.mean(norms)
    stats['std_norm'] = np.std(norms)
    
    return stats


def compute_kl_divergence(mu: np.ndarray, logvar: np.ndarray) -> float:
    """
    Compute KL divergence for VAE latent distribution.
    
    Measures divergence from standard normal N(0, 1).
    Used as regularization term in VAE training.
    
    Args:
        mu: Mean of latent distribution (B, latent_dim)
        logvar: Log variance of latent distribution (B, latent_dim)
        
    Returns:
        Mean KL divergence across batch
        
    Example:
        >>> kl_loss = compute_kl_divergence(mu, logvar)
    """
    # TODO: Implement KL divergence
    # Guidelines:
    # 1. Use KL(q||p) = -0.5 * sum(1 + logvar - mu^2 - exp(logvar))
    # 2. Average over batch and dimensions
    # 3. Return scalar value
    
    # KL divergence from N(0,1): -0.5 * sum(1 + log(var) - mu^2 - var)
    kl = -0.5 * np.sum(1 + logvar - mu**2 - np.exp(logvar), axis=1)
    return np.mean(kl)


class Timer:
    """
    Simple timer for measuring execution time.
    
    Can be used as context manager or manually started/stopped.
    
    Example:
        >>> with Timer() as t:
        ...     # some code
        >>> print(f"Elapsed: {t.elapsed:.3f}s")
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = 0.0
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
    
    def stop(self):
        """Stop the timer and compute elapsed time."""
        self.end_time = time.time()
        if self.start_time is not None:
            self.elapsed = self.end_time - self.start_time
        return self.elapsed
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def format_metrics(metrics: Dict[str, float], precision: int = 3) -> str:
    """
    Format metrics dictionary as readable string.
    
    Args:
        metrics: Dictionary of metric_name -> value
        precision: Number of decimal places
        
    Returns:
        Formatted string
        
    Example:
        >>> print(format_metrics({'loss': 0.123, 'accuracy': 0.95}))
        loss: 0.123, accuracy: 0.950
    """
    formatted = []
    for name, value in metrics.items():
        if isinstance(value, (int, np.integer)):
            formatted.append(f"{name}: {value}")
        elif isinstance(value, (float, np.floating)):
            formatted.append(f"{name}: {value:.{precision}f}")
        else:
            formatted.append(f"{name}: {value}")
    
    return ", ".join(formatted)


# Example usage and testing
if __name__ == "__main__":
    print("Testing evaluation metrics...")
    
    # Test MetricTracker
    print("\n=== Testing MetricTracker ===")
    tracker = MetricTracker(window_size=10)
    
    for i in range(20):
        tracker.update(loss=np.random.rand(), accuracy=np.random.rand())
    
    print(f"✓ Tracked 20 updates")
    print(f"  Mean loss: {tracker.get('loss', 'mean'):.3f}")
    print(f"  Mean accuracy: {tracker.get('accuracy', 'mean'):.3f}")
    print(f"  Summary: {tracker.get_summary('loss')}")
    
    # Test EpisodeMetrics
    print("\n=== Testing EpisodeMetrics ===")
    ep_metrics = EpisodeMetrics(window_size=10)
    
    for i in range(15):
        ret = np.random.randn() * 10 + 100
        length = np.random.randint(50, 200)
        success = np.random.rand() > 0.5
        ep_metrics.add_episode(ret, length, success)
    
    print(f"✓ Tracked 15 episodes")
    print(f"  {ep_metrics}")
    print(f"  Statistics: {ep_metrics.get_statistics()}")
    
    # Test reconstruction error
    print("\n=== Testing reconstruction error ===")
    original = np.random.rand(32, 3, 64, 64)
    reconstructed = original + np.random.randn(*original.shape) * 0.1
    
    mse = compute_reconstruction_error(original, reconstructed, metric='mse')
    mae = compute_reconstruction_error(original, reconstructed, metric='mae')
    psnr = compute_reconstruction_error(original, reconstructed, metric='psnr')
    
    print(f"✓ Reconstruction errors:")
    print(f"  MSE: {mse:.6f}")
    print(f"  MAE: {mae:.6f}")
    print(f"  PSNR: {psnr:.2f} dB")
    
    # Test prediction accuracy
    print("\n=== Testing prediction accuracy ===")
    true_obs = np.random.rand(16, 10, 3, 32, 32)
    pred_obs = true_obs + np.random.randn(*true_obs.shape) * 0.05
    
    errors = compute_prediction_accuracy(true_obs, pred_obs, horizon=10)
    print(f"✓ Per-timestep prediction errors:")
    for t, err in enumerate(errors):
        print(f"  t={t}: {err:.6f}")
    
    # Test latent statistics
    print("\n=== Testing latent statistics ===")
    latents = np.random.randn(100, 32)
    stats = compute_latent_statistics(latents)
    
    print(f"✓ Latent statistics:")
    print(f"  Active dimensions: {stats['active_dims']}/{latents.shape[1]}")
    print(f"  Sparsity: {stats['sparsity']:.3f}")
    print(f"  Mean norm: {stats['mean_norm']:.3f}")
    
    # Test KL divergence
    print("\n=== Testing KL divergence ===")
    mu = np.random.randn(32, 16) * 0.5
    logvar = np.random.randn(32, 16) * 0.1
    kl = compute_kl_divergence(mu, logvar)
    print(f"✓ KL divergence: {kl:.3f}")
    
    # Test Timer
    print("\n=== Testing Timer ===")
    with Timer() as t:
        time.sleep(0.1)
    print(f"✓ Timer measured: {t.elapsed:.3f}s")
    
    # Test format_metrics
    print("\n=== Testing format_metrics ===")
    metrics = {'loss': 0.123456, 'accuracy': 0.95, 'steps': 1000}
    formatted = format_metrics(metrics)
    print(f"✓ Formatted: {formatted}")
    
    print("\nAll tests completed!")

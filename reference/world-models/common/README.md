# Common Utilities for World Models

This directory contains shared utility modules used across different world model implementations. These utilities provide standard preprocessing, data management, visualization, and evaluation capabilities.

## 📁 Module Overview

### 1. `env_wrapper.py` - Environment Preprocessing

Provides gym environment wrappers for standard preprocessing operations.

**Key Classes:**
- `ResizeObservation`: Resize images to target resolution
- `NormalizeObservation`: Normalize pixel values to [0,1] or [-1,1]
- `GrayScaleObservation`: Convert RGB to grayscale
- `FrameStack`: Stack consecutive frames for temporal information
- `ActionRepeat`: Repeat actions for faster learning
- `EpisodeStatistics`: Track episode returns and lengths

**Quick Start:**
```python
from world_models.common import make_env

# Create fully preprocessed environment
env = make_env(
    'CarRacing-v2',
    size=(64, 64),           # Resize to 64x64
    action_repeat=4,         # Repeat each action 4 times
    frame_stack=1,           # No frame stacking
    normalize=True,          # Normalize to [0, 1]
)

obs = env.reset()
print(obs.shape)  # (3, 64, 64)
```

### 2. `replay_buffer.py` - Experience Storage

Efficient replay buffers for storing and sampling sequential experience.

**Key Classes:**
- `EpisodeBuffer`: Stores complete episodes, samples subsequences (for world models)
- `UniformBuffer`: Simple FIFO buffer with uniform sampling
- `PrioritizedBuffer`: Prioritized experience replay with importance sampling

**Quick Start:**
```python
from world_models.common import EpisodeBuffer

# Create buffer for sequence learning
buffer = EpisodeBuffer(
    capacity=1000000,        # Total timesteps to store
    obs_shape=(3, 64, 64),   # Observation shape
    action_shape=(2,),       # Action shape
    seq_len=50,              # Sequence length for sampling
    batch_size=50            # Batch size
)

# Collect experience
obs = env.reset()
for _ in range(1000):
    action = agent.act(obs)
    next_obs, reward, done, info = env.step(action)
    buffer.add(obs, action, reward, done)
    
    if done:
        obs = env.reset()
    else:
        obs = next_obs

# Sample sequences for training
batch = buffer.sample()
print(batch['observations'].shape)  # (50, 50, 3, 64, 64)
```

### 3. `video.py` - Visualization

Tools for saving rollouts and model predictions as videos.

**Key Functions:**
- `VideoRecorder`: Class for collecting and saving frames
- `save_video()`: Save list of frames as video
- `save_comparison_video()`: Side-by-side real vs predicted
- `save_grid_video()`: Multiple rollouts in grid layout
- `record_episode()`: Record agent episode
- `visualize_reconstructions()`: VAE reconstruction visualization

**Quick Start:**
```python
from world_models.common import VideoRecorder, save_comparison_video

# Record rollout
with VideoRecorder('rollout.mp4', fps=30) as recorder:
    obs = env.reset()
    for _ in range(100):
        recorder.add_frame(env.render())
        action = agent.act(obs)
        obs, _, done, _ = env.step(action)
        if done:
            break

# Compare real vs predicted observations
save_comparison_video(
    real_frames=real_observations,
    pred_frames=model_predictions,
    path='comparison.mp4',
    labels=("Ground Truth", "World Model")
)
```

### 4. `metrics.py` - Evaluation

Standardized metrics for tracking training progress and model quality.

**Key Classes:**
- `MetricTracker`: Track and aggregate any metrics with rolling windows
- `EpisodeMetrics`: Track episode returns, lengths, success rates
- `Timer`: Simple timer for profiling

**Key Functions:**
- `compute_reconstruction_error()`: MSE, MAE, RMSE, PSNR
- `compute_prediction_accuracy()`: World model prediction errors
- `compute_latent_statistics()`: Latent space diagnostics
- `compute_kl_divergence()`: VAE regularization term
- `format_metrics()`: Pretty-print metrics

**Quick Start:**
```python
from world_models.common import MetricTracker, EpisodeMetrics

# Track training metrics
tracker = MetricTracker(window_size=100)

for epoch in range(100):
    loss = train_step()
    tracker.update(loss=loss, accuracy=0.95)

print(f"Mean loss: {tracker.get('loss', 'mean'):.3f}")
print(tracker.get_summary('loss'))

# Track episode performance
ep_metrics = EpisodeMetrics(window_size=100)

for episode in range(1000):
    episode_return, episode_length = run_episode(env, agent)
    ep_metrics.add_episode(episode_return, episode_length)

print(ep_metrics.get_statistics())
```

## 🎯 Usage Patterns

### Pattern 1: Training World Model VAE

```python
from world_models.common import make_env, EpisodeBuffer, MetricTracker
from world_models.common import compute_reconstruction_error, visualize_reconstructions

# Setup
env = make_env('CarRacing-v2', size=(64, 64))
buffer = EpisodeBuffer(capacity=100000, obs_shape=(3, 64, 64))
tracker = MetricTracker()

# Collect data
collect_experience(env, buffer, num_steps=10000)

# Train VAE
for epoch in range(100):
    batch = buffer.sample()
    obs = batch['observations']
    
    # Forward pass
    recon, mu, logvar = vae(obs)
    
    # Compute losses
    recon_loss = compute_reconstruction_error(obs, recon, metric='mse')
    kl_loss = compute_kl_divergence(mu, logvar)
    
    # Track metrics
    tracker.update(recon_loss=recon_loss, kl_loss=kl_loss)
    
    # Visualize periodically
    if epoch % 10 == 0:
        visualize_reconstructions(obs[:8], recon[:8], f'recon_epoch_{epoch}.png')
```

### Pattern 2: Evaluating Agent

```python
from world_models.common import make_env, EpisodeMetrics, record_episode, save_video

env = make_env('CarRacing-v2', size=(64, 64), action_repeat=4)
metrics = EpisodeMetrics()

# Evaluate for multiple episodes
for episode_idx in range(100):
    frames, episode_return, episode_length = record_episode(env, agent, max_steps=1000)
    
    metrics.add_episode(episode_return, episode_length)
    
    # Save video of best episode
    if episode_return > best_return:
        save_video(frames, f'best_episode_{episode_return:.0f}.mp4')

print(metrics.get_statistics())
```

### Pattern 3: Comparing Models

```python
from world_models.common import save_grid_video

# Collect rollouts from different models
rollouts = []
for model in [model_v1, model_v2, model_v3, baseline]:
    frames, _, _ = record_episode(env, model)
    rollouts.append(frames)

# Create comparison video
save_grid_video(
    frame_groups=rollouts,
    path='model_comparison.mp4',
    grid_shape=(2, 2),
    labels=['ModelV1', 'ModelV2', 'ModelV3', 'Baseline']
)
```

## 🧪 Testing

Each module includes self-contained tests at the bottom. Run them with:

```bash
# Test individual modules
cd world-models/common
python env_wrapper.py
python replay_buffer.py
python video.py
python metrics.py

# Or test the whole package
python -c "from world_models.common import *; print('All imports successful!')"
```

## 📚 Educational Features

All utilities are designed for learning:

1. **Detailed Documentation**: Every function has comprehensive docstrings
2. **TODO Comments**: Key functions include guided implementation TODOs
3. **Paper References**: Citations to original papers
4. **Example Usage**: Working examples in docstrings and test code
5. **Error Handling**: Proper validation and error messages
6. **Type Hints**: Clear function signatures

## 🔗 References

- **World Models** (Ha & Schmidhuber, 2018): VAE + RNN world model
- **DreamerV1** (Hafner et al., 2020): Latent imagination for RL
- **DreamerV2** (Hafner et al., 2021): Discrete latent representations
- **DreamerV3** (Hafner et al., 2023): Scalable world models
- **IRIS** (Micheli et al., 2023): Autoregressive world models with transformers

## 💡 Design Philosophy

These utilities follow key principles:

1. **Modularity**: Each wrapper/buffer/metric is independent
2. **Composability**: Easy to combine and extend
3. **Efficiency**: Optimized for common use cases
4. **Clarity**: Readable code over clever tricks
5. **Completeness**: Handle edge cases gracefully

## 🐛 Common Issues

### Issue: Import errors
**Solution**: Install dependencies with `pip install -r requirements.txt`

### Issue: Out of memory when sampling
**Solution**: Reduce `seq_len` or `batch_size` in `EpisodeBuffer`

### Issue: Video codec not found
**Solution**: Install ffmpeg: `apt-get install ffmpeg` (Linux) or `brew install ffmpeg` (Mac)

### Issue: Gym environment not found
**Solution**: Install specific gym extras: `pip install gymnasium[box2d]`

## 📝 License

See parent directory LICENSE file.

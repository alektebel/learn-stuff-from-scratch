# DreamerV3 Implementation Templates

Educational templates for implementing DreamerV3 from scratch.

## Paper Reference

**Mastering Diverse Domains through World Models**  
Danijar Hafner, Jurgis Pasukonis, Jimmy Ba, Timothy Lillicrap  
arXiv 2023  
[Paper](https://arxiv.org/abs/2301.04104) | [Website](https://danijar.com/project/dreamerv3/)

## Overview

DreamerV3 achieves state-of-the-art performance across diverse domains (Atari, DMC, Minecraft, etc.) using a single set of hyperparameters. It simplifies and improves upon DreamerV2.

### Key Simplifications and Improvements

1. **Unified Architecture**: Single world model class, consistent MLP design
2. **Symlog Everywhere**: All predictions use symlog transformation
3. **Single Hyperparameter Set**: Works across all domains without tuning
4. **Robust Optimization**: Percentile normalization, improved stability
5. **SiLU Activation**: Better than ReLU/ELU across the board

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   UNIFIED WORLD MODEL                            │
│                                                                  │
│  Encoder → Embeddings                                            │
│     ↓                                                            │
│  RSSM: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})                       │
│        z_t ~ Categorical(h_t) or Categorical(h_t, embed_t)       │
│     ↓                                                            │
│  Decoder → Reconstructed observations                            │
│  Reward → symlog(r_t)                                            │
│  Continue → P(continue)                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 ROBUST ACTOR-CRITIC                              │
│                                                                  │
│  Actor: π(a | z, h)   [Tanh-transformed Gaussian]               │
│  Critic: V_symlog(z, h) [Value in symlog space]                 │
│  Returns: Percentile-normalized lambda returns                  │
└─────────────────────────────────────────────────────────────────┘
```

## Files

### 1. `world_model.py` - Unified World Model

Single cohesive world model with all components integrated.

**Components:**
- `MLP`: Standardized multi-layer perceptron (LayerNorm + SiLU)
- `WorldModel`: Unified model containing:
  - CNN encoder
  - RSSM (GRU + categorical distributions)
  - CNN decoder
  - Reward predictor (symlog output)
  - Continue predictor

**Key Methods:**
- `encode()`: Observations → embeddings
- `decode()`: Latent state → observations
- `prior()` / `posterior()`: Categorical sampling
- `dynamics_step()`: Recurrent dynamics
- `imagine()`: Generate future trajectories

### 2. `actor_critic.py` - Robust Actor-Critic

Simplified and robust policy learning.

**Components:**
- `Actor`: Tanh-transformed Gaussian policy
- `Critic`: Value network with symlog predictions
- `compute_returns()`: Lambda returns computation
- `percentile_normalize()`: Robust return normalization

**Key Features:**
- Symlog value predictions for numerical stability
- Percentile normalization (more robust than z-score)
- Consistent architecture throughout

### 3. `symlog.py` - Symlog Transformation Utilities

Core transformation for robustness across scales.

**Functions:**
- `symlog()`: Forward transformation
- `symexp()`: Inverse transformation
- `two_hot_encoding()`: For distributional critics
- `visualize_symlog()`: Plot transformation properties

**Properties:**
- Symmetric: symlog(-x) = -symlog(x)
- Monotonic: preserves ordering
- Linear near zero
- Logarithmic compression for large values

### 4. `train.py` - Simplified Training Loop

Single training procedure that works everywhere.

**Features:**
- Joint optimization of all components
- Single optimizer (instead of separate optimizers)
- Unified training step
- Works across domains without hyperparameter tuning

## Implementation Order

### Phase 1: Symlog Utilities
1. **symlog.py** - Implement transformations first
   - `symlog()` and `symexp()`
   - Test properties (symmetry, monotonicity)
   - Optional: two-hot encoding

### Phase 2: Unified World Model
2. **world_model.py** - Build world model
   - `MLP` class with LayerNorm + SiLU
   - `WorldModel` with all components
   - Test each component individually
   - Test imagination rollouts

### Phase 3: Robust Actor-Critic
3. **actor_critic.py** - Implement policy learning
   - `Actor` with TanhNormal distribution
   - `Critic` with symlog predictions
   - `compute_returns()` and `percentile_normalize()`
   - Test value prediction in symlog space

### Phase 4: Training Integration
4. **train.py** - Put it all together
   - `DreamerV3` class with single optimizer
   - Unified `train_step()` method
   - Action selection
   - Test on dummy data

## Key Concepts

### Symlog Transformation

The secret sauce for robustness:

```python
symlog(x) = sign(x) * log(|x| + 1)
```

**Why it matters:**
- Works with rewards from -1000 to +1000 equally well
- Smooth and differentiable everywhere
- Preserves sign and monotonicity
- No separate reward normalization needed

### Percentile Normalization

More robust than mean/std normalization:

```python
scale = percentile(|returns|, 95)
normalized = returns / max(scale, 1.0)
```

**Benefits:**
- Robust to outliers
- Works with heavy-tailed distributions
- No running statistics needed
- More stable than z-score

### Unified Hyperparameters

Single set works everywhere:

```python
# These work for Atari, DMC, Minecraft, etc.
rnn_hidden_dim = 512
hidden_dim = 640
mlp_layers = 3
learning_rate = 1e-4
gamma = 0.997
lambda_ = 0.95
```

No per-domain tuning required!

### SiLU Activation

Also known as Swish: `SiLU(x) = x * sigmoid(x)`

**Advantages:**
- Smoother than ReLU
- Non-monotonic (unlike ELU)
- Better empirical performance
- Now standard in many architectures

## Hyperparameters

Single set for all domains:

```python
# Architecture
num_categories = 32          # Categories per categorical
num_categoricals = 32        # Number of categoricals  
rnn_hidden_dim = 512        # Deterministic state (increased from V2)
hidden_dim = 640            # MLP hidden dim (increased from V2)
mlp_layers = 3              # Layers in all MLPs

# Training
batch_size = 16             # Sequences per batch
seq_len = 64                # Sequence length
imagination_horizon = 15    # Steps to imagine

# Optimization
learning_rate = 1e-4        # Single LR for everything
adam_eps = 1e-8             # Adam epsilon
gradient_clip = 1000        # Gradient clipping

# RL
gamma = 0.997               # Discount (higher than V2)
lambda_ = 0.95              # Lambda for returns
entropy_coef = 3e-4         # Entropy regularization

# Regularization
kl_coef = 1.0               # KL weight
free_nats = 1.0             # Free nats threshold
```

## Testing

```bash
cd world-models/paper4_dreamerv3

# Test components
python symlog.py
python world_model.py
python actor_critic.py

# Test integration
python train.py
```

## Key Differences from DreamerV2

| Aspect | DreamerV2 | DreamerV3 |
|--------|-----------|-----------|
| **World model** | Separate components | Unified class |
| **Optimizers** | 3 separate (WM, actor, critic) | 1 unified |
| **Normalization** | LayerNorm | LayerNorm |
| **Activation** | ELU | SiLU (Swish) |
| **Value prediction** | Direct | Symlog space |
| **Return normalization** | Mean/std | Percentile |
| **Hyperparameters** | Per-domain tuning | Single set |
| **Hidden dim** | 400 | 640 (increased) |
| **RNN hidden** | 200 | 512 (increased) |
| **Gamma** | 0.99 | 0.997 (higher) |
| **Domains** | Atari, DMC | Atari, DMC, Minecraft, etc. |

## Common Issues

### Symlog Numerical Issues
- **Symptom**: NaN values in symlog/symexp
- **Solution**: Clamp inputs, check for overflow

### Poor Generalization
- **Symptom**: Works on one domain but not others
- **Solution**: Check that all predictions use symlog, verify percentile normalization

### Unstable Training
- **Symptom**: Loss spikes
- **Solution**: Clip gradients, reduce learning rate slightly

### Slow Learning
- **Symptom**: No improvement after many steps
- **Solution**: Check imagination quality, verify KL not collapsed

## Debugging Tips

1. **Verify Symlog**: All rewards/values should use symlog
2. **Check Percentiles**: Monitor percentile values during training
3. **Visualize Imagination**: Save imagined trajectories
4. **Compare Scales**: Test on tasks with different reward scales
5. **Monitor KL**: Should be > free_nats but not too high

## Performance Expectations

With 100k environment steps:
- **Atari**: ~100-200% human performance
- **DMControl**: Near-optimal on most tasks
- **Minecraft**: Can collect diamonds

With 1M steps:
- **Atari**: Superhuman on many games
- **DMControl**: Optimal or near-optimal
- **Minecraft**: Complex tool use and crafting

## Resources

- **Paper**: https://arxiv.org/abs/2301.04104
- **Official implementation**: https://github.com/danijar/dreamerv3
- **Author's website**: https://danijar.com/project/dreamerv3/
- **Blog post**: https://danijar.com/dreamerv3/

## Extensions

1. **New Domains**: Test on your custom environments
2. **Discrete Actions**: Modify actor for categorical outputs
3. **Partial Observability**: Test on memory-intensive tasks
4. **Transfer Learning**: Pre-train on one domain, fine-tune on another
5. **World Model Analysis**: Study what the model learns

## Next Steps

After completing DreamerV3:
- **Paper 5**: IRIS - Transformer-based world models
- **Comparisons**: Benchmark V1, V2, V3 on same tasks
- **Ablations**: Study each simplification's impact
- **Deploy**: Use for real applications

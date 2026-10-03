# DreamerV2 Implementation Templates

Educational templates for implementing DreamerV2 from scratch.

## Paper Reference

**Mastering Atari with Discrete World Models**  
Danijar Hafner, Timothy Lillicrap, Mohammad Norouzi, Jimmy Ba  
ICLR 2021  
[Paper](https://arxiv.org/abs/2010.02193) | [Website](https://danijar.com/project/dreamerv2/)

## Overview

DreamerV2 improves upon DreamerV1 with discrete representations and better training dynamics. It achieves human-level performance on Atari while using significantly less data than model-free methods.

### Key Improvements Over DreamerV1

1. **Discrete Representations**: Uses categorical distributions instead of Gaussian
2. **KL Balancing**: Prevents posterior collapse with bidirectional KL
3. **Symlog Predictions**: Normalizes rewards across different scales
4. **Improved Architecture**: LayerNorm, ELU activations, better initialization

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORLD MODEL                                │
│                                                                 │
│  Encoder: o_t → embed_t (with LayerNorm, ELU)                  │
│                                                                 │
│  Discrete RSSM:                                                 │
│    Recurrent:  h_t = f(h_{t-1}, z_{t-1}, a_{t-1})              │
│    Prior:      z_t ~ Categorical(h_t)  [32 × 32 categoricals]  │
│    Posterior:  z_t ~ Categorical(h_t, embed_t)                 │
│    KL Balancing: αKL(post||prior) + (1-α)KL(prior||post)       │
│                                                                 │
│  Decoder: (z_t, h_t) → o_t (with LayerNorm)                    │
│  Reward:  (z_t, h_t) → symlog(r_t)  [normalized]               │
│  Continue: (z_t, h_t) → γ_t                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ACTOR-CRITIC                                 │
│                                                                 │
│  Actor:  π(a | z, h)  [Gaussian policy with improved arch]     │
│  Critic: V(z, h)      [Lambda returns for better estimates]    │
└─────────────────────────────────────────────────────────────────┘
```

## Files

### 1. `rssm.py` - Discrete Recurrent State-Space Model

The core innovation of DreamerV2: discrete latent representations.

**Key Components:**
- Categorical distributions (32 classes × 32 categoricals = 1024-dim)
- Straight-through gradient estimator for discrete sampling
- KL balancing: `α * KL(post || prior) + (1-α) * KL(prior || post)`
- Free nats regularization

**Key Methods:**
- `prior()`: Sample from p(z | h) using categorical distribution
- `posterior()`: Sample from q(z | h, o) using observation
- `kl_loss()`: Compute balanced KL divergence
- `rollout_observation()`: Train on real observations
- `rollout_imagination()`: Imagine trajectories for actor-critic

### 2. `networks.py` - Improved Encoder/Decoder

Enhanced architectures with better normalization and activations.

**Components:**
- `ConvEncoder`: Uses LayerNorm and ELU activations
- `ConvDecoder`: Symmetric decoder architecture
- `RewardPredictor`: Predicts symlog-transformed rewards
- `ContinuePredictor`: Binary classifier for episode termination

**Key Improvements:**
- LayerNorm instead of BatchNorm (more stable)
- ELU instead of ReLU (smoother gradients)
- Better depth progression

### 3. `actor_critic.py` - Lambda Returns and Robust Learning

Improved policy and value learning.

**Components:**
- `Actor`: Gaussian policy with improved architecture
- `Critic`: Value network with lambda returns
- `compute_lambda_returns()`: TD(λ) for better value estimates
- `compute_actor_loss()`: Policy gradient with entropy regularization
- `compute_critic_loss()`: MSE loss against lambda returns

**Key Concepts:**
- **Lambda Returns**: Interpolate between TD(0) and Monte Carlo
  ```
  G^λ_t = r_t + γ * ((1-λ) * V_{t+1} + λ * G^λ_{t+1})
  ```
- Better bias-variance tradeoff than pure TD or MC

### 4. `train.py` - Complete Training Loop

Integrates all components with key improvements.

**Features:**
- KL balancing for stable discrete representations
- Symlog/symexp transformations for rewards
- Efficient training loop
- Action selection for environment interaction

**Key Functions:**
- `symlog()`: Transform rewards to normalized scale
- `symexp()`: Inverse transformation
- `train_world_model()`: Learn dynamics from observations
- `train_actor_critic()`: Learn policy in imagination

## Implementation Order

### Phase 1: Discrete RSSM
1. **rssm.py** - Implement `DiscreteRSSM` class
   - Start with `prior()` and `posterior()` using categorical distributions
   - Implement straight-through gradient estimator
   - Add `recurrent_step()`
   - Implement `rollout_observation()` and `rollout_imagination()`
   - Add `kl_loss()` with balancing

### Phase 2: Improved Networks
2. **networks.py** - Implement improved architectures
   - `ConvEncoder` with LayerNorm and ELU
   - `ConvDecoder` with symmetric architecture
   - `RewardPredictor` and `ContinuePredictor`
   - Test with dummy data

### Phase 3: Actor-Critic
3. **actor_critic.py** - Implement policy learning
   - `Actor` and `Critic` networks
   - `compute_lambda_returns()` function
   - Loss computation functions
   - Test lambda return computation

### Phase 4: Integration
4. **train.py** - Integrate everything
   - Implement `DreamerV2` class
   - World model training loop
   - Actor-critic training loop
   - Action selection
   - Symlog transformations

## Key Concepts

### Discrete Representations

DreamerV2 uses categorical distributions instead of Gaussian:

**Why Discrete?**
- Better capacity for complex distributions
- Avoids issues with continuous optimization
- More stable training

**Implementation:**
```python
# Sample from categorical with straight-through gradient
z_sample = OneHotCategorical(logits).sample()
z = z_sample + probs - probs.detach()  # Straight-through
```

### KL Balancing

Prevents posterior collapse by balancing two KL terms:

```python
kl_loss = α * KL(post || prior) + (1-α) * KL(prior || post)
```

- First term: Regularizes posterior toward prior
- Second term: Encourages informative prior
- Balance coefficient α typically 0.8

### Symlog Transformation

Normalizes rewards across different scales:

```python
symlog(x) = sign(x) * log(|x| + 1)
symexp(x) = sign(x) * (exp(|x|) - 1)
```

**Benefits:**
- Works for positive and negative rewards
- Compresses large values
- Smooth around zero
- Reversible transformation

### Lambda Returns

Better value estimates by mixing TD and MC:

```python
G^λ_t = r_t + γ * c_t * ((1-λ) * V_{t+1} + λ * G^λ_{t+1})
```

- λ=0: Pure TD (low variance, high bias)
- λ=1: Pure MC (high variance, low bias)
- λ=0.95: Good balance

## Hyperparameters

Default hyperparameters from the paper:

```python
# Model architecture
num_categories = 32          # Classes per categorical
num_categoricals = 32        # Number of categoricals
state_dim = 1024            # Total stochastic state (32×32)
rnn_hidden_dim = 200        # Deterministic state
hidden_dim = 400            # Hidden layers
embed_dim = 1024            # Observation embedding

# Training
batch_size = 50             # Sequences per batch
seq_len = 50                # Sequence length
imagination_horizon = 15    # Steps to imagine

# KL regularization
kl_balance = 0.8            # KL balancing coefficient
free_nats = 1.0             # Free nats threshold

# Optimization
world_model_lr = 3e-4       # World model learning rate
actor_lr = 8e-5             # Actor learning rate
critic_lr = 8e-5            # Critic learning rate

# RL
gamma = 0.99                # Discount factor
lambda_ = 0.95              # Lambda for returns
```

## Testing

Test individual components:

```bash
cd world-models/paper3_dreamerv2

# Test components
python rssm.py
python networks.py
python actor_critic.py

# Test integration
python train.py
```

## Key Differences from DreamerV1

| Aspect | DreamerV1 | DreamerV2 |
|--------|-----------|-----------|
| **State representation** | Gaussian (continuous) | Categorical (discrete) |
| **State dimension** | 30-dim Gaussian | 32×32 categoricals (1024-dim) |
| **Gradient estimator** | Reparameterization | Straight-through |
| **KL loss** | Single direction | Balanced bidirectional |
| **Reward prediction** | Direct | Symlog-transformed |
| **Normalization** | BatchNorm | LayerNorm |
| **Activation** | ReLU | ELU |
| **Sample efficiency** | Good | Excellent |
| **Atari performance** | Sub-human | Human-level |

## Common Issues

### Posterior Collapse
- **Symptom**: KL loss drops to zero, poor reconstructions
- **Solution**: Increase free_nats, tune kl_balance (try 0.5-0.9)

### Categorical Degeneracy
- **Symptom**: Only few categories are used
- **Solution**: Check initialization, increase free_nats, add entropy regularization

### Unstable Training
- **Symptom**: Loss spikes, NaN values
- **Solution**: Reduce learning rates, clip gradients, check symlog implementation

### Poor Imagination Quality
- **Symptom**: Imagined trajectories diverge quickly
- **Solution**: Train world model longer, increase model capacity, check KL balance

## Debugging Tips

1. **Visualize Categorical Usage**: Plot which categories are being used
2. **Check KL Components**: Monitor both KL(post||prior) and KL(prior||post)
3. **Symlog Range**: Verify transformed rewards are in reasonable range
4. **Reconstruction Quality**: Save decoded images to check encoder/decoder
5. **Imagination Rollouts**: Visualize imagined trajectories vs real ones

## Extensions

Once you have a working implementation:

1. **Different Domains**: Test on DMControl, MiniGrid, custom environments
2. **Discrete Actions**: Modify for categorical action spaces
3. **Hierarchical Models**: Add temporal abstractions
4. **Multi-step Prediction**: Predict multiple steps ahead
5. **Ensemble Models**: Use multiple world models for uncertainty

## Performance Expectations

On Atari with 100k environment steps (400k frames):
- **DreamerV1**: ~50% human performance
- **DreamerV2**: ~100% human performance
- **DreamerV3**: ~200% human performance (see Paper 4)

## Resources

- **Paper**: https://arxiv.org/abs/2010.02193
- **Official implementation**: https://github.com/danijar/dreamerv2
- **Author's website**: https://danijar.com/project/dreamerv2/
- **Blog post**: https://danijar.com/dreamerv2/

## Next Steps

After completing DreamerV2:
- **Paper 4**: DreamerV3 with further simplifications and robustness
- **Compare**: Benchmark against DreamerV1 on same tasks
- **Ablations**: Study impact of discrete vs continuous representations

# DreamerV1 Implementation Templates

Educational templates for implementing DreamerV1 from scratch.

## Paper Reference

**Dream to Control: Learning Behaviors by Latent Imagination**  
Danijar Hafner, Timothy Lillicrap, Jimmy Ba, Mohammad Norouzi  
ICLR 2020  
[Paper](https://arxiv.org/abs/1912.01603) | [Website](https://danijar.com/project/dreamerv1/)

## Overview

DreamerV1 learns behaviors by imagining trajectories in a learned world model. Unlike the original World Models paper which trains components separately, DreamerV1 trains everything end-to-end with backpropagation.

### Key Innovations

1. **RSSM (Recurrent State-Space Model)**: Combines deterministic (h) and stochastic (z) states
2. **Latent Imagination**: Learn policies entirely in imagination without real environment steps
3. **End-to-End Training**: Train world model and policy jointly with gradients
4. **Actor-Critic in Latent Space**: Policy learning using imagined trajectories

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORLD MODEL                                │
│                                                                 │
│  Encoder: o_t → embed_t                                         │
│                                                                 │
│  RSSM:                                                          │
│    Recurrent:  h_t = f(h_{t-1}, z_{t-1}, a_{t-1})              │
│    Prior:      z_t ~ p(z_t | h_t)                              │
│    Posterior:  z_t ~ q(z_t | h_t, embed_t)                     │
│                                                                 │
│  Decoder: (z_t, h_t) → o_t                                      │
│  Reward:  (z_t, h_t) → r_t                                      │
│  Continue: (z_t, h_t) → γ_t                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ACTOR-CRITIC                                 │
│                                                                 │
│  Actor:  π(a | z, h)  [Learn policy in latent space]           │
│  Critic: V(z, h)      [Estimate values of imagined states]     │
└─────────────────────────────────────────────────────────────────┘
```

## Files

### 1. `rssm.py` - Recurrent State-Space Model

The core of the world model that maintains both deterministic and stochastic states.

**Key Components:**
- Recurrent network (GRU/LSTM) for deterministic state h
- Prior network p(z | h) for imagination
- Posterior network q(z | h, o) for learning from observations
- KL loss for regularization

**Key Methods:**
- `get_initial_state()`: Initialize RSSM state
- `prior()`: Compute p(z | h) for imagination
- `posterior()`: Compute q(z | h, o) from observations
- `rollout_imagination()`: Imagine trajectories without observations
- `rollout_observation()`: Learn from actual observations

### 2. `networks.py` - Encoder, Decoder, and Predictors

Neural networks that connect observations to latent states.

**Components:**
- `ConvEncoder`: 64x64x3 images → 1024-dim embeddings
- `ConvDecoder`: Latent states → reconstructed images
- `RewardPredictor`: Latent states → predicted rewards
- `ContinuePredictor`: Latent states → episode continuation probability

### 3. `actor_critic.py` - Policy and Value Networks

Networks for learning behaviors in imagination.

**Components:**
- `Actor`: Outputs stochastic policy π(a | z, h) as Gaussian distribution
- `Critic`: Estimates V(z, h) for value-based learning
- `compute_lambda_returns()`: TD(λ) for stable value learning
- `compute_actor_loss()`: Policy gradient in imagination
- `compute_critic_loss()`: Value function learning

### 4. `buffer.py` - Replay Buffer

Stores sequences of experience for training recurrent models.

**Features:**
- Episode-based storage
- Sequence sampling for recurrent training
- Efficient memory management
- Handles variable-length episodes

### 5. `train.py` - Main Training Loop

Integrates all components into the complete algorithm.

**Training Process:**
1. Collect experience in environment
2. Train world model on stored sequences
3. Imagine trajectories using world model
4. Train actor-critic on imagined trajectories
5. Repeat

## Implementation Order

Follow this order to implement DreamerV1:

### Phase 1: World Model
1. **networks.py** - Implement ConvEncoder
2. **networks.py** - Implement ConvDecoder
3. **networks.py** - Implement RewardPredictor and ContinuePredictor
4. **rssm.py** - Implement RSSM core (prior, posterior, recurrent step)
5. **rssm.py** - Implement rollout methods
6. **buffer.py** - Implement replay buffer

### Phase 2: Actor-Critic
7. **actor_critic.py** - Implement Actor network
8. **actor_critic.py** - Implement Critic network
9. **actor_critic.py** - Implement lambda returns
10. **actor_critic.py** - Implement loss functions

### Phase 3: Integration
11. **train.py** - Implement DreamerV1 class
12. **train.py** - Implement world model training
13. **train.py** - Implement actor-critic training
14. **train.py** - Implement full training loop

## Key Concepts

### Recurrent State-Space Model (RSSM)

The RSSM maintains two types of states:

- **Deterministic state h**: Updated via recurrence to capture temporal dependencies
  ```
  h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
  ```

- **Stochastic state z**: Captures uncertainty and variability
  ```
  Prior:     p(z_t | h_t)           [for imagination]
  Posterior: q(z_t | h_t, o_t)      [for learning]
  ```

### Learning in Imagination

Key insight: Once we have a good world model, we can learn policies entirely in imagination!

1. Start from a real state (z, h)
2. Imagine actions from current policy
3. Predict next states using RSSM prior
4. Predict rewards and continues
5. Compute policy gradients from imagined returns
6. Update policy without stepping environment!

### Loss Functions

**World Model Loss:**
```python
loss = reconstruction_loss + reward_loss + continue_loss + kl_loss
```

- Reconstruction: How well can we decode observations?
- Reward: How accurately do we predict rewards?
- Continue: Do we predict episode termination correctly?
- KL: Regularization between posterior and prior

**Actor Loss:**
```python
actor_loss = -mean(lambda_returns)  # Maximize returns
```

**Critic Loss:**
```python
critic_loss = MSE(predicted_values, lambda_returns)
```

## Hyperparameters

Default hyperparameters from the paper:

```python
# Model architecture
state_dim = 30              # Stochastic state dimension
rnn_hidden_dim = 200        # Deterministic state dimension
hidden_dim = 400            # Hidden layer dimension
embed_dim = 1024            # Observation embedding dimension

# Training
batch_size = 50             # Sequences per batch
seq_len = 50                # Sequence length
imagination_horizon = 15    # Steps to imagine for actor-critic
free_nats = 3.0             # Free nats for KL loss

# Optimization
world_model_lr = 6e-4       # World model learning rate
actor_lr = 8e-5             # Actor learning rate
critic_lr = 8e-5            # Critic learning rate

# RL
gamma = 0.99                # Discount factor
lambda_ = 0.95              # Lambda for returns
```

## Testing

Each file includes a test function. Run them to verify your implementation:

```bash
cd world-models/paper2_dreamerv1

# Test individual components
python rssm.py
python networks.py
python actor_critic.py
python buffer.py

# Test integration
python train.py --test
```

## Training

Once all components are implemented:

```bash
# Train on CarRacing
python train.py --env CarRacing-v0 --steps 1000000

# Train with custom settings
python train.py --env CarRacing-v0 --steps 2000000 --batch-size 50 --seq-len 50
```

## Debugging Tips

1. **Start small**: Test each component independently before integration
2. **Check shapes**: Print tensor shapes at each step
3. **Visualize reconstructions**: Save decoded images to verify encoder/decoder
4. **Monitor losses**: All losses should decrease over time
5. **KL collapse**: If KL loss drops to free_nats immediately, increase free_nats
6. **Imagination quality**: Sample imagined trajectories and visualize them

## Common Issues

### KL Divergence Collapse
- **Symptom**: KL loss immediately drops to free_nats and stays there
- **Solution**: Increase free_nats, reduce KL weight, or use KL balancing

### Poor Reconstructions
- **Symptom**: Decoder outputs blurry or blank images
- **Solution**: Check encoder/decoder architecture, increase reconstruction loss weight

### Unstable Training
- **Symptom**: Losses oscillate or explode
- **Solution**: Reduce learning rates, clip gradients, check for NaN values

### Policy Not Improving
- **Symptom**: Actor loss doesn't decrease, returns stay low
- **Solution**: Check imagination rollouts, verify reward predictions, increase imagination horizon

## Extensions

Once you have a working implementation, try:

1. **Different environments**: DMControl, Atari, custom environments
2. **Discrete RSSM**: Use categorical distributions (DreamerV2 style)
3. **Model-based planning**: Use learned model for online planning
4. **Exploration bonuses**: Add curiosity-driven exploration
5. **Hierarchical models**: Add higher-level temporal abstractions

## Resources

- **Paper**: https://arxiv.org/abs/1912.01603
- **Official implementation**: https://github.com/danijar/dreamer
- **Author's website**: https://danijar.com/project/dreamerv1/
- **DreamerV2**: Improved discrete version
- **DreamerV3**: Latest state-of-the-art version

## Differences from World Models (Paper 1)

| Aspect | World Models | DreamerV1 |
|--------|--------------|-----------|
| State representation | Separate VAE + RNN | Unified RSSM |
| Training | Sequential (VAE → RNN → Controller) | End-to-end |
| Policy learning | Evolution (CMA-ES) | Actor-critic with gradients |
| Imagination | Fixed horizon | Differentiable rollouts |
| State type | Deterministic latent + RNN hidden | Deterministic + Stochastic |

## Next Steps

After completing DreamerV1:
- **Paper 3**: DreamerV2 with discrete representations
- **Paper 4**: DreamerV3 with improved robustness
- Compare sample efficiency between papers
- Experiment with different domains

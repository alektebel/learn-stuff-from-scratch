# DreamerV1 Quick Start Guide

## Getting Started

This guide will walk you through implementing DreamerV1 step-by-step.

## Prerequisites

```bash
# Install dependencies
cd world-models
pip install -r requirements.txt
```

## Step-by-Step Implementation

### Step 1: Implement the Encoder (networks.py)

Start with `ConvEncoder` - it's the simplest component.

**Goal**: Convert 64x64x3 images to 1024-dim embeddings.

**Architecture**:
```
Input (64x64x3) 
  → Conv2d(3, 32, kernel=4, stride=2) + ReLU → (32x32x32)
  → Conv2d(32, 64, kernel=4, stride=2) + ReLU → (16x16x64)
  → Conv2d(64, 128, kernel=4, stride=2) + ReLU → (8x8x128)
  → Conv2d(128, 256, kernel=4, stride=2) + ReLU → (4x4x256)
  → Flatten → (4096)
  → Linear(4096, 1024) + ReLU → (1024)
```

**Test**: Run `python networks.py` to verify shapes.

### Step 2: Implement the Decoder (networks.py)

Reverse of the encoder.

**Goal**: Reconstruct 64x64x3 images from latent states.

**Architecture**:
```
Input (230) [30 (z) + 200 (h)]
  → Linear(230, 4096) + ReLU → (4096)
  → Reshape → (256, 4, 4)
  → ConvTranspose2d(256, 128, kernel=4, stride=2) + ReLU → (128, 8, 8)
  → ConvTranspose2d(128, 64, kernel=4, stride=2) + ReLU → (64, 16, 16)
  → ConvTranspose2d(64, 32, kernel=4, stride=2) + ReLU → (32, 32, 32)
  → ConvTranspose2d(32, 3, kernel=4, stride=2) + Sigmoid → (3, 64, 64)
```

**Test**: Encode then decode an image, check reconstruction.

### Step 3: Implement Predictors (networks.py)

Implement `DenseDecoder`, then wrap it for rewards and continues.

**DenseDecoder Architecture**:
```
Input (230) [z + h]
  → Linear(230, 400) + ReLU
  → Linear(400, 400) + ReLU
  → Linear(400, 400) + ReLU
  → Linear(400, 400) + ReLU
  → Linear(400, 1)
  → Optional activation (sigmoid for continues, none for rewards)
```

**Test**: Verify output shapes and value ranges.

### Step 4: Implement RSSM Core (rssm.py)

This is the most complex component. Break it down:

#### 4a. Implement `get_initial_state()`
```python
def get_initial_state(self, batch_size, device):
    h = torch.zeros(1, batch_size, self.rnn_hidden_dim, device=device)
    z = torch.zeros(batch_size, self.state_dim, device=device)
    return {'h': h, 'z': z}
```

#### 4b. Implement `prior()` and `posterior()`
```python
def prior(self, h):
    x = self.fc_prior(h)
    mean = self.fc_prior_mean(x)
    std = F.softplus(self.fc_prior_std(x)) + self.min_std
    return mean, std
```

#### 4c. Implement `recurrent_step()`
```python
def recurrent_step(self, prev_state, prev_action):
    h_prev = prev_state['h']
    z_prev = prev_state['z']
    x = torch.cat([z_prev, prev_action], dim=-1).unsqueeze(1)
    output, h_new = self.rnn(x, h_prev)
    h_out = output.squeeze(1)
    return h_out, h_new
```

#### 4d. Implement rollout methods

Start with `rollout_observation()` for training, then `rollout_imagination()` for actor-critic.

**Test**: Run `python rssm.py` after each substep.

### Step 5: Implement Replay Buffer (buffer.py)

Start with `SimpleBuffer` for debugging, then implement full `ReplayBuffer`.

**Key methods**:
1. `add()`: Store transitions
2. `sample()`: Return batch of sequences
3. Handle episode boundaries properly

**Test**: Add random data and sample batches, verify shapes.

### Step 6: Implement Actor (actor_critic.py)

**Architecture**:
```
Input (230) [z + h]
  → Linear(230, 400) + ReLU
  → Linear(400, 400) + ReLU
  → Linear(400, 400) + ReLU
  → Linear(400, 400) + ReLU
  → Split:
    → Mean: Linear(400, action_dim) → Tanh
    → Std: Linear(400, action_dim) → Softplus + clip
```

**Output**: Normal distribution over actions

**Test**: Sample actions, verify [-1, 1] range.

### Step 7: Implement Critic (actor_critic.py)

Similar to Actor but outputs a single value.

**Test**: Verify value predictions.

### Step 8: Implement Lambda Returns (actor_critic.py)

```python
def compute_lambda_returns(rewards, values, continues, gamma=0.99, lambda_=0.95):
    # Work backwards from end of trajectory
    lambda_return = values[:, -1]
    lambda_returns = []
    for t in reversed(range(len(rewards[0]))):
        lambda_return = rewards[:, t] + gamma * continues[:, t] * (
            (1 - lambda_) * values[:, t + 1] + lambda_ * lambda_return
        )
        lambda_returns.insert(0, lambda_return)
    return torch.stack(lambda_returns, dim=1)
```

**Test**: Verify with dummy data.

### Step 9: Integrate World Model Training (train.py)

Implement `DreamerV1.train_world_model()`:

1. Encode observations
2. Roll out RSSM
3. Decode states
4. Predict rewards and continues
5. Compute losses
6. Optimize

**Test**: Run with dummy batch, ensure losses decrease.

### Step 10: Integrate Actor-Critic Training (train.py)

Implement `DreamerV1.train_actor_critic()`:

1. Get initial states from real observations
2. Imagine trajectories using RSSM and actor
3. Compute lambda returns
4. Update actor and critic

**Test**: Run with dummy batch.

### Step 11: Implement Full Training Loop (train.py)

1. Initialize environment and agent
2. Collect initial experience (random policy)
3. Main loop:
   - Act in environment
   - Store in buffer
   - Sample batch
   - Train world model
   - Train actor-critic
   - Log and save

**Test**: Run for a few iterations, verify all components work together.

## Debugging Checklist

When something doesn't work:

- [ ] Check tensor shapes at each step
- [ ] Verify gradients are flowing (use `loss.backward()`, check `param.grad`)
- [ ] Check for NaN or Inf values
- [ ] Visualize reconstructions
- [ ] Monitor all losses
- [ ] Start with small networks and small batch sizes
- [ ] Test each component independently

## Common Issues

### Issue 1: NaN Losses
**Causes**: 
- Division by zero in std computation
- Log of negative values
- Exploding gradients

**Solutions**:
- Use softplus for std: `F.softplus(x) + min_std`
- Clip gradients: `torch.nn.utils.clip_grad_norm_()`
- Lower learning rates

### Issue 2: KL Collapse
**Symptom**: Posterior equals prior immediately

**Solutions**:
- Increase free_nats (e.g., 3.0 → 5.0)
- Use KL balancing
- Check posterior network receives observation

### Issue 3: Poor Reconstructions
**Causes**:
- Wrong decoder architecture
- Latent bottleneck too small
- Insufficient training

**Solutions**:
- Verify encoder/decoder are symmetric
- Check sigmoid on decoder output
- Normalize input images to [0, 1]

### Issue 4: Policy Not Learning
**Causes**:
- World model not accurate
- Imagination horizon too short
- Wrong reward predictions

**Solutions**:
- Train world model longer before actor-critic
- Increase imagination_horizon (e.g., 15 → 30)
- Check reward predictor accuracy

## Validation Steps

After implementation, verify:

1. **World Model**:
   - [ ] Reconstructions look reasonable
   - [ ] KL loss is positive and bounded
   - [ ] Reward predictions correlate with true rewards
   - [ ] Continue predictions match episode termination

2. **Actor-Critic**:
   - [ ] Actor outputs valid actions
   - [ ] Critic values are reasonable scale
   - [ ] Lambda returns computed correctly
   - [ ] Losses decrease over training

3. **Integration**:
   - [ ] Agent can act in environment
   - [ ] Buffer fills with data
   - [ ] Training runs without crashes
   - [ ] Returns improve over time

## Next Steps

Once everything works:

1. **Tune hyperparameters**: Learning rates, batch size, imagination horizon
2. **Try different environments**: DMControl, Atari
3. **Add visualization**: Save videos, plot metrics
4. **Experiment**: Different architectures, loss weights
5. **Compare to baselines**: How does it compare to model-free RL?

## Tips for Success

1. **Start simple**: Get each component working before moving on
2. **Test frequently**: Run tests after every change
3. **Visualize everything**: Reconstructions, imagined trajectories, etc.
4. **Use small networks**: Faster iterations during debugging
5. **Log extensively**: Track all losses and metrics
6. **Read the paper**: Understand the theory behind each component
7. **Check official code**: When stuck, refer to the official implementation

## Resources

- **Paper**: https://arxiv.org/abs/1912.01603
- **Official Code**: https://github.com/danijar/dreamer
- **Tutorial**: https://danijar.com/project/dreamerv1/
- **Discussion**: https://github.com/danijar/dreamer/issues

Good luck with your implementation! 🚀

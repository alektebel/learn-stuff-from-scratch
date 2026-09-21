# World Models - From Scratch Implementation

A comprehensive from-scratch implementation of the 5 most influential world model papers in Python for reinforcement learning and model-based control.

## Goal

Build functional world models to understand:
- **Latent Representations**: Learning compact world representations
- **Dynamics Modeling**: Predicting future states and rewards
- **Planning in Imagination**: Decision-making in learned world models
- **Sample Efficiency**: Learning from fewer environment interactions
- **Generalization**: Transferring learned models to new tasks

## What are World Models?

World models are learned representations of an agent's environment that enable:

1. **Representation Learning**: Compress high-dimensional observations (images) into compact latent states
2. **Dynamics Prediction**: Model how the world evolves over time
3. **Planning**: Make decisions by imagining future trajectories
4. **Sample Efficiency**: Learn behaviors with fewer real environment interactions

World models have become crucial for:
- Sample-efficient reinforcement learning
- Model-based control
- Sim-to-real transfer
- Zero-shot generalization

## Project Structure

```
world-models/
├── README.md                       # This file
├── IMPLEMENTATION_GUIDE.md         # Detailed step-by-step guide
├── requirements.txt                # Python dependencies
│
├── paper1_world_models/            # Ha & Schmidhuber (2018)
│   ├── vae.py                      # Variational Autoencoder
│   ├── rnn.py                      # MDN-RNN for dynamics
│   ├── controller.py               # CMA-ES controller
│   ├── train.py                    # Training script
│   └── eval.py                     # Evaluation
│
├── paper2_dreamerv1/               # Hafner et al. (2020)
│   ├── rssm.py                     # Recurrent State-Space Model
│   ├── networks.py                 # Encoder, Decoder, Models
│   ├── actor_critic.py             # Policy and Value networks
│   ├── train.py                    # World model + RL training
│   └── buffer.py                   # Replay buffer
│
├── paper3_dreamerv2/               # Hafner et al. (2021)
│   ├── rssm.py                     # Discrete RSSM
│   ├── networks.py                 # Improved architectures
│   ├── actor_critic.py             # Lambda returns
│   ├── train.py                    # Simplified training
│   └── utils.py                    # Helper functions
│
├── paper4_dreamerv3/               # Hafner et al. (2023)
│   ├── world_model.py              # Simplified world model
│   ├── actor_critic.py             # Robust actor-critic
│   ├── train.py                    # Unified training loop
│   └── symlog.py                   # Symlog predictions
│
├── paper5_iris/                    # Micheli et al. (2023)
│   ├── tokenizer.py                # Discrete autoencoder
│   ├── transformer.py              # World model transformer
│   ├── actor_critic.py             # Policy network
│   ├── train.py                    # Training script
│   └── sample.py                   # Trajectory sampling
│
├── common/                         # Shared utilities
│   ├── env_wrapper.py              # Environment preprocessing
│   ├── replay_buffer.py            # Experience storage
│   ├── video.py                    # Video generation
│   └── metrics.py                  # Evaluation metrics
│
└── solutions/                      # Complete implementations
    ├── README.md                   # Solution documentation
    ├── paper1_world_models/
    ├── paper2_dreamerv1/
    ├── paper3_dreamerv2/
    ├── paper4_dreamerv3/
    └── paper5_iris/
```

## The 5 Key Papers

### Paper 1: World Models (Ha & Schmidhuber, 2018)

**Paper**: [World Models](https://arxiv.org/abs/1803.10122)

**Key Contributions**:
- Three-component architecture: VAE + MDN-RNN + Controller
- Train components separately for simplicity
- Visualize what the agent "dreams"
- Achieves good performance on car racing

**Architecture**:
```
┌─────────────────────────────────────────────┐
│  Observation (Image) → VAE Encoder → z      │
│                                              │
│  z + action → MDN-RNN → next z, reward      │
│                                              │
│  z → Controller (CMA-ES) → action           │
└─────────────────────────────────────────────┘
```

**Components**:
1. **VAE**: Compresses 96x96x3 images to 32-dim latent vectors
2. **MDN-RNN**: Mixture Density Network RNN predicts next latent state
3. **Controller**: Linear policy optimized with CMA-ES

**What You'll Learn**:
- Variational autoencoders for observation compression
- Mixture density networks for stochastic predictions
- Evolution strategies for policy optimization
- Training models separately vs end-to-end

### Paper 2: DreamerV1 (Hafner et al., 2020)

**Paper**: [Dream to Control: Learning Behaviors by Latent Imagination](https://arxiv.org/abs/1912.01603)

**Key Contributions**:
- Recurrent State-Space Model (RSSM) for world dynamics
- Learn behaviors purely from imagined trajectories
- End-to-end training with backpropagation through time
- Outperforms model-free methods on many tasks

**Architecture**:
```
┌──────────────────────────────────────────────────┐
│  RSSM: Deterministic (h) + Stochastic (z) states │
│                                                   │
│  h_{t+1} = f(h_t, z_t, a_t)    [Recurrent]      │
│  z_t ~ p(z_t | h_t)             [Prior]         │
│  z_t ~ q(z_t | h_t, o_t)        [Posterior]     │
│                                                   │
│  Actor: π(a | z, h)   [Policy in latent space]  │
│  Critic: V(z, h)      [Value estimation]        │
└──────────────────────────────────────────────────┘
```

**Components**:
1. **Encoder**: Maps observations to latent representations
2. **RSSM**: Models world dynamics with recurrent + stochastic states
3. **Decoder**: Reconstructs observations from latent states
4. **Reward/Continue**: Predicts rewards and episode termination
5. **Actor-Critic**: Learns policy by imagining trajectories

**What You'll Learn**:
- State-space models for sequential prediction
- Latent imagination for policy learning
- KL balancing for stable training
- Actor-critic in latent space

### Paper 3: DreamerV2 (Hafner et al., 2021)

**Paper**: [Mastering Atari with Discrete World Models](https://arxiv.org/abs/2010.02193)

**Key Contributions**:
- Discrete latent representations (categorical variables)
- KL balancing for stable learning
- Works on challenging Atari games from pixels
- More robust than DreamerV1

**Key Improvements**:
```
DreamerV1 → DreamerV2
─────────────────────────
Continuous z    →  Discrete z (32 classes x 32 categories)
MSE loss       →  Symlog for rewards
Simple critic  →  Lambda returns
Direct KL      →  KL balancing
```

**Components**:
1. **Discrete RSSM**: Uses categorical distributions for stochastic state
2. **Improved Predictions**: Better reward and value predictions
3. **Lambda Returns**: More stable value learning
4. **KL Balancing**: Prevents posterior collapse

**What You'll Learn**:
- Discrete representations for world models
- Categorical distributions in latent space
- Advanced value learning techniques
- Stabilization tricks for deep RL

### Paper 4: DreamerV3 (Hafner et al., 2023)

**Paper**: [Mastering Diverse Domains through World Models](https://arxiv.org/abs/2301.04104)

**Key Contributions**:
- Single algorithm for diverse domains (Atari, DMC, Minecraft)
- Simplified architecture and training
- Robust to hyperparameters
- State-of-the-art sample efficiency

**Key Improvements**:
```
DreamerV2 → DreamerV3
─────────────────────────────
Complex tuning  →  Robust hyperparameters
Separate losses →  Unified predictions
Many tricks     →  Simplified training
Domain-specific →  General-purpose
```

**Components**:
1. **Symlog Predictions**: All predictions use symlog encoding
2. **Simplified World Model**: Unified architecture
3. **Robust Actor-Critic**: Works across domains
4. **Free Bits**: Improved KL regularization

**What You'll Learn**:
- General-purpose world model design
- Symlog encoding for various scales
- Hyperparameter-robust algorithms
- Cross-domain transfer learning

### Paper 5: IRIS (Micheli et al., 2023)

**Paper**: [Transformers are Sample Efficient World Models](https://arxiv.org/abs/2209.00588)

**Key Contributions**:
- Fully discrete world models with transformers
- Tokenizes observations, actions, rewards
- Efficient autoregressive prediction
- Matches or exceeds RNN-based models

**Architecture**:
```
┌──────────────────────────────────────────────────┐
│  Observation → VQ-VAE Tokenizer → Discrete tokens│
│                                                   │
│  Transformer: Autoregressively predict sequence  │
│  [obs_t, act_t, rew_t] → [obs_{t+1}, rew_{t+1}] │
│                                                   │
│  Actor: Transformer policy over tokens           │
└──────────────────────────────────────────────────┘
```

**Components**:
1. **Discrete Tokenizer**: VQ-VAE or similar for observation encoding
2. **Transformer World Model**: Autoregressive sequence modeling
3. **Transformer Actor**: Policy network with attention
4. **Efficient Training**: Parallel token prediction

**What You'll Learn**:
- Discrete tokenization for observations
- Transformer-based world models
- Autoregressive sequence modeling
- Attention mechanisms for RL

## Quick Start

### Prerequisites

- Python 3.8+
- PyTorch 1.12+
- Gymnasium (or OpenAI Gym)
- Basic understanding of RL and deep learning
- GPU recommended for faster training

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or manually:
pip install torch torchvision gymnasium numpy matplotlib imageio tqdm
```

### Training World Models

Each paper has its own training script:

```bash
# Paper 1: World Models
cd paper1_world_models
python train.py --env CarRacing-v2 --epochs 10

# Paper 2: DreamerV1
cd paper2_dreamerv1
python train.py --env dmc_walker_walk --steps 1000000

# Paper 3: DreamerV2
cd paper3_dreamerv2
python train.py --env atari_pong --steps 2000000

# Paper 4: DreamerV3
cd paper4_dreamerv3
python train.py --env minecraft_navigate --steps 10000000

# Paper 5: IRIS
cd paper5_iris
python train.py --env atari_breakout --steps 1000000
```

### Evaluating Trained Models

```bash
# Evaluate and generate videos
python eval.py --checkpoint model.pt --episodes 10 --render

# Generate imagined trajectories
python visualize.py --checkpoint model.pt --num-dreams 5
```

## Learning Path

### Phase 1: World Models (Ha & Schmidhuber) - 6-8 hours

**Goal**: Understand the foundation of learning world models

**Steps**:
1. **VAE for Observation Compression** (2-3 hours)
   - Implement encoder and decoder networks
   - Add reparameterization trick
   - Train VAE on collected observations
   - Visualize reconstructions

2. **MDN-RNN for Dynamics** (2-3 hours)
   - Implement LSTM-based RNN
   - Add mixture density network output
   - Train on latent sequences
   - Test next-state predictions

3. **Controller with CMA-ES** (2 hours)
   - Implement linear controller
   - Use CMA-ES for optimization
   - Evaluate in environment
   - Compare with random policy

**Skills Learned**:
- Variational autoencoders
- Recurrent neural networks
- Mixture density networks
- Evolution strategies
- Separating representation and control

### Phase 2: DreamerV1 - 8-10 hours

**Goal**: Learn end-to-end differentiable world models

**Steps**:
1. **RSSM Implementation** (3-4 hours)
   - Build deterministic RNN path
   - Add stochastic latent state
   - Implement prior and posterior
   - Test on simple sequences

2. **World Model Training** (2-3 hours)
   - Implement replay buffer
   - Train encoder, RSSM, decoder
   - Add reward and continue predictors
   - Monitor reconstruction quality

3. **Actor-Critic in Imagination** (3 hours)
   - Implement policy network
   - Add value network
   - Generate imagined trajectories
   - Compute actor-critic losses

**Skills Learned**:
- State-space models
- Latent imagination
- Policy gradient methods
- Value function approximation
- Model-based RL

### Phase 3: DreamerV2 - 6-8 hours

**Goal**: Master discrete representations and stability

**Steps**:
1. **Discrete RSSM** (3-4 hours)
   - Replace continuous with categorical
   - Implement straight-through gradients
   - Add KL balancing
   - Compare with continuous version

2. **Improved Predictions** (2-3 hours)
   - Implement symlog encoding
   - Add lambda returns
   - Improve value learning
   - Test on Atari environments

3. **Robustness Techniques** (1-2 hours)
   - Add free bits for KL
   - Implement gradient clipping
   - Tune hyperparameters
   - Compare stability

**Skills Learned**:
- Categorical distributions
- Discrete latent variables
- Advanced RL techniques
- Stabilization methods

### Phase 4: DreamerV3 - 5-7 hours

**Goal**: Build general-purpose world models

**Steps**:
1. **Unified Architecture** (2-3 hours)
   - Simplify world model design
   - Use symlog for all predictions
   - Implement free bits
   - Test across domains

2. **Robust Training** (2-3 hours)
   - Apply single hyperparameter set
   - Train on multiple environments
   - Monitor cross-domain performance
   - Compare with DreamerV2

3. **Analysis** (1 hour)
   - Ablation studies
   - Visualize learned representations
   - Test generalization
   - Document findings

**Skills Learned**:
- General-purpose algorithm design
- Cross-domain learning
- Robust hyperparameters
- Ablation analysis

### Phase 5: IRIS - 7-9 hours

**Goal**: Understand transformer-based world models

**Steps**:
1. **Discrete Tokenizer** (2-3 hours)
   - Implement VQ-VAE
   - Train on observations
   - Test reconstruction quality
   - Visualize codebook usage

2. **Transformer World Model** (3-4 hours)
   - Build transformer architecture
   - Implement autoregressive prediction
   - Add causal masking
   - Train sequence model

3. **Transformer Actor** (2 hours)
   - Design policy transformer
   - Sample actions autoregressively
   - Train with imagined rollouts
   - Evaluate performance

**Skills Learned**:
- Vector quantization
- Transformer architectures
- Autoregressive modeling
- Attention mechanisms in RL

**Total Time**: ~32-42 hours for all implementations

## Comparison of Approaches

| Feature | World Models | DreamerV1 | DreamerV2 | DreamerV3 | IRIS |
|---------|--------------|-----------|-----------|-----------|------|
| **Representation** | Continuous | Continuous | Discrete | Discrete | Discrete |
| **Architecture** | VAE+RNN | RSSM | RSSM | RSSM | Transformer |
| **Training** | Separate | End-to-end | End-to-end | End-to-end | End-to-end |
| **Policy Learning** | Evolution | Actor-Critic | Actor-Critic | Actor-Critic | Actor-Critic |
| **Sample Efficiency** | Low | High | Higher | Highest | High |
| **Domains** | Simple envs | DMC | Atari | All | Atari |
| **Complexity** | Low | Medium | High | Medium | High |

## Implementation Guidelines

### Template Files

Each paper directory contains template files with:

```python
# TODO: Implement the encoder network
# Guidelines:
# - Input: observation (e.g., 64x64x3 image)
# - Output: latent vector (e.g., 256-dim)
# - Architecture: CNN with 4 conv layers
# - Activation: ReLU
# - Use proper initialization

class Encoder(nn.Module):
    def __init__(self, obs_shape, latent_dim):
        super().__init__()
        # TODO: Define convolutional layers
        pass
    
    def forward(self, obs):
        # TODO: Implement forward pass
        pass
```

### Solution Files

Complete implementations in `solutions/` directory:

```python
class Encoder(nn.Module):
    """Vision encoder that maps observations to latent representations."""
    
    def __init__(self, obs_shape, latent_dim=256, depth=32):
        super().__init__()
        self.latent_dim = latent_dim
        
        # Convolutional encoder
        self.convs = nn.Sequential(
            nn.Conv2d(obs_shape[0], 1*depth, 4, 2, 1),
            nn.ReLU(),
            nn.Conv2d(1*depth, 2*depth, 4, 2, 1),
            nn.ReLU(),
            nn.Conv2d(2*depth, 4*depth, 4, 2, 1),
            nn.ReLU(),
            nn.Conv2d(4*depth, 8*depth, 4, 2, 1),
            nn.ReLU(),
        )
        
        # Output projection
        self.fc = nn.Linear(8*depth * 4 * 4, latent_dim)
    
    def forward(self, obs):
        # Normalize observations
        obs = obs / 255.0 - 0.5
        
        # Convolutional encoding
        x = self.convs(obs)
        x = x.reshape(x.size(0), -1)
        
        # Project to latent space
        return self.fc(x)
```

## Testing and Debugging

### Visualization Tools

```python
# Visualize VAE reconstructions
def visualize_vae(vae, dataset, num_samples=10):
    """Show original and reconstructed observations."""
    originals, reconstructions = [], []
    for obs in dataset[:num_samples]:
        recon, _, _ = vae(obs)
        originals.append(obs)
        reconstructions.append(recon)
    plot_comparison(originals, reconstructions)

# Visualize imagined trajectories
def visualize_imagination(world_model, actor, start_obs, horizon=15):
    """Show what the agent imagines will happen."""
    obs = start_obs
    trajectory = [obs]
    
    for t in range(horizon):
        action = actor(obs)
        next_obs, reward = world_model.predict(obs, action)
        trajectory.append(next_obs)
        obs = next_obs
    
    plot_trajectory(trajectory)

# Compare real vs predicted
def compare_predictions(world_model, real_trajectory):
    """Compare real environment vs world model predictions."""
    real_obs, predicted_obs = [real_trajectory[0]], [real_trajectory[0]]
    
    for t in range(1, len(real_trajectory)):
        action = real_trajectory[t]['action']
        pred_obs, _ = world_model.predict(predicted_obs[-1], action)
        predicted_obs.append(pred_obs)
        real_obs.append(real_trajectory[t]['obs'])
    
    plot_comparison(real_obs, predicted_obs)
```

### Metrics

Track these metrics during training:

**World Model Metrics**:
- Reconstruction loss (MSE or similar)
- KL divergence (for VAE/RSSM)
- Reward prediction accuracy
- Continue prediction accuracy
- Latent utilization

**Policy Metrics**:
- Episode return (sum of rewards)
- Episode length
- Value function accuracy
- Policy entropy
- Gradient norms

**Efficiency Metrics**:
- Sample efficiency (return vs environment steps)
- Computation time per step
- Memory usage
- Model size

### Common Issues

**"VAE produces blurry reconstructions"**:
- Increase β weight on KL term
- Use larger latent dimension
- Improve decoder architecture
- Train longer

**"RNN predictions diverge"**:
- Add gradient clipping
- Reduce learning rate
- Use layer normalization
- Check for NaN values

**"Policy doesn't improve"**:
- Verify world model accuracy
- Check reward predictions
- Increase imagination horizon
- Adjust actor learning rate

**"Training is unstable"**:
- Use KL balancing
- Add free bits
- Reduce learning rates
- Implement gradient clipping

**"Model doesn't generalize"**:
- Collect more diverse data
- Add data augmentation
- Reduce model capacity
- Use regularization

## Advanced Topics

After completing all 5 papers, explore:

### Architecture Variants
- Transformer world models (beyond IRIS)
- Hybrid RNN-Transformer models
- Multi-modal world models (vision + language)
- Hierarchical world models

### Training Improvements
- Offline RL with world models
- Multi-task world models
- Meta-learning for fast adaptation
- Curriculum learning strategies

### Applications
- Robotics simulation and transfer
- Autonomous driving
- Game playing (Atari, MineCraft)
- Scientific discovery
- Planning and control

### Research Directions
- Compositionality in world models
- Causal world models
- Uncertainty estimation
- Long-horizon planning

## Environments

Recommended environments for each paper:

**Paper 1: World Models**
- `CarRacing-v2`: Original paper environment
- `BipedalWalker-v3`: Continuous control
- Custom simple environments

**Paper 2: DreamerV1**
- `dmc_walker_walk`: DeepMind Control Suite
- `dmc_cartpole_balance`: Simpler DMC task
- `dmc_reacher_easy`: Manipulation task

**Paper 3: DreamerV2**
- `ALE/Pong-v5`: Simple Atari game
- `ALE/Breakout-v5`: Classic Atari
- `ALE/SpaceInvaders-v5`: More complex

**Paper 4: DreamerV3**
- Any Atari environment
- DeepMind Control Suite
- Minecraft tasks
- Custom domains

**Paper 5: IRIS**
- `ALE/Breakout-v5`: Good for testing
- `ALE/Pong-v5`: Fast iteration
- `ALE/Qbert-v5`: Complex dynamics

## Performance Benchmarks

Expected performance after proper training:

| Environment | World Models | DreamerV1 | DreamerV2 | DreamerV3 | IRIS |
|-------------|--------------|-----------|-----------|-----------|------|
| **CarRacing-v2** | 900+ | 950+ | 950+ | 950+ | - |
| **DMC Walker** | - | 800+ | 900+ | 950+ | - |
| **Atari Pong** | - | 15+ | 20+ | 20+ | 20+ |
| **Atari Breakout** | - | 200+ | 400+ | 450+ | 400+ |

*Note: Scores are approximate and depend on training time and hyperparameters*

## Resources

### Papers

**Core Papers** (Implemented):
1. [World Models](https://arxiv.org/abs/1803.10122) - Ha & Schmidhuber, 2018
2. [Dream to Control](https://arxiv.org/abs/1912.01603) - DreamerV1, 2020
3. [Mastering Atari](https://arxiv.org/abs/2010.02193) - DreamerV2, 2021
4. [Mastering Diverse Domains](https://arxiv.org/abs/2301.04104) - DreamerV3, 2023
5. [Transformers are Sample Efficient](https://arxiv.org/abs/2209.00588) - IRIS, 2023

**Related Papers**:
- [PlaNet](https://arxiv.org/abs/1811.04551) - Learning Latent Dynamics
- [SLAC](https://arxiv.org/abs/1907.00953) - Stochastic Latent Actor-Critic
- [TD-MPC](https://arxiv.org/abs/2203.04955) - Temporal Difference MPC
- [GameGAN](https://arxiv.org/abs/2005.12126) - Game Engine GANs

### Tutorials and Blogs

- [World Models Interactive Blog](https://worldmodels.github.io/)
- [DreamerV3 Blog Post](https://danijar.com/dreamerv3/)
- [IRIS Paper Walkthrough](https://github.com/eloialonso/iris)
- [Model-Based RL Tutorial](https://sites.google.com/view/mbrl-tutorial)

### Code Repositories

- [Official DreamerV3](https://github.com/danijar/dreamerv3)
- [Official IRIS](https://github.com/eloialonso/iris)
- [World Models](https://github.com/ctallec/world-models)
- [CleanRL Implementations](https://github.com/vwxyzjn/cleanrl)

### Video Courses

- [Reinforcement Learning Courses](https://github.com/Developer-Y/cs-video-courses#reinforcement-learning)
- [Deep Learning Courses](https://github.com/Developer-Y/cs-video-courses#deep-learning)
- [Machine Learning Courses](https://github.com/Developer-Y/cs-video-courses#machine-learning)

## Tips for Success

### Learning Strategy

1. **Start Simple**: Begin with Paper 1 (World Models)
2. **Visualize Everything**: Plot reconstructions, predictions, trajectories
3. **Test Components**: Verify each component works before combining
4. **Compare Papers**: Understand what each improves over previous
5. **Experiment**: Try different hyperparameters and architectures

### Implementation Tips

1. **Use Small Networks First**: Debug with tiny models
2. **Verify Gradients**: Check gradient flow through all components
3. **Save Checkpoints**: Save frequently during training
4. **Monitor Losses**: Track all loss components separately
5. **Use Tensorboard**: Visualize training progress

### Debugging Workflow

1. **Overfit Single Batch**: Ensure model can memorize
2. **Check Data Pipeline**: Verify inputs are correct
3. **Test Forward Pass**: Run model on dummy data
4. **Verify Losses**: Ensure losses decrease on simple tasks
5. **Gradual Complexity**: Add components one at a time

## License

Educational purposes. Use freely for learning.

## Acknowledgments

Inspired by:
- David Ha and Jürgen Schmidhuber - World Models
- Danijar Hafner et al. - Dreamer series
- Vincent Micheli et al. - IRIS
- The model-based RL research community
- OpenAI and DeepMind for environments and baselines

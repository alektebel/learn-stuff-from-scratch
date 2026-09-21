# World Models - Complete Implementation Solutions

This directory contains **complete, production-ready implementations** of the World Models paper (Ha & Schmidhuber, 2018).

## Files

### 1. `vae.py` - Variational Autoencoder (V - Vision Model)
Complete VAE implementation that compresses 96x96x3 RGB images into 32-dimensional latent representations.

**Features:**
- ✅ Encoder with 4 convolutional layers (3→32→64→128→256 channels)
- ✅ Decoder with 4 transposed convolutional layers
- ✅ Reparameterization trick for differentiable sampling
- ✅ Combined loss function (reconstruction + KL divergence)
- ✅ Working test function demonstrating all functionality

**Architecture:**
```
Input (3, 96, 96) 
  → Conv4x4(32, stride=2) → ReLU → (32, 48, 48)
  → Conv4x4(64, stride=2) → ReLU → (64, 24, 24)
  → Conv4x4(128, stride=2) → ReLU → (128, 12, 12)
  → Conv4x4(256, stride=2) → ReLU → (256, 6, 6)
  → Flatten → Linear(9216, 32) → mu, logvar
  → Reparameterize → z (32,)
  → Linear(32, 9216) → Reshape → (256, 6, 6)
  → TransposeConv4x4(128, stride=2) → ReLU → (128, 12, 12)
  → TransposeConv4x4(64, stride=2) → ReLU → (64, 24, 24)
  → TransposeConv4x4(32, stride=2) → ReLU → (32, 48, 48)
  → TransposeConv4x4(3, stride=2) → Sigmoid → (3, 96, 96)
```

### 2. `rnn.py` - MDN-RNN (M - Memory/World Model)
Complete Mixture Density Network + LSTM implementation for learning world dynamics.

**Features:**
- ✅ LSTM for temporal modeling
- ✅ Mixture of 5 Gaussians for stochastic next-state prediction
- ✅ Reward prediction head
- ✅ Done flag prediction head
- ✅ Negative log-likelihood loss for MDN
- ✅ Sampling from mixture distributions
- ✅ Complete training function with gradient clipping
- ✅ Working test function

**Architecture:**
```
Input: [z_t, a_t] (concat of latent state and action)
  → LSTM(hidden_dim=256) → h_t
  → FC(256, 5) → Softmax → pi (mixture weights)
  → FC(256, 5*32) → Reshape → mu (5 Gaussians × 32 dims)
  → FC(256, 5*32) → Exp → sigma (5 Gaussians × 32 dims)
  → FC(256, 1) → reward prediction
  → FC(256, 1) → Sigmoid → done probability
```

**Loss Function:**
- MDN loss: Negative log-likelihood of z_{t+1} under mixture distribution
- Reward loss: MSE between predicted and actual rewards
- Done loss: Binary cross-entropy for episode termination

### 3. `controller.py` - Linear Controller (C - Controller)
Simple but effective linear controller with CMA-ES optimization.

**Features:**
- ✅ Single linear layer mapping [z, h] → action
- ✅ Tanh activation for action bounding to [-1, 1]
- ✅ Parameter extraction/setting for evolutionary optimization
- ✅ Full CMA-ES optimizer wrapper (uses `cma` library)
- ✅ Evaluation in real environment
- ✅ Evaluation in dream (learned model)
- ✅ Working test function

**Architecture:**
```
Input: [z_t, h_t] (latent state + RNN hidden state)
  → Linear(288, 3) → Tanh → action
```

**Controller has only ~867 parameters**, demonstrating that with good representations from V and M, a simple controller is sufficient!

### 4. `train.py` - Complete Training Pipeline
Full training script orchestrating all three phases.

**Features:**
- ✅ Episode collection with random policy
- ✅ VAE training phase with progress tracking
- ✅ Episode encoding with trained VAE
- ✅ Sequence dataset creation for RNN training
- ✅ MDN-RNN training phase
- ✅ Controller optimization with CMA-ES
- ✅ Support for training in "dream" (learned model) or real environment
- ✅ Checkpoint saving/loading
- ✅ Final evaluation

**Training Phases:**
1. **Collect Data**: Random policy generates trajectories
2. **Train VAE**: Learn compressed latent representations
3. **Encode Episodes**: Convert observations to latent sequences
4. **Train RNN**: Learn world dynamics from latent sequences
5. **Optimize Controller**: Use CMA-ES to find optimal policy (can be done entirely in imagination!)

### 5. `eval.py` - Evaluation and Visualization
Comprehensive evaluation and visualization tools.

**Features:**
- ✅ Model loading from checkpoints
- ✅ Episode rollout with full pipeline
- ✅ Multi-episode evaluation with statistics
- ✅ VAE reconstruction visualization
- ✅ Latent space visualization with PCA
- ✅ Rollout video creation
- ✅ RNN prediction accuracy analysis
- ✅ Dream rollout (pure imagination without real environment)
- ✅ Dream vs reality comparison

## Usage

### Running Tests
```bash
# Test individual components
cd solutions/paper1_world_models
python vae.py
python rnn.py
python controller.py
```

### Training
```bash
# Basic training (small scale for testing)
python train.py \
  --env_name CarRacing-v2 \
  --num_episodes 100 \
  --vae_epochs 5 \
  --rnn_epochs 10 \
  --generations 50 \
  --use_dream \
  --final_eval

# Full training (paper settings)
python train.py \
  --env_name CarRacing-v2 \
  --num_episodes 10000 \
  --vae_epochs 10 \
  --rnn_epochs 20 \
  --generations 100 \
  --population_size 64 \
  --use_dream \
  --use_gpu \
  --final_eval
```

### Evaluation and Visualization
```bash
python eval.py \
  --vae_path checkpoints/vae.pt \
  --rnn_path checkpoints/rnn.pt \
  --controller_path checkpoints/controller.pt \
  --env_name CarRacing-v2 \
  --num_episodes 10 \
  --visualize \
  --create_video \
  --dream_rollout \
  --use_gpu
```

## Key Implementation Details

### VAE Details
- **Input normalization**: Images divided by 255 to get [0, 1] range
- **Loss balancing**: KL loss naturally balanced with reconstruction loss
- **Architecture**: Symmetric encoder-decoder with 4 conv/deconv layers each
- **Latent dimension**: 32 (compact but expressive)

### MDN-RNN Details
- **Mixture components**: 5 Gaussians (balance between expressiveness and complexity)
- **Sequence handling**: Supports both single timesteps and batched sequences
- **Numerical stability**: Log-sum-exp trick for mixture likelihood computation
- **Gradient clipping**: Max norm of 1.0 to prevent exploding gradients

### Controller Details
- **Simplicity**: Only a single linear layer with 867 parameters
- **CMA-ES**: Population size of 64, initial sigma of 0.5
- **Dream training**: Can be trained entirely in the learned world model
- **Fitness evaluation**: Average reward over multiple rollouts

### Training Details
- **Data collection**: 1000-10000 episodes with random policy
- **VAE training**: Adam optimizer, 10 epochs typically sufficient
- **RNN training**: Sequence length of 32, 20 epochs
- **Controller optimization**: 100 generations of CMA-ES
- **Batch sizes**: 32 for both VAE and RNN training

## Performance Notes

### Computational Requirements
- **VAE training**: ~5-10 minutes on GPU for 1000 episodes
- **RNN training**: ~10-20 minutes on GPU
- **Controller optimization**: 
  - In dream: ~30 minutes (very fast, no environment interaction)
  - In reality: ~2-4 hours (environment interaction is slow)

### Expected Results
With proper training on CarRacing-v2:
- **Random policy**: ~100-200 reward
- **Trained policy**: ~700-900 reward (paper reports 906±21)

## Differences from Paper

This implementation makes some practical choices:
1. Uses `gymnasium` instead of legacy `gym`
2. Uses modern PyTorch (2.0+) with improved APIs
3. Includes extensive documentation and comments
4. Adds visualization and analysis tools
5. Handles both old and new gym API returns

## Key Insights from World Models

1. **Compression**: VAE learns compact representations (96×96×3 = 27,648 dims → 32 dims)
2. **Prediction**: RNN learns accurate world dynamics in latent space
3. **Simplicity**: Linear controller with <1000 params can solve complex tasks
4. **Imagination**: Training in dream is faster and more sample-efficient
5. **Modularity**: V, M, and C can be trained separately and combined

## Dependencies

```bash
pip install torch numpy tqdm matplotlib scikit-learn cma gymnasium
```

For full functionality including video generation:
```bash
pip install gymnasium[box2d] imageio imageio-ffmpeg
```

## References

- Paper: "World Models" by Ha & Schmidhuber (2018)
- Blog: https://worldmodels.github.io/
- Code: https://github.com/hardmaru/WorldModelsExperiments

## Notes

All implementations are **complete and working** - no TODOs left! Each file can be run independently to test its functionality. The code is production-ready with proper error handling, documentation, and test coverage.

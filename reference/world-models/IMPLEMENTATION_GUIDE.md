# World Models Implementation Guide

This guide provides detailed, step-by-step instructions for implementing all 5 world model papers from scratch.

## Overview

You'll implement:
1. **World Models** (Ha & Schmidhuber, 2018) - Foundation
2. **DreamerV1** (Hafner et al., 2020) - End-to-end learning
3. **DreamerV2** (Hafner et al., 2021) - Discrete representations
4. **DreamerV3** (Hafner et al., 2023) - General-purpose
5. **IRIS** (Micheli et al., 2023) - Transformer-based

Each section includes:
- Mathematical foundations
- Architecture details
- Implementation steps with code templates
- Testing procedures
- Common pitfalls and solutions

---

## Paper 1: World Models (2018)

### Mathematical Foundation

**Problem**: Learn a compact representation of high-dimensional environments.

**Solution**: Separate vision (VAE), memory (RNN), and control (Controller).

**Forward Process**:
```
1. Observation o_t → VAE Encoder → latent z_t
2. (z_t, a_t) → RNN → (z_{t+1}, r_{t+1}) prediction
3. z_t → Controller → action a_t
```

### Component 1: Variational Autoencoder (VAE)

**Purpose**: Compress 96x96x3 images to 32-dimensional latent vectors.

**Architecture**:
```
Encoder:
  Input: (96, 96, 3)
  Conv2d(3 → 32, kernel=4, stride=2) + ReLU  → (48, 48, 32)
  Conv2d(32 → 64, kernel=4, stride=2) + ReLU → (24, 24, 64)
  Conv2d(64 → 128, kernel=4, stride=2) + ReLU → (12, 12, 128)
  Conv2d(128 → 256, kernel=4, stride=2) + ReLU → (6, 6, 256)
  Flatten + FC → (μ, logσ²) each with dim 32

Decoder:
  Input: z ~ N(μ, σ²) with dim 32
  FC → 1024
  Reshape → (256, 2, 2)
  ConvTranspose2d(256 → 128, kernel=5, stride=2) → (6, 6, 128)
  ConvTranspose2d(128 → 64, kernel=5, stride=2) → (14, 14, 64)
  ConvTranspose2d(64 → 32, kernel=6, stride=2) → (30, 30, 32)
  ConvTranspose2d(32 → 3, kernel=6, stride=2) + Sigmoid → (96, 96, 3)
```

**Loss Function**:
```
L_VAE = Reconstruction_Loss + KL_Divergence
      = MSE(x, x_reconstructed) + KL(q(z|x) || p(z))
      = MSE(x, x̂) + -0.5 * Σ(1 + logσ² - μ² - σ²)
```

**Implementation Steps**:

1. **Create VAE class**:
```python
import torch
import torch.nn as nn

class VAE(nn.Module):
    def __init__(self, latent_dim=32):
        super().__init__()
        self.latent_dim = latent_dim
        
        # TODO: Implement encoder
        # TODO: Implement decoder
        
    def encode(self, x):
        # TODO: Return mu and logvar
        pass
    
    def reparameterize(self, mu, logvar):
        # TODO: Implement reparameterization trick
        # z = μ + σ * ε, where ε ~ N(0, 1)
        pass
    
    def decode(self, z):
        # TODO: Reconstruct image from latent
        pass
    
    def forward(self, x):
        # TODO: Full forward pass
        # Return reconstruction, mu, logvar
        pass
```

2. **Training loop**:
```python
def train_vae(vae, dataloader, epochs=10):
    optimizer = torch.optim.Adam(vae.parameters(), lr=1e-3)
    
    for epoch in range(epochs):
        for batch_idx, (data, _) in enumerate(dataloader):
            # TODO: Forward pass
            recon, mu, logvar = vae(data)
            
            # TODO: Compute losses
            recon_loss = F.mse_loss(recon, data, reduction='sum')
            kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
            
            loss = recon_loss + kl_loss
            
            # TODO: Backward pass and optimization
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if batch_idx % 100 == 0:
                print(f'Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item():.4f}')
```

3. **Test reconstructions**:
```python
def test_vae(vae, test_data):
    vae.eval()
    with torch.no_grad():
        # TODO: Generate reconstructions
        recon, _, _ = vae(test_data)
        
        # TODO: Visualize originals vs reconstructions
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 8, figsize=(16, 4))
        for i in range(8):
            axes[0, i].imshow(test_data[i].permute(1, 2, 0))
            axes[1, i].imshow(recon[i].permute(1, 2, 0))
        plt.show()
```

### Component 2: MDN-RNN (Mixture Density Network RNN)

**Purpose**: Predict next latent state and reward given current state and action.

**Architecture**:
```
Input: [z_t, a_t] → LSTM(256 hidden units) → LSTM hidden state h_t

From h_t, predict:
1. Next latent z_{t+1} ~ Σ π_i * N(μ_i, σ_i²)  [Mixture of 5 Gaussians]
2. Reward r_{t+1} ~ N(μ_r, σ_r²)  [Single Gaussian]
3. Terminal flag done_{t+1} ~ Bernoulli(p_done)
```

**MDN Output**:
```
For each Gaussian component i (i=1 to 5):
  - π_i: mixing coefficient (use softmax)
  - μ_i: mean vector (32-dim)
  - σ_i: std deviation vector (32-dim, use exp)
```

**Loss Function**:
```
L_MDN = -log p(z_{t+1} | z_t, a_t)
      = -log(Σ π_i * N(z_{t+1} | μ_i, σ_i²))

L_reward = -log N(r_{t+1} | μ_r, σ_r²)
L_done = BCE(done_{t+1}, p_done)

Total: L = L_MDN + L_reward + L_done
```

**Implementation Steps**:

1. **Create MDN-RNN class**:
```python
class MDNRNN(nn.Module):
    def __init__(self, latent_dim=32, action_dim=3, hidden_dim=256, num_mixtures=5):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_mixtures = num_mixtures
        self.latent_dim = latent_dim
        
        # TODO: LSTM that takes [z, a] as input
        self.lstm = nn.LSTM(latent_dim + action_dim, hidden_dim)
        
        # TODO: MDN outputs for next latent
        # Predict: π (mixing), μ (means), σ (stds) for each mixture
        
        # TODO: Output heads for reward and done
        
    def forward(self, z, action, hidden=None):
        # TODO: Concatenate z and action
        # TODO: Pass through LSTM
        # TODO: Predict mixture parameters, reward, done
        pass
    
    def mixture_loss(self, z_next, pi, mu, sigma):
        # TODO: Compute negative log likelihood of mixture
        # Use logsumexp for numerical stability
        pass
```

2. **Training on sequences**:
```python
def train_mdnrnn(mdnrnn, vae, env, episodes=1000):
    optimizer = torch.optim.Adam(mdnrnn.parameters(), lr=1e-3)
    
    for episode in range(episodes):
        # TODO: Collect trajectory from environment
        obs, actions, rewards, dones = collect_episode(env)
        
        # TODO: Encode observations with VAE
        with torch.no_grad():
            mu, _ = vae.encode(obs)
            z = mu  # Use mean for deterministic encoding
        
        # TODO: Train on sequences
        for t in range(len(z) - 1):
            z_t, a_t = z[t], actions[t]
            z_next, r_next, done_next = z[t+1], rewards[t], dones[t]
            
            # TODO: Forward pass
            pi, mu, sigma, r_pred, done_pred, hidden = mdnrnn(z_t, a_t)
            
            # TODO: Compute losses
            loss_z = mdnrnn.mixture_loss(z_next, pi, mu, sigma)
            loss_r = F.mse_loss(r_pred, r_next)
            loss_done = F.binary_cross_entropy(done_pred, done_next)
            
            loss = loss_z + loss_r + loss_done
            
            # TODO: Optimization step
```

### Component 3: Controller (CMA-ES)

**Purpose**: Learn a simple linear policy using evolution strategies.

**Architecture**:
```
Input: z_t (32-dim latent)
Output: a_t (3-dim action)

Controller: Linear transformation
  a_t = W * z_t + b
  
Parameters: W (3x32), b (3)
Total: 99 parameters
```

**Optimization**: Use CMA-ES (Covariance Matrix Adaptation Evolution Strategy)

**Implementation Steps**:

1. **Controller class**:
```python
class Controller(nn.Module):
    def __init__(self, latent_dim=32, action_dim=3):
        super().__init__()
        # TODO: Simple linear layer
        self.fc = nn.Linear(latent_dim, action_dim)
    
    def forward(self, z):
        # TODO: Output action
        return torch.tanh(self.fc(z))  # Assume actions in [-1, 1]
```

2. **CMA-ES optimization**:
```python
import cma

def optimize_controller(vae, mdnrnn, env, generations=100):
    # TODO: Initialize CMA-ES
    latent_dim, action_dim = 32, 3
    num_params = latent_dim * action_dim + action_dim
    
    es = cma.CMAEvolutionStrategy(num_params * [0], 0.5)
    
    for generation in range(generations):
        # TODO: Sample candidate solutions
        solutions = es.ask()
        
        # TODO: Evaluate each solution
        fitness = []
        for params in solutions:
            # Set controller parameters
            controller = params_to_controller(params)
            
            # Evaluate in environment
            reward = evaluate(controller, vae, mdnrnn, env)
            fitness.append(-reward)  # CMA-ES minimizes
        
        # TODO: Update distribution
        es.tell(solutions, fitness)
        
        print(f'Generation {generation}, Best: {-min(fitness):.2f}')
```

3. **Evaluation**:
```python
def evaluate(controller, vae, mdnrnn, env, episodes=3):
    total_reward = 0
    
    for _ in range(episodes):
        obs = env.reset()
        done = False
        episode_reward = 0
        
        while not done:
            # TODO: Encode observation
            with torch.no_grad():
                z, _ = vae.encode(obs)
                action = controller(z)
            
            # TODO: Step environment
            obs, reward, done, _ = env.step(action.numpy())
            episode_reward += reward
        
        total_reward += episode_reward
    
    return total_reward / episodes
```

---

## Paper 2: DreamerV1 (2020)

### Mathematical Foundation

**Key Idea**: Learn behaviors by imagining trajectories in a learned world model.

**RSSM (Recurrent State-Space Model)**:
```
Deterministic state: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
Stochastic state:    z_t ~ p(z_t | h_t)          [Prior]
                     z_t ~ q(z_t | h_t, o_t)     [Posterior]

Observations:        o_t ~ p(o_t | h_t, z_t)
Rewards:             r_t ~ p(r_t | h_t, z_t)
Continue:            c_t ~ p(c_t | h_t, z_t)
```

**Actor-Critic in Imagination**:
```
Actor:  π(a_t | h_t, z_t)
Critic: V(h_t, z_t)

Imagine trajectories: τ = (h_1, z_1, a_1, r_1, ..., h_H, z_H)
Compute returns: R_t = Σ_{k=t}^{H} γ^{k-t} r_k
```

### Component 1: RSSM (Recurrent State-Space Model)

**Architecture**:
```
Components:
1. Observation encoder: o_t → e_t
2. Recurrent model: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
3. Representation model (posterior): e_t, h_t → z_t
4. Transition model (prior): h_t → z_t
5. Observation decoder: h_t, z_t → ô_t
6. Reward predictor: h_t, z_t → r̂_t
7. Continue predictor: h_t, z_t → ĉ_t
```

**Implementation**:

```python
class RSSM(nn.Module):
    def __init__(self, action_dim, hidden_dim=200, state_dim=30, embed_dim=1024):
        super().__init__()
        
        # Deterministic state model (RNN)
        # TODO: GRU that takes [z, a] and outputs h
        self.rnn = nn.GRUCell(state_dim + action_dim, hidden_dim)
        
        # Prior: p(z | h)
        # TODO: Network that outputs mean and std
        self.prior = nn.Sequential(
            nn.Linear(hidden_dim, 200),
            nn.ReLU(),
            nn.Linear(200, 2 * state_dim)  # mean and std
        )
        
        # Posterior: q(z | h, e)
        # TODO: Network that takes [h, e] and outputs mean and std
        self.posterior = nn.Sequential(
            nn.Linear(hidden_dim + embed_dim, 200),
            nn.ReLU(),
            nn.Linear(200, 2 * state_dim)  # mean and std
        )
        
    def forward(self, embed, action, prev_state, prev_hidden):
        # TODO: Implement one-step transition
        # 1. Update deterministic state
        # 2. Compute prior p(z|h)
        # 3. Compute posterior q(z|h,e)
        # 4. Sample z from posterior
        # 5. Return new state and statistics
        pass
    
    def imagine(self, actor, start_state, start_hidden, horizon=15):
        # TODO: Imagine trajectory without observations
        # Use prior p(z|h) for imagination
        states, actions = [start_state], []
        hidden = start_hidden
        
        for t in range(horizon):
            # TODO: Get action from policy
            # TODO: Predict next state using prior
            pass
        
        return states, actions
```

### Component 2: Encoder and Decoder

**Encoder**:
```python
class Encoder(nn.Module):
    def __init__(self, obs_shape=(3, 64, 64), embed_dim=1024):
        super().__init__()
        # TODO: Convolutional encoder
        self.convs = nn.Sequential(
            nn.Conv2d(obs_shape[0], 32, 4, 2, 1),
            nn.ReLU(),
            nn.Conv2d(32, 64, 4, 2, 1),
            nn.ReLU(),
            nn.Conv2d(64, 128, 4, 2, 1),
            nn.ReLU(),
            nn.Conv2d(128, 256, 4, 2, 1),
            nn.ReLU(),
        )
        # TODO: Output layer
        
    def forward(self, obs):
        # TODO: Encode observation to embedding
        pass
```

**Decoder**:
```python
class Decoder(nn.Module):
    def __init__(self, state_dim=30, hidden_dim=200, obs_shape=(3, 64, 64)):
        super().__init__()
        # TODO: Initial projection
        self.fc = nn.Linear(state_dim + hidden_dim, 1024)
        
        # TODO: Convolutional decoder
        self.deconvs = nn.Sequential(
            nn.ConvTranspose2d(1024, 128, 5, 2),
            nn.ReLU(),
            nn.ConvTranspose2d(128, 64, 5, 2),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 6, 2),
            nn.ReLU(),
            nn.ConvTranspose2d(32, obs_shape[0], 6, 2),
        )
    
    def forward(self, state, hidden):
        # TODO: Reconstruct observation
        pass
```

### Component 3: Actor-Critic

**Actor (Policy Network)**:
```python
class Actor(nn.Module):
    def __init__(self, state_dim=30, hidden_dim=200, action_dim=6, hidden_size=400):
        super().__init__()
        
        # TODO: Policy network
        self.net = nn.Sequential(
            nn.Linear(state_dim + hidden_dim, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, action_dim),
        )
    
    def forward(self, state, hidden):
        # TODO: Output action distribution (Gaussian)
        # Return mean and std
        pass
    
    def sample(self, state, hidden):
        # TODO: Sample action from policy
        pass
```

**Critic (Value Network)**:
```python
class Critic(nn.Module):
    def __init__(self, state_dim=30, hidden_dim=200, hidden_size=400):
        super().__init__()
        
        # TODO: Value network
        self.net = nn.Sequential(
            nn.Linear(state_dim + hidden_dim, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )
    
    def forward(self, state, hidden):
        # TODO: Output state value
        pass
```

### Training Loop

```python
def train_dreamer(env, num_steps=1000000):
    # TODO: Initialize components
    encoder = Encoder()
    decoder = Decoder()
    rssm = RSSM()
    actor = Actor()
    critic = Critic()
    replay_buffer = ReplayBuffer()
    
    # TODO: Optimizers
    model_optimizer = torch.optim.Adam(
        list(encoder.parameters()) + 
        list(decoder.parameters()) + 
        list(rssm.parameters()), lr=6e-4
    )
    actor_optimizer = torch.optim.Adam(actor.parameters(), lr=8e-5)
    critic_optimizer = torch.optim.Adam(critic.parameters(), lr=8e-5)
    
    # TODO: Training loop
    for step in range(num_steps):
        # 1. Collect experience
        if step % 100 == 0:
            obs = env.reset()
            for _ in range(100):
                action = select_action(obs, encoder, rssm, actor)
                next_obs, reward, done, _ = env.step(action)
                replay_buffer.add(obs, action, reward, done)
                obs = next_obs if not done else env.reset()
        
        # 2. Train world model
        batch = replay_buffer.sample(batch_size=50, seq_length=50)
        model_loss = train_world_model(batch, encoder, decoder, rssm, model_optimizer)
        
        # 3. Train actor-critic in imagination
        actor_loss, critic_loss = train_actor_critic(
            batch, rssm, actor, critic, 
            actor_optimizer, critic_optimizer, horizon=15
        )
        
        if step % 1000 == 0:
            print(f'Step {step}, Model: {model_loss:.4f}, '
                  f'Actor: {actor_loss:.4f}, Critic: {critic_loss:.4f}')
```

---

## Paper 3: DreamerV2 (2021)

### Key Changes from DreamerV1

**1. Discrete Latent Representations**:
```
DreamerV1: z ~ N(μ, σ²)  [Continuous]
DreamerV2: z ~ Categorical(logits)  [Discrete, 32 categories × 32 classes]
```

**2. KL Balancing**:
```
Loss = 0.5 * KL(sg(posterior) || prior) + 0.5 * KL(posterior || sg(prior))

where sg = stop_gradient
```

**3. Symlog Predictions**:
```
For rewards and values:
  symlog(x) = sign(x) * log(|x| + 1)
  symexp(x) = sign(x) * (exp(|x|) - 1)
```

### Implementation: Discrete RSSM

```python
class DiscreteRSSM(nn.Module):
    def __init__(self, action_dim, hidden_dim=200, 
                 num_categories=32, num_classes=32):
        super().__init__()
        self.num_categories = num_categories
        self.num_classes = num_classes
        self.state_dim = num_categories * num_classes
        
        # Deterministic state (same as DreamerV1)
        self.rnn = nn.GRUCell(self.state_dim + action_dim, hidden_dim)
        
        # Prior: p(z | h)
        # TODO: Output logits for categorical distribution
        self.prior = nn.Sequential(
            nn.Linear(hidden_dim, 200),
            nn.ReLU(),
            nn.Linear(200, num_categories * num_classes)
        )
        
        # Posterior: q(z | h, e)
        # TODO: Output logits for categorical distribution
        self.posterior = nn.Sequential(
            nn.Linear(hidden_dim + embed_dim, 200),
            nn.ReLU(),
            nn.Linear(200, num_categories * num_classes)
        )
    
    def forward(self, embed, action, prev_state, prev_hidden):
        # TODO: Update deterministic state
        input = torch.cat([prev_state, action], dim=-1)
        hidden = self.rnn(input, prev_hidden)
        
        # TODO: Compute prior logits
        prior_logits = self.prior(hidden)
        prior_logits = prior_logits.reshape(-1, self.num_categories, self.num_classes)
        
        # TODO: Compute posterior logits
        posterior_logits = self.posterior(torch.cat([hidden, embed], dim=-1))
        posterior_logits = posterior_logits.reshape(-1, self.num_categories, self.num_classes)
        
        # TODO: Sample from posterior using Gumbel-Softmax
        state = self.sample_state(posterior_logits)
        
        return state, hidden, prior_logits, posterior_logits
    
    def sample_state(self, logits, training=True):
        # TODO: Implement Gumbel-Softmax for backprop
        # During training: use straight-through estimator
        # During inference: use argmax
        
        if training:
            # Gumbel-Softmax
            state = F.gumbel_softmax(logits, tau=1.0, hard=True)
        else:
            # One-hot from argmax
            state = F.one_hot(logits.argmax(dim=-1), self.num_classes)
        
        # Flatten categories and classes
        state = state.reshape(state.size(0), -1)
        return state.float()
    
    def kl_loss(self, prior_logits, posterior_logits, free_nats=1.0, balance=0.8):
        # TODO: Implement KL balancing
        prior_dist = torch.distributions.Categorical(logits=prior_logits)
        posterior_dist = torch.distributions.Categorical(logits=posterior_logits)
        
        # KL from posterior to prior
        kl_forward = torch.distributions.kl_divergence(posterior_dist, prior_dist)
        
        # KL from prior to posterior (with stop gradient)
        kl_backward = torch.distributions.kl_divergence(
            torch.distributions.Categorical(logits=posterior_logits.detach()),
            prior_dist
        )
        
        # Combine with balancing
        kl = balance * kl_forward + (1 - balance) * kl_backward
        
        # Apply free nats
        kl = torch.maximum(kl, torch.tensor(free_nats))
        
        return kl.mean()
```

### Symlog Transformations

```python
def symlog(x):
    """Symmetric logarithm transformation."""
    return torch.sign(x) * torch.log(torch.abs(x) + 1)

def symexp(x):
    """Inverse of symlog."""
    return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)

class RewardPredictor(nn.Module):
    def __init__(self, state_dim, hidden_dim):
        super().__init__()
        # TODO: Predict reward in symlog space
        self.net = nn.Sequential(
            nn.Linear(state_dim + hidden_dim, 400),
            nn.ReLU(),
            nn.Linear(400, 400),
            nn.ReLU(),
            nn.Linear(400, 1)
        )
    
    def forward(self, state, hidden):
        # TODO: Predict symlog(reward)
        return self.net(torch.cat([state, hidden], dim=-1))
    
    def loss(self, pred, target):
        # TODO: MSE in symlog space
        target_symlog = symlog(target)
        return F.mse_loss(pred, target_symlog)
```

---

## Paper 4: DreamerV3 (2023)

### Key Simplifications

**1. Unified Predictions**: All predictions use symlog encoding
**2. Robust Hyperparameters**: Single set works across domains
**3. Simplified Architecture**: Fewer components

### Implementation Highlights

```python
class WorldModel(nn.Module):
    """Simplified DreamerV3 world model."""
    
    def __init__(self, obs_shape, action_dim):
        super().__init__()
        
        # TODO: All components use same architecture principles
        self.encoder = self.build_mlp([obs_shape, 512, 512, 1024])
        self.dynamics = DiscreteRSSM(...)  # From DreamerV2
        self.decoder = self.build_mlp([1024, 512, 512, obs_shape])
        
        # All predictions use symlog
        self.reward_head = self.build_mlp([1024, 512, 1])
        self.continue_head = self.build_mlp([1024, 512, 1])
    
    def build_mlp(self, sizes):
        """Build MLP with consistent architecture."""
        layers = []
        for i in range(len(sizes) - 1):
            layers.append(nn.Linear(sizes[i], sizes[i+1]))
            if i < len(sizes) - 2:
                layers.append(nn.LayerNorm(sizes[i+1]))
                layers.append(nn.ReLU())
        return nn.Sequential(*layers)
    
    def loss(self, observations, actions, rewards):
        # TODO: Unified loss computation
        # All predictions in symlog space
        pass
```

**Free Bits Implementation**:
```python
def free_bits_kl(kl, free_nats=1.0):
    """Allow some KL without penalty."""
    return torch.maximum(kl, torch.tensor(free_nats))
```

---

## Paper 5: IRIS (2023)

### Discrete Tokenization

**VQ-VAE (Vector Quantized VAE)**:
```
Encoder: obs → continuous embedding e
Quantization: e → discrete token (nearest codebook entry)
Decoder: token → reconstructed obs

Codebook: K vectors of dimension D
```

**Implementation**:

```python
class VectorQuantizer(nn.Module):
    def __init__(self, num_embeddings=512, embedding_dim=64):
        super().__init__()
        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        
        # Codebook
        self.embedding = nn.Embedding(num_embeddings, embedding_dim)
        self.embedding.weight.data.uniform_(-1/num_embeddings, 1/num_embeddings)
    
    def forward(self, z):
        # TODO: Quantize continuous z to discrete tokens
        
        # 1. Flatten spatial dimensions
        z_flattened = z.reshape(-1, self.embedding_dim)
        
        # 2. Find nearest codebook entries
        distances = torch.cdist(z_flattened, self.embedding.weight)
        indices = distances.argmin(dim=-1)
        
        # 3. Look up codebook vectors
        z_q = self.embedding(indices)
        
        # 4. Straight-through estimator
        z_q = z + (z_q - z).detach()
        
        # 5. Reshape back
        z_q = z_q.reshape(z.shape)
        
        return z_q, indices

class VQVAE(nn.Module):
    def __init__(self, obs_shape, num_embeddings=512, embedding_dim=64):
        super().__init__()
        self.encoder = Encoder(obs_shape, embedding_dim)
        self.vq = VectorQuantizer(num_embeddings, embedding_dim)
        self.decoder = Decoder(embedding_dim, obs_shape)
    
    def forward(self, obs):
        # TODO: Encode, quantize, decode
        z = self.encoder(obs)
        z_q, indices = self.vq(z)
        recon = self.decoder(z_q)
        return recon, indices
```

### Transformer World Model

```python
class TransformerWorldModel(nn.Module):
    def __init__(self, vocab_size=512, d_model=512, nhead=8, num_layers=6):
        super().__init__()
        
        # Token embeddings
        self.obs_embedding = nn.Embedding(vocab_size, d_model)
        self.action_embedding = nn.Embedding(action_vocab_size, d_model)
        self.reward_embedding = nn.Embedding(reward_vocab_size, d_model)
        
        # Position encoding
        self.pos_embedding = nn.Parameter(torch.randn(1, max_len, d_model))
        
        # Transformer
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Prediction heads
        self.obs_head = nn.Linear(d_model, vocab_size)
        self.reward_head = nn.Linear(d_model, reward_vocab_size)
    
    def forward(self, obs_tokens, action_tokens, reward_tokens):
        # TODO: Embed all tokens
        # TODO: Create sequence [obs_0, act_0, rew_0, obs_1, act_1, rew_1, ...]
        # TODO: Add positional encoding
        # TODO: Apply transformer with causal mask
        # TODO: Predict next tokens
        pass
    
    def generate(self, start_tokens, horizon=15):
        # TODO: Autoregressively generate trajectory
        pass
```

---

## Testing and Validation

### Unit Tests

```python
def test_vae():
    """Test VAE reconstruction."""
    vae = VAE(latent_dim=32)
    x = torch.randn(4, 3, 96, 96)
    recon, mu, logvar = vae(x)
    assert recon.shape == x.shape
    assert mu.shape == (4, 32)
    print("✓ VAE test passed")

def test_rssm():
    """Test RSSM forward pass."""
    rssm = RSSM(action_dim=3)
    embed = torch.randn(4, 1024)
    action = torch.randn(4, 3)
    state = torch.randn(4, 30)
    hidden = torch.randn(4, 200)
    
    new_state, new_hidden, prior, posterior = rssm(embed, action, state, hidden)
    assert new_state.shape == state.shape
    print("✓ RSSM test passed")

def test_imagination():
    """Test imagined rollouts."""
    rssm = RSSM(action_dim=3)
    actor = Actor(action_dim=3)
    
    state = torch.randn(1, 30)
    hidden = torch.randn(1, 200)
    
    states, actions = rssm.imagine(actor, state, hidden, horizon=15)
    assert len(states) == 16  # initial + 15 imagined
    assert len(actions) == 15
    print("✓ Imagination test passed")
```

### Integration Tests

```python
def test_world_model_training():
    """Test world model can overfit single batch."""
    # TODO: Create simple dataset
    # TODO: Train for many iterations
    # TODO: Verify loss decreases
    pass

def test_actor_critic():
    """Test actor-critic can learn simple task."""
    # TODO: Create simple MDP
    # TODO: Train with imagined rollouts
    # TODO: Verify policy improves
    pass
```

---

## Common Issues and Solutions

### Issue 1: VAE Produces Blurry Reconstructions

**Problem**: Reconstructions lack detail.

**Solutions**:
1. Decrease β in KL term (try 0.1)
2. Use perceptual loss instead of MSE
3. Increase latent dimension
4. Use more powerful decoder

### Issue 2: RNN Predictions Diverge

**Problem**: Multi-step predictions explode or collapse.

**Solutions**:
1. Add gradient clipping (max norm 100)
2. Use layer normalization in RNN
3. Reduce learning rate
4. Add regularization on predictions

### Issue 3: Actor Doesn't Improve

**Problem**: Policy fails to learn.

**Solutions**:
1. Check world model accuracy first
2. Increase imagination horizon
3. Verify gradient flow through imagination
4. Adjust actor learning rate
5. Add entropy regularization

### Issue 4: Discrete Representations Collapse

**Problem**: VQ-VAE uses only few codebook entries.

**Solutions**:
1. Use codebook reset (reinitialize unused entries)
2. Increase commitment loss weight
3. Use exponential moving average for codebook
4. Try different codebook sizes

---

## Performance Optimization

### Training Speed

1. **Use Mixed Precision**:
```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

with autocast():
    loss = compute_loss()

scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

2. **Parallel Data Loading**:
```python
dataloader = DataLoader(
    dataset,
    batch_size=50,
    num_workers=4,
    pin_memory=True
)
```

3. **Gradient Accumulation**:
```python
for i, batch in enumerate(dataloader):
    loss = compute_loss(batch) / accumulation_steps
    loss.backward()
    
    if (i + 1) % accumulation_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

### Memory Optimization

1. **Gradient Checkpointing**:
```python
from torch.utils.checkpoint import checkpoint

def forward_with_checkpointing(x):
    return checkpoint(expensive_module, x)
```

2. **Efficient Replay Buffer**:
```python
# Store as uint8 to save 4x memory
buffer = np.zeros((capacity, *obs_shape), dtype=np.uint8)
```

---

## Next Steps

After completing all implementations:

1. **Benchmarking**: Compare all 5 approaches on same tasks
2. **Ablations**: Test which components matter most
3. **Extensions**: Add your own improvements
4. **Applications**: Apply to new domains
5. **Research**: Explore open problems

## Conclusion

You now have complete guides for implementing all 5 key world model papers. Start with World Models, progress through the Dreamer series, and finish with IRIS. Each builds on previous concepts while introducing new ideas.

Happy learning!

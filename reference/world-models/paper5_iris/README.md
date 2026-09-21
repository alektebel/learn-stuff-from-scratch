# IRIS Implementation Templates

Educational templates for implementing IRIS (Transformers are Sample Efficient World Models) from scratch.

## Paper Reference

**Transformers are Sample Efficient World Models**  
Vincent Micheli, Eloi Alonso, François Fleuret  
NeurIPS 2023  
[Paper](https://arxiv.org/abs/2209.00588) | [Code](https://github.com/eloialonso/iris)

## Overview

IRIS replaces RNNs with Transformers for world modeling and policy learning. This provides better sample efficiency, stronger representations, and improved long-term credit assignment.

### Key Innovations

1. **VQ-VAE Tokenization**: Discrete tokens enable autoregressive modeling
2. **Transformer World Model**: Parallel training, long-term dependencies
3. **Transformer Policy**: Can attend to full observation history
4. **Autoregressive Training**: Predict next observation and reward tokens

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VQ-VAE TOKENIZER                             │
│                                                                  │
│  Image (64×64) → Encoder → Quantize → Decoder → Reconstructed   │
│                              ↓                                   │
│                      Token indices (16×16)                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                TRANSFORMER WORLD MODEL                           │
│                                                                  │
│  Input: [obs_tokens_1, act_1, obs_tokens_2, act_2, ...]         │
│     ↓                                                            │
│  Causal Transformer                                              │
│     ↓                                                            │
│  Output: Next obs_tokens, rewards                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                TRANSFORMER POLICY                                │
│                                                                  │
│  Input: obs_tokens history                                       │
│     ↓                                                            │
│  Causal Transformer                                              │
│     ↓                                                            │
│  Output: Action distribution                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Files

### 1. `tokenizer.py` - VQ-VAE Tokenizer

Discretizes observations into tokens for autoregressive modeling.

**Components:**
- `VectorQuantizer`: Nearest-neighbor quantization with straight-through gradients
- `Encoder`: CNN that downsamples 64×64 → 16×16
- `Decoder`: CNN that upsamples 16×16 → 64×64
- `VQVAETokenizer`: Complete tokenization pipeline

**Key Features:**
- Learns discrete codebook (e.g., 4096 codes)
- Each image → 16×16 = 256 tokens
- Enables autoregressive prediction
- Straight-through gradient estimator

### 2. `transformer.py` - World Model Transformer

Autoregressive transformer for predicting next observations and rewards.

**Components:**
- `CausalSelfAttention`: Masked attention for autoregression
- `TransformerBlock`: Standard transformer layer
- `WorldModelTransformer`: Full world model

**Key Features:**
- Processes interleaved observation and action tokens
- Causal masking ensures autoregressive property
- Parallel training (unlike RNNs)
- Can model long-term dependencies

### 3. `actor_critic.py` - Transformer Policy

Transformer-based actor and critic networks.

**Components:**
- `TransformerActor`: Processes observation history → actions
- `TransformerCritic`: Processes observation history → values
- Loss computation functions

**Key Features:**
- Can attend to full observation history
- Better credit assignment than RNNs
- Parallel training
- Scales to long contexts

### 4. `train.py` - Complete Training Loop

Integrates all components for end-to-end training.

**Features:**
- Three-stage training:
  1. Train tokenizer
  2. Train world model
  3. Train policy
- Can also train jointly
- Imagination-based policy learning

## Implementation Order

### Phase 1: VQ-VAE Tokenizer
1. **tokenizer.py** - Implement discrete tokenization
   - `VectorQuantizer` with codebook
   - `Encoder` and `Decoder` CNNs
   - Test reconstruction quality
   - Verify codebook usage

### Phase 2: Transformer World Model
2. **transformer.py** - Build transformer
   - `CausalSelfAttention` with masking
   - `TransformerBlock` 
   - `WorldModelTransformer`
   - Test autoregressive prediction

### Phase 3: Transformer Policy
3. **actor_critic.py** - Implement policy
   - `TransformerActor`
   - `TransformerCritic`
   - Test with dummy tokens

### Phase 4: Integration
4. **train.py** - Put it all together
   - `IRIS` class
   - Training loops for each component
   - Imagination and policy learning
   - Action selection

## Key Concepts

### Vector Quantization

Maps continuous embeddings to discrete codes:

```python
# Find nearest codebook vector
distances = ||z - e_i||^2
index = argmin(distances)
z_q = codebook[index]

# Straight-through gradient
z_q = z + (z_q - z).detach()
```

**Benefits:**
- Enables autoregressive modeling
- Reduces dimensionality
- Learns useful discrete representations

### Autoregressive World Modeling

Predict sequence element-by-element:

```
p(obs_1, ..., obs_T | actions) = ∏_t p(obs_t | obs_<t, actions_≤t)
```

**Training:**
- Use teacher forcing (true previous observations)
- Maximize likelihood of next observation
- Also predict rewards

**Inference:**
- Sample from predicted distribution
- Feed back as input for next step

### Causal Attention

Position i can only attend to positions ≤ i:

```python
# Compute attention scores
scores = Q @ K.T / sqrt(d_k)

# Apply causal mask
mask = torch.tril(torch.ones(L, L))
scores = scores.masked_fill(mask == 0, -inf)

# Softmax and weighted sum
attn = softmax(scores)
output = attn @ V
```

### Transformer vs RNN

| Aspect | RNN (Dreamer) | Transformer (IRIS) |
|--------|---------------|-------------------|
| **Training** | Sequential | Parallel |
| **Dependencies** | Limited (gradient issues) | Long-range |
| **Computation** | O(T) sequential | O(T²) parallel |
| **Memory** | Fixed hidden state | Full context |
| **Scalability** | Limited | Scales with compute |

## Hyperparameters

Default hyperparameters:

```python
# Tokenizer
num_embeddings = 4096        # Codebook size
embedding_dim = 256          # Code dimension
commitment_cost = 0.25       # VQ loss weight

# World model
model_embed_dim = 512        # Transformer embedding
model_layers = 6             # Transformer depth
model_heads = 8              # Attention heads
max_seq_len = 512            # Maximum context

# Policy
policy_embed_dim = 256       # Policy transformer embedding
policy_layers = 4            # Policy transformer depth
policy_heads = 4             # Policy attention heads

# Training
tokenizer_lr = 3e-4          # Tokenizer learning rate
model_lr = 1e-4              # World model learning rate
policy_lr = 3e-4             # Policy learning rate
batch_size = 16              # Sequences per batch
seq_len = 64                 # Sequence length

# RL
gamma = 0.99                 # Discount factor
lambda_ = 0.95               # Lambda for returns
imagination_horizon = 15     # Steps to imagine
```

## Testing

Test each component:

```bash
cd world-models/paper5_iris

# Test tokenizer
python tokenizer.py

# Test transformer
python transformer.py

# Test policy
python actor_critic.py

# Test integration
python train.py
```

## Key Differences from Dreamer

| Aspect | Dreamer (RNN) | IRIS (Transformer) |
|--------|---------------|-------------------|
| **Observations** | Continuous latents | Discrete tokens |
| **World model** | RSSM (GRU) | Transformer |
| **Training** | Sequential | Parallel |
| **Context** | Single hidden state | Full history |
| **Sample efficiency** | Good | Better |
| **Long-term planning** | Limited | Strong |
| **Computation** | Lower | Higher |
| **Parallelization** | None | High |

## Common Issues

### Codebook Collapse
- **Symptom**: Only few codes used
- **Solution**: Increase commitment cost, add codebook loss, restart training

### Poor Tokenization
- **Symptom**: Bad reconstructions
- **Solution**: Train tokenizer longer, increase codebook size, check architecture

### Transformer Overfitting
- **Symptom**: Perfect training loss, poor test performance
- **Solution**: Add dropout, reduce model size, use weight decay

### Slow Convergence
- **Symptom**: Training takes very long
- **Solution**: Check learning rates, reduce sequence length, increase batch size

### Memory Issues
- **Symptom**: OOM errors
- **Solution**: Reduce batch size, reduce sequence length, use gradient checkpointing

## Debugging Tips

1. **Visualize Tokens**: Plot codebook usage distribution
2. **Check Reconstructions**: Save tokenizer output images
3. **Monitor Attention**: Visualize attention patterns
4. **Test Imagination**: Generate imagined trajectories
5. **Ablate Components**: Test world model without policy, etc.

## Performance Expectations

On Atari with 100k environment steps:
- **Dreamer (RNN)**: ~50-100% human performance
- **IRIS (Transformer)**: ~100-150% human performance
- Better sample efficiency
- Stronger representations
- Improved long-term planning

## Advantages of IRIS

**Over RNN-based methods:**
1. **Better sample efficiency**: Learns faster from less data
2. **Stronger representations**: Transformer > RNN for modeling
3. **Long-term dependencies**: No gradient vanishing
4. **Parallel training**: Much faster
5. **Scalability**: Can use larger models

**Trade-offs:**
- Higher computational cost (O(T²) vs O(T))
- More memory usage
- Requires more tuning

## Resources

- **Paper**: https://arxiv.org/abs/2209.00588
- **Official code**: https://github.com/eloialonso/iris
- **VQ-VAE**: https://arxiv.org/abs/1711.00937
- **Transformers**: https://arxiv.org/abs/1706.03762

## Extensions

Once you have a working implementation:

1. **Hierarchical Tokenization**: Multi-scale tokens
2. **Latent Transformers**: Transformer on continuous latents
3. **Masked Autoencoding**: BERT-style pre-training
4. **Multi-modal**: Combine vision and language
5. **Retrieval-Augmented**: Add memory retrieval

## Comparison Across Papers

| Method | Paper | State | World Model | Sample Efficiency |
|--------|-------|-------|-------------|------------------|
| World Models | 1 | VAE + RNN | Separate training | Moderate |
| DreamerV1 | 2 | Continuous RSSM | End-to-end | Good |
| DreamerV2 | 3 | Discrete RSSM | End-to-end | Better |
| DreamerV3 | 4 | Discrete RSSM | Unified | Best (RNN) |
| **IRIS** | **5** | **Discrete tokens** | **Transformer** | **Best overall** |

## Next Steps

After completing IRIS:
- Compare sample efficiency across all 5 papers
- Benchmark on same environments
- Study learned representations
- Experiment with hybrid models (RNN + Transformer)
- Apply to your own domains

---

**Congratulations!** You've now implemented the full evolution of world models from the original paper through to state-of-the-art transformer-based methods. 🎉

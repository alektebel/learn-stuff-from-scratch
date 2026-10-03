"""
Transformer-based World Model for IRIS

IRIS replaces RNNs with Transformers for world modeling. This provides:
- Better long-term dependencies
- Parallel training
- Stronger representation learning

Architecture:
- Token sequences: [obs_1, act_1, obs_2, act_2, ...]
- Causal transformer processes sequences autoregressively
- Predicts next observation and reward tokens

Paper: Transformers are Sample Efficient World Models (Robine et al., 2023)
Section 3.2: World Model Transformer
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class CausalSelfAttention(nn.Module):
    """
    Causal self-attention for autoregressive modeling.
    
    Ensures that position i can only attend to positions ≤ i.
    
    Args:
        embed_dim: Embedding dimension
        num_heads: Number of attention heads
        dropout: Dropout probability (default: 0.1)
    """
    
    def __init__(self, embed_dim, num_heads, dropout=0.1):
        super().__init__()
        assert embed_dim % num_heads == 0
        
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.scale = self.head_dim ** -0.5
        
        # TODO: Implement causal attention
        # Guidelines:
        # - QKV projection: single linear layer for efficiency
        # - Output projection
        # - Dropout for regularization
        # - Causal mask (register as buffer, not parameter)
        #
        # self.qkv = nn.Linear(embed_dim, 3 * embed_dim)
        # self.proj = nn.Linear(embed_dim, embed_dim)
        # self.attn_dropout = nn.Dropout(dropout)
        # self.proj_dropout = nn.Dropout(dropout)
        
        pass  # Remove when implementing
    
    def forward(self, x):
        """
        Apply causal self-attention.
        
        Args:
            x: Input (batch, seq_len, embed_dim)
            
        Returns:
            out: Output (batch, seq_len, embed_dim)
        """
        # TODO: Implement attention forward
        # Guidelines:
        # 1. Compute QKV
        # 2. Split into heads
        # 3. Compute attention scores with causal mask
        # 4. Apply softmax and dropout
        # 5. Compute weighted values
        # 6. Concatenate heads and project
        pass


class TransformerBlock(nn.Module):
    """
    Transformer block with causal self-attention and feedforward.
    
    Standard architecture:
    - LayerNorm → Attention → Residual
    - LayerNorm → FFN → Residual
    
    Args:
        embed_dim: Embedding dimension
        num_heads: Number of attention heads
        mlp_ratio: Expansion ratio for FFN (default: 4)
        dropout: Dropout probability (default: 0.1)
    """
    
    def __init__(
        self,
        embed_dim,
        num_heads,
        mlp_ratio=4,
        dropout=0.1
    ):
        super().__init__()
        
        # TODO: Implement transformer block
        # Guidelines:
        # - Pre-normalization (LayerNorm before attention and FFN)
        # - Causal self-attention
        # - Feedforward network (2-layer MLP with GELU)
        # - Residual connections
        #
        # self.ln1 = nn.LayerNorm(embed_dim)
        # self.attn = CausalSelfAttention(embed_dim, num_heads, dropout)
        # self.ln2 = nn.LayerNorm(embed_dim)
        # self.mlp = nn.Sequential(
        #     nn.Linear(embed_dim, mlp_ratio * embed_dim),
        #     nn.GELU(),
        #     nn.Linear(mlp_ratio * embed_dim, embed_dim),
        #     nn.Dropout(dropout)
        # )
        
        pass  # Remove when implementing
    
    def forward(self, x):
        """
        Apply transformer block.
        
        Args:
            x: Input (batch, seq_len, embed_dim)
            
        Returns:
            out: Output (batch, seq_len, embed_dim)
        """
        # TODO: Implement forward
        # Guidelines:
        # 1. Attention path: x = x + self.attn(self.ln1(x))
        # 2. FFN path: x = x + self.mlp(self.ln2(x))
        # 3. Return x
        pass


class WorldModelTransformer(nn.Module):
    """
    Transformer-based world model for IRIS.
    
    Processes sequences of observation and action tokens autoregressively
    to predict next observations and rewards.
    
    Args:
        num_obs_tokens: Size of observation token vocabulary (default: 4096)
        num_actions: Dimension of action space
        embed_dim: Embedding dimension (default: 512)
        num_layers: Number of transformer layers (default: 6)
        num_heads: Number of attention heads (default: 8)
        max_seq_len: Maximum sequence length (default: 512)
        dropout: Dropout probability (default: 0.1)
    """
    
    def __init__(
        self,
        num_obs_tokens=4096,
        num_actions=6,
        embed_dim=512,
        num_layers=6,
        num_heads=8,
        max_seq_len=512,
        dropout=0.1
    ):
        super().__init__()
        self.num_obs_tokens = num_obs_tokens
        self.num_actions = num_actions
        self.embed_dim = embed_dim
        self.max_seq_len = max_seq_len
        
        # TODO: Implement world model transformer
        # Guidelines:
        # 1. Token embeddings:
        #    - Observation tokens: nn.Embedding(num_obs_tokens, embed_dim)
        #    - Action embeddings: nn.Linear(num_actions, embed_dim)
        # 
        # 2. Positional encoding:
        #    - Learnable positional embeddings
        #    - nn.Parameter(torch.zeros(1, max_seq_len, embed_dim))
        # 
        # 3. Transformer blocks:
        #    - Stack of TransformerBlock modules
        #    - nn.ModuleList([TransformerBlock(...) for _ in range(num_layers)])
        # 
        # 4. Output heads:
        #    - Observation prediction: nn.Linear(embed_dim, num_obs_tokens)
        #    - Reward prediction: nn.Linear(embed_dim, 1)
        # 
        # 5. Dropout and LayerNorm
        #
        # Paper reference: Section 3.2, Transformer architecture
        pass
    
    def embed_sequence(self, obs_tokens, actions):
        """
        Embed observation and action tokens into sequence.
        
        Args:
            obs_tokens: Observation token indices (batch, seq_len, 16, 16)
            actions: Actions (batch, seq_len, num_actions)
            
        Returns:
            embeddings: Embedded sequence (batch, 2*seq_len, embed_dim)
        """
        # TODO: Implement sequence embedding
        # Guidelines:
        # 1. Embed observations:
        #    obs_emb = self.obs_embedding(obs_tokens)
        #    Flatten spatial: (batch, seq_len, 256, embed_dim) → (batch, seq_len*256, embed_dim)
        # 
        # 2. Embed actions:
        #    act_emb = self.action_embedding(actions)
        #    (batch, seq_len, embed_dim)
        # 
        # 3. Interleave observations and actions:
        #    [obs_1, act_1, obs_2, act_2, ...]
        # 
        # 4. Add positional encodings
        # 
        # 5. Return embedded sequence
        pass
    
    def forward(self, obs_tokens, actions):
        """
        Predict next observations and rewards.
        
        Args:
            obs_tokens: Observation tokens (batch, seq_len, 16, 16)
            actions: Actions (batch, seq_len, num_actions)
            
        Returns:
            obs_logits: Next observation predictions (batch, seq_len, 16, 16, num_obs_tokens)
            reward_preds: Reward predictions (batch, seq_len)
        """
        # TODO: Implement forward pass
        # Guidelines:
        # 1. Embed sequence
        # 2. Pass through transformer blocks
        # 3. Apply output heads
        # 4. Reshape to appropriate dimensions
        # 5. Return predictions
        pass
    
    def imagine(self, initial_obs_tokens, policy, horizon):
        """
        Imagine future trajectory autoregressively.
        
        Args:
            initial_obs_tokens: Starting observation (batch, 16, 16)
            policy: Policy network
            horizon: Number of steps to imagine
            
        Returns:
            imagined_obs: Sequence of imagined observations
            imagined_actions: Sequence of actions
            imagined_rewards: Sequence of rewards
        """
        # TODO: Implement imagination
        # Guidelines:
        # 1. Initialize sequence with initial observation
        # 2. For each step:
        #    a. Get action from policy
        #    b. Predict next observation tokens
        #    c. Sample from predicted distribution
        #    d. Predict reward
        #    e. Append to sequence
        # 3. Return imagined trajectory
        pass


def test_transformer():
    """Test transformer world model."""
    print("Testing Transformer World Model...")
    
    # Hyperparameters
    batch_size = 2
    seq_len = 10
    num_obs_tokens = 512  # Smaller for testing
    num_actions = 6
    embed_dim = 128
    num_layers = 2
    
    # Create model
    model = WorldModelTransformer(
        num_obs_tokens=num_obs_tokens,
        num_actions=num_actions,
        embed_dim=embed_dim,
        num_layers=num_layers,
        num_heads=4
    )
    
    print(f"✓ Created transformer world model")
    print(f"  - Embedding dim: {embed_dim}")
    print(f"  - Num layers: {num_layers}")
    print(f"  - Num heads: 4")
    
    # Test forward pass
    obs_tokens = torch.randint(0, num_obs_tokens, (batch_size, seq_len, 16, 16))
    actions = torch.randn(batch_size, seq_len, num_actions)
    
    obs_logits, reward_preds = model(obs_tokens, actions)
    print(f"✓ Forward pass works")
    print(f"  - Obs logits: {obs_logits.shape}")
    print(f"  - Reward preds: {reward_preds.shape}")
    
    # Test imagination
    initial_obs = torch.randint(0, num_obs_tokens, (batch_size, 16, 16))
    
    class DummyPolicy:
        def __call__(self, obs_tokens):
            return torch.randn(obs_tokens.shape[0], num_actions)
    
    policy = DummyPolicy()
    horizon = 5
    
    imag_obs, imag_actions, imag_rewards = model.imagine(initial_obs, policy, horizon)
    print(f"✓ Imagination works")
    print(f"  - Imagined {horizon} steps")
    
    # Test gradients
    loss = obs_logits.sum() + reward_preds.sum()
    loss.backward()
    print(f"✓ Gradients flow through transformer")
    
    print("\n✅ All transformer tests passed!")
    print("\nKey advantages over RNNs:")
    print("  - Parallel training")
    print("  - Better long-term dependencies")
    print("  - Stronger representations")
    print("  - State-of-the-art in language modeling")


if __name__ == "__main__":
    test_transformer()

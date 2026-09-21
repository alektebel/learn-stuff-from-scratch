"""
Transformer — the block, and the model. Complete Solution.

A GPT is: embed tokens, add position, run N identical blocks, project back to
the vocabulary. Each block is attention, then a feed-forward network, each
wrapped in a residual connection and a layer norm.

Everything below is a decision with a measurable consequence.

DESIGN DECISION — residual connections. Why?
  The famous answer is "vanishing gradients", which is true and vague. The
  precise statement: with `y = x + f(x)`, the derivative dy/dx is `1 + f'(x)`.
  The 1 is a path along which the gradient reaches every earlier layer
  UNCHANGED, however small f' becomes. Without it the gradient is a product of
  N Jacobians and it decays geometrically in depth. Section 2 measures that
  decay at 12 layers with and without the skip.

DESIGN DECISION — layer norm BEFORE the sublayer, or after?
  The original paper put it after: `x = norm(x + attn(x))`. Every model since
  about 2019 puts it before: `x = x + attn(norm(x))`.
  CHOSEN: pre-norm. The difference is that in post-norm the residual path
  passes THROUGH a normalisation, so the clean gradient highway is broken at
  every layer; in pre-norm the residual stream is untouched from input to
  output. Post-norm transformers need a learning-rate warmup to train at all
  and get unstable past a few dozen layers; pre-norm ones do not. One line, and
  it is the difference between "trains" and "needs a recipe".

DESIGN DECISION — how does the model know what order the tokens are in?
  It does not. Attention is a weighted sum, and a sum is PERMUTATION
  INVARIANT: shuffle the input rows and the output rows shuffle with them, with
  identical values. A transformer with no positional information cannot tell
  "dog bites man" from "man bites dog".
  CHOSEN: a learned positional embedding added to the token embedding. Section
  3 removes it and shows the outputs coming back identical under a shuffle,
  which is the proof rather than the claim.
  REJECTED here: sinusoidal (extrapolates past the trained length, but is worse
  in practice) and rotary/RoPE (what modern models use, applied inside
  attention rather than added at the input — the best extension in this file).

DESIGN DECISION — tie the input embedding and the output projection?
  They are both `vocab x d_model` matrices and they mean related things: one
  maps a token to a vector, the other scores a vector against every token.
  CHOSEN: offer it, and measure it. On a small model the embedding tables are
  most of the parameters, so tying can halve the model — and section 4 shows
  exactly what fraction.

Learning Path:
1. LayerNorm and FeedForward
2. Block — pre-norm, residual around each sublayer
3. GPT — embeddings, positions, blocks, final norm, output head
4. GPT.loss — next-token prediction over every position at once
5. Measure: the residual gradient highway, permutation-equivariance without
   positions, and what weight tying saves
"""

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

from engine import (Linear, Module, Tensor, causal_mask, embedding,
                    layer_norm, masked_softmax)
from attention import MultiHeadAttention


class LayerNorm(Module):
    def __init__(self, width: int):
        self.gain = Tensor([1.0] * width, (1, width), requires_grad=True)
        self.bias = Tensor([0.0] * width, (1, width), requires_grad=True)

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError


class FeedForward(Module):
    """d_model -> 4*d_model -> d_model.

    The 4x is not principled; it is what the original paper used and what
    everyone kept. What matters is that it is WIDER in the middle: the block's
    only per-token nonlinear processing happens here, and roughly two thirds of
    a transformer's parameters live in these two matrices rather than in
    attention. "Attention is all you need" names the interesting part, not the
    big part.
    """

    def __init__(self, d_model: int, multiplier: int = 4,
                 rng: Optional[random.Random] = None):
        rng = rng or random.Random(0)
        hidden = d_model * multiplier
        self.up = Linear(d_model, hidden, activation="relu", rng=rng)
        self.down = Linear(hidden, d_model, activation="linear", rng=rng)

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError


class Block(Module):
    """Pre-norm attention, then pre-norm feed-forward, both residual."""

    def __init__(self, d_model: int, heads: int, pre_norm: bool = True,
                 rng: Optional[random.Random] = None):
        rng = rng or random.Random(0)
        self.pre_norm = pre_norm
        self.norm1 = LayerNorm(d_model)
        self.attention = MultiHeadAttention(d_model, heads, rng=rng)
        self.norm2 = LayerNorm(d_model)
        self.feed_forward = FeedForward(d_model, rng=rng)

    def forward(self, x: Tensor, mask: Optional[List[List[bool]]] = None
                ) -> Tensor:
        raise NotImplementedError


class GPT(Module):
    """A decoder-only transformer, small enough to train in pure Python."""

    def __init__(self, vocab_size: int, d_model: int = 32, heads: int = 2,
                 layers: int = 2, block_size: int = 16,
                 positional: bool = True, tie_weights: bool = False,
                 pre_norm: bool = True, seed: int = 0):
        rng = random.Random(seed)
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.block_size = block_size
        self.positional = positional
        self.tie_weights = tie_weights

        scale = 1.0 / math.sqrt(d_model)
        self.token_embedding = Tensor.randn(vocab_size, d_model, scale=scale,
                                            requires_grad=True, rng=rng)
        self.position_embedding = Tensor.randn(block_size, d_model, scale=scale,
                                               requires_grad=True, rng=rng)
        self.blocks = [Block(d_model, heads, pre_norm, rng)
                       for _ in range(layers)]
        self.final_norm = LayerNorm(d_model)
        self.head = (None if tie_weights
                     else Linear(d_model, vocab_size, activation="linear",
                                 bias=False, rng=rng))

    def forward(self, ids: Sequence[int]) -> Tensor:
        raise NotImplementedError

    def loss(self, ids: Sequence[int]) -> Tensor:
        """Next-token prediction: predict ids[1:] from ids[:-1].

        Every position is a training example, in one forward pass. A sequence
        of 16 tokens gives 15 supervised predictions — which is why language
        models are so sample-efficient per unit of text, and why the causal
        mask has to be exactly right: one position seeing one token too far and
        every example after it is free.
        """
        raise NotImplementedError

    def parameters(self) -> List[Tensor]:
        raise NotImplementedError

    def zero_grad(self) -> None:
        for parameter in self.parameters():
            parameter.zero_grad()

    def num_parameters(self) -> int:
        return sum(len(p.data) for p in self.parameters())

    def parameter_breakdown(self) -> Dict[str, int]:
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. The parameter breakdown by component. Note where the weights actually
       are — the feed-forward is bigger than the attention.
    2. Gradient norm reaching the input at depth 2, 6 and 12, with and without
       residual connections. y = x + f(x) has derivative 1 + f'(x), and the 1
       is a path the gradient reaches every layer along unchanged.
    3. Permutation-equivariance: shuffle the rows of an UNMASKED attention's
       input and the outputs shuffle identically, to the last bit. Then add a
       positional vector and watch it break. Attention is a weighted sum, and
       a sum has no idea what order anything is in.
    4. Weight tying priced across realistic vocabulary sizes.
    5. Pre-norm against post-norm. Be honest about the size of the effect at
       the depths pure Python can reach — you can see its sign, not its full
       magnitude.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

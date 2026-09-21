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
        return layer_norm(x, self.gain, self.bias)


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
        return self.down(self.up(x).relu())


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
        if self.pre_norm:
            x = x + self.attention(self.norm1(x), mask)
            return x + self.feed_forward(self.norm2(x))
        x = self.norm1(x + self.attention(x, mask))
        return self.norm2(x + self.feed_forward(x))


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
        if len(ids) > self.block_size:
            raise ValueError(f"{len(ids)} tokens exceeds block size "
                             f"{self.block_size}")
        x = embedding(self.token_embedding, list(ids))
        if self.positional:
            x = x + embedding(self.position_embedding, list(range(len(ids))))
        mask = causal_mask(len(ids))
        for block in self.blocks:
            x = block(x, mask)
        x = self.final_norm(x)
        if self.tie_weights:
            # Score against the embedding table itself. The output projection
            # and the input embedding are the same matrix, used in both
            # directions.
            return x @ self.token_embedding.transpose()
        return self.head(x)

    def loss(self, ids: Sequence[int]) -> Tensor:
        """Next-token prediction: predict ids[1:] from ids[:-1].

        Every position is a training example, in one forward pass. A sequence
        of 16 tokens gives 15 supervised predictions — which is why language
        models are so sample-efficient per unit of text, and why the causal
        mask has to be exactly right: one position seeing one token too far and
        every example after it is free.
        """
        logits = self(list(ids[:-1]))
        return logits.softmax_cross_entropy(list(ids[1:]))

    def parameters(self) -> List[Tensor]:
        found = [self.token_embedding, self.position_embedding]
        found += self.final_norm.parameters()
        for block in self.blocks:
            found += block.parameters()
        if self.head is not None:
            found += self.head.parameters()
        return found

    def zero_grad(self) -> None:
        for parameter in self.parameters():
            parameter.zero_grad()

    def num_parameters(self) -> int:
        return sum(len(p.data) for p in self.parameters())

    def parameter_breakdown(self) -> Dict[str, int]:
        blocks = sum(len(p.data) for b in self.blocks for p in b.parameters())
        attention = sum(len(p.data) for b in self.blocks
                        for p in b.attention.parameters())
        return {
            "token embedding": len(self.token_embedding.data),
            "position embedding": len(self.position_embedding.data),
            "attention": attention,
            "feed-forward": blocks - attention
            - sum(len(p.data) for b in self.blocks
                  for p in b.norm1.parameters() + b.norm2.parameters()),
            "layer norms": sum(len(p.data) for b in self.blocks
                               for p in b.norm1.parameters() + b.norm2.parameters())
            + len(self.final_norm.parameters()[0].data) * 2,
            "output head": 0 if self.head is None
            else sum(len(p.data) for p in self.head.parameters()),
        }


def _demo() -> None:
    import time

    print("=" * 78)
    print("TRANSFORMER — four decisions, each with a measurement")
    print("=" * 78)

    print("\n1. The shape of the thing")
    print("-" * 78)
    model = GPT(vocab_size=64, d_model=32, heads=2, layers=2, block_size=16)
    logits = model([1, 2, 3, 4, 5])
    print(f"  5 token ids in -> logits {logits.shape}  "
          f"(one distribution over the vocabulary per position)")
    print(f"  {model.num_parameters():,} parameters:")
    for label, count in model.parameter_breakdown().items():
        share = count / model.num_parameters()
        print(f"    {label:<20}{count:>8,}  {'#' * int(share * 30)} "
              f"{share:.0%}")
    print("  Note where the parameters are. Attention is the famous part and")
    print("  the feed-forward is the big part — roughly two thirds of a real")
    print("  transformer's weights sit in those two matrices per block.")

    print("\n2. Residual connections are a gradient highway")
    print("-" * 78)
    print(f"    {'depth':>7}{'grad norm WITH residual':>26}"
          f"{'WITHOUT':>14}{'ratio':>12}")
    for depth in (2, 6, 12):
        norms = {}
        for residual in (True, False):
            rng = random.Random(4)
            x = Tensor.randn(4, 16, rng=rng, requires_grad=True)
            h = x
            for _ in range(depth):
                layer = Linear(16, 16, activation="linear", rng=random.Random(5))
                # Deliberately under-scaled, the way a deep stack drifts.
                layer.weight = Tensor([v * 0.35 for v in layer.weight.data],
                                      layer.weight.shape, requires_grad=True)
                h = (h + layer(h).tanh()) if residual else layer(h).tanh()
            h.sum().backward()
            norms[residual] = math.sqrt(sum(g * g for g in x.grad))
        print(f"    {depth:>7}{norms[True]:>26.4f}{norms[False]:>14.6f}"
              f"{norms[True] / max(norms[False], 1e-12):>11.0f}x")
    print("  y = x + f(x) has derivative 1 + f'(x). The 1 is a path along which")
    print("  the gradient arrives at every earlier layer UNCHANGED, whatever")
    print("  f' does. Without it the gradient is a product of N Jacobians and")
    print("  decays geometrically — by 12 layers there is nothing left to")
    print("  train the first one with.")

    print("\n3. Attention has no idea what order anything is in")
    print("-" * 78)
    from attention import MultiHeadAttention
    from engine import Tensor as T

    rows = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    shuffled_order = [2, 0, 3, 1]
    head = MultiHeadAttention(4, 1, rng=random.Random(8))

    plain = head(T.from_rows(rows), None).rows()
    shuffled = head(T.from_rows([rows[i] for i in shuffled_order]), None).rows()
    difference = max(abs(a - b) for i, target in enumerate(shuffled_order)
                     for a, b in zip(shuffled[i], plain[target]))
    print(f"  unmasked attention, rows shuffled {shuffled_order}:")
    print(f"    max difference from the same rows, shuffled the same way: "
          f"{difference:.2e}")

    positions = T.randn(4, 4, scale=0.5, rng=random.Random(9))
    with_positions = head(T.from_rows(rows) + positions, None).rows()
    shuffled_with = head(T.from_rows([rows[i] for i in shuffled_order])
                         + positions, None).rows()
    difference = max(abs(a - b) for i, target in enumerate(shuffled_order)
                     for a, b in zip(shuffled_with[i], with_positions[target]))
    print(f"  the same, with a positional vector added first: "
          f"{difference:.2e}")
    print("  Attention is a weighted SUM, and a sum is permutation-equivariant:")
    print("  shuffle the input rows and the output rows shuffle with them, to")
    print("  the last bit. 'dog bites man' and 'man bites dog' are the SAME")
    print("  input. Adding a position vector is what breaks the symmetry.")
    print("  A causal mask breaks it too — position i only sees 0..i — which is")
    print("  why a decoder-only model can partly infer position from the mask")
    print("  alone. It still works much better with the embeddings, and every")
    print("  real model has them.")

    print("\n4. Weight tying, priced")
    print("-" * 78)
    print(f"    {'vocabulary':>11}{'d_model':>9}{'untied':>11}{'tied':>11}"
          f"{'saved':>9}")
    for vocab, width in ((64, 32), (256, 32), (1000, 64), (50000, 768)):
        untied = GPT(vocab, width, 2, 2, 16, tie_weights=False, seed=3)
        tied = GPT(vocab, width, 2, 2, 16, tie_weights=True, seed=3)
        saved = 1 - tied.num_parameters() / untied.num_parameters()
        print(f"    {vocab:>11,}{width:>9}{untied.num_parameters():>11,}"
              f"{tied.num_parameters():>11,}{saved:>8.0%}")
    print("  At a realistic vocabulary the two embedding tables dominate the")
    print("  parameter count, and tying them removes one entirely. It also")
    print("  usually helps quality slightly, which is unusual for a change")
    print("  that halves a model — the two matrices genuinely encode related")
    print("  information, in opposite directions.")

    print("\n5. Pre-norm against post-norm")
    print("-" * 78)
    print(f"    {'placement':<12}{'depth':>7}"
          f"{'gradient reaching the input':>30}")
    for pre_norm in (True, False):
        for depth in (2, 8):
            model = GPT(vocab_size=32, d_model=16, heads=2, layers=depth,
                        block_size=8, pre_norm=pre_norm, seed=6)
            model.zero_grad()
            model.loss([1, 2, 3, 4, 5, 6, 7, 8]).backward()
            g = model.token_embedding.grad or [0.0]
            print(f"    {'pre-norm' if pre_norm else 'post-norm':<12}"
                  f"{depth:>7}{math.sqrt(sum(v * v for v in g)):>30.6f}")
    print("  In post-norm the residual path passes THROUGH a normalisation at")
    print("  every layer, so the clean highway from section 2 is interrupted N")
    print("  times; in pre-norm the residual stream runs untouched from input")
    print("  to output. The gradient reaching the embeddings is consistently")
    print("  attenuated here — but be honest about the size of it: at 2 to 8")
    print("  layers this is a mild effect, and pure Python cannot train the")
    print("  50-plus-layer models where post-norm actually becomes untrainable")
    print("  without a warmup schedule. What you can see at this scale is the")
    print("  SIGN of the effect, not its full magnitude.")

    print("\n" + "=" * 78)
    print("Next: train.py fits one of these to real text.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()

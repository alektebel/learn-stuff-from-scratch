"""
Attention — the operation the whole architecture is named after. Complete Solution.

    Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V

Three matmuls and a softmax. Everything else in a transformer is plumbing
around that line, and each piece of the plumbing exists for a reason this file
measures.

DESIGN DECISION — why divide by sqrt(d_k)?
  Q and K have roughly unit-variance entries, so their dot product over d_k
  dimensions has variance ~d_k and typical magnitude ~sqrt(d_k). At d_k = 64
  the scores span ±8 before training has done anything; softmax of ±8 is
  essentially one-hot, and the gradient through a saturated softmax is ~0.
  CHOSEN: divide by sqrt(d_k), which puts the scores back at unit variance.
  Section 1 measures the entropy of the attention distribution with and without
  it — unscaled, the model starts out already committed to one token per query
  and cannot learn its way out.

DESIGN DECISION — why several heads instead of one wide one?
  One head produces ONE distribution over positions. A token that needs to
  attend to its subject AND its verb has to average them, and the average is
  neither.
  CHOSEN: h heads of width d_model/h. Same parameter count, same FLOPs, h
  independent distributions. This is not a capacity increase — it is a
  structural one, and it is why "more heads" and "wider model" are different
  knobs.

DESIGN DECISION — where does the causal mask go?
  BEFORE the softmax, as -inf. After it — zeroing probabilities and
  renormalising — gives the same forward answer and a WRONG gradient, because
  the masked scores are still inside the sum softmax differentiates through.
  This is the one line standing between a language model and a model that has
  read the answer, and section 4 shows what happens without it.

Learning Path:
1. scaled_dot_product — three matmuls and a masked softmax
2. MultiHeadAttention — ONE projection, then slice per head
3. Measure attention entropy with and without the sqrt(d_k) scaling
"""

import math
import random
from typing import List, Optional, Sequence, Tuple

from engine import (Linear, Module, Tensor, causal_mask, concat_columns,
                    masked_softmax, slice_columns)


def scaled_dot_product(q: Tensor, k: Tensor, v: Tensor,
                       mask: Optional[List[List[bool]]] = None
                       ) -> Tuple[Tensor, Tensor]:
    """One head. Returns (output, attention weights).

    Returning the weights is not debug clutter — an attention map is the most
    interpretable object in the whole architecture, and every analysis of what
    a transformer "looks at" is a picture of this matrix.
    """
    raise NotImplementedError


class MultiHeadAttention(Module):
    """h heads over one projection, sliced rather than projected separately.

    The heads are a VIEW of one d_model-wide projection, not h separate small
    ones. Mathematically identical; in practice one big matmul instead of h
    small ones, which on real hardware is most of the speed.
    """

    def __init__(self, d_model: int, heads: int, rng: Optional[random.Random] = None):
        if d_model % heads:
            raise ValueError(f"d_model {d_model} is not divisible by "
                             f"{heads} heads")
        rng = rng or random.Random(0)
        self.d_model, self.heads = d_model, heads
        self.head_dim = d_model // heads
        self.to_q = Linear(d_model, d_model, activation="linear", bias=False, rng=rng)
        self.to_k = Linear(d_model, d_model, activation="linear", bias=False, rng=rng)
        self.to_v = Linear(d_model, d_model, activation="linear", bias=False, rng=rng)
        self.out = Linear(d_model, d_model, activation="linear", rng=rng)
        self.last_weights: List[Tensor] = []

    def forward(self, x: Tensor, mask: Optional[List[List[bool]]] = None
                ) -> Tensor:
        raise NotImplementedError


def entropy(distribution: Sequence[float]) -> float:
    """Bits. log2(n) means "spread evenly over n options", 0 means "certain".

    This is the right measurement for an attention row precisely because it is
    scale-free: it says how many positions the query is effectively looking at,
    which is the thing scaling by sqrt(d_k) is trying to control.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. Mean attention entropy at d_k of 4, 16, 64, 256, with and without the
       sqrt(d_k) scaling, against log2(sequence length) for reference.
       Unscaled at d_k=256 the softmax has already collapsed to near-certainty
       before training starts, and a saturated softmax has ~zero gradient.
    2. A causal attention matrix printed row by row: upper triangle exactly
       zero, every row still summing to 1.
    3. How many positions a query attends to with and without the mask.
    4. Per-head entropy on the same input — several independent distributions,
       which is the structural reason heads are not just extra width.
    5. Score-matrix size against sequence length from 128 to 32k, beside the
       linear feed-forward work. 65,536x against 256x is why long context is a
       research area.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

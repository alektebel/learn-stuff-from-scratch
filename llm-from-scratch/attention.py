"""
Scaled dot-product attention — the one operation a transformer is made of.

    Attention(Q, K, V) = softmax(Q·Kᵀ / √d) · V

Every token forms a query, compares it against every token's key, turns the
similarities into weights that sum to one, and takes that weighted average of the
values. Masking, multi-head, and the whole rest of the architecture are details hung
off this one line.

DESIGN DECISION — expose one head or many?
  Multi-head is the production shape, but with multiple heads the arithmetic disappears
  behind reshaping and you cannot see the softmax.
  CHOSEN: a single head, plain nested lists. Get this exact, then `context-caching/`
  stacks real blocks on top of it.

DESIGN DECISION — how to make softmax safe?
  exp overflows above ~709. Logits in a real model routinely exceed that after a few
  layers, so the naive `exp(x) / sum(exp(x))` becomes `inf / inf = nan`.
  CHOSEN: subtract the row max before exponentiating: `exp(x - max) / sum(exp(x - max))`.
  Mathematically identical, numerically stable. This is the line people omit.

DESIGN DECISION — where does the causal mask go?
  Zeroing the weights after the softmax breaks the sum-to-one property and leaks a
  little probability mass.
  CHOSEN: set masked scores to -inf BEFORE the softmax, so `exp(-inf) = 0` and the
  remaining weights renormalise on their own.
"""

import math
from typing import List


def dot(a: List[float], b: List[float]) -> float:
    """Dot product of two equal-length vectors."""
    raise NotImplementedError


def softmax(scores: List[float]) -> List[float]:
    """Numerically stable softmax: subtract the max, then normalise.

    The returned values sum to 1. Must not overflow for large inputs such as
    [1000, 1001] and must not divide by zero for a single element.
    """
    raise NotImplementedError


def scaled_dot_product_attention(
    Q: List[List[float]],
    K: List[List[float]],
    V: List[List[float]],
    causal: bool = False,
) -> List[List[float]]:
    """One head of attention.

    Q is (n_q, d), K and V are (n_k, d). Return (n_q, d): for each query, the
    softmax-weighted average of the values. Scale scores by 1/√d.

    With causal=True, query i may attend only to keys j <= i; mask the future to
    -inf before the softmax so each row still sums to 1.
    """
    raise NotImplementedError

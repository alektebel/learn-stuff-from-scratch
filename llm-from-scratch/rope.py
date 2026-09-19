"""
Rotary position embeddings (RoPE) — position without adding a position vector.

Instead of adding a learned position embedding to each token, RoPE rotates each
`(x₂ᵢ, x₂ᵢ₊₁)` pair of the query and key by an angle proportional to position. Because
both the query and the key are rotated by their own position, their dot product ends up
depending only on the *difference* in positions.

DESIGN DECISION — add a position vector, or rotate?
  Adding is simpler, but it puts position in the same space as the token embedding, so
  the two must share capacity, and extrapolation to longer contexts fails abruptly.
  CHOSEN: rotate. Relative position falls out of an identity (`Rᵀ(a)R(b) = R(b-a)`), and
  the norm of every vector is unchanged, which is what keeps attention logits in range.

DESIGN DECISION — apply before or after projecting to Q/K?
  CHOSEN: after. The cache stores already-rotated keys, so at decode time the past keys
  never need re-rotating — only the new one does. This is why RoPE composes with a KV
  cache for free.

The two things to verify are not "it runs": the norm is preserved, and the relative dot
product is invariant to the absolute position. If the second drifts, long contexts break
in a way short tests never show.
"""

import math
from typing import List, Tuple


def rope_freqs(dim: int, seq_len: int, base: float = 10000.0) -> List[List[float]]:
    """Angles per position per pair: `(seq_len, dim // 2)`.

    angle[pos][i] = pos * base ** (-2i / dim). Lower i rotates faster (higher
    frequency); the first pair has wavelength 2π.
    """
    raise NotImplementedError


def rotate_pair(x_even: float, x_odd: float, angle: float) -> Tuple[float, float]:
    """Rotate one 2D pair by `angle` (standard rotation matrix)."""
    raise NotImplementedError


def apply_rope(vec: List[float], pos: int, freqs: List[List[float]]) -> List[float]:
    """Rotate every pair of `vec` by its angle for position `pos`.

    Returns a new list of the same length. Preserves the vector's norm.
    """
    raise NotImplementedError

"""
Rotary position embeddings — complete solution.

DESIGN DECISION — rotate, don't add; relative position falls out of the identity.
DESIGN DECISION — apply after projecting, so cached keys need no re-rotation.
"""

import math
from typing import List, Tuple


def rope_freqs(dim: int, seq_len: int, base: float = 10000.0) -> List[List[float]]:
    half = dim // 2
    inv = [base ** (-2.0 * i / dim) for i in range(half)]
    return [[pos * inv[i] for i in range(half)] for pos in range(seq_len)]


def rotate_pair(x_even: float, x_odd: float, angle: float) -> Tuple[float, float]:
    c = math.cos(angle)
    s = math.sin(angle)
    return x_even * c - x_odd * s, x_even * s + x_odd * c


def apply_rope(vec: List[float], pos: int, freqs: List[List[float]]) -> List[float]:
    angles = freqs[pos]
    out: List[float] = []
    for i in range(len(vec) // 2):
        e, o = rotate_pair(vec[2 * i], vec[2 * i + 1], angles[i])
        out.extend((e, o))
    return out


if __name__ == "__main__":
    dim, seq = 8, 32
    freqs = rope_freqs(dim, seq)
    q = [math.sin(j + 1) for j in range(dim)]
    k = [math.cos(2 * j + 1) for j in range(dim)]

    norms = [abs(sum(x * x for x in apply_rope(q, p, freqs)) - sum(x * x for x in q))
             for p in range(seq)]
    print(f"max norm drift over {seq} positions: {max(norms):.2e} (rotation preserves norm)")

    d = 7
    dots = [sum(a * b for a, b in zip(apply_rope(q, p, freqs), apply_rope(k, p + d, freqs)))
            for p in range(seq - d)]
    spread = max(dots) - min(dots)
    print(f"dot(q@p, k@(p+{d})) spread over p: {spread:.2e} (depends only on distance, not p)")
    print(f"example dot at p=0: {dots[0]:.6f}, at p=10: {dots[10]:.6f}")

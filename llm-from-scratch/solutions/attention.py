"""
Scaled dot-product attention — complete solution.

DESIGN DECISION — single head, plain lists, so the softmax is visible.
DESIGN DECISION — subtract the row max before exp (stable softmax).
DESIGN DECISION — mask to -inf before the softmax, never after.
"""

import math
from typing import List


def dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def softmax(scores: List[float]) -> List[float]:
    if not scores:
        return []
    top = max(scores)
    exps = [math.exp(s - top) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def scaled_dot_product_attention(
    Q: List[List[float]],
    K: List[List[float]],
    V: List[List[float]],
    causal: bool = False,
) -> List[List[float]]:
    d = len(Q[0])
    scale = 1.0 / math.sqrt(d)
    out: List[List[float]] = []
    for i, q in enumerate(Q):
        scores = [dot(q, k) * scale for k in K]
        if causal:
            scores = [s if j <= i else float("-inf") for j, s in enumerate(scores)]
        weights = softmax(scores)
        out.append([
            sum(weights[j] * V[j][c] for j in range(len(V)))
            for c in range(len(V[0]))
        ])
    return out


if __name__ == "__main__":
    Q = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    K = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    V = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]

    causal = scaled_dot_product_attention(Q, K, V, causal=True)
    print(f"causal row 0 attends only to key 0 -> {causal[0]} (equals V[0]={V[0]})")
    print(f"causal row 0 still sums to 1:        {sum(causal[0]):.6f}")
    print(f"stable softmax([1000, 1001]):        {softmax([1000, 1001])} (no overflow)")

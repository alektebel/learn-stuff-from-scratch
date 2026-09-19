"""
The KV cache — complete solution.

DESIGN DECISION — cache projected keys/values, not hidden states.
DESIGN DECISION — correctness means bit-for-bit equality with the uncached path.
DESIGN DECISION — cost measured in query-key interactions so the ratio is printable.
"""

import math
from typing import Dict, List


def softmax(scores: List[float]) -> List[float]:
    if not scores:
        return []
    top = max(scores)
    exps = [math.exp(s - top) for s in scores]
    total = sum(exps)
    if total == 0.0:
        return [1.0 / len(scores)] * len(scores)
    return [e / total for e in exps]


def attention(q: List[float], keys: List[List[float]], values: List[List[float]]) -> List[float]:
    d = len(q)
    scores = [sum(x * y for x, y in zip(q, k)) / math.sqrt(d) for k in keys]
    weights = softmax(scores)
    return [
        sum(weights[j] * values[j][c] for j in range(len(values)))
        for c in range(len(values[0]))
    ]


class KVCache:
    def __init__(self) -> None:
        self._keys: List[List[float]] = []
        self._values: List[List[float]] = []

    def append(self, key: List[float], value: List[float]) -> None:
        self._keys.append(list(key))
        self._values.append(list(value))

    def __len__(self) -> int:
        return len(self._keys)

    def keys(self) -> List[List[float]]:
        return self._keys

    def values(self) -> List[List[float]]:
        return self._values


def cached_step(q: List[float], cache: KVCache) -> List[float]:
    return attention(q, cache.keys(), cache.values())


def recompute_step(q: List[float], keys: List[List[float]], values: List[List[float]]) -> List[float]:
    return attention(q, keys, values)


def recompute_work(prompt_len: int, decode_steps: int, d: int) -> int:
    return sum((prompt_len + t) ** 2 * d for t in range(1, decode_steps + 1))


def cached_work(prompt_len: int, decode_steps: int, d: int) -> int:
    return sum((prompt_len + t) * d for t in range(1, decode_steps + 1))


if __name__ == "__main__":
    d = 8
    K = [[math.sin(i + j) for j in range(d)] for i in range(16)]
    V = [[math.cos(i * j + 1) for j in range(d)] for i in range(16)]
    q = [math.sin(3 + j) for j in range(d)]

    cache = KVCache()
    for k, v in zip(K, V):
        cache.append(k, v)
    exact = max(abs(a - b) for a, b in zip(cached_step(q, cache), recompute_step(q, K, V)))

    prompt, steps = 64, 64
    r = recompute_work(prompt, steps, d)
    c = cached_work(prompt, steps, d)
    print(f"cache length:                 {len(cache)}")
    print(f"max |cached - recomputed|:    {exact:.2e}  (must be ~0)")
    print(f"work, {steps} tokens after {prompt}-token prompt:")
    print(f"  recompute (no cache):       {r:,} interactions")
    print(f"  with KV cache:              {c:,} interactions  ({r / c:.1f}x less)")

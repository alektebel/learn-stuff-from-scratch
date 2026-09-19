"""
Decoding — complete solution.

DESIGN DECISION — filters take/return logits, one softmax at the end.
DESIGN DECISION — temperature <= 0 is hard greedy (one-hot at argmax).
DESIGN DECISION — top-p uses >= after adding, so the crossing token is kept.
DESIGN DECISION — ties break by smallest index.
"""

import math
from random import Random
from typing import List, Optional


def softmax(logits: List[float]) -> List[float]:
    if not logits:
        return []
    top = max(logits)
    exps = [math.exp(s - top) for s in logits]
    total = sum(exps)
    if total == 0.0:
        return [1.0 / len(logits)] * len(logits)
    return [e / total for e in exps]


def apply_temperature(logits: List[float], temperature: float) -> List[float]:
    if temperature <= 0:
        best = max(range(len(logits)), key=lambda i: (logits[i], -i))
        return [0.0 if i == best else float("-inf") for i in range(len(logits))]
    return [x / temperature for x in logits]


def top_k_filter(logits: List[float], k: int) -> List[float]:
    if k >= len(logits):
        return list(logits)
    order = sorted(range(len(logits)), key=lambda i: (-logits[i], i))
    kept = set(order[:k])
    return [logits[i] if i in kept else float("-inf") for i in range(len(logits))]


def top_p_filter(logits: List[float], p: float) -> List[float]:
    if p >= 1.0:
        return list(logits)
    order = sorted(range(len(logits)), key=lambda i: (-logits[i], i))
    probs = softmax(logits)
    kept = set()
    cumulative = 0.0
    for i in order:
        kept.add(i)
        cumulative += probs[i]
        if cumulative >= p:
            break
    return [logits[i] if i in kept else float("-inf") for i in range(len(logits))]


def sample(
    logits: List[float],
    rng: Random,
    temperature: float = 1.0,
    k: Optional[int] = None,
    p: Optional[float] = None,
) -> int:
    scores = apply_temperature(logits, temperature)
    if k is not None:
        scores = top_k_filter(scores, k)
    if p is not None:
        scores = top_p_filter(scores, p)
    probs = softmax(scores)
    r = rng.random()
    cumulative = 0.0
    for i, probability in enumerate(probs):
        cumulative += probability
        if r < cumulative:
            return i
    return len(probs) - 1


if __name__ == "__main__":
    logits = [2.0, 1.0, 0.5, -1.0]
    print(f"greedy (temperature 0):        index {sample(logits, Random(0), temperature=0.0)}")
    print(f"top-2 masks index 3:           {top_k_filter(logits, 2)[3] == float('-inf')}")
    probs = [0.5, 0.3, 0.15, 0.05]
    logp = [math.log(x) for x in probs]
    kept = [x != float("-inf") for x in top_p_filter(logp, 0.9)]
    print(f"top-p=0.9 keeps indices:       {[i for i, k in enumerate(kept) if k]} (the 0.15 crosses)")
    s1 = sample(logits, Random(42), temperature=0.8, k=3, p=0.95)
    s2 = sample(logits, Random(42), temperature=0.8, k=3, p=0.95)
    print(f"same seed -> same sample:      {s1 == s2} (index {s1})")

"""Evals From Scratch — stage 5: ranking metrics, and the ideal that is not ideal

SOLUTION. The only line that matters is the IDCG: it sorts every key in the
relevance map, not the keys that came back. Everything else here is the
textbook formula.
"""

import math


def recall_at_k(relevant, retrieved, k):
    wanted = set(relevant)
    if not wanted:
        return 0.0
    seen = set(list(retrieved)[:k]) if k is not None else set(retrieved)
    return len(seen & wanted) / len(wanted)


def mrr(queries):
    queries = list(queries)
    if not queries:
        return 0.0
    total = 0.0
    for query in queries:
        wanted = set(query["relevant"])
        for rank, key in enumerate(query["retrieved"], start=1):
            if key in wanted:
                total += 1.0 / rank
                break
    return total / len(queries)


def dcg(gains):
    return sum((2.0 ** gain - 1.0) / math.log2(rank + 1.0)
               for rank, gain in enumerate(gains, start=1))


def ndcg(retrieved, relevance, k=None):
    order = list(retrieved)
    if k is not None:
        order = order[:k]
    gains = [relevance.get(key, 0) for key in order]
    ideal = sorted(relevance.values(), reverse=True)
    if k is not None:
        ideal = ideal[:k]
    best = dcg(ideal)
    if best <= 0:
        return 0.0
    return dcg(gains) / best

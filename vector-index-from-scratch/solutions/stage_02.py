"""Vector Index From Scratch — stage 2: the metric, and the norm cache

SOLUTION. norm/l2/cosine are three lines each; the interesting part is the
cache: each stored vector's norm is derived once, at add time, and the search
loop reads it instead of recomputing it. The query is not stored, so its norm
is the one cost a search cannot avoid.
"""

import math


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def l2(a, b):
    if len(a) != len(b):
        raise ValueError(f"l2() got vectors of {len(a)} and {len(b)} dimensions")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError(
            f"cosine() got vectors of {len(a)} and {len(b)} dimensions")
    na, nb = norm(a), norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


class CosineIndex:
    def __init__(self):
        self._vectors = {}
        self._norms = {}
        self._order = {}
        self._next = 0
        self.norm_evaluations = 0

    def add(self, key, vector):
        v = tuple(vector)
        if key not in self._order:
            self._order[key] = self._next
            self._next += 1
        self._vectors[key] = v
        self._norms[key] = norm(v)
        self.norm_evaluations += 1

    def search(self, query, k):
        q = tuple(query)
        q_norm = norm(q)
        self.norm_evaluations += 1
        rows = []
        for key, v in self._vectors.items():
            stored = self._norms[key]
            if q_norm == 0.0 or stored == 0.0:
                score = 0.0
            else:
                score = sum(x * y for x, y in zip(q, v)) / (q_norm * stored)
            rows.append((key, score))
        rows.sort(key=lambda kv: (-kv[1], self._order[kv[0]]))
        return rows[:max(0, k)]

    def __len__(self):
        return len(self._vectors)

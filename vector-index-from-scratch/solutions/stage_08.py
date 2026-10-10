"""Vector Index From Scratch — stage 8: deletions, and why not to unlink

SOLUTION. A tombstone set, and a walk that filters while it explores: dead
nodes stay in the graph as stepping stones (never returned, never counted
against the pool), so the links that keep the live nodes reachable are exactly
the links stage 6 built.
"""

import heapq

from stage_06 import build, layers, neighbors


def _dot(a, b):
    total = 0.0
    for x, y in zip(a, b):
        total += x * y
    return total


class DeletableIndex:
    def __init__(self, vectors, M, seed):
        self._vectors = {k: tuple(v) for k, v in vectors.items()}
        self._graph = build(self._vectors, M, seed)
        self._deleted = set()
        self._order = {k: i for i, k in enumerate(vectors)}

    def delete(self, key):
        if key in self._vectors:
            self._deleted.add(key)

    def deleted(self, key):
        return key in self._deleted

    def add(self, key, vector):
        v = tuple(vector)
        self._vectors[key] = v
        self._graph["vectors"][key] = v
        self._deleted.discard(key)

    def __len__(self):
        return len(self._vectors) - len(self._deleted)

    def search(self, query, k, ef):
        if ef < k:
            raise ValueError(f"ef={ef} cannot return k={k} rows")
        q = tuple(query)
        vecs = self._vectors
        if not vecs or k <= 0:
            return []
        ef = min(ef, len(vecs))

        cur = self._graph["entry"]
        cur_score = _dot(q, vecs[cur])
        for layer in range(layers(self._graph)[-1], 0, -1):
            improved = True
            while improved:
                improved = False
                for j in neighbors(self._graph, cur, layer):
                    s = _dot(q, vecs[j])
                    if s > cur_score:
                        cur, cur_score, improved = j, s, True

        visited = {cur}
        candidates = [(-cur_score, cur)]
        best = []
        if cur not in self._deleted:
            best.append((cur_score, cur))
        while candidates:
            neg_score, node = heapq.heappop(candidates)
            if len(best) >= ef and best and -neg_score < best[0][0]:
                break
            for j in neighbors(self._graph, node, 0):
                if j in visited:
                    continue
                visited.add(j)
                s = _dot(q, vecs[j])
                heapq.heappush(candidates, (-s, j))
                if j in self._deleted:
                    # a stepping stone: expanded, never returned, never
                    # occupying a slot of the answer pool
                    continue
                if len(best) < ef or s > best[0][0]:
                    heapq.heappush(best, (s, j))
                    if len(best) > ef:
                        heapq.heappop(best)

        rows = sorted(best, key=lambda kv: (-kv[0], kv[1]))
        return [(key, score) for score, key in rows][:k]

"""Vector Index From Scratch — stage 7: the walk, and ef

SOLUTION. The same best-first walk build() needs, made explicit: a greedy
descent through the upper layers to find a good place to start, then one
best-first walk at layer 0 with a pool of ef. The answer is the k best rows the
walk SAW, sorted at the end — not the node it happened to stop on.
"""

import heapq

from stage_06 import layers, neighbors


def _dot(a, b):
    total = 0.0
    for x, y in zip(a, b):
        total += x * y
    return total


def search(graph, query, k, ef):
    if ef < k:
        raise ValueError(
            f"ef={ef} is the pool width and k={k} is the answer size: a pool "
            f"narrower than the answer cannot return k rows")

    q = tuple(query)
    vecs = graph["vectors"]
    if not vecs:
        return []
    if k <= 0:
        return []
    ef = min(ef, len(vecs))

    cur = graph["entry"]
    cur_score = _dot(q, vecs[cur])
    for layer in range(layers(graph)[-1], 0, -1):
        improved = True
        while improved:
            improved = False
            for j in neighbors(graph, cur, layer):
                s = _dot(q, vecs[j])
                if s > cur_score:
                    cur, cur_score, improved = j, s, True

    visited = {cur}
    candidates = [(-cur_score, cur)]
    best = [(cur_score, cur)]
    while candidates:
        neg_score, node = heapq.heappop(candidates)
        if len(best) >= ef and -neg_score < best[0][0]:
            break
        for j in neighbors(graph, node, 0):
            if j in visited:
                continue
            visited.add(j)
            s = _dot(q, vecs[j])
            if len(best) < ef or s > best[0][0]:
                heapq.heappush(candidates, (-s, j))
                heapq.heappush(best, (s, j))
                if len(best) > ef:
                    heapq.heappop(best)

    rows = sorted(best, key=lambda kv: (-kv[0], kv[1]))
    return [(key, score) for score, key in rows][:k]

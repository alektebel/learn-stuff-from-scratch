"""Vector Index From Scratch — stage 6: the HNSW graph, built not searched

SOLUTION. Levels are drawn geometrically (mL = 1/ln(M)); every insertion walks
down from the entry point, links the M nearest candidates at each layer
(2*M at layer 0), and prunes symmetrically so the graph stays undirected. The
candidate search used while building is a local best-first walk with a pool of
ef_construction; stage 7 turns that walk into the thing being measured.
"""

import heapq
import math
import random


def _dot(a, b):
    total = 0.0
    for x, y in zip(a, b):
        total += x * y
    return total


def _greedy(vecs, query, cur, cur_score, layer, links):
    """Walk to the neighbour closest to the query while that improves it."""
    improved = True
    while improved:
        improved = False
        for j in sorted(links.get((cur, layer), ())):
            s = _dot(query, vecs[j])
            if s > cur_score:
                cur, cur_score, improved = j, s, True
    return cur, cur_score


def _search_layer(vecs, query, entries, ef, layer, links):
    """The ef best rows of one layer, best-first from `entries`."""
    visited = set(entries)
    candidates = [(-_dot(query, vecs[k]), k) for k in entries]
    heapq.heapify(candidates)
    best = [(_dot(query, vecs[k]), k) for k in entries]
    heapq.heapify(best)
    while candidates:
        neg_score, node = heapq.heappop(candidates)
        if len(best) >= ef and -neg_score < best[0][0]:
            break
        for j in sorted(links.get((node, layer), ())):
            if j in visited:
                continue
            visited.add(j)
            s = _dot(query, vecs[j])
            if len(best) < ef or s > best[0][0]:
                heapq.heappush(candidates, (-s, j))
                heapq.heappush(best, (s, j))
                if len(best) > ef:
                    heapq.heappop(best)
    return [(k, s) for s, k in best]


def _prune(vecs, links, node, layer, cap):
    """Keep the `cap` closest neighbours, and remove the reverse links too."""
    neighbours = links[(node, layer)]
    if len(neighbours) <= cap:
        return
    ordered = sorted(neighbours, key=lambda j: (-_dot(vecs[node], vecs[j]), j))
    keep = set(ordered[:cap])
    for dropped in neighbours - keep:
        links[(dropped, layer)].discard(node)
    links[(node, layer)] = keep


def build(vectors, M, seed, mL=None, ef_construction=32):
    if M <= 1:
        raise ValueError(f"M={M} has no level distribution: mL = 1/ln(M)")
    if mL is None:
        mL = 1.0 / math.log(M)

    vecs = {k: tuple(v) for k, v in vectors.items()}
    if not vecs:
        raise ValueError("build() needs at least one vector")

    rng = random.Random(seed)
    levels, links = {}, {}
    entry, top = None, -1

    for key in vecs:
        u = rng.random()
        if u <= 0.0:
            u = 1e-12
        level = int(-math.log(u) * mL)
        levels[key] = level
        for layer in range(level + 1):
            links[(key, layer)] = set()

        v = vecs[key]
        if entry is None:
            entry, top = key, level
            continue

        cur, cur_score = entry, _dot(v, vecs[entry])
        for layer in range(top, level, -1):
            cur, cur_score = _greedy(vecs, v, cur, cur_score, layer, links)

        for layer in range(min(level, top), -1, -1):
            cap = 2 * M if layer == 0 else M
            found = _search_layer(vecs, v, [cur], ef_construction, layer, links)
            chosen = [k for k, _ in sorted(found, key=lambda kv: (-kv[1], kv[0]))[:cap]]
            links[(key, layer)] = set(chosen)
            for j in chosen:
                links[(j, layer)].add(key)
                _prune(vecs, links, j, layer, cap)
            if chosen:
                best = sorted(chosen, key=lambda k: (-_dot(v, vecs[k]), k))[0]
                cur, cur_score = best, _dot(v, vecs[best])

        if level > top:
            entry, top = key, level

    return {"entry": entry, "vectors": vecs, "levels": levels, "links": links,
            "M": M, "mL": mL}


def neighbors(graph, key, layer):
    if key not in graph["levels"]:
        raise KeyError(f"{key} is not in the graph")
    return sorted(graph["links"].get((key, layer), ()))


def level(graph, key):
    if key not in graph["levels"]:
        raise KeyError(f"{key} is not in the graph")
    return graph["levels"][key]


def layers(graph):
    return sorted(set(graph["levels"].values()))

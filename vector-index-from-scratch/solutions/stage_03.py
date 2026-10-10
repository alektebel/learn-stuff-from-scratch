"""Vector Index From Scratch — stage 3: k-means, the partition IVF scans

SOLUTION. k-means++ init, Lloyd iterations, stop when the assignments stop
changing. An empty cluster keeps its previous centroid: it cannot happen with
k-means++ and a k <= n start, but "cannot happen" is how NaN gets in.
"""

import random


def squared_l2(a, b):
    if len(a) != len(b):
        raise ValueError(
            f"squared_l2() got vectors of {len(a)} and {len(b)} dimensions")
    total = 0.0
    for x, y in zip(a, b):
        d = x - y
        total += d * d
    return total


def assign(vectors, centroids):
    """The nearest centroid per vector; ties to the lowest index."""
    out = []
    for v in vectors:
        best, best_d = 0, float("inf")
        for j, c in enumerate(centroids):
            d = squared_l2(v, c)
            if d < best_d:
                best, best_d = j, d
        out.append(best)
    return out


def _plus_plus(vectors, nlist, rng):
    """k-means++: the first centroid at random, the rest weighted by D^2."""
    picked = [rng.randrange(len(vectors))]
    while len(picked) < nlist:
        weights = []
        for v in vectors:
            nearest = min(squared_l2(v, vectors[j]) for j in picked)
            weights.append(nearest)
        total = sum(weights)
        if total <= 0.0:
            # every point already sits on a chosen centroid; the weighting has
            # no information left, so draw uniformly rather than divide by zero
            choice = rng.randrange(len(vectors))
        else:
            target = rng.random() * total
            choice = len(vectors) - 1
            acc = 0.0
            for i, w in enumerate(weights):
                acc += w
                if acc >= target:
                    choice = i
                    break
        picked.append(choice)
    return [list(vectors[j]) for j in picked]


def kmeans(vectors, nlist, seed, iters=20):
    vectors = [tuple(v) for v in vectors]
    n = len(vectors)
    if nlist < 1 or nlist > n:
        raise ValueError(f"nlist={nlist} is impossible for {n} vectors")

    rng = random.Random(seed)
    centroids = _plus_plus(vectors, nlist, rng)
    assignments = assign(vectors, centroids)

    for _ in range(iters):
        for j in range(nlist):
            members = [vectors[i] for i, a in enumerate(assignments) if a == j]
            if not members:
                continue    # keep the previous centroid, never a NaN
            dim = len(members[0])
            centroids[j] = [sum(v[d] for v in members) / len(members)
                            for d in range(dim)]
        updated = assign(vectors, centroids)
        if updated == assignments:
            break
        assignments = updated

    return centroids, assignments

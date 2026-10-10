"""Vector Index From Scratch — stage 3: k-means, the partition IVF scans

DESIGN DECISION — k-means++ initialisation, seeded.
    Uniform-random initial centroids can land in the same dense region twice and
    leave another region with none; after the iterations that cluster is empty
    or the partition depends on the draw. Then your recall moves between runs
    for a reason you cannot point at in the code. k-means++ picks the first
    centroid at random and every next one with probability proportional to the
    squared distance to the closest chosen centroid, so the seeds start spread
    out. Seeded, the whole partition is reproducible — which is what makes the
    frontier in stage 5 a measurement instead of an anecdote.

DESIGN DECISION — a result you can check is a fixed point, not a loop count.
    "Every centroid is the mean of its assigned vectors" and "every vector is
    assigned to its nearest centroid" are both checkable from the output alone.
    Stop when the assignments stop changing; running a fixed number of
    iterations and hoping is how a partition ends up half-converged, and how the
    same seed silently produces different partitions after you edit an
    unrelated line.

TODO: implement

    squared_l2(a, b) -> sum((x - y) ** 2) — the distance k-means++ weights by,
                        and the one to use inside assignment loops (no sqrt)

    assign(vectors, centroids) -> list[int]
        the index of the nearest centroid per vector, ties to the lowest index

    kmeans(vectors, nlist, seed, iters=20) -> (centroids, assignments)
        centroids: list[list[float]] of length nlist; assignments: list[int]
        parallel to vectors. Use random.Random(seed) for every draw. An empty
        cluster keeps its previous centroid — never a NaN, which would spread
        through every later distance and compare False to everything. Raise
        ValueError when nlist < 1 or nlist > len(vectors): a request for more
        clusters than points is a bug in the caller, and papering over it hides
        the off-by-one that caused it.
"""


def squared_l2(a, b):
    raise NotImplementedError("stage 3: implement squared_l2()")


def assign(vectors, centroids):
    raise NotImplementedError("stage 3: implement assign()")


def kmeans(vectors, nlist, seed, iters=20):
    raise NotImplementedError("stage 3: implement kmeans()")

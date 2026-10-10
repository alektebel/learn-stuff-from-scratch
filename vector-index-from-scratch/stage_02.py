"""Vector Index From Scratch — stage 2: the metric, and the norm you must not recompute

DESIGN DECISION — the metric is a ranking, and naming it once is the point.
    Squared L2 and L2 order vectors identically — the square root is monotone —
    so mistakes like "forgot the sqrt" change the *number you report* and not
    the order. That is exactly why they survive review: retrieval looks fine
    while the distance you printed is wrong. Dot and cosine do not even agree on
    the order unless the vectors are unit length: cosine divides the magnitudes
    out, so a long document and a short one pointing the same way are a tie
    under cosine and a rout under dot. Pick one here, use it everywhere.

DESIGN DECISION — the norms are data, so cache them.
    cosine(a, b) = dot(a, b) / (|a| * |b|). A stored vector's norm never
    changes, and computing it inside the comparison loop makes a scan cost one
    square root per comparison instead of per vector. `norm_evaluations` counts
    the times a norm is derived from scratch, and the check holds you to the
    cache: adding ten vectors and running two searches must cost 12, not 30.

TODO: implement

    norm(v)      -> sqrt(sum(x * x))
    l2(a, b)     -> the euclidean distance, sqrt applied; ValueError on a length
                    mismatch (the squared distance is a valid ranking key, but it
                    is not the distance, and calling it one hides the bug)
    cosine(a, b) -> dot(a, b) / (norm(a) * norm(b)); 0.0 when either norm is 0.0,
                    because a zero vector has no direction and dividing by it
                    gives nan — a value that compares False to everything,
                    including itself, so it poisons every sort it enters

    CosineIndex()
        .add(key, vector)   store the raw vector, derive and cache its norm once
        .search(query, k)   -> [(key, cosine)] descending, ties by insertion order
        .norm_evaluations   norms derived from scratch so far (a cached stored
                            vector costs nothing; the query's norm is one per
                            search — it is not stored, so it cannot be cached)
"""

import math


def norm(v):
    raise NotImplementedError("stage 2: implement norm()")


def l2(a, b):
    raise NotImplementedError("stage 2: implement l2()")


def cosine(a, b):
    raise NotImplementedError("stage 2: implement cosine()")


class CosineIndex:
    def __init__(self):
        raise NotImplementedError("stage 2: implement CosineIndex.__init__()")

    def add(self, key, vector):
        raise NotImplementedError("stage 2: implement CosineIndex.add()")

    def search(self, query, k):
        raise NotImplementedError("stage 2: implement CosineIndex.search()")

    def __len__(self):
        raise NotImplementedError("stage 2: implement CosineIndex.__len__()")

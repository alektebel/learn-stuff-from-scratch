"""Vector Index From Scratch — stage 1: the exact baseline and recall@k

DESIGN DECISION — an approximation is only measurable against an exact answer.
    Every number this course produces — recall, visit counts, the shape of the
    frontier — is relative to the index in this file. If the baseline is wrong,
    the frontier is wrong, and nothing downstream will tell you: an approximate
    index that misses the true nearest neighbour on top of a broken baseline
    looks like a tuning problem, so you tune.

DESIGN DECISION — count work, do not time it.
    `comparisons` is the number of dot products a search performed. Wall-clock
    latency on a laptop is noise (caches, the scheduler, a fan); a counter makes
    every comparison in this course reproducible, which is what lets the checks
    assert a number rather than a vibe.

TODO: implement the exact index and the recall metric.

    dot(a, b) -> float
        The sum of products over the pairs. Raise ValueError when the lengths
        differ: zip() silently truncates to the shorter vector, which turns a
        dimension bug into a plausible-looking score.

    ExactIndex()
        .add(key, vector)   store a copy of the vector; keys are unique and a
                            repeat add replaces the vector
        .search(query, k)   -> [(key, score)] by score descending, ties broken by
                            insertion order (oldest first), at most k rows
        .comparisons        dot products performed by search() since the counter
                            was last reset (0 at construction)
        .reset_counter()
        __len__()           number of stored vectors

    recall_at_k(gold, retrieved, k) -> float
        |set(gold) & set(retrieved[:k])| / |set(gold)| — the denominator is the
        number of relevant documents, not k and not len(retrieved). An empty
        gold set returns 1.0: there was nothing to miss.

    Vectors are dense tuples of floats, unit-normalised by the caller (stage 2
    is where they become unit length). The score is therefore a dot product in
    [-1, 1], and the ranking is the cosine ranking.
"""


def dot(a, b):
    raise NotImplementedError("stage 1: implement dot()")


class ExactIndex:
    def __init__(self):
        raise NotImplementedError("stage 1: implement ExactIndex.__init__()")

    def add(self, key, vector):
        raise NotImplementedError("stage 1: implement ExactIndex.add()")

    def search(self, query, k):
        raise NotImplementedError("stage 1: implement ExactIndex.search()")

    def reset_counter(self):
        raise NotImplementedError("stage 1: implement ExactIndex.reset_counter()")

    def __len__(self):
        raise NotImplementedError("stage 1: implement ExactIndex.__len__()")


def recall_at_k(gold, retrieved, k):
    raise NotImplementedError("stage 1: implement recall_at_k()")

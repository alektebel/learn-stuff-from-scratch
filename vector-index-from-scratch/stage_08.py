"""Vector Index From Scratch — stage 8: deletions, and why not to unlink

DESIGN DECISION — never unlink a node to delete it.
    The links are the search's road network, and they are shared: an edge you
    remove to take one node out can be the only path between two regions, so the
    delete quietly turns every later query for those regions into a recall
    failure — a slow, invisible corruption that no single query exposes. The
    honest options are a tombstone (mark it and filter) or a rebuild. This stage
    makes the cost of the first one visible, and shows why it is usually still
    the right answer.

DESIGN DECISION — filter during the walk, not only at the end.
    Filtering the final rows is not enough: a tombstone sitting in the candidate
    pool occupies one of the ef slots, so the walk explores less of the graph
    and can return fewer than k rows even though k live nodes exist. Mark each
    tombstone, skip it when it is discovered, and make sure the pool is wide
    enough that the k best live rows still surface.

TODO: implement

    class DeletableIndex:
        __init__(self, vectors, M, seed)
            build the stage 6 graph over the live vectors.

        .delete(key)      mark it; deleting an already-deleted key or a key that
                          was never in the index is a no-op (a check-driven API
                          must not raise on the second call — an operation that
                          is idempotent in intent has to be idempotent in fact)
        .deleted(key)     -> bool
        .add(key, vector) re-admit a deleted key with the new vector: the links
                          stay (this stage is about deletion; inserting a key the
                          index never saw is out of scope), but the score must be
                          the score of the NEW vector
        .search(query, k, ef) -> [(key, score)]
                          the k best LIVE rows, descending, ties by key
                          ascending. With L live keys and k >= L it returns all L.
        __len__()         live keys only
"""


class DeletableIndex:
    def __init__(self, vectors, M, seed):
        raise NotImplementedError("stage 8: implement DeletableIndex.__init__()")

    def delete(self, key):
        raise NotImplementedError("stage 8: implement DeletableIndex.delete()")

    def deleted(self, key):
        raise NotImplementedError("stage 8: implement DeletableIndex.deleted()")

    def add(self, key, vector):
        raise NotImplementedError("stage 8: implement DeletableIndex.add()")

    def search(self, query, k, ef):
        raise NotImplementedError("stage 8: implement DeletableIndex.search()")

    def __len__(self):
        raise NotImplementedError("stage 8: implement DeletableIndex.__len__()")

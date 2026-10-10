"""RAG From Scratch — stage 3: exact brute-force vector index

DESIGN DECISION — brute force first.
    Approximate nearest-neighbour indexes are only interesting against the
    exact answer. This stage is your ground truth for stage B2 (HNSW) and for
    every recall number you will ever quote.

TODO: implement `VectorIndex`.

    add(key, vector)         store a copy; keep insertion order
    search(query, k)         -> [(key, score)] sorted by score descending,
                                ties broken by insertion order (oldest first)
    __len__                  number of stored vectors
    score = dot product of the sparse dicts (vectors are normalised upstream)
"""


class VectorIndex:
    def __init__(self):
        raise NotImplementedError("stage 3: implement VectorIndex.__init__()")

    def add(self, key, vector):
        raise NotImplementedError("stage 3: implement VectorIndex.add()")

    def search(self, query, k):
        raise NotImplementedError("stage 3: implement VectorIndex.search()")

    def __len__(self):
        raise NotImplementedError("stage 3: implement VectorIndex.__len__()")

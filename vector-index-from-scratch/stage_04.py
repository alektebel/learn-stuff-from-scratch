"""Vector Index From Scratch — stage 4: IVF, scanning fewer vectors

DESIGN DECISION — probe the centroids nearest the query, not the first nprobe.
    The partition from stage 3 is useless until you choose which lists to open,
    and "list 0, list 1, ..." opens the wrong ones: the query is a point in the
    same space as the corpus, so the reachable answers live in the clusters
    nearest the query. With nprobe = nlist the result must be *identical* to the
    exact index, row for row; anything less than that is a bug in the probe
    selection, not "approximate".

DESIGN DECISION — rank across the probed lists, never inside them.
    A very common IVF bug: iterate the probed clusters and emit each cluster's
    best rows in cluster order. On a query whose true best two neighbours land
    in different clusters, that returns them in the order the clusters were
    probed — a plausible list, off by a swap, and invisible unless you compare
    against the exact answer. Score every visited vector, keep one heap of the k
    best across all of them, sort once.

TODO: implement

    IVFIndex(vectors, nlist, seed)
        `vectors` is a dict {key: unit vector}; fit k-means (stage 3) over its
        values and keep, per cluster, the keys whose vector is nearest to it.
        Vectors are unit length, so the score is the dot product.

        .search(query, k, nprobe=1) -> [(key, score)]
            descending by score, ties broken by insertion order (oldest first).
            Probe the nprobe clusters whose centroid is nearest the query (ties
            to the lowest cluster index) and score only their members.
            nprobe > nlist clamps to nlist; nprobe < 1 raises ValueError.

        .visited    vectors scored by the last search — the work the query
                    actually cost, and the number the frontier in stage 5 is
                    drawn against. With nprobe == nlist it is len(vectors).

        .nlist          number of clusters
        .sizes          list[int]: how many vectors landed in each cluster
        .assignment(key) -> int: which cluster holds this key (KeyError for a
                        key the index never saw). A partition you cannot
                        inspect is a partition you cannot debug — the check
                        uses it to prove a probe stayed inside one list.

    Unlike the exact index, this one is allowed to miss: the answer is the best
    k among the vectors it visited, and it should never pretend otherwise.
"""


class IVFIndex:
    def __init__(self, vectors, nlist, seed):
        raise NotImplementedError("stage 4: implement IVFIndex.__init__()")

    def assignment(self, key):
        raise NotImplementedError("stage 4: implement IVFIndex.assignment()")

    def search(self, query, k, nprobe=1):
        raise NotImplementedError("stage 4: implement IVFIndex.search()")

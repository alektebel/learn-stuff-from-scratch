"""Vector Index From Scratch — stage 4: IVF, scanning fewer vectors

SOLUTION. One k-means fit at construction (deterministic from the seed), one
sort of the centroids per search, and — the part that matters — a single
ranking of the union of the probed lists, not one ranking per list.
"""

from stage_03 import kmeans, squared_l2


class IVFIndex:
    def __init__(self, vectors, nlist, seed):
        self._keys = list(vectors)
        self._vectors = {k: tuple(v) for k, v in vectors.items()}
        self._order = {k: i for i, k in enumerate(self._keys)}

        flat = [self._vectors[k] for k in self._keys]
        self._centroids, assignments = kmeans(flat, nlist, seed)

        self.nlist = nlist
        self._lists = [[] for _ in range(nlist)]
        self._cluster_of = {}
        for key, cluster in zip(self._keys, assignments):
            self._lists[cluster].append(key)
            self._cluster_of[key] = cluster
        self.sizes = [len(lst) for lst in self._lists]
        self.visited = 0

    def assignment(self, key):
        if key not in self._cluster_of:
            raise KeyError(f"{key} is not in the index")
        return self._cluster_of[key]

    def search(self, query, k, nprobe=1):
        if nprobe < 1:
            raise ValueError(f"nprobe={nprobe} probes no list at all")
        nprobe = min(nprobe, self.nlist)

        q = tuple(query)
        probed = sorted(range(self.nlist),
                        key=lambda j: (squared_l2(q, self._centroids[j]), j))
        probed = probed[:nprobe]

        rows = []
        for cluster in probed:
            for key in self._lists[cluster]:
                v = self._vectors[key]
                rows.append((key, sum(x * y for x, y in zip(q, v))))
        self.visited = len(rows)

        rows.sort(key=lambda kv: (-kv[1], self._order[kv[0]]))
        return rows[:max(0, k)]

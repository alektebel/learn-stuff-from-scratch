"""Vector Index From Scratch — stage 1: the exact baseline and recall@k

SOLUTION. The exact index is a list of (key, vector) pairs and one sort; the
only care needed is that the sort is total (score, then insertion order) and
that the vectors are copied on the way in.
"""


def dot(a, b):
    if len(a) != len(b):
        raise ValueError(
            f"dot() got vectors of {len(a)} and {len(b)} dimensions")
    total = 0.0
    for x, y in zip(a, b):
        total += x * y
    return total


class ExactIndex:
    def __init__(self):
        self._vectors = {}
        self._order = {}
        self._next = 0
        self.comparisons = 0

    def add(self, key, vector):
        if key not in self._order:
            self._order[key] = self._next
            self._next += 1
        self._vectors[key] = tuple(vector)

    def reset_counter(self):
        self.comparisons = 0

    def search(self, query, k):
        """[(key, score)] descending; ties by insertion order."""
        q = tuple(query)
        rows = []
        for key, vector in self._vectors.items():
            if len(vector) != len(q):
                raise ValueError(
                    f"{key} has {len(vector)} dimensions, the query has {len(q)}")
            rows.append((key, dot(q, vector)))
        self.comparisons += len(rows)
        rows.sort(key=lambda kv: (-kv[1], self._order[kv[0]]))
        return rows[:max(0, k)]

    def __len__(self):
        return len(self._vectors)


def recall_at_k(gold, retrieved, k):
    relevant = set(gold)
    if not relevant:
        return 1.0
    top = set(list(retrieved)[:max(0, k)])
    return len(relevant & top) / len(relevant)

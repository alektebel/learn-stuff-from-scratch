"""RAG From Scratch — stage 3 solution: exact brute-force vector index."""


class VectorIndex:
    def __init__(self):
        self._items = []
        self._counter = 0

    def add(self, key, vector):
        self._items.append((key, dict(vector), self._counter))
        self._counter += 1

    def search(self, query, k):
        scored = []
        for key, vec, order in self._items:
            score = sum(w * vec.get(t, 0.0) for t, w in query.items())
            scored.append((key, score, order))
        scored.sort(key=lambda x: (-x[1], x[2]))
        return [(key, score) for key, score, _ in scored[:k]]

    def __len__(self):
        return len(self._items)

"""RAG From Scratch — stage 8 solution: tenant-scoped retrieval."""


class TenantIndex:
    def __init__(self):
        self._tenants = {}

    def add(self, tenant, key, vector):
        self._tenants.setdefault(tenant, []).append((key, dict(vector)))

    def search(self, tenant, query, k):
        items = self._tenants.get(tenant, [])
        scored = []
        for order, (key, vec) in enumerate(items):
            score = sum(w * vec.get(t, 0.0) for t, w in query.items())
            scored.append((key, score, order))
        scored.sort(key=lambda x: (-x[1], x[2]))
        return [(key, score) for key, score, _ in scored[:k]]

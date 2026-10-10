"""RAG From Scratch — stage 8: tenant isolation

DESIGN DECISION — make the leak unrepresentable.
    A `WHERE tenant_id = ?` you can forget is a breach waiting for one call
    site. Here `search` takes the tenant as a required argument and looks only
    in that tenant's partition, so there is no query that can cross tenants.
    The enterprise RAG guide's warning applies: an embedding is the document,
    lightly encoded, so isolation has to hold for vectors too.

TODO: implement `TenantIndex`.

    add(tenant, key, vector)         store under that tenant's partition
    search(tenant, query, k)         -> [(key, score)] from that tenant only;
                                        ties by insertion order; unknown tenant
                                        returns []
"""


class TenantIndex:
    def __init__(self):
        raise NotImplementedError("stage 8: implement TenantIndex.__init__()")

    def add(self, tenant, key, vector):
        raise NotImplementedError("stage 8: implement TenantIndex.add()")

    def search(self, tenant, query, k):
        raise NotImplementedError("stage 8: implement TenantIndex.search()")

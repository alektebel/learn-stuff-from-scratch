# 2 — Zero-trust multi-tenant RAG

## What it is

A retrieval system serving many tenants from shared infrastructure, where the isolation
between tenants is enforced somewhere that a forgotten `WHERE` clause cannot bypass, and
where you can *demonstrate* the isolation rather than assert it.

## What it actually demonstrates

The original claim — "Tenant A's AI can never see Tenant B's embeddings" — is a security
claim, and security claims are worth exactly as much as the adversary you tested against.
Building this project without an attack suite demonstrates that you can configure row-level
security. Building it with one demonstrates that you know what isolation means, which is
the actual skill.

There is one fact that changes how you should think about the whole project:

> Morris, Kuleshov, Shmatikov & Rush, *Text Embeddings Reveal (Almost) As Much As Text*
> (EMNLP 2023) recover **92% of 32-token inputs exactly** by inverting dense embeddings,
> including full names from clinical notes.

An embedding is not a hash and it is not de-identified data. It is the document, lightly
encoded. Every isolation argument you make about documents has to hold for vectors, and
"they're only embeddings" is not a mitigation.

## The substrate

**Postgres + pgvector**, because RLS is a real database feature you can attack:

```sql
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings FORCE ROW LEVEL SECURITY;   -- the line everyone forgets
CREATE POLICY tenant_isolation ON embeddings
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

`FORCE` matters: without it the table *owner* is exempt from the policy, and your
application very likely connects as the owner. That single missing word is the most
common way this project is silently wrong.

Qdrant is the credible alternative — it has explicit multitenancy guidance built around
a tenant payload key and index partitioning. Use it if you want to compare enforcement
in the database against enforcement in a purpose-built vector store; the comparison is
more interesting than either one alone.

## The decisions

**Where the boundary lives.** Three positions, and you should be able to argue all three:

| Position | Cost |
|---|---|
| Application filter (`WHERE tenant_id = ?` in your code) | One forgotten call site is a breach. Fastest, and the reason most incidents happen. |
| Database RLS | The connection's session variable becomes the credential. Cost: connection pooling now has to reset `app.current_tenant` reliably, and a pooler that hands you a dirty session is a cross-tenant read. |
| Database per tenant | Genuinely hard to get wrong. Cost: one HNSW index per tenant, so per-tenant recall and memory both degrade at small N, and 5,000 tenants is 5,000 databases. |

**Connection pooling is where RLS goes wrong.** With transaction-level pooling, a
`SET app.current_tenant` outside a transaction leaks to the next borrower of that
connection. Use `SET LOCAL` inside the transaction, and then write the test that proves
it — two tenants hammering the same pool, asserting neither sees the other.

**Shared index or partitioned.** A single HNSW index over all tenants gives better
recall per unit memory, and creates a real question about whether graph traversal across
tenant boundaries can leak anything (distances to non-returned neighbours, timing).
Partitioned indexes remove the question and cost you memory. Say which you chose and
what you gave up.

**The retrieval path is not the only path.** Isolation has to hold for: search, the
prompt assembled from results, the model's cache, your logs, your traces, your error
messages, and your evaluation dataset. A stack trace containing another tenant's chunk
is the same breach as a bad query.

## The attack suite — the part that makes this project real

Do not skip this. Write it as tests, and make each one fail first against a deliberately
naive version:

1. **Forgotten filter.** Call the retrieval path with the tenant context unset. It must
   return zero rows, not all rows.
2. **Pool bleed.** Two tenants, concurrent load, one connection pool. Assert no
   cross-tenant row is ever returned.
3. **Superuser / owner path.** Connect as the table owner without `FORCE`. Watch it
   return everything. Then add `FORCE` and watch it stop.
4. **Prompt injection for exfiltration.** A document in tenant A that instructs the model
   to call the retrieval tool with a different tenant id. The boundary must not be
   reachable from model output.
5. **Metadata leakage.** Total result counts, latency differences, id sequences, error
   text. Does a tenant learn anything about another tenant's corpus size?
6. **Embedding inversion.** Take a vector your system does return, invert it with
   `vec2text`, and see how much of the source document comes back. Then re-read your
   own claim about what an embedding is.

## Where it breaks

A tenant is deleted, or exercises a right to erasure. Deleting rows does not remove them
from an HNSW index until the index is rebuilt, does not remove them from your backups,
and does not remove them from whatever you cached. Work out what "deleted" means in your
system and how long it takes to become true.

## Resources

- Morris, Kuleshov, Shmatikov, Rush, *Text Embeddings Reveal (Almost) As Much As Text*, EMNLP 2023 — [2310.06816](https://arxiv.org/abs/2310.06816) `[v]`. Code: <https://github.com/jxmorris12/vec2text> `[v]`
- PostgreSQL row security policies — <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>. Read the whole page; the owner-exemption behaviour is stated there and skipped by every tutorial.
- pgvector — <https://github.com/pgvector/pgvector>
- Qdrant multitenancy guidance — <https://qdrant.tech/documentation/guides/multiple-partitions/>
- OWASP Top 10 for LLM Applications — <https://genai.owasp.org/> — for the injection and data-disclosure entries, as a checklist for attack 4.

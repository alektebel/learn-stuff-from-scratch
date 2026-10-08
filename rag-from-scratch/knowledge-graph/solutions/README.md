# Solutions — RAG project 6 (knowledge graph + vector)

The complete implementation and the measurement it produces. Read [`graph.py`](graph.py);
its docstring names each design decision and the cost of the choice, and `check.py` in the
parent directory grades the template against the same behaviour.

## What it builds

- `TripleStore` — an in-memory store of `(subject, predicate, object)` triples with
  `add`, exact `match(subject, predicate, object)` and undirected **typed adjacency**
  `neighbours(node, predicate)`. Deterministic ordering everywhere.
- `load_graph(corpus=None)` — builds the entity list, the corpus's typed relations and
  the derived document links (`about`, `owned_by`, `authored_by`) into one store with
  `store.entities` set. With no argument it loads the shared eval set's seed-0 corpus;
  passing a corpus dict makes it fully self-contained.
- `link_entities(query, entities)` — resolves the entity ids a query names, whole-word and
  case-insensitive; `[]` when it names none.
- `multi_hop(start_ids, hops, store)` — the nodes reachable in 1..`hops` edges, sorted;
  the hop limit is enforced by construction.
- `documents_for_entities(entity_ids, documents)` — the documents directly linked to those
  entities, via each document's derived `entity_ids`.
- `lexical_retrieve` / `graph_retrieve` / `hybrid_retrieve` — the lexical first stage
  (sibling `../bm25`, with a local fallback), the graph stage bounded by `HOP_LIMIT`, and
  the union-then-RRF fusion.
- `evaluate(corpus, query_sets, k)` — the shared metrics shape (`overall`, `by_type`,
  `per_query`, `abstention`) for `lexical`, `graph` and `hybrid`, plus the predictions.

## Expected output

`python3 solutions/graph.py` (from `rag-from-scratch/knowledge-graph/`, seed 0, 66
documents, 24 queries, k=5):

```
seed 0, 66 documents, 24 queries; 29 entities, 30 relations, 198 derived document links
graph: triple store, 2 hops, fusion RRF(k=60) with graph weight 1.0

family       lex r@5  grph r@5  hyb r@5  lex MRR  grph MRR  hyb MRR  lex nDCG  grph nDCG  hyb nDCG
lexical        1.000     0.000    1.000    0.917     0.000    0.917     0.938      0.000     0.938
semantic       0.950     0.950    0.950    0.900     0.900    0.900     0.913      0.913     0.913
filtered       1.000     1.000    1.000    1.000     1.000    1.000     1.000      1.000     1.000
multi_hop      0.304     0.304    0.304    1.000     1.000    1.000     0.929      0.929     0.929
no_answer      0.000     0.000    0.000    0.000     0.000    0.000     0.000      0.000     0.000
overall        0.653     0.403    0.653    0.708     0.479    0.708     0.708      0.473     0.708

abstention (a prediction is empty):
  lexical  tp=1 fp=0 fn=5 precision=1.000 recall=0.167
  graph    tp=6 fp=6 fn=0 precision=0.500 recall=1.000
  hybrid   tp=1 fp=0 fn=5 precision=1.000 recall=0.167

limit case 1 — a query whose words name no entity expands to nothing:
  LEX-01: graph-only candidates 0, relevant 0 (the policy code is not an entity)
  hybrid still answers it from the lexical stage: recall@5=1.000

limit case 2 — a graph expansion that adds noise:
  query 'Engineering' reaches 27 documents by following any edge; only the ones about the department's topics answer it, the rest is noise the lexical stage never asked for

limit case 3 — a multi-hop question whose connecting edge is absent:
  the question is answerable from the corpus (['DOC-0000']) but the graph returns []: without the reports_to edge the report is unreachable
```

The numbers are reported as measured. The graph is **not** assumed to beat the lexical
stage: it adds nothing on the `lexical` family and noise on parts of `semantic`, and on
`multi_hop` all three systems share the same recall@5 because ~15 documents are relevant
and k=5 caps them — the graph's contribution there is MRR 1.0 (it ranks the manager's
documents first). The checker asserts the structural contract (`hybrid ⊇ lexical ∪ graph`)
and the limit cases, not a win. The graph's abstention tells the same story from the other
side: it returns *some* answer to every one of the six no-answer queries (recall 1.000) but
also to six answerable ones, so its precision is 0.500 — a graph that always has an edge to
follow invents an answer where the lexical stage correctly returns nothing.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. Against the
template it reports six TODOs and no failures or errors. The mutation suite
(`_build/mutations.py`) plants six bugs and each is CAUGHT by the named step.

## Notes on the eval-set and sibling imports

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. Both `solutions/graph.py` and `check.py` therefore import its `corpus`,
`queries` and `metrics` from `../eval-set/solutions` (adding that directory to `sys.path`
lazily). `load_graph` accepts an explicit corpus so the hand-built checks and the mutation
harness never need it. The lexical stage imports `../bm25/solutions` and falls back to a
self-contained Okapi BM25 when the sibling is absent, which keeps the union-contract half
of step 4 runnable in a bare temporary directory.

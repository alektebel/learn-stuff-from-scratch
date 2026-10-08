# RAG project 6 — knowledge graph + vector

The graph stage of the [RAG plan](../README.md): a standard-library **triple store** over
the shared evaluation set's entities (people, departments, topics) and typed relations,
**entity linking** of a query's words, a **hop-bounded multi-hop traversal**, and the
documents the traversal reaches, **combined with the lexical first stage** (the sibling
[`../bm25`](../bm25/) retriever). The result is one hybrid retrieval whose candidate set
is provably the union of the lexical and graph candidates.

This is a graded module in the repo's `graded-module` format. Fill in the template
`graph.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/knowledge-graph
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/graph.py  # the demo: per-family lexical / graph / hybrid numbers, abstention, and the limit cases
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network).
`check.py` adds `../eval-set/solutions` to `sys.path` in the end-to-end step only;
`graph.py` reuses `../bm25/solutions` and carries a small in-module BM25 fallback so the
hand-built checks run in a tree without the sibling.

## The graph

The eval-set corpus carries the raw material: `entities` (person `PER-*`, department
`DEP-*`, topic `TOP-*`), typed `relations` (`works_in`, `reports_to`, `owns`) and
documents with `topics`, `department` and `author`. `load_graph` derives the document
links that make the graph reach documents:

| Edge | From → to | Source |
|---|---|---|
| `works_in` | `PER-*` → `DEP-*` | corpus relation |
| `reports_to` | `PER-*` → `PER-*` | corpus relation |
| `owns` | `DEP-*` → `TOP-*` | corpus relation |
| `about` | `DOC-*` → `TOP-*` | document's `topics` |
| `owned_by` | `DOC-*` → `DEP-*` | document's `department` |
| `authored_by` | `DOC-*` → `PER-*` | document's `author` |

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | graph.py | the loaded entity/relation counts match the corpus, `match` is exact per component, `neighbours` is typed and undirected, and duplicates are ignored |
| 2 | graph.py | whole-word, case-insensitive entity linking (`engineers` must not link `Engineering`); `documents_for_entities` returns exactly the linked subset |
| 3 | graph.py | a hand-built chain gives exact reachable sets at 1, 2 and 3 hops, and the hop limit binds (a three-hop node is absent from the two-hop answer) |
| 4 | graph.py | end to end on the shared eval set: `hybrid ⊇ lexical ∪ graph` per query, then lexical / graph / hybrid recall@k, MRR and nDCG@k per family, with `multi_hop` called out and no claim that the graph wins |
| 5 | graph.py | the limit cases: a non-multi-hop query the graph cannot help, an expansion that adds noise, and a multi-hop question whose connecting edge is absent returning `[]` from graph-only |
| 6 | graph.py | a query naming no entity and a no-answer query abstain through the graph and the hybrid |

## Design decisions

Summarised; the full rationale is in `solutions/graph.py`.

- **A directed triple store with undirected, typed traversal.** Facts keep their
  direction; `neighbours(node, predicate)` returns the other endpoint of any incident
  edge so a traversal can follow `reports_to` *against* the arrow to find a person's
  reports. Cost: direction is lost to traversal.
- **Breadth-first search bounded by hops, not a connected-component walk.** The
  component is a few hundred nodes; returning all of it would be a corpus scan in graph
  costume. Cost: a genuinely long (3+ edge) question is unreachable.
- **Whole-word entity linking by regex lookarounds.** A substring rule links "engineers"
  to "Engineering"; the lookarounds on both sides prevent it. Cost: a possessive or
  hyphenated mention ("Engineering's") still matches only on the word "Engineering".
- **The lexical stage is the sibling `../bm25`, with a self-contained fallback.** Reuse
  keeps the comparison honest; the fallback lets the hand checks and the mutation harness
  run without the sibling. Cost: a little duplicated scoring code.
- **The hybrid forms the union first, then ranks by reciprocal rank fusion.** The
  contract is `hybrid ⊇ lexical ∪ graph`, so neither stage can silently drop the other's
  candidates. Cost: RRF discards score magnitudes, so a graph candidate the lexical stage
  ranked low can jump ahead of the lexical stage's own top hit.
- **Graph candidates are ordered by hop distance, then doc_id.** Distance is the graph's
  only relevance signal; the doc_id tie-break makes every run byte-identical. Cost: the
  graph has no scoring model of its own.

## What the measurement actually says

Seed 0, 66 documents, 24 queries, k=5 (from `python3 solutions/graph.py`):

```
family       lex r@5  grph r@5  hyb r@5  lex MRR  grph MRR  hyb MRR  lex nDCG  grph nDCG  hyb nDCG
lexical        1.000     0.000    1.000    0.917     0.000    0.917     0.938      0.000     0.938
semantic       0.950     0.950    0.950    0.900     0.900    0.900     0.913      0.913     0.913
filtered       1.000     1.000    1.000    1.000     1.000    1.000     1.000      1.000     1.000
multi_hop      0.304     0.304    0.304    1.000     1.000    1.000     0.929      0.929     0.929
no_answer      0.000     0.000    0.000    0.000     0.000    0.000     0.000      0.000     0.000
overall        0.653     0.403    0.653    0.708     0.479    0.708     0.708      0.473     0.708
```

The graph adds nothing on the **lexical** family (the policy code is not an entity, so
graph-only is empty) and only noise on parts of **semantic** (an expansion reaches
documents the question did not ask for). On **multi_hop** the graph reaches every
relevant document — its MRR is 1.0, the manager's documents come first — but with ~15
relevant documents and k=5 the recall ceiling is what caps both stages. This is reported
as measured; the checker asserts the union contract and the limit cases, never that the
graph wins. The abstention block says the same from the other side: graph-only answers all
six no-answer queries (recall 1.000) but also six answerable ones, so its precision is
0.500, while lexical and hybrid abstain cleanly (precision 1.000, recall 0.167). A graph
that always has an edge to follow invents an answer where the lexical stage returns none.

## Mutation table

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/knowledge-graph rag-from-scratch/knowledge-graph/_build/mutations.py
```

Every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | the loader drops the `reports_to` predicate type | the loaded relation count/set no longer matches the corpus |
| 2 | linking matches a prefix substring, so `engineers` links `Engineering` | the whole-word case must return `[]` |
| 2 | `documents_for_entities` returns every document regardless of link | `documents_for_entities(["TOP-00"])` must be exactly the linked subset |
| 3 | `multi_hop` ignores the hop limit and walks the whole component | the three-hop node appears in the two-hop set |
| 4 | `hybrid_retrieve` drops the lexical half | `hybrid ⊇ lexical ∪ graph` fails for a lexical-only query |
| 6 | the abstention path returns every entity | a query naming no entity must return `[]` |

## Questions to answer (no answers here)

1. The graph reaches all 15 relevant multi-hop documents but recall@5 is ~0.30. Is that
   the graph failing, or k being too small for a question with 15 correct answers? Which
   metric would you read instead of recall@5?
2. `HOP_LIMIT = 2` reaches the manager's documents (one edge) and the report's documents
   (two edges). A question "who does the person reporting to X report to?" needs three
   edges. How would you raise the limit without turning every query into a component
   scan?
3. Entity linking matches names exactly. "the Engineering team", "Eng", and "the person
   who reports to B. Okafor" name no entity here. What would an alias table or a
   relation-aware linker buy, and what would it cost in precision?
4. `documents_for_entities` treats a document's `about` / `owned_by` / `authored_by` links
   as equally strong. Should `about` outrank `authored_by` when ranking graph candidates?
   What evidence in the corpus would tell you?
5. The hybrid uses RRF with graph weight 1.0. When the graph returns 30 candidates and
   the lexical stage returns 5, what does equal weighting do to the top-5, and how would
   you detect the dilution from the per-family table?
6. The graph is built from a frozen corpus. In a real system, entity and relation
   extraction is an LLM step with errors. Which failure — a missing edge or a spurious
   edge — hurts this pipeline more, and where would each show up in the metrics?

## Limits

- The triple store is in-memory and rebuilt per process; there is no persistence, no
  index and no query language. At 200 links that is fine; it is the structure the project
  is about.
- Traversal is undirected over typed edges: it can reach anything connected, but it
  cannot express a *directional* multi-hop query directly.
- The graph ranking is hop distance then doc_id; it has no trained scorer, so it cannot
  separate two documents at the same distance.
- The eval-set corpus is synthetic and regular (authors appear on many documents,
  departments own topics cyclically), so the graph finds many documents per entity; the
  absolute numbers do not transfer, only the comparison between the three systems. See
  the eval set's own limits.

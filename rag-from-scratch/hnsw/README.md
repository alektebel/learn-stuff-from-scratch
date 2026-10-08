# RAG project 1, stage 3 — HNSW and approximate nearest neighbours

The third stage of [hybrid search]: a real multilayer navigable small-world graph over the
LSA document embeddings of the shared [evaluation set](../eval-set/). The pipeline is
BM25 -> LSA -> **HNSW** -> fusion; this stage turns "find the nearest dense vectors" from
a linear scan into a graph walk, and reports the recall it gives up for the work it saves.

This is a graded module in the repo's `graded-module` format. Fill in the template
`hnsw.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/hnsw
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/hnsw.py   # the demo: recall@10 vs exact, and distance calls, by ef
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network).
`check.py` adds `../eval-set/solutions` to `sys.path` lazily, in step 4 only; the other
steps use hand-built points so the mutation suite can run them from a bare directory.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | hnsw.py | `l2` is the root (not the square) and symmetric; `cosine` is `1 - cos`, sign-correct, with the zero-vector convention |
| 2 | hnsw.py | a small index returns exactly the brute-force neighbours at a large `ef`, and the graph is genuinely layered (higher layers smaller, upper links bidirectional) |
| 3 | hnsw.py | recall@k rises with `ef` (never falls), reaches 1.0, and small `ef` stays cheaper than a scan |
| 4 | hnsw.py | on the eval-set LSA embeddings the indexed search reproduces exact search at a large `ef` |
| 5 | hnsw.py | a controlled query is genuinely missed at small `ef` — the approximation is measured, not hidden |
| 6 | hnsw.py | a very selective metadata filter applied AFTER the ANN returns fewer than k (possibly zero) |

## Design decisions

Summarised; the full rationale is in the `solutions/hnsw.py` docstring.

- **`l2` and `cosine` are real metrics, not similarities.** `l2` returns the Euclidean
  distance (the square root); `cosine` returns `1 - cos` in `[0, 2]`. Both are
  non-negative and zero only for an exact match/direction. Cost: a square root per
  comparison. The squared distance is planted as a mutation precisely because it ranks
  identically while lying about the metric.
- **Geometric level assignment**, `floor(-ln(U)/ln(M))`, so each higher layer holds
  exponentially fewer nodes and descent is `O(log N)`. Cost: the graph depends on the
  seed, so every check is seeded.
- **Bidirectional links pruned to `M` (`2M` on layer 0).** Insert runs an
  `ef_construction`-bounded beam search at every layer the node reaches. This is the
  build-time budget; `ef_construction` is the knob.
- **`distance_calls` is audited.** `search` resets it and counts every comparison, so
  recall is always read against the work that bought it. A perfect answer that touches the
  whole corpus is a linear scan wearing a graph costume (step 3 rejects it).
- **Metadata filtering is post-ANN.** The graph has no filter awareness: ask for the top
  k, then drop non-matching documents. A very selective filter genuinely returns fewer
  than k, possibly zero. Building a filtered graph is the honest alternative this stage
  does not take; step 6 measures the shortfall rather than hiding it.
- **The LSA fit is re-derived locally**, because this module must run when only it and
  `../eval-set` are present (the checker and mutation suite use that layout). Cost: the
  tokeniser and the smoothed idf must agree with the sibling `../lsa` stage; only the
  eval-set wiring is shared.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/hnsw rag-from-scratch/hnsw/_build/mutations.py`
— every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | `l2` returns the squared distance | hand-computed root on `[0,0]`–`[3,4]` |
| 2 | `insert` never links a node at the upper layers | upper-layer links must be bidirectional |
| 2 | `search` returns the query's own key as nearest (self-match) | query key absent from the index must never appear |
| 3 | `search` ignores `ef` (always greedy depth-1) | recall@10 must reach 1.0 as `ef` grows |
| 3 | `recall_at_k` divides by the wrong count | denominator checked by hand (`["a"]` vs four keys) |
| 6 | the selective filter returns the whole corpus | a filter matching nothing must yield zero |

## Questions to answer (no answers here)

1. Recall@10 is 0.10 at `ef=1` and 1.00 at `ef=16` on 66 embeddings. Why does such a small
   `ef` already saturate, and what would make the graph hard (higher dimension? clustered
   data? random insertion order instead of nearest-first)?
2. `mean distance calls` at `ef=128` is 68.7, slightly *above* the 66 of an exhaustive
   scan. When is the index actually a win, and how does that change with corpus size and
   embedding dimension?
3. Upper-layer links are bidirectional and pruned to `M`. What breaks if the prune keeps
   the *farthest* `M` instead of the closest (the "diversity" heuristic Malkov &
   Yashunin discuss), and which step here would or would not notice?
4. Filtering after the ANN returns fewer than k. What would a filtered graph have to store
   to answer the same query with k results, and why is that incompatible with one shared
   index over all metadata values?
5. The level assignment uses `1/ln(M)`. What happens to the layer structure and the search
   cost as `M` grows, and why is `M=16` a common default?

## Limits

- The eval set is small (66 embeddings) and its vocabulary is controlled, so this stage is
  a correctness and mechanism exercise, not a benchmark of HNSW at scale. The absolute
  numbers do not transfer; the recall/work trade-off does.
- The LSA basis is copied, not shared: a change to the sibling stage's tokeniser or idf
  would silently desynchronise the two copies.
- No deletions, no updates, no persistence. A real index needs to remove superseded
  documents and rebuild or tombstone.
- Filtering is post-ANN and therefore approximate under selective filters; pre-filtering
  and filtered graph traversal are out of scope.
- The distance is always `l2`. LSA embeddings are L2-normalised, so `l2` and cosine rank
  equivalently here, but the API does not let the caller choose.

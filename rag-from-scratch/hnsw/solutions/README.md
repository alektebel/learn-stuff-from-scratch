# Solutions — RAG project 1, stage 3 (HNSW)

The complete implementation and the measurement it produces. Read
[`hnsw.py`](hnsw.py); its docstring names each design decision and the cost of the
choice, and `check.py` in the parent directory grades the template against the same
behaviour.

## Expected output

`python3 solutions/hnsw.py` (from `rag-from-scratch/hnsw/`, seed 0, 66 documents):

```
seed 0, 66 documents, 23 embedded queries, LSA rank 16
HNSW recall@10 vs exact search (same embeddings), by ef:
     ef  mean recall@10   mean distance calls
      1           0.100                  53.2
      2           0.200                  56.7
      4           0.400                  66.7
      8           0.800                  70.8
     16           1.000                  71.7
     32           1.000                  71.7
     64           1.000                  71.7
    128           1.000                  71.7
  a linear scan would use 66 distance calls per query

HNSW over the LSA embeddings, ef=128 (metadata filtered AFTER the ANN):
  family      recall@10     MRR  nDCG@10
  lexical         1.000   0.549    0.658
  semantic        1.000   1.000    0.974
  filtered        1.000   1.000    1.000
  multi_hop       0.433   0.833    0.730
  no_answer       0.000   0.000    0.000
  overall         0.679   0.616    0.625
  abstention: tp=1 fp=0 fn=5 (precision=1.000, recall=0.167)
  mean distance calls per query: 68.7 (vs 66 for an exhaustive scan)
  at small ef the index does far less work; ef=128 buys exactness at a scan's cost. Recall below 1.0 at small ef is the approximation as designed.
  the filtered family here is 1.0 because the ANN top-10 happened to contain the matching documents; a very selective filter after the ANN shortens the list (step 6 measures that limit, it is not free).
```

The first table is the whole point of the stage, reported honestly: at `ef=1` the graph
finds one of the true top-10 (recall 0.10) using about 53 distance computations; by
`ef=16` it recovers the exact top-10. Because the corpus is only 66 embeddings, the
"cheap" and "exact" ends are close to an exhaustive scan (66 calls); the search is exact
from `ef=16` upward because `ef` then exceeds the number of reachable nodes. On a real
corpus the same curve separates the two ends by orders of magnitude.

`evaluate` (second table) indexes the LSA embeddings and post-filters metadata. The
`filtered` family scores 1.000 here because the ANN top-10 happened to contain the
matching documents; the *limit* is that a more selective filter would shorten the list
below k, which step 6 of `check.py` asserts instead of hiding.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. It also prints
the measured trade-off as it goes:

```
      ef 1..128: mean recall@10 0.10 -> 1.00, distance calls/query 59.7 -> 199.8 of 180
      HNSW vs exact on 66 LSA embeddings (rank 16) at ef=512: mean recall@10=1.000, distance calls/query=71.7
      small ef=2 missed 3 of the true top-5 (recall 0.40); ef=256 recovers all five
      post-ANN filter counts out of k=10: none=0, {department=Finance}=1, {year=1999}=0
```

Against the template it reports six TODOs and no failures; the mutation suite
(`_build/mutations.py`) is designed so each planted bug is CAUGHT by the step named in the
module README.

## Notes on the eval-set import

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. `solutions/hnsw.py` and `check.py` therefore import the eval set's `corpus`,
`queries` and `metrics` from `../eval-set/solutions` (adding that directory to
`sys.path`). The import is done lazily, inside `_import_metrics` / `demo` and inside check
step 4, so steps 1–3, 5 and 6 run without the eval set — which is what lets the mutation
suite exercise them from a temporary directory holding only this stage.

Unlike the BM25 and LSA stages, the LSA embeddings are **re-derived here** rather than
imported from `../lsa/solutions/lsa.py`: this module must run when only it and
`../eval-set` sit side by side, which is the layout the checker and the mutation runner
use. The local fit is the same pipeline (lowercase `[a-z0-9]+` tokeniser, smoothed BM25
idf, row-normalised tf-idf, centring, truncated SVD by Jacobi on the smaller Gram matrix);
the README calls out the cost of keeping two copies in sync.

## Notes on the mutation suite

`_build/mutations.py` plants six bugs: a squared `l2`; upper layers left unlinked; `search`
ignoring `ef`; `search` fabricating the query's own key; `recall_at_k` dividing by the
wrong count; and the selective-filter helper returning the whole corpus. Each targets a
step that runs without the eval set, so
`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/hnsw rag-from-scratch/hnsw/_build/mutations.py`
reports every row CAUGHT from a bare temporary copy.

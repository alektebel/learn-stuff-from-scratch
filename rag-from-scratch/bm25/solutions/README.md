# Solutions — RAG project 1, stage 1 (BM25)

The complete implementation and the measurement it produces. Read
[`bm25.py`](bm25.py); its docstring names each design decision and the cost of the choice,
and `check.py` in the parent directory grades the template against the same behaviour.

## Expected output

`python3 solutions/bm25.py` (from `rag-from-scratch/bm25/`, seed 0, 66 documents):

```
seed 0, 66 documents, 24 queries
family        BM25 r@10  BM25 MRR  base r@10  base MRR
lexical           1.000     0.917      1.000     0.917
semantic          1.000     0.900      1.000     0.900
filtered          1.000     1.000      1.000     1.000
multi_hop         0.542     1.000      0.542     1.000
no_answer         0.000     0.000      0.000     0.000
overall           0.693     0.708      0.693     0.708
abstention  BM25: tp=1 fp=0 fn=5 | baseline: tp=6 fp=0 fn=0
```

On this controlled corpus BM25 and the token-overlap baseline agree on the retrieval
metrics. The gap is in abstention: the baseline strips stopwords and abstains on all six
no-answer queries (`tp=6`), while BM25 has no stopword list and answers five of them
because generic tokens (function words like `a`/`for`/`on`, plus `policy` on one query)
appear in the corpus (`tp=1, fn=5`). That is the honest,
measured difference the later stages have to fix; step 5 of `check.py` requires exactly
this to be reported, not hidden. The `no_answer` family scores 0.0 on retrieval metrics by
construction (empty relevance); abstention is what grades it.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. Against the
template it reports six TODOs and no failures; the mutation suite
(`_build/mutations.py`) is designed so each planted bug is CAUGHT by the step named in
the module README.

## Notes on the eval-set import

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. Both `solutions/bm25.py` and `check.py` therefore import the eval set's
`corpus`, `queries`, `metrics` and `baseline` from `../eval-set/solutions` (adding that
directory to `sys.path`). The import is done lazily, inside `evaluate_bm25` / `_import_metrics`
and inside check step 5, so the hand-computed steps 1–4 and 6 run without the eval set.

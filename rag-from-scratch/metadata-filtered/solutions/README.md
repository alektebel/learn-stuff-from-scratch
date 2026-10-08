# Solutions — RAG project 2 (metadata-filtered RAG)

The complete implementation and the measurement it produces. Read
[`filtered.py`](filtered.py); its docstring names each design decision and the cost of
the choice, and `check.py` in the parent directory grades the template against the same
behaviour.

## What it builds

- `build_db(docs)` — a standard-library `sqlite3` table of documents plus their
  metadata, with a **secondary index on every filterable column** (`department`, `date`,
  `author`, `region`, `access_level`, `superseded`).
- `FilteredRetriever` — a self-contained BM25 ranker over the SQLite store with three
  execution strategies: `pre_filter` (SQL filter first), `post_filter` (rank first, then
  drop — the anti-pattern) and `filter_aware` (drive on the most selective indexed
  predicate, re-check the rest over the small candidate set).
- `selectivity(conn, filters)` — the fraction of the corpus a filter matches.
- `evaluate(corpus, queries, k)` — the shared metrics shape (`overall`, `by_type`,
  `per_query`, `abstention`) for each strategy, plus the mean number of results returned
  for the `filtered` family, which exposes the post-filter shortfall.

## Expected output

`python3 solutions/filtered.py` (from `rag-from-scratch/metadata-filtered/`, seed 0,
66 documents, 24 queries):

```
seed 0, 66 documents, 24 queries
strategy      filtered r@10 filtered MRR filtered nDCG  mean results
pre_filter            1.000        1.000         1.000         10.00
post_filter           1.000        1.000         1.000          4.75
filter_aware          1.000        1.000         1.000         10.00

selective-filter shortfall (a filter matching a tiny fraction):
  filter {'department': 'Engineering', 'region': 'EMEA', 'access_level': 'public', 'year': 2024}: 1 of 66 documents (selectivity 0.0152), query 'standard'
  pre_filter     returned  1: ['DOC-0060']
  post_filter    returned  0: []
  filter_aware   returned  1: ['DOC-0060']
```

The retrieval metrics are equal on this cleaned, synthetic `filtered` family (all
strategies reach every relevant document at k=10), so the two numbers that separate them
are **mean results returned** and the selective case: pre-filtering and filter-aware
retrieval fill k and find the one matching document, while post-filtering returns 0. This
is reported as measured; the checker does not assert one strategy wins on quality.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. Against the
template it reports six TODOs and no failures; the mutation suite
(`_build/mutations.py`) plants nine bugs and each is CAUGHT by the named step.

## Notes on the eval-set import

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. Both `solutions/filtered.py` and `check.py` therefore import the eval set's
`corpus`, `queries` and `metrics` from `../eval-set/solutions` (adding that directory to
`sys.path`). The import is lazy, so `load_documents`, `evaluate` and check step 4 are the
only things that need it; steps 1–3 and 5–6 run on hand-built corpora and work in a bare
temporary directory (which is what lets the mutation harness run them without the eval
set).

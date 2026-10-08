# Solutions — RAG project 7 (corrective RAG, offline)

The complete implementation and the measurement it produces. Read
[`corrective.py`](corrective.py); its docstring names each design decision and the cost of
the choice, and `check.py` in the parent directory grades the template against the same
behaviour.

## What it builds

- `load_eval_set(seed=0)` — locates `../eval-set/solutions`, imports its `corpus`,
  `queries` and `metrics`, and returns the generated corpus, its documents, the family dict,
  the flattened query list and the metrics module.
- `quality_gate(results, threshold=None)` — `"weak"` when the results are empty, the top
  score is below the threshold, or the top-`GATE_TOPK` documents share too few terms;
  `"ok"` otherwise. Computed from the results only.
- `rewrite_prf(query, results, top_n, terms)` — pseudo-relevance feedback: counts the
  non-stopword terms shared across the top-`top_n` results, sorts by `(-count, term)`,
  appends up to `n_terms` new terms and returns the original terms followed by the added
  ones. Deterministic.
- `SECOND_CORPUS` / `build_second_corpus()` — five deterministic "external" documents
  covering topics the primary corpus lacks, returned as a fresh list.
- `retrieve_primary(query, k, documents)` — the first stage: scored results from the sibling
  `../bm25` (metadata filters included, empty result abstains), with a self-contained Okapi
  BM25 fallback. Scores and content terms are recomputed locally so the gate has a stable
  signal.
- `retrieve_second(query, k, documents=None)` — the fallback over the second corpus.
- `corrective_retrieve(query, k, documents, threshold=None)` — the loop: primary → gate →
  PRF rewrite + retry → second corpus → keep the best or abstain. Returns
  `{"documents", "results", "path", "gate", "expanded", "abstained"}` with `path` one of
  `raw`, `rewritten`, `fallback` or `abstain`.
- `evaluate(query_sets, documents=None, k=5, threshold=None)` — per query, both pipelines
  against `_relevance_map`, the path counts and the abstention count, and mean
  recall@k/MRR/nDCG@k per family and overall (exponential-gain nDCG, matching
  `../eval-set/solutions/metrics.py`).

## Expected output

`python3 solutions/corrective.py` (from `rag-from-scratch/corrective/`, seed 0):

```
primary corpus: 66 documents; second corpus: 5 documents
correction: heuristic gate (top score + top-3 consensus), PRF rewrite (top_n=3, +5 terms), second-corpus fallback
raw retrieval:
  lexical     n= 6 recall@5=1.000 mrr=0.917 ndcg@5=0.938
  semantic    n= 5 recall@5=0.950 mrr=0.900 ndcg@5=0.913
  filtered    n= 4 recall@5=1.000 mrr=1.000 ndcg@5=1.000
  multi_hop   n= 3 recall@5=0.304 mrr=1.000 ndcg@5=0.929
  no_answer   n= 6 recall@5=0.000 mrr=0.000 ndcg@5=0.000
  overall     n=24 recall@5=0.653 mrr=0.708 ndcg@5=0.708
corrective retrieval:
  lexical     n= 6 recall@5=1.000 mrr=0.917 ndcg@5=0.938
  semantic    n= 5 recall@5=0.950 mrr=0.900 ndcg@5=0.913
  filtered    n= 4 recall@5=1.000 mrr=1.000 ndcg@5=1.000
  multi_hop   n= 3 recall@5=0.304 mrr=1.000 ndcg@5=0.929
  no_answer   n= 6 recall@5=0.000 mrr=0.000 ndcg@5=0.000
  overall     n=24 recall@5=0.653 mrr=0.708 ndcg@5=0.708
paths: raw=21 rewritten=2 fallback=0 abstained=1 (n=24)
invented documents: 0 (every returned doc_id belongs to a corpus)

limit case 1 - query drift: PRF adds off-topic terms
  raw 'widget'        -> ['R', 'X']
  PRF expansion        -> ['widget', 'gadget', 'sprocket']
  rewritten            -> ['X', 'Y', 'R'] (the off-topic doc overtakes the relevant one)

limit case 2 - a weak query the correction cannot help
  'zzzq nonexistent topic' -> path=abstain documents=[] gate=weak (empty, not a hallucination)
```

The numbers are reported as measured. Corrective **ties** the raw stage on this easy
synthetic corpus — the checker does not assert that correction wins — and the two
`rewritten` paths are no-answer queries whose weak match PRF confidently re-expands onto the
same wrong documents, which is the drift the limit case isolates. The value of the module is
the measurable path accounting and the two constructed limit cases, not a recall gain here.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. Against the
template it reports six TODOs and no failures or errors. The mutation suite
(`_build/mutations.py`) plants six bugs and each is CAUGHT by the named step: step 1
(always-`ok` gate), step 2 (no expansion), step 3 (fallback skipped, and fallback reading the
primary corpus), step 4 (path decided from the test judgments), step 6 (abstention returns
the whole corpus). Run it with:

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/corrective rag-from-scratch/corrective/_build/mutations.py
```

## Notes on the eval set and the sibling imports

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. `solutions/corrective.py` and `check.py` therefore import its `corpus`, `queries`
and `metrics` from `../eval-set/solutions` (adding that directory to `sys.path` lazily).
`evaluate` accepts an explicit document list, so the self-contained leak check and every
hand-built step run in a bare temporary directory without the eval set. The first stage
imports `../bm25/solutions` and falls back to a self-contained Okapi BM25 when the sibling
is absent, so the mutation harness (which copies only the solutions and `check.py`) still
runs. nDCG uses the exponential gain `2**grade - 1` with the `log2` discount, exactly the
shared `metrics.ndcg_at_k`, and step 4 cross-checks the raw recall against that module.

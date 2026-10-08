# RAG project 1, stage 3 — FUSION (hybrid search)

The combination stage of [hybrid search]: it asks the lexical [BM25](../bm25/) stage and
the dense [LSA](../lsa/) stage for their rankings of the **same** documents for the
**same** queries (the shared [evaluation set](../eval-set/)), and fuses the two into one
ranking. A lexical query that names an exact policy code and a paraphrase that shares no
token with its answer are handled by different stages; fusion is how one system serves
both. HNSW and trained embeddings are later passes.

This is a graded module in the repo's `graded-module` format. Fill in the template
`fusion.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/fusion
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/fusion.py # the demo: BM25 / LSA / RRF / weighted on seed 0
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network).
`check.py` imports `../bm25/solutions/bm25.py` and `../lsa/solutions/lsa.py` the same way
the LSA checker reaches BM25, and adds `../eval-set/solutions` to `sys.path` lazily.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | fusion.py | `rrf` matches hand-computed `Σ w_r / (k + rank_r)` scores, including a single-ranking key and a deliberate tie broken by id |
| 2 | fusion.py | `normalize_scores` min-max and z-score match hand values (and a constant list does not divide by zero); `weighted_fusion` reproduces a hand-computed combined ranking |
| 3 | fusion.py | fusion recovers a dense-only document (synonym) **and** a lexical-only document (rare literal) that one stage misses — the point of hybrid search; a BM25-only fusion fails it |
| 4 | fusion.py | end to end on the eval set (seed 0): BM25, LSA, RRF and weighted reported per family with **paired** per-query win/loss/tie counts, whichever way it goes |
| 5 | fusion.py | limit: weights tuned on one family (lexical) degrade another (semantic) — weights do not transfer |
| 6 | fusion.py | limit: both stages empty makes fusion abstain; one stage empty still returns the other's hits; a filter that empties both abstains |

## Design decisions

Summarised; the full rationale is in the `solutions/fusion.py` docstring.

- **The fusion input is a ranking, not a document.** Each stage is adapted through a
  `scored(query, depth, filters) -> [(doc_id, score)]` hook, so BM25 and LSA can change
  internally without touching the fusion logic and the fusion logic is testable on
  hand-built rankings. Cost: a stage that exposes only doc_ids must be re-scored to
  recover magnitudes; LSA's scores are recomputed exactly from its fitted model, and BM25
  is re-derived from the corpus with the same Okapi formula and tokeniser (check step 4
  asserts the re-derived numbers equal the siblings').
- **RRF is `Σ w_r / (k + rank_r)` with 1-based ranks and `k = 60`,** ties by id ascending.
  Robust to BM25 scores and cosine similarities not being comparable as numbers. Cost: it
  discards magnitude entirely, so unanimous #1s and marginal #1s score the same.
- **Weighted fusion min-max normalises each stage per query, then weight-sums.** A
  document a stage did not return contributes `0.0` from that stage. z-score is offered as
  the alternative. Cost: min-max is compressed by a single outlier; z-score can go
  negative, which is only meaningful with the missing-document value fixed at 0.0.
- **Abstention is inherited and asymmetric:** both stages empty means the hybrid returns
  `[]`; one stage empty still returns the other's hits. That asymmetry is the whole point
  of hybrid search, so it is pinned by step 6.
- **The comparison is paired and per query.** A sign test over the discordant pairs and
  the mean per-query difference are reported, not two independent averages, because the
  same queries are run through every method. Cost: with 24 queries the test has little
  power, which is stated rather than hidden.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/fusion rag-from-scratch/fusion/_build/mutations.py`
— every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | `rrf` uses `rank` instead of `1/(k+rank)` | hand-computed RRF scores and order |
| 1 | `rrf` ignores the per-retriever weights | weighted order assertion |
| 2 | `normalize_scores` forgets the min | hand min-max values |
| 2 | `normalize_scores` divides by zero on a constant list | constant-list case |
| 2 | `weighted_fusion` adds raw scores without normalising | hand combined ranking |
| 3 | the hybrid drops the second stage (degenerates to BM25) | dense-only recovery in step 3 |
| 6 | the no-answer path returns the whole corpus | both-empty abstention case |

## Questions to answer (no answers here)

1. RRF uses only ranks; weighted fusion uses magnitudes. Construct a pair of rankings where
   the two methods disagree on the winner, and say which one you would trust and why.
2. Min-max maps each stage's best candidate to 1.0, so on the shared set RRF and weighted
   fusion coincide in the reported metrics (recall@10 and the paired counts), even though
   their orderings can differ. What property of the score lists makes them differ, and how
   would you detect that it holds before choosing a method?
3. Step 5 tunes a single scalar split between two stages and shows it does not transfer
   across families. What would a per-family (or per-query) weighting cost, and how would
   you keep it from overfitting the 24-query set?
4. The paired sign test on 24 queries cannot reach `p < 0.05` unless almost every query
   moves one way. Is that a failure of fusion or of the eval set? How would you increase
   power without leaking the test set?
5. Fusion can only return documents some stage retrieved. Give a query in the eval set's
   families where the correct document is in neither stage's candidate list, and say what
   layer has to change.
6. Abstention is `both stages empty`. What false-abstention and false-answer failure modes
   does that rule have, and where does a calibrated threshold belong?

## Limits

- Fusion is recall-bounded by its stages: it can never surface a document neither stage
  retrieved.
- The shared eval set is saturated on three of five families (both stages at 1.000), so
  step 4 is honest but low-signal there; only `multi_hop` separates the methods.
- Weight tuning is a one-dimensional grid on a constructed case; it demonstrates
  non-transfer, it does not find a good weighting for the eval set.
- The BM25 adapter re-derives Okapi scoring rather than calling a scoring hook (the
  sibling exposes none); it is kept honest by step 4's exact-agreement assertion.
- No score calibration: the zero-score abstention rule is weak, exactly as in BM25/LSA.
- No reranker, no query classification, no learned fusion; those are later passes.

# RAG project 7 — corrective RAG (offline)

The [RAG plan](../README.md) row 7: **a retrieval-quality gate; query rewriting
(pseudo-relevance feedback first); fallback to a second corpus**. A first-stage retriever
is happy to return *something* even when the corpus has no good answer. Corrective RAG
(CRAG) wraps it in a small control loop: judge the first-stage result, correct it when it
looks weak — rewrite with pseudo-relevance feedback and retry, then fall back to a second
corpus — and never invent a document. This stage builds that loop in the standard library,
on the shared eval set's primary corpus and the sibling [`../bm25`](../bm25/) lexical stage.
The trained retrieval evaluator of the CRAG paper (Yan et al., 2024) needs labels and a
model and is explicitly deferred; the LLM rewrite and web fallback come later.

This is a graded module in the repo's `graded-module` format. Fill in the template
`corrective.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/corrective
python3 check.py              # stop at the first unimplemented step
python3 check.py --all        # run everything
python3 solutions/corrective.py   # the demo: raw vs corrective numbers and the limit cases
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network). `check.py`
adds `../eval-set/solutions` to `sys.path` only in the second half of step 4; `corrective.py`
reuses `../bm25/solutions` and carries a small in-module BM25 fallback so the hand-built
checks and the mutation harness run in a tree without the sibling.

## The pipeline

1. **First stage.** `retrieve_primary(query, k, documents)` retrieves from the shared
   eval-set corpus with the sibling BM25 stage (filters included), returning scored results
   with each document's content terms. A document matching no query term scores 0 and is
   dropped.
2. **Gate.** `quality_gate(results, threshold)` returns `"ok"` or `"weak"` from the results
   alone: weak when there is nothing, when the top score is below the threshold, or when the
   top-k documents share too few terms.
3. **Rewrite.** `rewrite_prf(query, results, top_n, terms)` assumes the top-n results are
   relevant, counts their most shared non-stopword terms and appends them to the query.
4. **Retry, then fallback.** A weak query is rewritten and retried; if it is still weak,
   `retrieve_second` searches a small deterministic external corpus. If nothing helps, the
   primary/rewrite result is kept — or the query abstains.
5. **Tag.** `corrective_retrieve` returns `{"documents", "results", "path", "gate",
   "expanded", "abstained"}` with `path` one of `raw`, `rewritten`, `fallback`, `abstain`,
   so the route taken is measurable.

## The second corpus

`SECOND_CORPUS` is a handful of deterministic in-module documents covering topics the
primary corpus lacks, so the fallback has somewhere to go offline:

| Doc | Topic |
|---|---|
| `EXT-0001` | surface-code quantum error correction |
| `EXT-0002` | mangrove restoration after storms |
| `EXT-0003` | lead-free terracotta glaze chemistry |
| `EXT-0004` | bicycle derailleur alignment |
| `EXT-0005` | sourdough starter hydration |

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | corrective.py | the gate calls a strong hand-built result `ok` and a near-zero or disagreeing one `weak`, deterministically and with no eval set |
| 2 | corrective.py | PRF adds a top-document term (not a stopword) and the rewritten query retrieves the document the raw query missed |
| 3 | corrective.py | a query only the second corpus answers misses the primary stage and is returned by the fallback, tagged `fallback` |
| 4 | corrective.py | end to end on the shared eval set: raw vs corrective recall@k, MRR and nDCG@k per family and the path counts; the corrective result is a valid retrieval, and blanking the labels does not change the paths |
| 5 | corrective.py | the limit cases: PRF query drift, and a weak query whose rewrite cannot help and whose fallback is empty |
| 6 | corrective.py | a no-answer query stays empty through the rewrite and the fallback |

## Prediction, and what the measurement says

Stated here before the checker was written into the docs: on this synthetic corpus the
forecast is that the **corrective stage ties the raw stage** on recall@k, MRR and nDCG@k —
lexical BM25 is strong here, so the gate has little to correct — while the value shows up in
the **path counts** and in the two limit cases. Seed 0, 66 primary + 5 external documents,
24 queries, k=5:

```
raw retrieval:          overall recall@5=0.653 mrr=0.708 ndcg@5=0.708
corrective retrieval:   overall recall@5=0.653 mrr=0.708 ndcg@5=0.708
paths: raw=21 rewritten=2 fallback=0 abstained=1 (n=24)
```

The tie is the honest result and the checker does **not** assert that correction wins. The
two `rewritten` paths are no-answer queries whose only match is a generic word: the gate
fires, PRF expands from those weak documents, and the retry looks confident on the same
wrong documents. That is query drift, not a fix — and the no-answer recall stays 0, so it is
visible. The first-stage `no_answer` behaviour is inherited unchanged from `../bm25`: five of
the six no-answer queries return a document, only one abstains, so abstention recall is 1/6
at precision 1.0.

## Design decisions

Summarised; the full rationale is in `solutions/corrective.py`.

- **The gate is a score/consensus heuristic, not a trained evaluator.** Weak when the top
  score is below a threshold *or* the top-k documents share too few terms. No labels, no
  model, no network; it cannot leak the test judgments. Cost: heuristic — it misses weak
  matches that agree, and its rewrite can make a weak match look strong. The trained
  evaluator is the deferred variant.
- **The correction is pseudo-relevance feedback, with explicit knobs.** PRF counts the
  most shared content terms of the top-n documents and appends them, excluding stopwords and
  the original terms. Deterministic. Cost: when the top-n are not relevant, the expansion
  drifts the query onto the wrong topic (step 5a).
- **The fallback is a tiny deterministic in-module corpus.** Offline, seeded, covering
  topics the primary corpus lacks, so the fallback path is testable with no network. Cost: a
  toy stand-in for a real web/enterprise search.
- **No path invents a document.** Every returned `doc_id` comes from one of the two corpora;
  when nothing helps, the primary/rewrite result is kept or the query abstains. Cost: a weak
  query may keep a weak result rather than say "I don't know" — the honest measurement
  shows it.
- **The gate reads only the results.** `check.py` re-runs the evaluation with the relevance
  labels blanked and requires identical path counts: a judgment-reading that actually moves
  a routing decision is caught. Cost: the check is behavioural, so a peek that never changes
  a path on the self-contained set (say, one that only upgrades a result the default gate
  already passes) is not caught; only the shared-set numbers would show its effect.

## Mutation table

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/corrective rag-from-scratch/corrective/_build/mutations.py
```

Every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | `quality_gate` always returns `"ok"` | a near-zero hand-built result list must be `weak` |
| 2 | `rewrite_prf` returns the original terms | the expansion must add a top-document term and retrieve the missed document |
| 3 | the fallback never runs | the fallback probe must be tagged `fallback` |
| 3 | the fallback returns the primary corpus | the returned document must not be a primary document |
| 6 | abstention returns the whole corpus | a no-answer query must stay empty |
| 4 | `evaluate` decides the path from the test judgments | blanking the labels must not change the path counts |

## Questions to answer (no answers here)

1. The gate reads only scores and term overlap, never the query. Which weak retrievals can
   it never catch, and what would a trained evaluator change about that?
2. The gate uses an absolute score threshold, so it depends on the corpus and the BM25
   constants. What breaks when the corpus scales up tenfold, and how would you normalise the
   signal?
3. PRF assumes the top-n are relevant. The step-5a drift is one consequence. What is the
   cheapest guard against it that does not just lower `top_n`?
4. On the shared set the corrective stage ties the raw stage. Is that because the loop is
   unnecessary here, because the gate is too conservative, or because the metric cannot see
   the difference — and how would you tell the three apart?
5. The second corpus is disjoint from the primary corpus's topics. What happens to
   precision when it overlaps, and when should the fallback be gated too?
6. `corrective_retrieve` keeps the rewrite when the fallback is empty. Is keeping a weak
   result better than abstaining? Which metric decides, and what does it cost on the
   answerable queries?
7. The trained retrieval evaluator is deferred. What labels would you need to collect, and
   how would you know it beats the heuristic gate rather than just fitting the eval set?

## Limits

- The gate is a two-signal heuristic with an absolute threshold tuned to this corpus; it is
  not calibrated and does not transfer.
- The rewrite is pseudo-relevance feedback only; there is no LLM rewriting and no feedback
  from answer quality.
- The second corpus is five hand-written documents; it is a test fixture, not a retrieval
  source, and every eval-set query is either answerable from the primary corpus or genuinely
  unanswered.
- The eval set is synthetic and regular, so the measured tie is not a transferable estimate
  of CRAG's value; only the structural checks and the limit cases are.

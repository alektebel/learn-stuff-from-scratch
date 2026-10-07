# RAG step 0 — the shared evaluation set

The corpus, query sets and metrics every retrieval project in
[rag-from-scratch](../README.md) is judged against. Built before any retriever: a
retriever you cannot measure is not a retriever.

This is a graded module in the repo's `graded-module` format. Fill in the templates,
run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/eval-set
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network).

## What is in the set

- **`corpus.py`** — a seeded, deterministic generator of a synthetic company-docs
  collection: 66 documents (60 current + 6 superseded revisions), with department,
  region, author, date, access level, topics and a policy code; three tables; 29
  entities and 30 typed relations for the graph project.
- **`queries.py`** — five families of query with graded relevance judgments:
  - `lexical` (6): an exact policy code;
  - `semantic` (5): a paraphrase of a topic;
  - `filtered` (4): topic plus region/year constraints;
  - `multi_hop` (3): answerable only through the `reports_to` relation;
  - `no_answer` (6): nothing in the corpus answers them; relevance is empty.
- **`metrics.py`** — recall@k, MRR, nDCG@k, abstention precision/recall, latency stats,
  and paired per-query comparison (Wilson interval, exact McNemar, seeded paired
  bootstrap), copied from [harness-lab/eval/stats.py](../../harness-lab/eval/stats.py).
- **`baseline.py`** — a trivial token-overlap retriever with metadata pre-filtering and
  abstention, so the metrics are exercised and later retrievers have a floor to beat.

## The eval set, in one line

| seed | documents | current | superseded | queries | lexical recall@10 | lexical MRR |
|---|---|---|---|---|---|---|
| 0 | 66 | 60 | 6 | 24 | 1.000 | 0.917 |

Overall baseline (seed 0): recall@10 = 0.693, MRR = 0.708, nDCG@10 = 0.713; abstention
precision = 1.0, recall = 1.0. The `no_answer` family scores 0.0 on retrieval metrics by
construction — abstention is what grades it.

## Design decisions

Named in full in the solution docstrings; the summary:

- **Synthetic and seeded** rather than downloaded (no network, and ground truth can be
  constructed instead of guessed). Cost: scores do not transfer to real corpora.
- **Superseded documents stay in the corpus**, never relevant. This is the invariant the
  whole set leans on; recall looks fine even when the stale version wins, which is why
  MRR and nDCG are reported too.
- **Graded relevance**, so nDCG is meaningful.
- **No-answer queries are constructed**, not sampled: empty relevance is a fact.
- **Recall of a no-answer query is 0.0**, not undefined, so the family is never silently
  skipped.
- **Abstention is a per-query classification**: empty ranked list = abstain.
- **Pairing** is the unit of comparison (same queries, same seeds).

## Provided vs learner

Templates are generated from `solutions/`; everything not listed here is *provided*
scaffolding (constants, `_current`, `_by`, `tokenize`, `_passes_filters`,
`LexicalBaseline.__init__`) and is copied unchanged into the template.

| File | The learner writes |
|---|---|
| `corpus.py` | `generate_corpus` |
| `queries.py` | `build_query_sets` |
| `metrics.py` | `recall_at_k`, `mrr`, `ndcg_at_k`, `abstention_metrics`, `latency_stats`, `evaluate`, `wilson_interval`, `mcnemar_exact`, `paired_bootstrap_ci` |
| `baseline.py` | `LexicalBaseline.retrieve` |

## Check steps

| # | File | What it proves |
|---|---|---|
| 1 | corpus.py | same seed → identical corpus; new seed → new corpus |
| 2 | corpus.py | metadata, version chains, tables, triples are well formed |
| 3 | queries.py | five families, unique qids, all fields present |
| 4 | queries.py | no-answer empty; superseded never relevant; filtered judgments consistent |
| 5 | metrics.py | recall@k and MRR on hand-computed cases |
| 6 | metrics.py | nDCG@k with graded relevance and the log discount |
| 7 | metrics.py | edge cases: empty relevance, k=0, k>n, ties, duplicates |
| 8 | metrics.py | abstention precision and recall |
| 9 | metrics.py | latency mean/median/p95/max |
| 10 | metrics.py | Wilson, exact McNemar, seeded paired bootstrap |
| 11 | baseline.py | filters, k limit, determinism, non-degenerate lexical scores |
| 12 | baseline.py | abstains on every no-answer query, none other |
| 13 | metrics.py | `evaluate()` per-family and overall assembly |

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/eval-set rag-from-scratch/eval-set/_build/mutations.py`
— every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | generator uses the global RNG | determinism check |
| 2 | `superseded_by` never set | version-chain structure check |
| 4 | superseded documents left in the ground truth | exclusion invariant |
| 4 | a no-answer query given non-empty relevance | empty-relevance invariant |
| 5 | MRR counts ranks from 0 | hand-computed MRR |
| 6 | nDCG without the log discount | hand-computed nDCG |
| 8 | abstention counts a returned document as correct | asymmetric abstention case |
| 11 | baseline ignores the k limit | k-limit assertion |
| 12 | baseline never abstains | no-answer abstention recall |

## Questions to answer before building the retrievers (no answers here)

1. The baseline gets lexical recall@10 = 1.0 but MRR = 0.917. Which query is it losing
   rank on, and what does that say about superseded documents in an index?
2. `no_answer` retrieval metrics are 0.0 by definition. If you wanted one number for the
   whole system, how would you combine retrieval and abstention, and where would it hide
   a system that abstains on everything?
3. The paired bootstrap resamples *queries*. What does the width of the interval tell you
   about how many queries this set needs before a reranker's gain is believable?
4. The filtered family pre-filters. What does check step 11 require of a post-filtering
   retriever, and how does the 0.1% filter limit case from the plan break it?
5. The corpus is synthetic and repetitive. Which failure mode of a real corpus can this
   set simply not see, and how would you add one without a network?

## Limits

- 24 queries is enough to exercise the metrics, not enough to settle a close comparison;
  see question 3.
- The vocabulary is controlled, so a method can look better here than it would on real
  text (in particular lexical overlap is unusually clean).
- Tables and the metadata store are generated but not queried yet; the SQL + vector and
  graph projects will add their own query families against the same corpus.

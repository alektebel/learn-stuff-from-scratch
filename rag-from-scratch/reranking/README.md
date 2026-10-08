# Reranking (RAG project 3)

Retrieve deep with the lexical first stage (`../bm25`), then rerank to a short list
with a **reranker trained here**. This is project-table row 3 of
[`../README.md`](../README.md): *retrieve 100, rerank to 5 with a reranker trained
here*.

## What it measures

The first stage decides what the reranker is even allowed to see. If the relevant
document is not in the first stage's top-100, no reranker can return it. That is the
**ceiling**: `recall@100` of the first stage bounds `recall@k` of the reranked list for
every reranker. The demo prints both numbers, and `check.py` step 5 makes the ceiling
bind by growing the index past the candidate budget, then shows the same reranker ranks
an injected document first.

The reranker is judged on two things:

1. Does it reorder a fixed candidate list? (It must never invent or fetch documents.)
2. Does it move relevant documents up the list, per query family, on a **held-out** set
   of queries that were not used for training?

On this corpus that is deliberately not the same as "does recall go up": the shared
corpus has 66 documents, fewer than the 100-deep candidate list, so the first stage
already returns everything relevant and recall@5 is capped by the list length. The
honest signal here is nDCG@5 on `multi_hop` (0.786 → 0.854); recall is flat. The demo
reports exactly that.

## Files

| File | Role |
|---|---|
| `rerank.py` | the template you implement |
| `check.py` | the six progress checks; `python3 check.py --all` |
| `solutions/rerank.py` | the reference implementation |
| `solutions/README.md` | design write-up and expected output |
| `_build/hints.py` | staged hints, from first nudge to near-answer |
| `_build/mutations.py` | planted bugs a passing checker must catch |

## The learned reranker (standard library only)

The repository's [`ml-systems/framework`](../../ml-systems/framework/) is the intended
trainer, but this environment has **no numpy and no pip** (Python 3.14) and that
framework's tensors are numpy-backed. This module therefore trains a small
**logistic-regression** ranker by deterministic gradient descent over nine hand-built
features, each a property of `(query, document)`:

1. `stage_score` — the first-stage BM25 score, squashed;
2. `lexical_cosine` — bag-of-words cosine between query and document;
3. `term_coverage` — distinct query terms present;
4. `idf_coverage` — coverage weighted by inverse document frequency;
5. `exact_phrase` — the whole query appears contiguously;
6. `title_match` — fraction of query terms in the title;
7. `length_ratio` — document length over the corpus average, capped;
8. `dense_cosine` — latent-semantic cosine from the sibling LSA stage;
9. `is_current` — 0.0 for a superseded document.

No feature encodes the candidate's rank, so the model cannot merely imitate the first
stage. `fit` runs a fixed number of gradient steps at a fixed step size from zero
weights; there is no random state. `ml-systems/framework` remains the alternative path
once numpy exists.

## The train/eval split

Queries are split, not documents: within each family, queries sorted by `qid` alternate
between train and eval, and the two sets are asserted disjoint. Splitting by document
would leak the query into training and turn the reported metric into training accuracy.
No-answer queries go to eval only — they carry no positive example, and they are what the
abstention metrics grade.

## Limits, and where the checks are adversarial

- **Dropped feature.** Step 1 requires *every* feature to vary across a toy document set
  for at least one query; a feature reduced to a constant fails even if the others vary.
- **No learning.** Step 2 uses a hand-built example whose first-stage feature ranks the
  distractor first and requires training to reverse it while the loss falls.
- **Whole-corpus scoring.** Step 3 hands the reranker a strict subset and requires the
  result to be a subset of it.
- **Leaky split.** Step 4 checks disjointness on a tiny query set before it touches the
  shared eval set, so the contract is verifiable on its own.
- **The ceiling.** Step 5 grows the index past the candidate budget, finds a relevant
  document outside the top 100, and asserts the reranker can reach it only when it is
  injected as a candidate.
- **Invented results.** Step 6 makes an empty first stage (an abstention) stay empty
  through the reranker.

## Mutation table

Every planted bug below is caught by the named step (`python3
.claude/skills/graded-module/scripts/mutate.py rag-from-scratch/reranking
rag-from-scratch/reranking/_build/mutations.py`):

| Mutation | Caught by |
|---|---|
| `rerank` echoes the candidate order (no-op) | step 2 |
| `term_coverage` dropped to a constant | step 1 |
| `rerank` re-scores the whole corpus | step 3 |
| `fit` leaves the weights at zero | step 2 |
| `fit` pins the weights to a constant and only learns the bias | step 2 |
| abstention path returns the whole candidate list | step 6 |
| the split leaks (eval queries also trained on) | step 4 |

## Reproducibility

No randomness: gradient descent runs a fixed number of iterations at a fixed step size,
weights start at zero, and ties break by document id. Two runs print the same numbers.

## Running

```sh
cd rag-from-scratch/reranking
python3 check.py --all          # your template against the six checks
python3 solutions/rerank.py     # the reference demo
```

The shared eval set is resolved from `../eval-set/solutions` exactly as `../bm25`,
`../lsa` and `../fusion` resolve it. The first stage is the sibling `../bm25` module, so
this project stages on top of project 1 instead of inventing a second retriever.

## Questions to answer before building (no answers here)

1. Why is the first stage's `recall@100` the correct ceiling, and why is `nDCG@5` the
   metric that can still improve after the first stage?
2. What goes wrong if training examples are split by document rather than by query?
3. A fresh policy and its superseded predecessor both match the query. Which feature
   lets the reranker prefer the current one, and what happens without it?
4. Why must the reranker's candidate list be fixed by the first stage, rather than the
   reranker scanning the corpus for each query?

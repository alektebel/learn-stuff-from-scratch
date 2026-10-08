# solutions — RERANKING (RAG project 3)

The complete implementation. `rerank.py` is pure standard library (`math`, `re`, `os`,
`pathlib`, `sys`, `collections`): no numpy, no pip, no network. It imports the sibling
first stage from `../bm25/solutions/bm25.py` (and `../lsa/solutions/lsa.py` for the dense
feature) and the shared evaluation set from `../eval-set/solutions/`, so the base and the
reranked numbers are measured on exactly the same documents and queries as every other
stage.

The repository's intended trainer is [`ml-systems/framework`](../../ml-systems/framework/),
but this environment has no numpy and no pip (Python 3.14), and that framework's tensors
are numpy-backed. The reranker is therefore a **logistic-regression ranker trained by
deterministic gradient descent** over nine hand-built features. The framework remains the
alternative path once numpy is available; the contract around the model — deep first
stage, fixed candidate list, disjoint train/eval queries, an honest ceiling — is the point
of this module.

Run the demo from the module directory:

```
cd rag-from-scratch/reranking
python3 solutions/rerank.py
```

## Expected demo output (seed 0)

```
seed 0, 66 documents, 24 queries
first stage: bm25, candidate depth 100; reranker: logistic regression trained here
train queries 10, eval queries 14 (disjoint: True)
first-stage recall@100 (the ceiling) = 1.000

family        base r@5  rerank r@5  base MRR  rerank MRR  base nDCG@5 rerank nDCG@5
lexical          1.000       1.000     1.000       1.000        1.000         1.000
semantic         1.000       1.000     1.000       1.000        1.000         1.000
filtered         1.000       1.000     1.000       1.000        1.000         1.000
multi_hop        0.267       0.267     1.000       1.000        0.786         0.854
no_answer        0.000       0.000     0.000       0.000        0.000         0.000
overall          0.519       0.519     0.571       0.571        0.556         0.561

reported as measured: the reranker is not assumed to beat the base ranking,
and its recall@5 can never exceed the first-stage ceiling above.

ceiling query: LEX-01 — a relevant document (DOC-0060) is not in the first-stage top-100 once the index holds more documents
  the reranker returns only candidates, so it cannot return it: ['CLONE-LEX-01-0000', 'CLONE-LEX-01-0001', 'CLONE-LEX-01-0002', 'CLONE-LEX-01-0003', 'CLONE-LEX-01-0004']
  injected as a candidate it is ranked first: ['DOC-0060']
```

## How to read these numbers honestly

- **The reranker does not beat the base ranking on recall@5, and that is reported as
  measured.** On this corpus the first stage already returns every relevant document
  within the top 100 (`recall@100 = 1.000`), and the families that fit in a top-5 list
  (lexical, semantic, filtered) are already perfect. The only signal is `multi_hop`: 15
  relevant documents cannot all fit in five slots, so recall@5 is capped by the list
  length, not by ranking quality. There the reranker leaves recall flat and improves
  nDCG@5 from 0.786 to 0.854 — it moves the graded-relevant documents up.
- The checks do **not** assert a win. Step 4 only asserts the split is disjoint and that
  the reranked recall@5 over answerable queries does not exceed the first-stage
  `recall@100` (the ceiling).
- The reranker is worth its place where the first stage's *order* is wrong but its
  *membership* is right. That is what nDCG@5 shows here; recall cannot show it.

## The ceiling on this corpus

The shared corpus has 66 documents, fewer than the 100-deep candidate list, so on seed 0
the depth-100 ceiling is **not binding** — the first stage returns the whole matching
corpus. To demonstrate the ceiling the module appends 140 deterministic clone documents
that repeat the query's own tokens, so BM25 ranks them above the real documents. Then a
relevant document (`DOC-0060` for `LEX-01`) genuinely falls outside the top 100:

- the reranker returns only the candidates it was given, so it cannot return `DOC-0060`;
- injected as a candidate, the same reranker ranks `DOC-0060` **first**.

That pair of facts is the whole lesson: the first stage, not the reranker, decides what is
reachable. `check.py` step 5 re-derives the case and asserts both halves.

## Design decisions (short form; the file has the full write-ups)

- **Pointwise logistic ranker, trained by fixed-step gradient descent.** No RNG, no
  seed; the same examples produce the same weights every run. Cost: it is linear, so it
  cannot learn feature interactions a cross-encoder would.
- **Nine features, each a property of `(query, document)`** — `stage_score`,
  `lexical_cosine`, `term_coverage`, `idf_coverage`, `exact_phrase`, `title_match`,
  `length_ratio`, `dense_cosine`, `is_current`. No feature encodes the candidate's rank,
  so the model does not merely imitate the first stage. Cost: it must combine the stage
  score with text evidence itself.
- **`is_current` is a feature.** Superseded documents are never relevant even though
  their text matches; without this the reranker would promote stale policies. Cost: it
  relies on revision metadata being present.
- **The split is by query, alternating within each family, and asserted disjoint.**
  Splitting by document would leak the query into training. Cost: few queries per family,
  so the held-out estimate has wide error bars.

`check.py` on the solutions is the executable version of this page:

```
cd rag-from-scratch/reranking
cp solutions/rerank.py rerank.py        # or work in a temporary copy beside ../eval-set
python3 check.py --all
```

`check.py` adds `../eval-set/solutions`, `../bm25/solutions` and `../lsa/solutions` to
`sys.path` lazily, in the steps that need them (1, 2, 3 and 6 are hand-built and need no
siblings; step 4's split contract is checked on a tiny query set before the shared eval set
is touched, so it is verifiable even when the fixture is absent).

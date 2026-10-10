# RAG project 8 — Self-RAG (offline control loop)

The [RAG plan](../README.md) row 8: **decide whether to retrieve, grade the evidence, check
support of the answer**. Self-RAG (Asai et al., 2023) trains a model to emit *reflection
tokens* during decoding — a retrieve decision, a relevance grade per passage, and a support
grade for the answer. This module builds the part that does not need the trained model: the
**control loop** around those decisions, with the reflection model injected. A deterministic
`OverlapReflectionModel` stands in offline, so the loop is seeded, standard-library only and
checkable; the prompted/trained model is the deferred variant (see Limits).

This is a graded module in the repo's `graded-module` format. Fill in the template
`self_rag.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/self-rag
python3 check.py              # stop at the first unimplemented step
python3 check.py --all        # run everything
python3 solutions/self_rag.py # the demo: accuracy, abstention and path counts
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network). Only step 4
needs the shared eval set in `../eval-set`; steps 1, 2, 3 and 5 run on hand-built passages
and scripted models, so the mutation harness works in a bare temporary directory.

## The loop

`self_rag_answer(query, retriever, model)` returns `{"answer", "evidence", "path",
"retrieved", "attempts", "supported"}` with `path` one of `no_retrieve`, `answered`,
`abstain`:

1. **Decide.** `should_retrieve` asks the model; an unclear or missing decision retrieves
   (retrieval can only add evidence), a query with no content terms does not, and a
   no-retrieve call abstains rather than answer from weights the offline loop does not have.
2. **Retrieve.** The injected `retriever(query, k)` returns scored passages (the demo builds
   one over the shared corpus; the checks pass hand-built ones).
3. **Grade.** `grade_evidence` keeps exactly the passages the model marks relevant, in
   retrieval order — a subsequence, never a re-ranking and never an invention.
4. **Draft and check.** `_extractive_answer` returns the evidence passage's most on-topic
   sentence; `check_support` asks the model whether that sentence follows from the evidence.
   Supported → the answer is returned with its evidence; unsupported → the passage is
   dropped and the loop retries, up to `MAX_ATTEMPTS`, then abstains.

`evaluate` runs the loop over every family of the shared eval set and reports answer
accuracy, abstention precision/recall and the path counts. It scores; the loop decides, so it
never reads the relevance judgments and blanking them cannot change a path.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | self_rag.py | the retrieve decision is fail-safe: no decision or no model retrieves, a clear no does not, a content-free query never does |
| 2 | self_rag.py | evidence grading keeps exactly the relevant passages, in order, and nothing below `min_relevant` |
| 3 | self_rag.py | every branch of the loop: no-retrieve abstains, a supported draft is answered, no relevant evidence abstains, an unsupported draft retries then abstains |
| 4 | self_rag.py | end to end on the shared eval set: no evidence is invented, and blanking the labels leaves the path counts unchanged |
| 5 | self_rag.py | the limit cases: a query nothing matches abstains, and relevance without support never produces an answer |

## Measurement, and what it says

Seed 0, 66 documents, 24 queries, k=5, with the overlap reflection model:

```
answer accuracy (answerable): 0.833   (15/18)
abstention precision/recall:  0.833 / 1.000
paths: {'answered': 19, 'abstain': 5} (n=24)
  lexical   correct 0.833   semantic 0.800   filtered 1.000
  multi_hop correct 0.667   no_answer 0.833
```

The checker asserts none of these numbers — it asserts the structural invariants (no
invention, no label leak) and the branches. `multi_hop` is the weakest family (2/3): the
relation needs the `reports_to` hop the lexical retriever alone cannot make, so the answer's
evidence is a related but not the judged document. One `no_answer` query (of six) is answered
by a generic-word overlap, so abstention precision is 0.833 while recall is 1.0: the loop
abstains on every query that truly has no answer, but not only on those. That is the honest
result; the loop is not claimed to beat anything here.

## Design decisions

Summarised; the full rationale is in `solutions/self_rag.py`.

- **Reflection is an injected interface, not a trained model.** The loop is the module; the
  three decisions (retrieve? relevant? supported?) arrive from a `model` argument. The
  offline `OverlapReflectionModel` answers them by content-term overlap. Cost: the numbers
  measure the loop, not a real model's reflection — the loop is what transfers, not the
  scores.
- **No parameterised answering.** A no-retrieve decision abstains. Cost: a real model would
  answer from its weights; the offline loop cannot, and says so instead of hallucinating.
- **The answer is extractive.** `_extractive_answer` returns the evidence's most on-topic
  sentence, so support is checkable without generation. Cost: no fluent prose; the support
  check grades the evidence, not the wording.
- **Relevance and support are separate gates.** Grading a passage relevant does not mean it
  supports the drafted sentence; step 5 is exactly that gap. Cost: two model calls per
  attempt.
- **The loop never sees the judgments.** `self_rag_answer` reads only `text` and `filters`;
  step 4 blanks the labels and requires identical paths. Cost: the check is behavioural, so a
  peek that never moves a path is not caught.

## Mutation table

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/self-rag rag-from-scratch/self-rag/_build/mutations.py
```

Every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | `should_retrieve` always retrieves | the clear-no model must not retrieve |
| 2 | `grade_evidence` ignores the model | the relevant-only subsequence |
| 3 | `check_support` always returns True | the unsupported draft must retry, then abstain |
| 3 | `self_rag_answer` ignores the retrieve decision | the no-retrieve path must abstain |
| 5 | `self_rag_answer` answers without support | the over-eager model must not answer |
| 4 | `evaluate` decides the path from the labels | blanking the labels must not change paths |

## Questions to answer (no answers here)

1. The offline reflection model is term overlap. Which reflection verdict is it most wrong
   about — retrieve, relevant, or supported — and what does a real model change?
2. `should_retrieve` defaults to retrieving on an unclear decision. When is that the wrong
   default, and what does it cost on a query the corpus cannot answer?
3. The extractive answer is one sentence. What fraction of the support failures is the
   sentence choice rather than the passage, and how would you tell?
4. The loop drops a passage and retries on an unsupported draft. Is dropping the right move,
   or would re-drafting from the same evidence be better? Which metric decides?
5. `multi_hop` is the weakest family. Is that the retriever, the support check, or the
   corpus — and what would you add to separate them?

## Limits

- The reflection model is a heuristic, not trained and not prompted; the scores do not
  transfer, and the module is not an evaluation of Self-RAG as published.
- The answer is extractive and one sentence; a generative answer would change the support
  check entirely.
- The retriever is a lexical overlap ranker (the sibling stages' baseline), so retrieval
  error and support error are confounded in the numbers.
- `MAX_ATTEMPTS` and `MIN_RELEVANT` are fixed constants, not tuned, and the eval set is
  synthetic and regular.

# rag_attack — an adversarial harness for a retrieval system (agent-evals #5)

## What it is

A standard-library-only harness that probes one retrieval system with deterministic
adversarial inputs and reports where it breaks. It answers one question an ordinary recall
score cannot: given a query whose true document the system finds today, does a **small,
meaning-preserving change** to the query push that document out of the top-k, and does a
**cheap injected document** that merely repeats the query's own words climb above it?

It needs no model — retrieval is offline. It needs a *system under test* (SUT) and the shared
evaluation set. The SUT is a factory `sut_factory(documents) -> retrieve`, so the harness can
hand the system an **augmented** corpus: the real documents plus one synthetic poison
document built from the query. `retrieve(query, k) -> [{"doc_id", "score"}, ...]` ranks at
most k documents.

LEARN mode: the SUT adapters, the eval-set loader and the token/metric helpers are shipped
**implemented** as test infrastructure (decided: implemented — the tests need a corpus and a
ranked result to attack, not the attack itself). The four attack entry points
(`perturb_text`, `poison_document`, `probe`, `evaluate_attacks`) are `NotImplementedError`
stubs; the tests define what the learner must make true.

## What it demonstrates

The correction recorded in `agent-evals/README.md`, row #5: **recall@k is a single number
that hides a whole class of failures.** A term-count retriever scores 1.0 clean and 1.0 after
our attack, because the true document never left the top-k — yet the attack *succeeded*: a
document nobody wrote, stuffed with the query's words, now sits above the answer. The harness
therefore reports three separate things per family: clean recall, attacked recall, and an
`attack_success` rate that counts a dropped answer **or** a poison in the top-k. It also
separates answerable queries (scored by recall) from no-answer probes (scored by whether the
system correctly abstained) — the same abstention split the RAG project uses.

The attack has two independent knobs, and the harness measures their effect instead of
assuming it:

- **perturbation** — a typo/synonym-free character edit that breaks exact-term matching
  without changing intent;
- **poisoning** — a new document outside the ground truth that lexically mimics the query.

A robust system survives both. A lexical one fails the second. The report says which.

## The interface

```python
# --- provided infrastructure (implemented; its tests pass today) ---

def tokenize(text: str) -> list[str]: ...
def content_terms(text: str) -> list[str]: ...          # tokens minus stopwords
def local_sut_factory(documents) -> LocalRetriever: ...  # deterministic lexical SUT

class LocalRetriever:
    def __call__(self, query, k: int = 5) -> list[dict]: ...

def load_eval_set(seed: int = 0) -> dict: ...
    # {"documents", "query_sets", "queries"} from rag-from-scratch/eval-set

def _recall(ids, relevant, k: int) -> float | None: ...
    # fraction of relevant docs in the top k; None when there are none

# --- the core (LEARN: implement these) ---

def perturb_text(text: str, *, seed: int, rate: float) -> str: ...

def poison_document(query, *, seed: int = 0) -> dict: ...

def probe(sut_factory, documents, query, *,
          k: int = 5, rate: float = 0.2, seed: int = 0) -> dict: ...

def evaluate_attacks(sut_factory, documents, query_sets, *,
                     k: int = 5, rate: float = 0.2, seed: int = 0) -> dict: ...
```

`probe` returns EXACTLY: `qid`, `clean` (doc_ids), `attacked` (doc_ids), `relevant`
(doc_ids), `dropped` (relevant was found clean and is gone after), `poisoned` (the poison
entered the attacked top-k), `abstained` (attacked result empty).

`evaluate_attacks` returns `{"families": {family: report}, "overall": report}`; every report
has EXACTLY: `n`, `answerable`, `clean_recall`, `attacked_recall`, `attack_success`, `drops`,
`poisons`, `abstention`. Recall is the mean of `_recall` over the answerable probes;
`attack_success` is the fraction of answerable probes where the answer was `dropped` or the
result was `poisoned`; `abstention` is the fraction of no-answer probes that abstained, or
`None` when the family has none. The attack reads only the query **text**, never its
judgments — otherwise it would be cheating.

Determinism: every stochastic entry point takes an explicit `seed` and uses its own
`random.Random`; nothing depends on global RNG state or `PYTHONHASHSEED`. Standard library
only (no numpy, no pip in this environment).

## Attack families (from the shared eval set)

| family | what it stresses |
|---|---|
| `lexical` | exact-term matching; the easy case, and the poison's easiest target |
| `semantic` | vocabulary mismatch (paraphrase) |
| `filtered` | metadata filters; a perturbation that changes a term cannot bypass a filter, but a poison that ignores filters can |
| `multi_hop` | answers spread across documents |
| `no_answer` | must abstain; scored by `abstention`, not recall |

## Acceptance

- **A1** `perturb_text` alters roughly `rate` of the words by a single edit (swap, delete,
  duplicate, next-letter substitution), preserves the word count, and is deterministic.
- **A2** `poison_document` returns a corpus-shaped document whose id is prefixed `ADV-`,
  derived from the query id, and **not** in the query's ground truth; its text repeats the
  query's content terms.
- **A3** `probe` returns the exact key set and correctly flags `dropped` (answer leaves the
  top-k) and `poisoned` (the injected id enters it), independently.
- **A4** `evaluate_attacks` produces the exact per-family and overall shape; counts answerable
  vs no-answer probes; computes recall only over answerable ones.
- **A5** on the lexical SUT the harness reports clean recall 1.0 **and** `attack_success` 1.0
  — the poison is detected even though recall never moved.

## Limit cases

- **L1** `rate <= 0` is the identity, so the perturbation is a no-op and only the poison can
  fire.
- **L2** words shorter than two characters are left alone; nothing raises.
- **L3** the whole report is reproducible under a fixed seed.
- **L4** a SUT that always returns the true document first is never marked `dropped`, even at
  `rate = 1.0` — the harness must not manufacture failures.
- **L5** a family with no answerable queries reports `abstention`; a family with no no-answer
  queries reports `abstention = None`; recall of an empty answerable set is `None`, not 0.

## Out of scope

Generation, citations and hallucination checking (reliability #5, needs a model); a CLI;
persisting reports; attacking a live service (that is #8's fuzzer). This module probes
retrieval only, offline.

## How to run

```sh
cd agent-evals && python3.12 -m pytest -q tests/test_rag_attack.py
# 2 passed, 14 xfailed  -- infrastructure green, core unwritten
# implement the four stubs -> the 14 xfail turn into passes
```

Reference metrics (local SUT, hand-built corpus, `seed=0`): clean recall 1.0, attacked recall
1.0, `attack_success` 1.0 via poisoning — the point of A5.

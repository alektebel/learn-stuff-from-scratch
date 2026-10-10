# edge_cases — generate synthetic edge cases for a gold task set (LEARN mode)

## What it is

A small, dependency-free **generator of edge cases** for an evaluation set. Given a gold
set of task statements, it derives inputs that probe the failures a happy-path set misses —
an empty request, a non-ascii one, an over-long one, a boundary value, a self-contradictory
instruction, a prompt-injection payload — and then refuses the two ways a generator lies: a
near-copy of a task already in the set, and a case that is trivially solvable.

It is project #12. The original brief suggested a model-backed generator; a model call is
neither reproducible nor testable, and a paraphrase of a gold task teaches nothing. This
generates by **deterministic transformations** instead: a seed and the gold set fix every
case. A model-backed generator is named as out of scope.

Everything is standard library and deterministic: no numpy, no network, no model calls, and
no dependence on Python's salted `hash()`.

## What it demonstrates

- **Generation must be reproducible.** The same seed and gold set give the same cases, so a
  regression in generated input is a real diff, not sampling noise.
- **Novelty is measured, not assumed.** MinHash estimates the shingle-overlap of a case with
  the gold set and with the cases already kept, so a near-duplicate is dropped (A4, L1).
- **Cosmetic differences are not novelty.** Case, whitespace and punctuation variants are
  the same case after `normalize` (L4).
- **A generator can emit a worthless case.** One whose transformation did nothing, or whose
  text is empty, is filtered before it reaches the set (A3, L2).
- **A cheap estimate has a known error.** MinHash agrees with exact Jaccard closely enough to
  gate on, and the contract says so rather than pretending they are equal (L3).

## The interface

Module: `agent-evals/edge_cases/edge_cases.py`, imported as `edge_cases.edge_cases`.
Constants: `FAMILIES`, `NEGATIONS`, `INJECTION_MARKERS`, `GOLD`.

```python
Case(source, family, statement, meta={})

# implemented infrastructure (tests may rely on it now)
normalize(text) -> str
shingles(text, k=3) -> set[str]
jaccard(a, b, k=3) -> float
minhash(text, k=3, n=64) -> tuple[int, ...]
minhash_similarity(a, b, k=3, n=64) -> float

# core the learner writes (NotImplementedError until then)
transform(family, statement, rng) -> list[str]
generate(gold, seed=0, families=FAMILIES) -> list[Case]
is_trivial(case, gold) -> bool
deduplicate(cases, gold, threshold=0.9, k=3, n=64) -> list[Case]
build(gold, seed=0, families=FAMILIES, threshold=0.9) -> list[Case]
```

Contracts the stubs must satisfy once implemented:

- `transform` — a pure function of `(family, statement, rng)` returning at least one string
  that **differs** from `statement`, per family:
  - `empty` — the empty / whitespace-only input (`"".join(s.split()) == ""`);
  - `unicode` — a statement containing at least one non-ascii codepoint (`ord(c) > 127`);
  - `long` — a statement whose length is at least three times the source's;
  - `boundary` — a statement that injects a numeric boundary and differs from the source;
  - `contradiction` — a statement containing a member of `NEGATIONS`;
  - `injection` — a statement containing a member of `INJECTION_MARKERS`.
  An unknown family raises `ValueError`.
- `generate` — for each gold task and each requested family, one `Case(source, family,
  statement)` whose `source` is the gold id; deterministic for a fixed `(gold, seed,
  families)`; only the requested families appear.
- `is_trivial` — true for a case whose normalised statement is empty **or** equal to
  `normalize(gold[case.source])` (the transformation changed nothing; a missing source is
  treated as unchanged only if empty).
- `deduplicate` — keep a case iff its `minhash_similarity` to every gold statement and to
  every already-kept case is **below** `threshold`; order of the input decides which of two
  near-copies survives.
- `build` — `generate`, then drop `is_trivial`, then `deduplicate`; reproducible end to end.

## Acceptance items

- **A1** `generate` is deterministic for a fixed seed and returns one case per
  (task, family), covering exactly the requested families.
- **A2** each `transform` family produces a statement with the property named above, and
  differs from its source; an unknown family raises `ValueError`.
- **A3** `is_trivial` is true for an empty statement and for an unchanged one.
- **A4** `deduplicate` drops a case that is a near-copy of a gold task and keeps a novel one.
- **A5** `build` returns a reproducible list with no trivial cases and no near-duplicates.

## Limit cases

- **L1** Two generated cases that are near-copies of each other: only the first survives.
- **L2** A transformation that returns the source unchanged is filtered by `is_trivial`, so
  it never reaches `deduplicate`.
- **L3** `minhash_similarity` stays within 0.1 of exact `jaccard` on the sample texts.
- **L4** A case differing from a gold task only in case or whitespace is a duplicate.
- **L5** An empty gold mapping yields an empty case list, with no crash.

## Out of scope

- Calling a model to invent cases; generation is deterministic transformations.
- Executing the generated cases or scoring a model on them; that is the runner's job.
- Attacks on a live system (that is #5/#8); these are offline inputs for a gold set.
- Coverage guarantees: dedup measures overlap, not whether the families are *sufficient*.

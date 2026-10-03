# SPADE From Scratch

Replicate **SPADE** — synthesising data-quality assertions from prompt version
history — in pure Python, then **cite** each surviving assertion back to the
prompt delta that justified it, using the ContextCite machinery next door.

> **Shankar et al. "spade: Synthesizing Data Quality Assertions for Large
> Language Model Pipelines." PVLDB 17(12), 2024.**
> [paper](https://www.vldb.org/pvldb/vol17/p4173-shankar.pdf) ·
> [code](https://github.com/shreyashankar/spade-experiments)

Do [`../contextcite/`](../contextcite/) first. The last check here imports it.

## What the paper does

Developers iterate on prompts. Each edit is a *delta*. Deltas quietly encode
the failure modes the developer has already seen. SPADE:

1. Diffs consecutive prompt versions into **prompt deltas**
2. Classifies each added sentence against a **taxonomy** (structural vs content)
3. Turns each classified delta into **candidate assertions** (boolean functions)
4. Selects a **minimal set** that covers labelled failures without exceeding a
   false-failure-rate budget — an ILP in the paper; a small exact search here
5. Uses **subsumption** when labels are too few to identify a useful assertion

**The selected assertions are the product.** Everything else is how you stop
shipping fifty overlapping checks.

## Why it sits next to ContextCite

SPADE tells you *which checks to run*. ContextCite tells you *which context
caused the output those checks are looking at*. The last file here, `cite.py`,
attributes each surviving assertion to the prompt-delta sentence that produced
it. An assertion you cannot cite back to a delta is a guess you happened to
keep.

```bash
cd week-05/spade
python3 check.py          # 8 graded checks against YOUR code
```

Checks only. The templates raise `NotImplementedError`. There is no
`solutions/` yet — fill the stubs, then compare with the paper.

## The files

| File | What it is |
|---|---|
| `fixtures.py` | **Provided** — a movie-recommendation prompt history and labels |
| `deltas.py` | Diff consecutive versions; additions are the candidates |
| `taxonomy.py` | Structural vs content-based categories from Figure 2 |
| `candidates.py` | Turn a classified delta into a boolean assertion |
| `selector.py` | Cover failures, cap false-failure rate, drop subsumed checks |
| `cite.py` | Attribute each kept assertion to its source delta via ContextCite |

No dependencies beyond the Python 3 standard library and `../contextcite/`.

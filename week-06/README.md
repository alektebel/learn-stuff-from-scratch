# Week 6 · Sep 28–Oct 4, 2026

> **Provenance, algebraically.**
> The exact version of last week. Annotate a query with semiring elements and the derivation falls out as an algebraic object — not estimated, computed.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`provenance-semirings/`](provenance-semirings/) | 45 | core |

**45 block hours**, plus the daily Lean slot (~8.4 h) = 53 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `semiring.py` first: the laws, and the concrete semirings. Get the annihilator and identity right before anything else; `Why`'s zero and one are the classic silent error.
2. `krelation.py` — the operators are **forced**, not chosen. Alternatives get `+`, joint requirements get `×`. Every operator definition is one of those two.
3. **The universality check is the one that matters**: evaluate a query once in ℕ[X], then derive every other semantics by mapping the answer, and assert it agrees with having evaluated natively. An operator using the wrong operation passes every row-count test and fails exactly this one.
4. Then recursion, and the termination question absorption answers.

## Done means

- `week-06/provenance-semirings/` prints 8/8.
- One query, evaluated once, yielding set semantics, bag semantics, why-provenance, shortest path and security clearance.
- You can say why a cyclic graph has no fixpoint over ℕ[X] and does over PosBool, and why that is the same fact as minimality.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 6
python3 ../progress.py --checks
```

[← Week 5](../week-05/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-6) · [Week 7 →](../week-07/)

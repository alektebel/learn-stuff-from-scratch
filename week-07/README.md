# Week 7 · Oct 5–Oct 11, 2026

> **Goal-directed reasoning.**
> Answer set programming that runs backwards from a query, with justification trees as a first-class output and negation that actually works.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`scasp/`](scasp/) | 45 | full only |

**45 block hours**, plus the daily Lean slot (~8.4 h) = 53 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `unify.py` and the resolution core first.
2. Then dual-rule generation — constructive negation is the mechanism that makes s(CASP) different from a Prolog with a `not`.
3. Then coinductive success, for loops through even negation.
4. Justification trees last. They are the deliverable: an answer you can read the derivation of.

## Done means

- `week-07/scasp/` prints 8/8.
- A query answered with a justification tree you can read aloud.
- You can say what a dual rule is for, and what breaks without one.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 7
python3 ../progress.py --checks
```

[← Week 6](../week-06/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-7) · [Week 8 →](../week-08/)

# Week 8 · Oct 12–Oct 18, 2026

> **Parser in front, prover behind.**
> The neurosymbolic architecture, and an honest measurement of what it buys. The claim is that all residual risk moves to the parse step and stays auditable there. Half of that is true.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`linc/`](linc/) | 30 | full only |
| [`distributed-training/`](distributed-training/) | 18 | full only |

**48 block hours**, plus the daily Lean slot (~8.4 h) = 56 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `fol.py` and `parser.py`, then the prover.
2. `faults.py` is the interesting file: the parse-error taxonomy from LINC's own error analysis — dropped negation, flipped quantifier, reversed implication, hallucinated predicate, dropped premise.
3. `pipeline.py` last, and **measure two things**: the share of errors that arrive with a valid proof of a wrong conclusion, and the fraction of premises an audit actually has to read.
4. `distributed-training` is short — ten hours. You already wrote gradient accumulation in `autograd`; this is the same idea with a network in between.

## Done means

- `week-08/linc/` prints 8/8.
- You can say which parse faults fail SAFE (the prover falls silent) and which fail CERTIFIED (a valid proof of the wrong thing), and why the second kind is worse than an unjustified guess.
- A data-parallel loss curve matching single-device training.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 8
python3 ../progress.py --checks
```

[← Week 7](../week-07/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-8) · [Week 9 →](../week-09/)

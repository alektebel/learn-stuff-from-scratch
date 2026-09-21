# Week 17 · Dec 14–Dec 20, 2026

> **Databases deeper, light, and Haskell.**
> The heaviest week, and still the most arbitrary — three unrelated things sharing a slot. If the plan slips this is the week to cut from, and `haskell-projects` (61 h) is the first candidate: it is orthogonal to everything else you are keeping, and the other two have checkers while it does not.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`database-internals/`](database-internals/) | 45 | core |
| [`ray-tracer/`](ray-tracer/) | 35 | full only |
| [`haskell-projects/`](haskell-projects/) | 61 | full only |

**141 block hours**, plus the daily Lean slot (~8.4 h) = 149 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `database-internals` first, and `estimation.py` before anything else in it. Reproducing the Leis et al. result — that estimation error compounds multiplicatively with join count, so the planner picks a bad plan **correctly** from bad numbers — changes how you read every `EXPLAIN` for the rest of your life. It needs week 9 finished.
2. `ray-tracer`: `vec.py` → `shapes.py` → `bvh.py` → `material.py` → `render.py`. **Predict what noise does from 16 to 64 samples before reading the table.**
3. `haskell-projects` last: JSON parser first — parser combinators are the payoff — then the calculator, then the build tool. Delete each `-- TODO`.

## Done means

- `week-17/database-internals/` prints 11/11.
- You can say why your `EXPLAIN` lies, and it is not the cost model.
- `week-17/ray-tracer/` prints 6/6 and `render.ppm` opens in an image viewer.
- You can say why a BVH is 1.5x at four objects and 12x at a thousand.
- Your JSON parser round-trips a nested document with escapes and unicode.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 17
python3 ../progress.py --checks
```

[← Week 16](../week-16/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-17) · [Week 18 →](../week-18/)

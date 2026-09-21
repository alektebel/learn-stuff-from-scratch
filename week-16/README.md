# Week 16 · Dec 7–Dec 13, 2026

> **CUDA.**
> One directory, one hundred and twenty-two hours, no context switching. Memory hierarchy, coalescing, shared memory, occupancy, then a matmul you tune yourself.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`cuda-from-scratch/`](cuda-from-scratch/) | 142 | core · spine |

**142 block hours**, plus the daily Lean slot (~8.4 h) = 150 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. Strictly the directory's own order. Every kernel builds on the previous one's understanding of memory.
2. **Profile every kernel you write.** `ncu` or `nsight-compute`. A kernel you have not profiled is a kernel you do not understand.
3. Keep the table as you go: kernel, GB/s achieved, GB/s theoretical, occupancy. That table is the week's real deliverable.
4. Delete each `TODO` comment as you satisfy it — the CUDA bars in `progress.py` only move if you do.

## Done means

- A naive, a tiled and a register-blocked matmul, with measured GFLOP/s for each.
- You can say what fraction of peak bandwidth each kernel reaches and why the gap is what it is.
- You can explain warp divergence in terms of the mask stack from week 15.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 16
python3 ../progress.py --checks
```

[← Week 15](../week-15/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-16) · [Week 17 →](../week-17/)

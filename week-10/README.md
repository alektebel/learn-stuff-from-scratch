# Week 10 · Oct 26–Nov 1, 2026

> **Consensus, and its refusal.**
> The same partition, opposite answers. A bank ledger wants one; a shopping cart wants the other. Having built both, you can say which.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`dynamo-paper/`](dynamo-paper/) | 21 | core · spine |
| [`raft/`](raft/) | 30 | core |

**51 block hours**, plus the daily Lean slot (~8.4 h) = 59 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `dynamo-paper` first, with the SOSP 2007 paper open. `partitioning.py` and `vector_clock.py` before anything else — the rest assumes them.
2. **Predict the availability table for (3,2,2), (3,3,1) and (3,1,3), sloppy and strict, before running `dynamo_cluster.py`.** The cells you got wrong are the ones you learned from.
3. `raft` after it, and read Figure 8 **before** you write `replication.py`. It is the counterexample that makes the obvious commit rule wrong.
4. Write the Raft-versus-Dynamo table in the journal before you move on.

## Done means

- Two checkers green: 17/17 and 7/7.
- You can say why 'a majority has it' is the wrong commit rule, using Figure 8 and not a hand-wave.
- You can say what Dynamo refuses and what that refusal buys.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 10
python3 ../progress.py --checks
```

[← Week 9](../week-09/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-10) · [Week 11 →](../week-11/)

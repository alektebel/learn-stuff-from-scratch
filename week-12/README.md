# Week 12 · Nov 9–Nov 15, 2026

> **AWS certification block.**
> The graded half of exam preparation: service selection under constraints, storage and network arithmetic, DR patterns with computed RPO and RTO. The ungraded half is the drill you have been running since week 1.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`aws-certification/`](aws-certification/) | 35 | core |
| [`aws-deploy/`](aws-deploy/) | 20 | core |

**55 block hours**, plus the daily Lean slot (~8.4 h) = 63 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. **Pull the current official exam guides first** and diff them against the check list. Codes, blueprints and service names change; treat any conflict as the guide being right.
2. `decide.py` — elimination by a **named** constraint, and boundaries that actually move when a requirement changes.
3. `storage.py`, `network.py`, `resilience.py` — the arithmetic. Reuse the minimum-object-size and minimum-duration rules from week 1's `pricing.py`.
4. `mlstack.py` — the SageMaker and Bedrock surface mapped onto mechanisms you already built. The serverless-vs-provisioned crossover is the same shape as DynamoDB's.
5. `wellarchitected.py` last. A review returning six green ticks is a review that was not done.
6. `aws-deploy` alongside it — `check.py` lints policy documents, IaC graphs and idle cost **offline**, with no account and no spend.
7. **`RUNBOOK.md` is the other half and it is not graded.** Phase 0 should already be done from week 1; phases 1–6 are a real account, a real domain and a real failed build. It ends on the only claim here that cannot be faked: rebuild the whole stack from empty, from code, in under an hour, and tear it down to a zero bill. Twice.

## Done means

- `week-12/aws-certification/` prints 10/10.
- `resilience.py` returns the **cheapest** pattern clearing a stated RPO, not the best one.
- The drill has a twelve-week streak. That is the part that decides whether you pass.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 12
python3 ../progress.py --checks
```

[← Week 11](../week-11/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-12) · [Week 13 →](../week-13/)

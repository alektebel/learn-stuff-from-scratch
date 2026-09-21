# Week 5 · Sep 21–Sep 27, 2026

> **Attribution, on a real task.**
> Three takes on the same question: which part of the input is this answer actually resting on? Statistical, then structural, then applied to text-to-SQL.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`contextcite/`](contextcite/) | 13 | core |
| [`spade/`](spade/) | 16 | core |
| [`mars-sql/`](mars-sql/) | 20 | core |

**49 block hours**, plus the daily Lean slot (~8.4 h) = 57 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `contextcite` first — ablation plus a LASSO surrogate. It is the approximate answer, and the one that works without any structure.
2. `spade` next: candidate deltas, a taxonomy, and selection.
3. `mars-sql` last, and it is the applied one — schema linking, ReAct recovery after a bad query, generative selection against majority vote, and citing the SQL back to its schema sources.
4. Hold the comparison in view: week 6 does this **exactly** and algebraically. These three do it approximately, on inputs where exact is not available.

## Done means

- Three checkers green: 14/14, 8/8, 8/8.
- You can say what ContextCite estimates and what it cannot know.
- A typo in a generated query becomes an observation the agent recovers from, rather than a crash.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 5
python3 ../progress.py --checks
```

[← Week 4](../week-04/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-5) · [Week 6 →](../week-06/)

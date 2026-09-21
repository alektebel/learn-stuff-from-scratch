# Week 18 · Dec 21–Dec 27, 2026

> **The long tail.**
> Five small directories, deliberately. Finishing on five completions beats finishing mid-way through something large.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`spectral-graphs/`](spectral-graphs/) | 5 | full only |
| [`sas-lineage-tool/`](sas-lineage-tool/) | 8 | full only |
| [`web-scraping/`](web-scraping/) | 6 | full only |
| [`ml-in-production/`](ml-in-production/) | 8 | full only |
| [`mlops/`](mlops/) | 12 | full only |

**39 block hours**, plus the daily Lean slot (~8.4 h) = 47 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `spectral-graphs`, then `sas-lineage-tool`, then `web-scraping`, then `ml-in-production`, then `mlops` — a day or less each.
2. Then go back to [`../reference/`](../reference/) and write the comparison you have been owed since week 4: your scheduler and paged allocator against vLLM's, your batching against TensorRT-LLM's.
3. **Reserve the last day.** Run every checker in the repo, re-read the journal from week 1, and write the closing entry: what you can now re-derive that you could not in August.

## Done means

- `python3 ../progress.py --track <yours> --checks` reports every checker passing.
- A written comparison of your serving stack against the production ones.
- A closing journal entry. It is the only artifact of these eighteen weeks that will still be useful in a year.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 18
python3 ../progress.py --checks
```

[← Week 17](../week-17/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-18)

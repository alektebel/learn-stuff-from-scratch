# Week 9 · Oct 19–Oct 25, 2026

> **A database from the disk up.**
> Pages, an index, a log, isolation, a parser, a planner and an executor. The highest density of reusable mechanism per hour in the repo.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`database-engine/`](database-engine/) | 77 | core · spine |

**77 block hours**, plus the daily Lean slot (~8.4 h) = 85 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `pager.py` first: slotted pages, free-space arithmetic, the buffer pool and its LRU. **Predict how many rows fit in a 4096-byte page before running the demo.**
2. Then `btree.py`, then **`wal.py` before `mvcc.py`** — durability is one writer and a disk, isolation is several writers and each other. The other order makes both confusing.
3. Then `sql.py` (recursive descent, precedence climbing), `executor.py` (Volcano iterators), `planner.py`, `database.py`.
4. The eighteen checks are the order — for the SQL half.
5. `lsm.py` next, the counterweight to `btree.py`: memtable, immutable sorted runs, bloom filters, tombstones, and both compaction policies. **Measure read, write AND space amplification** — the RUM conjecture says you get two of three, and the point is seeing which corner each policy stands in rather than being told.
6. **The head-to-head is the check to write first:** run both structures on a write-heavy and a read-heavy workload. If one wins both, the workload is not exercising the difference.
7. `datastep.py` last. The PDV, the implicit loop, `RETAIN`, BY-groups with `first.`/`last.`, `MERGE`, `OUTPUT`/`DELETE`. Then the same five transformations in SQL — the interesting rows are the two SQL cannot express cleanly.

## Done means

- `week-09/database-engine/` prints 18/18, plus the LSM and DATA step checks.
- You can say why an LSM is write-optimised in one sentence without using the
  word "fast", and name what it gave up to get there.
- You can name a transformation the DATA step expresses cleanly and SQL does
  not, and say why.
- You can say in one sentence what `wal.py` promises after a crash and what `mvcc.py` promises a concurrent reader — and why write skew slips past the second one.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 9
python3 ../progress.py --checks
```

[← Week 8](../week-08/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-9) · [Week 10 →](../week-10/)

# Week 13 · Nov 16–Nov 22, 2026

> **Sockets.**
> The systems half of the plan starts here. Everything you have built for twelve weeks sits on the other side of a file descriptor; this is that side.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`bash-from-scratch/`](bash-from-scratch/) | 8 | core |
| [`http-server/`](http-server/) | 86 | core · spine |

**94 block hours**, plus the daily Lean slot (~8.4 h) = 102 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `bash-from-scratch/shell.c` first — two days. `fork`, `exec`, `wait`, pipes, signals, exit statuses.
2. Then `http-server` for the rest of the week: accept loop, then request parsing, then static files, then a real 404 — in that order, running a real browser against it after each one.
3. Concurrency and keep-alive last, and do not stop until it survives load.

## Done means

- `./shell` runs `ls | grep x > out.txt` and survives `Ctrl-C`.
- A browser renders a page with its CSS and images, each with the right `Content-Type`.
- `ab -n 10000 -c 100` completes with zero failed requests.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 13
python3 ../progress.py --checks
```

[← Week 12](../week-12/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-13) · [Week 14 →](../week-14/)

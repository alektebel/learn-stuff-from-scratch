# Week 14 · Nov 23–Nov 29, 2026

> **What a byte stream carries.**
> A name lookup, a checksum, five wire protocols with framing, and a proxy that reads none of it.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`dns-server/`](dns-server/) | 9 | full only |
| [`cryptographic-library/`](cryptographic-library/) | 5 | full only |
| [`communication-protocols/`](communication-protocols/) | 34 | full only |
| [`toralizer/`](toralizer/) | 21 | full only |

**69 block hours**, plus the daily Lean slot (~8.4 h) = 77 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `dns-server` and `cryptographic-library` are short and mostly parsing — treat them as one two-day block.
2. `communication-protocols` is the week's bulk. `uart.c` and `spi.c` first; I2C, CAN and RS-485 build on their framing ideas.
3. `toralizer` last — a socket exercise you are now over-prepared for, which is the point of putting it here.

## Done means

- Your resolver answers A and CNAME queries against a real root server and retries over TCP on truncation.
- Your SHA-256 matches `sha256sum` on ten files, including an empty one and one landing exactly on a block boundary.
- You can draw the UART, SPI and I2C frame layouts from memory and say which needs a clock line and why.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 14
python3 ../progress.py --checks
```

[← Week 13](../week-13/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-14) · [Week 15 →](../week-15/)

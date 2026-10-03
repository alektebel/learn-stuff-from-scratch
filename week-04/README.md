# Week 4 · Sep 14–Sep 20, 2026

> **Serving it yourself.**
> Twelve steps from 'what happens on the GPU for one token' to 'find the point where throughput stops scaling and explain why'. Build it, watch it fall apart, fix the specific thing that broke.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`inference-from-scratch/`](inference-from-scratch/) | 70 | core · spine |
| [`deploy-and-debug/`](deploy-and-debug/) | 10 | core |

**80 block hours**, plus the daily Lean slot (~8.4 h) = 88 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. Work the directory's own order: `inference_path.py` → `naive_server.py` → `batching.py` → `kv_runtime.py` → `scheduler.py` → `paged_kv.py` → `gpu_opt.py` → `speculate.py` → `observe.py` → `traffic.py`.
2. **Measure TTFT, TPOT and throughput from step 3 onward**, not at the end. The point of the naive server is to watch specific numbers degrade.
3. `deploy-and-debug` alongside it — it is the one that teaches you to read a fault signature instead of guessing.
4. `compare.py` and `deeper.py` last. Then go read [`../reference/vllm-engine/`](../reference/vllm-engine/) with your own scheduler open beside it. That comparison is why those directories are reference and not schedule.

## Done means

- Two checkers green: 12/12 and 12/12.
- A latency-versus-throughput curve for your own server, and you can point at the knee and say what is saturating.
- You can explain why decode is memory-bandwidth bound and prefill is not.
- A written comparison against vLLM's design decisions.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 4
python3 ../progress.py --checks
```

[← Week 3](../week-03/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-4) · [Week 5 →](../week-05/)

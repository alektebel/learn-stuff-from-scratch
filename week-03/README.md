# Week 3 · Sep 7–Sep 13, 2026

> **Teaching a model: distil, then reward.**
> Two ways to supervise a model that already runs. A teacher gives you a full distribution at every token; RL gives you one scalar at the end of the episode. Same axis, opposite ends.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`rl-posttraining/`](rl-posttraining/) | 30 | core |
| [`context-caching/`](context-caching/) | 28 | core |

**58 block hours**, plus the daily Lean slot (~8.4 h) = 66 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. **Write the nine checks in `rl-posttraining/check.py` first.** The bodies are not written; each docstring says what to assert and names the weak version to avoid. Then implement against them.
2. `policy_gradient.py` against finite differences before anything else — every later claim assumes it.
3. Then `baselines.py`, `kl_estimators.py` (k3 is the only one both unbiased and non-negative), `ppo.py`, `grpo.py`, `async_rl.py`, `reward_hacking.py`, `dpo.py`.
4. `context-caching/kv_cache.py` next, and **do not move past it until cached and uncached attention agree to zero** — not small, zero. You have your own attention from week 2 to check it against.
5. Then the prefix, radix, paged, semantic and routing caches.

## Done means

- Two checkers green: 9/9 and 16/16.
- `serving_demo.py` reports bit-identical output with the cache on and off. If it does not, the cache is a bug, not a cache.
- You can say why k1 goes negative and k3 does not, and why that decided it.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 3
python3 ../progress.py --checks
```

[← Week 2](../week-02/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-3) · [Week 4 →](../week-04/)

# Week 2 · Aug 31–Sep 6, 2026

> **LLMs.**
> The arithmetic under everything downstream, then a working transformer on top of it. Eighty-five hours and the heaviest week in the plan — it is heavy because `autograd` has to be finished before `llm-from-scratch` can start.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`autograd/`](autograd/) | 30 | core · spine |
| [`llm-from-scratch/`](llm-from-scratch/) | 55 | core · spine |

**85 block hours**, plus the daily Lean slot (~8.4 h) = 93 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `autograd/tensor.py` first: reverse mode over arrays, topological sort, gradient accumulation, `_unbroadcast`. **Do not move on until every operation's gradient matches central differences.**
2. Then `nn.py`, `optim.py`, `train.py`, `generative.py`. 10/10 before you open the next directory.
3. `llm-from-scratch/tokenizer.py` — BPE, merges applied in **rank order**. Pure string processing, so it needs none of the above.
4. Then `attention.py` → `transformer.py` → `train.py` → `sample.py`.
5. `distill.py` last: forward vs reverse KL, on-policy vs off-policy, the privilege illusion. It is the bridge into week 3.

## Done means

- Two checkers green: 10/10 and 15/15.
- A tensor used twice gets the SUM of both paths, and you can say why running `backward` before the topological sort finishes trains a slightly worse model forever without ever raising an error.
- You can demonstrate permutation-equivariance by shuffling the input of a transformer with its positional information removed.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 2
python3 ../progress.py --checks
```

[← Week 1](../week-01/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-2) · [Week 3 →](../week-03/)

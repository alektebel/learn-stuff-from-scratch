# Week 15 · Nov 30–Dec 6, 2026

> **Compilers, and a machine for them.**
> The clearest MVP-then-limit-case ladder in the repo: it works on `1+2`, then a nested expression breaks the register allocator, then a branch breaks the GPU's lockstep assumption.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`firewall-from-scratch/`](firewall-from-scratch/) | 25 | full only |
| [`c-compiler/`](c-compiler/) | 27 | core · spine |
| [`compiler-and-vgpu/`](compiler-and-vgpu/) | 16 | core · spine |
| [`quantum-computing-lang/`](quantum-computing-lang/) | 8 | full only |

**76 block hours**, plus the daily Lean slot (~8.4 h) = 84 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. `firewall-from-scratch` first — raw sockets and packet parsing, the last purely-systems thing before compilers.
2. `c-compiler` is the week's spine. **Get `int main(){return 2+3;}` compiling and running end to end on day one, THEN add features.** A compiler that compiles nothing on Sunday is the standard way this week fails.
3. `compiler-and-vgpu` after it — one 32-bit ISA, two execution models. `python3 check.py` grades you.
4. `quantum-computing-lang` is a palate cleanser: an interpreter over complex amplitudes.

## Done means

- Your C compiler compiles a program with a loop, a function call and recursion, and the binary runs.
- `week-15/compiler-and-vgpu/` prints 12/12.
- You can explain why right-nested expressions spill registers and left-nested ones do not, and what a warp does at an `if` where lanes disagree.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 15
python3 ../progress.py --checks
```

[← Week 14](../week-14/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-15) · [Week 16 →](../week-16/)

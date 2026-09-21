# Week 11 · Nov 2–Nov 8, 2026

> **Byzantine, and open membership.**
> The third corner. Raft and Dynamo both assume participants follow the protocol and that you know who they are. Neither survives an open network where lying is profitable, and Sybil resistance is the only genuinely new idea here.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`blockchain-from-scratch/`](blockchain-from-scratch/) | 55 | core |

**55 block hours**, plus the daily Lean slot (~8.4 h) = 63 h on the full track.

Plus the AWS drill, daily, since week 1 — [`../week-12/aws-certification/drill.py`](../week-12/aws-certification/drill.py). It is not graded and it cannot be crammed.

Plus **~2 h on the live system** — see [`../LIVE.md`](../LIVE.md). It runs from week 1 because ninety days of uptime takes ninety days, and that is the one requirement here that effort cannot compress.

## What to do, in order

1. **Write the eleven checks first.** Each docstring names the weak version to avoid — several of these checks pass trivially if written carelessly.
2. `chain.py`, `pow.py`, `utxo.py`, `script.py` — the Bitcoin half.
3. `fork.py` is the week's centre: heaviest **work** not most blocks, Nakamoto's `(q/p)^k` simulated against the closed form, and selfish mining swept over gamma.
4. `accounts.py`, `evm.py`, `trie.py`, `pos.py` — the Ethereum half, carried as two design decisions: UTXO vs accounts, and no-jumps vs gas.
5. `pos.py` last: hand-build conflicting finality and assert at least a third of the stake is slashable. Same shape as Raft's Figure 8.

## Done means

- `week-11/blockchain-from-scratch/` prints 11/11.
- You can say what proof of work actually buys, in one sentence, without using the word puzzle.
- You can explain why 'six confirmations' is a risk tolerance rather than a guarantee.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 11
python3 ../progress.py --checks
```

[← Week 10](../week-10/) · [Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-11) · [Week 12 →](../week-12/)

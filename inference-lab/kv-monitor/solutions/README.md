# KV-cache monitor — solutions

Complete versions of the three templates (`allocator.py`, `simulator.py`,
`monitor.py`) plus the provided `kv.py`. Pure Python 3, standard library only.

## Verify the solutions

`check.py` imports the files next to it, so run it from a copy that holds the solutions:

```bash
cd inference-lab/kv-monitor
d=$(mktemp -d) && cp solutions/*.py check.py "$d" && (cd "$d" && python3 check.py --all)
```

Expected:

```
  1. allocator.py blocks_needed rounds up to whole blocks
  2. allocator.py the pool never over-allocates or over-releases
  3. simulator.py a workload that fits completes with no preemption
  4. simulator.py an over-subscribed workload preempts, not crashes
  5. monitor.py   utilisation, headroom and a preemption-free cap

  5/5 passing
```

## Demos

Run from this directory (the files import each other by name).

`python3 kv.py` — the arithmetic:

```
KV cache arithmetic — Llama-3-8B
  bytes per token: 131,072 (128 KiB)
  one 16-token block: 2.0 MiB
  A100-80GB at util 0.90: 27648 blocks = 54.0 GiB of KV
  a 32k-token sequence needs 2048 blocks
```

`python3 allocator.py` — the pool:

```
block allocator — total 8 blocks, block_size 4
  blocks_needed(0, 4)=0 blocks_needed(4, 4)=1 blocks_needed(5, 4)=2 blocks_needed(16, 4)=4
  allocate(5): used=5 free=3 utilisation=62%
  fits(3)=True fits(4)=False
  release(5): used=0 free=8
```

`python3 simulator.py` — the step loop, by concurrency cap:

```
simulate — 8 blocks of 4 tokens, three 8->16 token requests
  cap=None: peak=8/8 blocks, preemptions=1, completed=3, oom=False
  cap=   3: peak=8/8 blocks, preemptions=1, completed=3, oom=False
  cap=   2: peak=8/8 blocks, preemptions=0, completed=3, oom=False
  cap=   1: peak=4/8 blocks, preemptions=0, completed=3, oom=False
```

`python3 monitor.py` — the reading and the recommendation:

```
monitor — three 8->16 token requests against 8 blocks of 4 tokens
  peak utilisation: 100%
  steps above 90%:  3 of 16
  preemptions:      1
  recommended max_num_seqs: 2 (preemptions there: 0)
```

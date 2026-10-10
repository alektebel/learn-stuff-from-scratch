# KV-cache monitor

A block-level memory monitor for an LLM server. Given a trace of requests and a fixed
pool of KV cache blocks, it replays a continuous-batching step loop, tracks how full the
pool gets, and finds the concurrency that spends the pool **without preempting**. No GPU:
the mechanism is real, the block accounting is real, the numbers are the simulator's.

This is inference-lab project **#3**. The *calculator* half — bytes per token, cache
capacity, max concurrent sequences — already exists in
[`deploy-and-debug/capacity.py`](../../deploy-and-debug/capacity.py) and is restated here as
provided infrastructure (`kv.py`). The new work is the monitor built on top: the part that
watches a running server and tells you when it is about to fall off the memory cliff.

## Why this, and what it teaches

A capacity calculation answers "how many blocks do I have?". It does not answer "how close
does my traffic get to spending them, and what happens when it does?". A serving stack that
runs out of KV blocks does not crash — it **preempts**: it evicts running work, frees its
blocks, and recomputes it later. Preemption is the symptom that the pool, not the
concurrency cap, is the binding constraint. The block rounding (`ceil(L / block_size)`) means
every sequence wastes up to `block_size - 1` tokens of its last block; at small block sizes
that waste is a rounding error, at large ones it is a capacity decision.

## Steps

| step | file | check | what you build |
|---|---|---|---|
| 1 | `allocator.py` | `blocks_needed` rounds up to whole blocks | `blocks_needed` |
| 2 | `allocator.py` | the pool never over-allocates or over-releases | `BlockAllocator.allocate` / `.release` |
| 3 | `simulator.py` | a workload that fits completes with no preemption | `simulate` |
| 4 | `simulator.py` | an over-subscribed workload preempts, not crashes | `simulate` (the preemption path) |
| 5 | `monitor.py` | utilisation, headroom and a preemption-free cap | `peak_utilisation`, `steps_above`, `recommend_max_num_seqs` |

## How to run

```bash
cd inference-lab/kv-monitor
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # every step; TODO is not a failure
```

Provided and not to be edited: `kv.py` (the arithmetic and the request model). `check.py`
and `solutions/` are the grader and the reference. Start each file's `__main__` demo once it
runs.

## Design decisions (named, with the cost)

- **Simulated, not measured.** No GPU here, so the loop advances "one step = one decode
  token" and prefill is instant. This isolates the memory question and makes the run
  deterministic; the cost is that no number here is a latency or a throughput. That is
  project #2's job, on hardware.
- **Blocks, not bytes.** A serving stack admits and evicts whole blocks, so utilisation is
  `used_blocks / total_blocks`. Exact byte accounting would fit a few more tokens but no
  attention kernel addresses half a block; the waste is the point.
- **Preemption picks the sequence with the most blocks.** It frees the most room in the
  fewest evictions. The alternatives — most recently admitted (vLLM's default), longest —
  trade fewer recomputes against more of them; see the questions.
- **A request that cannot fit alone is rejected, not queued.** `blocks_needed(prompt +
  output) > total_blocks` can never complete; naming it in `rejected` beats an infinite
  queue. `oom` is reserved for the simulator failing to make progress at all.
- **The recommendation is the largest preemption-free cap.** Preemption means the pool
  bound the workload; the biggest cap that never preempts spends it without thrashing. A
  smaller cap is idle concurrency.
- **The headroom threshold is 0.9, and it is a parameter.** At 90% utilisation the queueing
  factor is ~9x the service time; an alert should fire below full, not at it.

## The numbers on a tiny pool

From the demos (`python3 kv.py`, `python3 monitor.py`): Llama-3-8B on an A100-80GB at
`gpu_memory_utilization=0.90` leaves **27,648 blocks (54 GiB)**, and one 32k-token sequence
needs 2,048 of them. On the toy pool (8 blocks of 4 tokens, three requests that each peak at
4 blocks):

```
cap=None: peak=8/8 preemptions=1 completed=3
cap=   3: peak=8/8 preemptions=1 completed=3
cap=   2: peak=8/8 preemptions=0 completed=3   <- recommended
cap=   1: peak=4/8 preemptions=0 completed=3
```

The monitor reports peak utilisation 100%, three steps above 90%, and recommends
`max_num_seqs = 2`.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py <this dir> <this dir>/_build/mutations.py`

| planted bug | file | step that catches it |
|---|---|---|
| floor instead of ceil in `blocks_needed` | `allocator.py` | 1 |
| allocate without the fits guard | `allocator.py` | 2 |
| admit without reserving blocks | `simulator.py` | 3 |
| no preemption, just OOM | `simulator.py` | 4 |
| recommendation ignores preemption | `monitor.py` | 5 |
| peak utilisation always 0 | `monitor.py` | 5 |

## Questions (answer them yourself)

1. On the toy trace the recommendation is 2. If preemption evicted the *most recently
   admitted* sequence instead of the largest allocation, would all three still complete?
   Which metric would show the policy's cost?
2. The peak is 100% for several steps. Is a full pool efficient or dangerous? What would you
   measure (not "utilisation") to tell the two apart?
3. `capacity.py` sizes the pool against the *average* context. How does block rounding in
   `blocks_needed` change the number of sequences that average supports?
4. Double `block_size`. Does the per-sequence waste rise or fall, and what happens to the
   preemption count on this trace? (Try it.)
5. Preemption here keeps a sequence's generated tokens. If it were recomputed from the
   prompt instead, what extra quantity would the monitor need to report?
6. Why is `gpu_memory_utilization` 0.90 and not 1.0, and which failure does the *monitor*
   catch that the capacity calculation cannot?

## Limits

- No hardware: one step is one token, prefill is free. The output is block counts, not
  latency or throughput (that is #2).
- No chunked prefill (#8) and no paged copy-on-write, beam search or shared-prefix blocks
  (#9); the last partial block is waste, full stop.
- Preemption keeps progress and costs nothing to recompute; the recompute tax is not
  modelled.
- One pool on one node; no prefill/decode disaggregation or KV transfer (#10).

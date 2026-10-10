"""
simulator.py — a continuous-batching step loop with a real block budget (solution).

`simulate` replays a trace of requests against a fixed KV block pool, one
serving step at a time, and records what the cache looked like at each step.
It is a *scheduler* model, not a model of the hardware: prefill is instant (no
chunked prefill — that is #8), the model costs nothing, and the only scarcity is
the block pool.

Sources
-------
- Kwon et al., PagedAttention (SOSP 2023), §5: when the pool is exhausted the
  scheduler *preempts* running sequences and their blocks are freed; a
  preempted sequence is recomputed later. Preemption, not crashing, is the
  back-pressure.
- vLLM `max_num_seqs`: an upper bound on concurrent sequences, a scheduling knob
  independent of how many blocks exist.

DESIGN DECISION — decode is one token per step, per running sequence.
  A wall-clock model needs hardware; the block *trajectory* does not. What this
  isolates is the memory question: when does the pool fill, and what does the
  scheduler do then.

DESIGN DECISION — preemption picks the running sequence with the most blocks.
  Alternatives: the most recently admitted (vLLM's default priority order), or
  the longest one. Freeing the largest allocation makes room in the fewest
  evictions; a recompute or FIFO policy is a different trade-off and a fine
  exercise (see the README questions). Preempted work keeps its progress: it is
  requeued at the front with its generated tokens intact.

DESIGN DECISION — a request whose final length cannot fit alone is rejected.
  `blocks_needed(prompt + output) > total_blocks` can never complete, so it is
  dropped and named in `rejected` rather than spinning in the queue. This is
  distinct from `oom`, which is the simulator failing to make progress at all.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Sequence

from allocator import BlockAllocator, blocks_needed
from kv import Request, ServingConfig


@dataclass(eq=False)
class _Waiting:
    request: Request
    current: int  # tokens the sequence already holds (prompt, or progress kept across preemption)


@dataclass(eq=False)
class _Running:
    request: Request
    current: int
    blocks: int


@dataclass(frozen=True)
class Timeline:
    """The trace of one simulation, one entry per serving step."""

    total_blocks: int
    used_blocks: tuple[int, ...]
    running: tuple[int, ...]
    waiting: tuple[int, ...]
    preemptions: int
    completed: int
    rejected: tuple[str, ...]
    oom: bool

    @property
    def steps(self) -> int:
        return len(self.used_blocks)

    @property
    def peak_blocks(self) -> int:
        return max(self.used_blocks, default=0)


def simulate(requests: Sequence[Request], config: ServingConfig,
             max_num_seqs: Optional[int] = None,
             max_model_len: Optional[int] = None,
             max_steps: int = 100_000) -> Timeline:
    """Replay `requests` against `config`'s block pool.

    Each step: arrivals join the queue, running sequences generate one token
    (freeing themselves on completion, preempting to make room if the pool is
    full), and waiting sequences are admitted while a block budget and
    `max_num_seqs` allow. `max_model_len`, if given, rejects anything longer.
    """
    # TODO: Per step: move arrivals (arrive <= step) into a FIFO deque; for each running sequence generate one token, growing its block count via blocks_needed and, when the pool is full, preempting the running sequence with the most blocks (free it, requeue at the front, count it) then retrying; completing a sequence releases its blocks and bumps `completed`; then admit from the queue while len(running) < cap and the blocks fit, rejecting any request whose final length exceeds total_blocks. Record alloc.used_blocks each step. Return a Timeline(total, used, running_counts, waiting_counts, preemptions, completed, rejected, oom).
    raise NotImplementedError("simulate")


if __name__ == "__main__":
    config = ServingConfig(bytes_per_token=4, block_size=4, total_blocks=8)
    reqs = [Request("a", 0, 8, 8), Request("b", 0, 8, 8), Request("c", 0, 8, 8)]
    print("simulate — 8 blocks of 4 tokens, three 8->16 token requests")
    for cap in (None, 3, 2, 1):
        t = simulate(reqs, config, max_num_seqs=cap)
        print(f"  cap={str(cap):>4}: peak={t.peak_blocks}/8 blocks, "
              f"preemptions={t.preemptions}, completed={t.completed}, oom={t.oom}")

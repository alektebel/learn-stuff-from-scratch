"""
Provided — a simulated GPU that only keeps a ledger.

Not an exercise. Your serving code calls `launch` and `memcpy`; the checker
reads `bytes_moved`, `flops`, `launches`, `syncs`. Peak numbers are
constants chosen so the ridge point (peak_flops / peak_bandwidth) sits at
a round 200 FLOP/byte — typical of a memory-bound decode kernel.

    ridge = PEAK_FLOPS / PEAK_BANDWIDTH = 200 FLOP/byte
    intensity = flops / bytes_moved
    compute-bound  iff intensity > ridge
    bandwidth-bound iff intensity < ridge
"""

from dataclasses import dataclass, field
from typing import List, Optional


PEAK_FLOPS = 200_000          # "FLOPs per tick"
PEAK_BANDWIDTH = 1_000        # "bytes per tick"
RIDGE = PEAK_FLOPS / PEAK_BANDWIDTH  # 200


@dataclass
class Event:
    name: str
    flops: int
    bytes_moved: int
    synced: bool = False


@dataclass
class ToyGPU:
    events: List[Event] = field(default_factory=list)
    clock: int = 0
    occupied_until: int = 0

    def launch(self, name: str, flops: int, bytes_moved: int) -> None:
        """A kernel. Occupies the GPU for max(flops/peak, bytes/peak) ticks."""
        compute = flops / PEAK_FLOPS
        memory = bytes_moved / PEAK_BANDWIDTH
        duration = max(compute, memory)
        start = max(self.clock, self.occupied_until)
        self.occupied_until = start + duration
        self.events.append(Event(name, flops, bytes_moved))

    def memcpy(self, name: str, bytes_moved: int) -> None:
        self.launch(name, flops=0, bytes_moved=bytes_moved)

    def synchronize(self) -> None:
        """CPU waits for the GPU. Marks the last event as a sync point."""
        self.clock = max(self.clock, self.occupied_until)
        if self.events:
            self.events[-1].synced = True

    @property
    def flops(self) -> int:
        return sum(e.flops for e in self.events)

    @property
    def bytes_moved(self) -> int:
        return sum(e.bytes_moved for e in self.events)

    @property
    def launches(self) -> int:
        return len(self.events)

    @property
    def syncs(self) -> int:
        return sum(1 for e in self.events if e.synced)

    @property
    def intensity(self) -> float:
        return self.flops / self.bytes_moved if self.bytes_moved else float("inf")

    @property
    def bound(self) -> str:
        return "compute" if self.intensity > RIDGE else "bandwidth"

    @property
    def util(self) -> float:
        """Fraction of wall time the GPU was occupied, after a sync."""
        wall = max(self.clock, 1e-9)
        busy = self.occupied_until  # started at 0 in a fresh GPU
        return min(1.0, busy / wall) if wall else 0.0

    def reset(self) -> None:
        self.events.clear()
        self.clock = 0
        self.occupied_until = 0


# Cost model the serving code is expected to use. Prefill is quadratic in
# prompt length (attention scores); decode with a cache is linear in the
# cached length (reading K,V) and constant in new FLOPs for the matmuls
# of a single token.
D_MODEL = 64
LAYERS = 4
BYTES_PER_ELEMENT = 2          # fp16


def prefill_cost(prompt_len: int) -> tuple:
    """(flops, bytes) for a full-prompt forward."""
    flops = LAYERS * (2 * prompt_len * D_MODEL * D_MODEL          # QKV
                      + 2 * prompt_len * prompt_len * D_MODEL     # attn
                      + 2 * prompt_len * D_MODEL * D_MODEL)       # out
    bytes_moved = LAYERS * (3 * prompt_len * D_MODEL * BYTES_PER_ELEMENT)
    return flops, bytes_moved


def decode_cost(cached_len: int, use_kv: bool) -> tuple:
    """(flops, bytes) for one new token."""
    if use_kv:
        flops = LAYERS * (2 * D_MODEL * D_MODEL * 4)              # QKV+out, one token
        # Read K,V of the prefix; write the new K,V.
        bytes_moved = LAYERS * ((2 * cached_len + 2) * D_MODEL
                                * BYTES_PER_ELEMENT)
    else:
        # Recompute the whole prefix — prefill of cached_len+1.
        return prefill_cost(cached_len + 1)
    return flops, bytes_moved

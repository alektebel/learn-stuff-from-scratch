"""
Occupancy — how many warps an SM can keep resident
==================================================

Source: the CUDA programming guide occupancy model. Restated, not copied.

Occupancy is active warps per SM divided by the maximum warps the SM supports. It is not a
goal by itself — more resident warps hide more memory latency — but it bounds how much
latency hiding is available, and the *limiting* resource is what you change to raise it.

Per SM there is a register file, a block of shared memory, a maximum number of threads and
a maximum number of blocks. A block is admitted only if all four have room for it, so the
resident block count is the minimum of the per-resource caps. Occupancy is that count times
the warps per block, over the maximum warps.

DESIGN DECISION — allocate registers per warp and round to a granularity?
If you only compute `regs_per_thread * threads_per_block`, two kernels using 33 and 40
registers look different when the hardware allocates both as 40 (registers are handed out
per warp in units of 8), and a 100-thread block really occupies four warps. Rounding is
what makes the calculator match the hardware, and it is a real limit case: 33 registers is
not free. Chosen: registers per warp = round_up(regs_per_thread, 8) * 32; warps per block =
ceil(threads / 32); shared memory rounded up to 256 bytes.

DESIGN DECISION — one SM's limits, hardcoded or passed in?
A real GPU's limits differ by architecture. Hardcoding one set would make the module a
table to memorise; passing an `SMLimits` makes the arithmetic the lesson and lets you ask
"what if the register file were 128K?". Chosen: limits are a parameter, with a default
resembling a mid-range SM.
"""

from dataclasses import dataclass

WARP = 32


@dataclass(frozen=True)
class SMLimits:
    registers_per_sm: int
    shared_mem_per_sm: int
    max_threads_per_sm: int
    max_blocks_per_sm: int
    register_granularity: int = 8
    smem_granularity: int = 256

    @property
    def max_warps_per_sm(self):
        return self.max_threads_per_sm // WARP


DEFAULT_SM_LIMITS = SMLimits(
    registers_per_sm=65536,
    shared_mem_per_sm=49152,
    max_threads_per_sm=1536,
    max_blocks_per_sm=16,
)


def round_up(value, multiple):
    """Smallest multiple of `multiple` that is at least `value`."""
    return ((value + multiple - 1) // multiple) * multiple


def warps_per_block(threads_per_block):
    """Warps a block occupies: ceil(threads / 32), a partly filled warp is a whole warp."""
    return round_up(threads_per_block, WARP) // WARP


def registers_per_block(regs_per_thread, threads_per_block, limits=DEFAULT_SM_LIMITS):
    """Registers a block occupies, as the hardware allocates them."""
    regs_per_warp = round_up(regs_per_thread, limits.register_granularity) * WARP
    return regs_per_warp * warps_per_block(threads_per_block)


def block_caps(regs_per_thread, smem_per_block, threads_per_block, limits=DEFAULT_SM_LIMITS):
    """Blocks that fit, one cap per resource: threads, registers, shared memory, slots."""
    if threads_per_block <= 0:
        return {"threads": 0, "registers": 0, "shared_memory": 0, "blocks": 0}
    by_threads = limits.max_threads_per_sm // threads_per_block
    by_regs = limits.registers_per_sm // registers_per_block(regs_per_thread, threads_per_block, limits)
    if smem_per_block == 0:
        by_smem = limits.max_blocks_per_sm
    else:
        by_smem = limits.shared_mem_per_sm // round_up(smem_per_block, limits.smem_granularity)
    return {
        "threads": by_threads,
        "registers": by_regs,
        "shared_memory": by_smem,
        "blocks": limits.max_blocks_per_sm,
    }


def max_active_blocks(regs_per_thread, smem_per_block, threads_per_block, limits=DEFAULT_SM_LIMITS):
    """Resident blocks on one SM: a block needs room under every resource at once."""
    caps = block_caps(regs_per_thread, smem_per_block, threads_per_block, limits)
    return max(0, min(caps.values()))


def active_warps(regs_per_thread, smem_per_block, threads_per_block, limits=DEFAULT_SM_LIMITS):
    """Warps resident on one SM."""
    blocks = max_active_blocks(regs_per_thread, smem_per_block, threads_per_block, limits)
    return min(blocks * warps_per_block(threads_per_block), limits.max_warps_per_sm)


def occupancy(regs_per_thread, smem_per_block, threads_per_block, limits=DEFAULT_SM_LIMITS):
    """Active warps / maximum warps, in [0, 1]."""
    return active_warps(regs_per_thread, smem_per_block, threads_per_block, limits) / limits.max_warps_per_sm


def limiting_resource(regs_per_thread, smem_per_block, threads_per_block, limits=DEFAULT_SM_LIMITS):
    """Which resource caps the block count: registers, shared_memory, threads or blocks."""
    caps = block_caps(regs_per_thread, smem_per_block, threads_per_block, limits)
    fewest = min(caps.values())
    for name in ("registers", "shared_memory", "threads", "blocks"):
        if caps[name] == fewest:
            return name
    return "blocks"


def _demo():
    print(f"{'regs':>5}{'smem':>8}{'thr':>6}{'blocks':>8}{'warps':>7}{'occ':>7}  limiting")
    for regs, smem, thr in ((32, 0, 256), (64, 0, 256), (128, 0, 256),
                            (32, 16384, 256), (32, 0, 1024)):
        print(f"{regs:>5}{smem:>8}{thr:>6}{max_active_blocks(regs, smem, thr):>8}"
              f"{active_warps(regs, smem, thr):>7}{occupancy(regs, smem, thr):>7.2f}"
              f"  {limiting_resource(regs, smem, thr)}")


if __name__ == "__main__":
    _demo()

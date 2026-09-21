"""Occupancy is arithmetic, not a mystery — and it is not the goal.

Fregly ch. 6 and 8. Registers per thread, shared memory per block and threads per block each cap how many warps an SM can hold, and the binding constraint is whichever runs out first. It is a closed-form calculation you can do before compiling. Then the harder lesson (Volkov and Demmel, SC 2008): higher occupancy is NOT always faster, because instruction-level parallelism can hide latency with fewer warps. Compute it, then find the case where lowering it wins.

Pure arithmetic and simulation -- no GPU required, and that is the point: every
number here is one you should be able to compute BEFORE running anything, then
compare against what the profiler reports.

TODO(skeleton): signatures only. Write the CHECK in check_perf.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def warps_per_sm(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def limited_by_registers(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def limited_by_shared_memory(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def limited_by_block_size(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def occupancy(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def binding_constraint(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def ilp_tradeoff(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



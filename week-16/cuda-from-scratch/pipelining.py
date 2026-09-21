"""Overlapping what the GPU does with what it waits for.

Fregly ch. 10 and 11. Copy, compute, copy back -- done serially, the GPU idles through both transfers. Split the work into chunks across CUDA streams and the copies overlap the compute, and total time approaches max(transfer, compute) instead of their sum. Model it as a timeline and you can predict the number of streams past which nothing improves, which is the number worth knowing before you write any of it.

Pure arithmetic and simulation -- no GPU required, and that is the point: every
number here is one you should be able to compute BEFORE running anything, then
compare against what the profiler reports.

TODO(skeleton): signatures only. Write the CHECK in check_perf.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Timeline:
    """TODO"""


def serial_time(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def pipelined_time(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def optimal_chunks(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def overlap_efficiency(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def amdahl_ceiling(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def stream_schedule(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



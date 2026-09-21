"""Arithmetic intensity, and the one plot that predicts every kernel.

Fregly, AI Systems Performance Engineering, ch. 9; Williams, Waterman and Patterson, "Roofline: An Insightful Visual Performance Model" (CACM 2009). Count the FLOPs, count the bytes moved, divide -- that ratio decides whether your kernel is limited by arithmetic or by memory, and therefore which optimisation can possibly help. Optimising the wrong side is the most common way a week of tuning produces nothing, and this file is how you avoid it BEFORE writing the kernel.

Pure arithmetic and simulation -- no GPU required, and that is the point: every
number here is one you should be able to compute BEFORE running anything, then
compare against what the profiler reports.

TODO(skeleton): signatures only. Write the CHECK in check_perf.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def flops(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def bytes_moved(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def arithmetic_intensity(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def ridge_point(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def is_memory_bound(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def attainable_flops(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def roofline_position(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def speedup_ceiling(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



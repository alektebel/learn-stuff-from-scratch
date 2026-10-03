"""What one warp's memory request actually costs.

Fregly ch. 7. A warp issues one instruction; the hardware turns it into some number of memory TRANSACTIONS depending on which addresses the 32 lanes touched. Contiguous and aligned is one transaction per cache line; strided or misaligned can be 32. Count the transactions for a given access pattern -- that count, not the code, is what the profiler will show you.

Pure arithmetic and simulation -- no GPU required, and that is the point: every
number here is one you should be able to compute BEFORE running anything, then
compare against what the profiler reports.

TODO(skeleton): signatures only. Write the CHECK in check_perf.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def transactions_for(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def is_coalesced(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def stride_penalty(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def alignment_penalty(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def aos_vs_soa(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def bank_conflicts(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def conflict_degree(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def padding_fix(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



"""Batch at a time, and where the Volcano model's time actually goes.

Boncz, Zukowski and Nes, "MonetDB/X100: Hyper-Pipelining Query Execution" (CIDR 2005). The Volcano iterator in executor.py makes one virtual call PER TUPLE PER OPERATOR, and on a modern machine that interpretation overhead dwarfs the work. Process a thousand tuples per call instead and measure what happens. Then read Neumann (VLDB 2011) for the other answer -- compile the query instead of interpreting it.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

class Batch:
    """TODO"""


class VectorizedScan:
    """TODO"""


class VectorizedFilter:
    """TODO"""


class VectorizedProject:
    """TODO"""


def run_vectorized(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def overhead_per_tuple(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def batch_size_sweep(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



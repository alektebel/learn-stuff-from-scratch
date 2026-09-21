"""Three join algorithms, and the one that survives not fitting in memory.

Nested loop, sort-merge, and hash -- then the case that matters: the build side does not fit. Grace hash join partitions both inputs to disk and joins partition by partition; radix partitioning does the same with cache in mind instead of disk. Measure I/O, not time.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

def sort_merge_join(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def grace_hash_join(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def radix_partition(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def spill_to_disk(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def io_cost(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def choose_join(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def skew_penalty(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



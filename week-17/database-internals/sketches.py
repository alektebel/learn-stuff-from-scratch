"""Counting things you cannot afford to count exactly.

HyperLogLog for distinct values, Count-Min for frequencies, reservoir sampling for everything else. These are what the planner's statistics ACTUALLY are -- not a scan. Every one trades a bounded error for constant space, and the bound is provable rather than hoped for.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

class HyperLogLog:
    """TODO"""


class CountMinSketch:
    """TODO"""


def reservoir_sample(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def distinct_estimate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def frequency_estimate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def error_bound(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def space_vs_accuracy(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



"""Proof of work, difficulty, and retargeting.

Finding a block is a geometric random variable with mean 2^difficulty hashes. Nothing about that is a puzzle in any interesting sense -- it is a lottery whose ticket price is electricity, and the only thing it buys is that rewriting history costs the same again. Measure the distribution, then measure what retargeting does when hashrate doubles.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def target_from_difficulty(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def meets_target(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def mine(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def expected_hashes(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def retarget(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



"""Column stores, compression, and late materialization.

Stonebraker et al., "C-Store" (VLDB 2005). Store by column and a scan touches only the columns it needs -- but the real win is compression, because a column is homogeneous and a row is not. Run-length, dictionary and frame-of-reference encodings, then late materialization: stay in the compressed domain as long as possible and only reconstruct rows at the end.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

class ColumnStore:
    """TODO"""


def run_length_encode(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def dictionary_encode(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def frame_of_reference(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def scan_column(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def late_materialize(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def compression_ratio(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def selectivity_crossover(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



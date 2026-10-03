"""Unspent outputs, double spends, and the mempool.

A UTXO can be spent exactly once, and that is the whole double-spend defence -- not a rule enforced by checking history, but a set from which spending removes. Build the set, then try to spend the same output twice and watch where it is refused.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def apply_transaction(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def validate_transaction(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def utxo_set(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def fee(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def mempool_select(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def double_spend_attempt(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



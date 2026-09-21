"""Ethereum's account model, and the nonce that replaces the UTXO set.

Accounts have balances, not coins, so nothing is consumed by spending and a signed transaction stays valid forever. The nonce is what stops replay -- and it is the exact price of dropping the UTXO set. Run the replay attack with and without it.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Account:
    """TODO"""


def apply(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def nonce_check(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def replay_attack(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def compare_models(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



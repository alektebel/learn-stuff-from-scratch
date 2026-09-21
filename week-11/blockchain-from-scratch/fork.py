"""Reorgs, Nakamoto's catch-up probability, and selfish mining.

The longest chain is not a rule about length, it is a rule about accumulated work. An attacker k blocks behind with hash share q catches up with probability (q/p)^k -- simulate it and check the closed form. Then selfish mining: withholding blocks earns MORE than your hash share above a threshold, and the threshold depends on how much of the honest network you can reach first.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def total_work(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def choose_head(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def reorg(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def catch_up_probability(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def selfish_mining_revenue(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



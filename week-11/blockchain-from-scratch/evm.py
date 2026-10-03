"""A stack VM with gas, and halting bought with money.

Loops mean the halting problem, so execution is metered: every opcode costs gas, gas runs out, the transaction reverts and the sender still pays. Write an infinite loop and confirm it terminates. Then measure gas against work done, which is the only thing making a public VM safe to run.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Machine:
    """TODO"""


def step(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def run(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def gas_cost(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def out_of_gas(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def revert(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



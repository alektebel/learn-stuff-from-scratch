"""Bitcoin Script: a stack machine with no loops, on purpose.

P2PKH is six opcodes. The design decision worth the whole file is the absence of jumps: no loops means every script provably halts, so no gas metering is needed and validation cost is bounded by script length. Ethereum made the other choice, and evm.py is what that costs.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Stack:
    """TODO"""


def execute(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def op_checksig(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def p2pkh_script(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def halts_by_construction(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



"""Casper FFG finality, and accountable safety.

Proof of work makes rewriting expensive. Proof of stake makes it ATTRIBUTABLE: two conflicting finalised checkpoints require at least a third of the stake to have signed contradictory attestations, and those signatures are evidence. Build the violation by hand and assert the slashing condition catches it -- the same shape as raft.py's Figure 8 check.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Attestation:
    """TODO"""


def justify(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def finalize(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def fork_choice(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def slashable(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def accountable_safety(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



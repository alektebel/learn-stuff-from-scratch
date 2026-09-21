"""IAM policy documents are DATA, so they can be linted before they are applied.

You already wrote the evaluation rule in week 1's iam.py. Point it at a real policy document and you can answer, offline and before any deploy: does this grant more than the named actions need, is there a wildcard on a write, does the trust policy name the right principal, does the permission boundary actually bound anything.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
Nothing in this file touches the network -- it lints artifacts offline. The
real-account half is RUNBOOK.md.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def parse_policy(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def granted_actions(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def excess_over(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def wildcard_writes(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def trust_policy_principals(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def boundary_effective(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def simulate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



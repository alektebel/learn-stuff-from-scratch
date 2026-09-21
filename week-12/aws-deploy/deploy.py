"""The deploy as a state machine, including the half that fails.

Build, upload, invalidate, health-check, promote -- or roll back. Model it as states and transitions and you can inject a failure at each step and assert the system ends somewhere safe. A deploy pipeline that has never been failed on purpose has not been tested.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
Nothing in this file touches the network -- it lints artifacts offline. The
real-account half is RUNBOOK.md.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class State:
    """TODO"""


def plan(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def advance(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def inject_failure(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def is_safe_state(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def rollback(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def health_gate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



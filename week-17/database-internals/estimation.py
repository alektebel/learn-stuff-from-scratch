"""Cardinality estimation, and why optimisers actually fail.

Leis, Gubichev, Mirchev, Boncz, Kemper and Neumann, "How Good Are Query Optimizers, Really?" (VLDB 2015). The finding is not that cost models are wrong. It is that the INPUTS are: estimation error compounds roughly MULTIPLICATIVELY with each join, so a four-way join can be off by orders of magnitude, and the planner then picks a bad plan correctly. Measure the error growth against join count. This is the deepest single result in query processing and it is three afternoons of work to reproduce.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

def histogram(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def estimate_selectivity(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def estimate_join(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def error_factor(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def compound_error(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def plan_regret(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def independence_assumption(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def correlated_columns(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



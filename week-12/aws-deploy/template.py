"""Infrastructure as a graph, with a rollback path and a complete teardown.

A CloudFormation or CDK template is a dependency graph. Order it, and you can check what a console click cannot: that nothing depends on a resource created later, that every resource has a deletion path, that a mid-way failure rolls back to nothing rather than to half a stack, and that teardown leaves no orphans.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
Nothing in this file touches the network -- it lints artifacts offline. The
real-account half is RUNBOOK.md.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def parse_template(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def dependency_order(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def has_cycle(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def rollback_plan(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def orphans_after_teardown(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def drift(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def diff(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



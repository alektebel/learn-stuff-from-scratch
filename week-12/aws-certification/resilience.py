"""DR patterns, with RPO and RTO as numbers rather than adjectives.

Backup-and-restore, pilot light, warm standby, multi-site active-active. Each has an RTO you can compute and a standing cost you can compute, and the exam question is always which one fits a stated RPO/RTO at least cost. Multi-AZ against multi-region is the same calculation at a different blast radius.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def pattern_rto(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def pattern_cost(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def pattern_for(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def blast_radius(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def failover_time(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def backup_window(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



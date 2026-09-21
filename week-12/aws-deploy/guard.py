"""What bills while you sleep.

The expensive AWS mistake is almost never a big instance -- it is a forgotten resource that charges per hour whether or not anyone uses it. NAT gateways, unattached elastic IPs, load balancers, provisioned IOPS, idle RDS. Compute the idle burn of a stack before you apply it, and set the budget alarm below the point where you would care.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
Nothing in this file touches the network -- it lints artifacts offline. The
real-account half is RUNBOOK.md.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def idle_hourly_cost(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def bills_while_idle(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def free_tier_headroom(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def budget_threshold(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def forecast(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def alarm_before_spend(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



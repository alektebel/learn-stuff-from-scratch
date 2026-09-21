"""VPC past stateful-vs-stateless, and the six ways to connect two networks.

vpc.py taught security groups against NACLs. The exam wants topology: subnets and route tables, IGW against NAT against gateway and interface endpoints, and then Direct Connect against Site-to-Site VPN against Transit Gateway against peering -- chosen on bandwidth, latency guarantee, encryption and cost. Route 53 routing policies belong here too.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def route_for(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def reachable(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def connectivity_choice(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def endpoint_saving(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def routing_policy_for(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def resolve(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



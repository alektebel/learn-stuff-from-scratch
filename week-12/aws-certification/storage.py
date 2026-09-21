"""The storage decision surface, and the arithmetic under it.

S3 classes and lifecycle transitions, Glacier retrieval tiers, EBS gp3/io2/st1/sc1 with their IOPS and throughput ceilings, and where EFS or FSx beat both. The exam asks which; the arithmetic says which, and you already have the minimum-object-size and minimum-duration rules from pricing.py.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def class_for_access_pattern(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def lifecycle_cost(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def retrieval_time(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def ebs_for_workload(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def iops_ceiling(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def throughput_ceiling(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def shared_filesystem_choice(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



"""The credential chain, and never putting a long-lived key on disk.

Resolution order, role assumption, session expiry, and the check that matters: a static access key where a short-lived session belongs. Everything else in this directory is downstream of getting this right, and it is the one mistake that is expensive AND public.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
Nothing in this file touches the network -- it lints artifacts offline. The
real-account half is RUNBOOK.md.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def resolve_chain(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def assume_role(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def session_expiry(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def is_long_lived(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def redact(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def audit_credential_sources(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



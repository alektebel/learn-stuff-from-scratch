"""Service selection under constraints — the question the exams actually ask.

Nearly every scenario question is the same shape: here are requirements (an access pattern, an RPO, a latency ceiling, a compliance rule, a budget), name the service. That is derivable, not memorised, IF you know the mechanisms -- which is what aws-from-scratch gave you. This file turns that into a graded decision procedure so you can be scored on the reasoning rather than on having seen the question.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Requirements:
    """TODO"""


def candidates(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def eliminate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def choose(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def justify(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def cost_of_choice(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



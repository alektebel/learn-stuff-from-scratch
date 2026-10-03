"""Two-phase locking, optimistic control, and MVCC under real contention.

mvcc.py showed one answer. The trade only appears under CONTENTION: 2PL blocks and can deadlock, OCC never blocks and aborts instead, MVCC lets readers through and still admits write skew. Sweep the conflict rate and measure throughput, abort rate and blocked time for all three. The crossover is the answer, and it moves with the workload.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

class TwoPhaseLocking:
    """TODO"""


class OptimisticControl:
    """TODO"""


def deadlock_detect(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def wait_for_graph(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def validate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def abort_rate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def throughput_under_contention(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def crossover_conflict_rate(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError



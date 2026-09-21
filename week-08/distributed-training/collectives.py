"""What a collective actually costs, before you own the cluster.

Fregly, AI Systems Performance Engineering, ch. 4; Thakur, Rabenseifner &
Gropp, "Optimization of Collective Communication Operations in MPICH" (IJHPCA
2005); Patarasuk & Yuan on bandwidth-optimal all-reduce.

Every collective has a cost model of the form `alpha * hops + beta * bytes` --
a latency term and a bandwidth term -- and which term dominates decides the
algorithm:

    ring all-reduce   2(p-1) steps, each moving N/p bytes. BANDWIDTH-optimal:
                      total bytes per node is independent of p. Latency grows
                      linearly with p, so it is wrong for small messages.
    tree/recursive    log(p) steps. LATENCY-optimal, and it moves more bytes.

Real libraries switch between them at a message size you can compute. Compute
it, then compare against what NCCL actually picks -- the gap is either a
hardware detail you have not modelled or a bug in your model, and both are
worth finding.

No cluster required. Every number here is arithmetic you should be able to do
before requesting the nodes.

TODO(skeleton): signatures only.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple


def ring_allreduce_cost(*args, **kwargs) -> float:
    """2(p-1) steps of N/p bytes. Bandwidth-optimal, latency-linear. TODO"""
    raise NotImplementedError


def tree_allreduce_cost(*args, **kwargs) -> float:
    """log2(p) steps. Latency-optimal, moves more bytes. TODO"""
    raise NotImplementedError


def crossover_message_size(*args, **kwargs) -> float:
    """Where the ring overtakes the tree, for given alpha and beta. TODO"""
    raise NotImplementedError


def bandwidth_term(*args, **kwargs) -> float:
    """TODO"""
    raise NotImplementedError


def latency_term(*args, **kwargs) -> float:
    """TODO"""
    raise NotImplementedError


def gradient_bytes(*args, **kwargs) -> float:
    """Parameters x dtype size. The message every step must all-reduce. TODO"""
    raise NotImplementedError


def overlap_with_backward(*args, **kwargs) -> float:
    """Bucketing: all-reduce layer n's gradients while layer n-1 still computes.

    This is the single largest win in data-parallel training and it is a
    SCHEDULING change, not a communication one -- the bytes are identical.
    Model the timeline and find the bucket size where the overlap saturates.

    TODO
    """
    raise NotImplementedError


def scaling_efficiency(*args, **kwargs) -> float:
    """Achieved speedup / p. Where it falls off is the answer. TODO"""
    raise NotImplementedError

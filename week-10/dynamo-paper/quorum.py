"""
Quorum Reads & Writes (N, R, W) — From Scratch
==============================================
Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007),
       section 4.5 ("Execution of get() and put() operations").

Requires: partitioning.py and vector_clock.py (implement those first).

Build the quorum layer to understand:
- What R + W > N actually buys you, and what it does not
- Why a storage node appends siblings instead of overwriting
- Read repair: opportunistic consistency on the read path
- Why the paper's cart service runs W=1 rather than a "safe" W=2

Learning Path:
1. Implement StorageNode.local_put / local_get with sibling append
2. Implement Coordinator.put — increment the clock, fan out, count acks
3. Implement Coordinator.get — fan out, coalesce, return siblings + context
4. Add read repair
5. Experiment: kill nodes and find where each (N, R, W) config breaks

Background:
  N = replicas per key (the length of the preference list)
  R = replicas that must answer a read
  W = replicas that must acknowledge a write

  R + W > N means the read set and write set must share at least one node, so
  a read is guaranteed to see the last successful write. That guarantee holds
  only for a *strict* quorum against the same N nodes — the sloppy quorum in
  hinted_handoff.py trades it away deliberately.

  Latency is set by the slowest of R (or W) responses, so raising either raises
  the tail. The paper's 99.9th-percentile SLA is why Amazon ran W=1 for the
  cart: a write that waits for two machines waits for whichever one is
  garbage-collecting.

  A storage node must never overwrite a concurrent version on a local put —
  that would silently discard a sibling and defeat the whole versioning scheme.
  Local puts append and then coalesce.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from partitioning import ConsistentHashRing
from vector_clock import VectorClock, VersionedValue, coalesce


class NodeUnavailable(Exception):
    """Raised by a storage node simulating a crash or dropped packet."""


class QuorumNotMet(Exception):
    """Fewer than R (or W) replicas answered."""


# ---------------------------------------------------------------------------
# Step 1: The storage node
# ---------------------------------------------------------------------------

class StorageNode:
    """One machine's local store: key -> list of sibling versions.

    Internals:
      data:  key -> List[VersionedValue]
      alive: flip to False to simulate a failure
    """

    def __init__(self, name: str):
        self.name = name
        self.alive = True
        self.data: Dict[str, List[VersionedValue]] = {}
        self.stats = {"local_puts": 0, "local_gets": 0, "rejected": 0}

    def kill(self) -> None:
        self.alive = False

    def revive(self) -> None:
        self.alive = True

    def _check(self) -> None:
        """TODO: raise NodeUnavailable(self.name) when not alive, and count it."""
        raise NotImplementedError

    def local_put(self, key: str, version: VersionedValue) -> None:
        """Store a version alongside whatever is already here.

        TODO:
        1. _check() first.
        2. data[key] = coalesce(existing + [version])

        Note this is idempotent: replaying the same version changes nothing,
        which is what makes hinted handoff and anti-entropy safe to retry.
        """
        raise NotImplementedError

    def local_get(self, key: str) -> List[VersionedValue]:
        """TODO: _check(), then return a copy of data.get(key, [])."""
        raise NotImplementedError

    def keys(self) -> List[str]:
        return sorted(self.data)

    def __repr__(self) -> str:
        return f"<StorageNode {self.name} {'up' if self.alive else 'DOWN'}>"


# ---------------------------------------------------------------------------
# Step 2-4: The coordinator
# ---------------------------------------------------------------------------

class GetResult:
    """What a client sees: possibly several siblings, plus the context."""

    def __init__(self, versions: List[VersionedValue], context: Dict[str, int],
                 replicas_answered: int):
        self.versions = versions
        self.context = context
        self.replicas_answered = replicas_answered

    @property
    def value(self) -> Any:
        if len(self.versions) != 1:
            raise ValueError(f"{len(self.versions)} siblings — the app must reconcile")
        return self.versions[0].value

    @property
    def values(self) -> List[Any]:
        return [v.value for v in self.versions]

    @property
    def has_conflict(self) -> bool:
        return len(self.versions) > 1


class Coordinator:
    """Client-facing entry point. Any node can coordinate any request."""

    def __init__(self, ring: ConsistentHashRing, nodes: Dict[str, StorageNode],
                 n: int = 3, r: int = 2, w: int = 2, read_repair: bool = True):
        self.ring = ring
        self.nodes = nodes
        self.n, self.r, self.w = n, r, w
        self.read_repair = read_repair
        self.stats = {"puts": 0, "gets": 0, "put_failures": 0, "get_failures": 0,
                      "read_repairs": 0}

    def put(self, key: str, value: Any, context: Optional[Dict[str, int]] = None,
            coordinating_node: Optional[str] = None) -> VectorClock:
        """Write a value, superseding the version identified by `context`.

        TODO:
        1. preference = ring.preference_list(key, n); raise QuorumNotMet if empty.
        2. coordinator = coordinating_node or preference[0].
        3. clock = VectorClock.from_context(context or {}).increment(coordinator)
        4. Fan out local_put to every node in the preference list, counting acks
           and swallowing NodeUnavailable.
        5. Raise QuorumNotMet if acks < W; otherwise return the clock.

        Try it with context=None twice from different coordinators — you should
        get two siblings, because neither write knew about the other.
        """
        raise NotImplementedError

    def get(self, key: str) -> GetResult:
        """Read from the preference list and merge what comes back.

        TODO:
        1. Collect (node_name, versions) from each reachable replica.
        2. Raise QuorumNotMet if fewer than R answered.
        3. merged = coalesce(all versions from all responses)
        4. If read_repair is on, call _repair().
        5. Build the context as the pointwise max over all merged clocks, and
           return GetResult(merged, context, len(responses)).
        """
        raise NotImplementedError

    def _repair(self, key: str, merged: List[VersionedValue],
                responses: List[Tuple[str, List[VersionedValue]]]) -> None:
        """Push the merged view back to replicas that were behind.

        TODO: for each responding node, if coalesce(its versions + merged)
        differs from coalesce(its versions), local_put each merged version and
        bump stats["read_repairs"].

        Read repair only fixes keys that someone actually reads. Cold data needs
        the Merkle sync in merkle_sync.py — that is why Dynamo has both.
        """
        raise NotImplementedError

    def get_and_reconcile(self, key: str,
                          merge_fn: Callable[[List[Any]], Any]) -> Optional[Any]:
        """TODO: get(), and if there are siblings, merge them with merge_fn and
        put() the result back with the returned context."""
        raise NotImplementedError


def build_cluster(num_nodes: int = 5, tokens_per_node: int = 64,
                  n: int = 3, r: int = 2, w: int = 2
                  ) -> Tuple[ConsistentHashRing, Dict[str, StorageNode], Coordinator]:
    """TODO: build a ring with num_nodes nodes, a StorageNode for each, and a
    Coordinator over both."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify each of these:

    1. put then get returns the value, 3/3 replicas answering.
    2. Kill one replica: reads and writes both still succeed (R=W=2).
    3. Kill two: R=2 can no longer be met and get() raises QuorumNotMet.
       (Sloppy quorum, in hinted_handoff.py, is what rescues the write path.)
    4. Two clients that read the same context and both write produce two
       siblings, and no node is allowed to pick between them.
    5. A replica that missed a write while down is silently fixed by the next
       read that touches the key.
    """
    ring, nodes, coord = build_cluster(num_nodes=5, n=3, r=2, w=2)
    coord.put("cart:user-42", {"book": 1})
    print(coord.get("cart:user-42").value)


if __name__ == "__main__":
    _demo()

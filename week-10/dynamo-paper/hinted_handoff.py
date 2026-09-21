"""
Sloppy Quorum & Hinted Handoff — From Scratch
==============================================
Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007),
       section 4.6 ("Handling Failures: Hinted Handoff").

Requires: partitioning.py, vector_clock.py, quorum.py.

Build the availability layer to understand:
- The difference between a strict and a sloppy quorum, precisely
- What a "hint" is and who is responsible for delivering it
- That an acknowledged write can still be lost, and under exactly what
  conditions

Learning Path:
1. Implement HintedNode.store_hint and deliver_hints
2. Implement SloppyCoordinator.put — fall forward past dead replicas
3. Implement SloppyCoordinator.get, optionally consulting hints
4. Run the hint-delivery loop and confirm the data goes home
5. Construct a case where an acknowledged write is genuinely lost

Background:
  A strict quorum only ever talks to the top-N nodes of the preference list.
  If N=3, W=2 and two of the three owners are down, the write fails — even
  though the cluster has plenty of healthy machines sitting idle.

  A sloppy quorum keeps walking the ring past the top N until W healthy nodes
  have accepted the write. The extra nodes are not owners; they store the data
  in a separate local area with a *hint* saying who it really belongs to, and a
  background loop hands it over once that node is reachable again.

  The trade: you gain availability, you lose the R + W > N guarantee. A read
  hitting only the top-N nodes can miss a write that is parked on a fallback,
  and if the fallback dies before delivering the hint, the write is gone.
  Anti-entropy narrows that window but does not close it.
"""

from typing import Any, Dict, List, Optional, Tuple

from partitioning import ConsistentHashRing
from quorum import GetResult, NodeUnavailable, QuorumNotMet, StorageNode
from vector_clock import VectorClock, VersionedValue, coalesce


class Hint:
    """A replica held on behalf of a node that was unreachable."""

    __slots__ = ("key", "version", "intended_for")

    def __init__(self, key: str, version: VersionedValue, intended_for: str):
        self.key = key
        self.version = version
        self.intended_for = intended_for

    def __repr__(self) -> str:
        return f"Hint({self.key!r} for {self.intended_for}, {self.version.clock})"


# ---------------------------------------------------------------------------
# Step 1: A node that can hold data for its peers
# ---------------------------------------------------------------------------

class HintedNode(StorageNode):
    """A StorageNode with a separate area for hinted replicas.

    Keeping hints out of the main store matters for two reasons: the node must
    not serve them as if it owned the key, and the delivery loop needs to scan
    them cheaply without walking the whole keyspace.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.hints: List[Hint] = []
        self.stats.update({"hints_stored": 0, "hints_delivered": 0})

    def store_hint(self, key: str, version: VersionedValue,
                   intended_for: str) -> None:
        """TODO: _check(), append a Hint, bump stats["hints_stored"]."""
        raise NotImplementedError

    def deliver_hints(self, nodes: Dict[str, "HintedNode"]) -> int:
        """Hand every held hint back to its intended owner; return the count.

        TODO:
        1. Return 0 if this node is itself down.
        2. For each hint: if the target exists and is alive, local_put the
           version onto it and count it; otherwise keep the hint for later.
        3. Replace self.hints with the undelivered remainder.

        Delivery is idempotent — local_put coalesces — so a hint delivered
        twice costs nothing. Design for that; the alternative is tracking
        acknowledgements you do not need.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 2-3: The sloppy coordinator
# ---------------------------------------------------------------------------

class SloppyCoordinator:
    """Quorum coordinator that falls forward past unreachable replicas."""

    def __init__(self, ring: ConsistentHashRing, nodes: Dict[str, HintedNode],
                 n: int = 3, r: int = 2, w: int = 2, read_repair: bool = True):
        self.ring = ring
        self.nodes = nodes
        self.n, self.r, self.w = n, r, w
        self.read_repair = read_repair
        self.stats = {"puts": 0, "gets": 0, "sloppy_writes": 0, "put_failures": 0,
                      "get_failures": 0, "read_repairs": 0}

    def _extended_preference(self, key: str) -> List[str]:
        """The full ring order for this key: top-N first, then the fallbacks.

        TODO: ring.preference_list(key, len(self.nodes)).
        """
        raise NotImplementedError

    def put(self, key: str, value: Any, context: Optional[Dict[str, int]] = None,
            coordinating_node: Optional[str] = None) -> VectorClock:
        """Write, falling forward onto healthy nodes when owners are down.

        TODO:
        1. ordered = _extended_preference(key); top_n = ordered[:n].
        2. Build the clock exactly as in quorum.Coordinator.put.
        3. Try local_put on each of top_n; count acks, and record which owners
           were unreachable in a `missing` list.
        4. While acks < W and `missing` is non-empty, walk ordered[n:]: for each
           live fallback, store_hint(key, version, intended_for=missing.pop(0)),
           count an ack, and bump stats["sloppy_writes"].
        5. Raise QuorumNotMet if acks < W.

        Notice that step 4 stops as soon as W is satisfied — it does NOT create
        a hint for every missing owner. So an owner can stay stale even after
        all hints are delivered, which is precisely the gap anti-entropy fills.
        """
        raise NotImplementedError

    def get(self, key: str, include_hints: bool = True) -> GetResult:
        """Read the home replicas, optionally consulting hints in flight.

        Real Dynamo reads only the top-N. `include_hints=True` is a teaching
        lever: it shows that a write parked on a fallback was never lost, only
        misfiled.

        TODO:
        1. Collect responses from top_n as in quorum.Coordinator.get; remember
           how many of those were real owners.
        2. If include_hints, scan the live fallback nodes for hints matching
           this key, collect those versions, and count each holder toward R.
        3. Raise QuorumNotMet if the total responders are fewer than R.
        4. coalesce everything, read-repair the OWNERS only (never the hint
           holders — they must not become permanent replicas), and return.
        """
        raise NotImplementedError

    def run_hint_delivery(self) -> int:
        """TODO: sum deliver_hints(self.nodes) across every node."""
        raise NotImplementedError

    def pending_hints(self) -> Dict[str, List[Hint]]:
        return {name: list(node.hints) for name, node in self.nodes.items()
                if node.hints}


def build_sloppy_cluster(num_nodes: int = 6, tokens_per_node: int = 64,
                         n: int = 3, r: int = 2, w: int = 2
                         ) -> Tuple[ConsistentHashRing, Dict[str, HintedNode],
                                    SloppyCoordinator]:
    """TODO: ring + HintedNodes + SloppyCoordinator."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, walk through these five states:

    1. Kill two of three owners. A strict W=2 write would fail here.
    2. The sloppy put succeeds; a hint appears on a fallback node.
    3. A read of the owners alone fails R=2; a read including hints finds the
       value. The write was never lost.
    4. Revive the owners, run hint delivery, and watch the data go home. Check
       how many owners actually ended up with it — it may not be all three.
    5. Now the uncomfortable case: kill ALL THREE owners, write (W=2 is met
       entirely by hints), then kill the hint holders before delivery. Revive
       the owners and read. The value is gone, and it was acknowledged.

    Step 5 is the honest limit of this design. Write it down before moving on
    to merkle_sync.py.
    """
    ring, nodes, coord = build_sloppy_cluster(num_nodes=6, n=3, r=2, w=2)
    home = ring.preference_list("cart:user-42", 3)
    for name in home[:2]:
        nodes[name].kill()
    coord.put("cart:user-42", {"book": 1})
    print("pending hints:", coord.pending_hints())


if __name__ == "__main__":
    _demo()

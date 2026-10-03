"""
Dynamo Partitioning — From Scratch
===================================
Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007)
       DeCandia et al., sections 4.2 and 6.2.

Build Dynamo's partitioning layer to understand:
- Why a preference list is not the same thing as a consistent-hash lookup
- How virtual nodes ("tokens") let heterogeneous machines carry uneven load
- Why the paper eventually abandoned random tokens for fixed partitions

Learning Path:
1. Implement ConsistentHashRing.add_node / remove_node / coordinator
2. Implement preference_list — the part that actually matters for replication
3. Add datacenter awareness so replicas span failure domains
4. Measure load imbalance and key migration when a node joins
5. Implement PartitionedRing (the paper's "strategy 3") and compare

Background:
  Every key hashes to a position on a ring of size 2^32. The first node
  clockwise from that position coordinates the key; the next N-1 *distinct
  physical* nodes clockwise store the replicas. That list is the key's
  "preference list", and every other mechanism in Dynamo is defined in terms
  of it — quorums, hinted handoff, anti-entropy, all of it.

  The "distinct physical" part is the subtle bit. A node owns many virtual
  tokens, so walking the ring naively can hand you the same machine three
  times and leave you with one copy of the data instead of three.

  Strategy 1 (this file's ConsistentHashRing): each node claims T random
  tokens. Simple, but partition boundaries move whenever membership changes,
  which makes bootstrapping a new node expensive — it has to scan its peers'
  entire key space to find what it now owns.

  Strategy 3 (PartitionedRing): cut the ring into Q equal partitions up front
  and assign whole partitions to nodes. Boundaries never move, so a joining
  node receives entire partition files. Q is fixed at deploy time and must be
  much larger than the maximum node count.
"""

import bisect
import hashlib
from typing import Dict, List, Optional, Tuple

RING_SIZE = 2 ** 32


def md5_hash(key: str) -> int:
    """Hash a key onto the ring [0, 2^32). Dynamo used MD5 for this."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % RING_SIZE


# ---------------------------------------------------------------------------
# Step 1-4: Strategy 1 — T random tokens per node
# ---------------------------------------------------------------------------

class ConsistentHashRing:
    """Dynamo's original partitioning scheme.

    Internals to maintain:
      _positions: sorted list of token positions (use bisect.insort)
      _owner:     position -> node name
      _nodes:     node name -> datacenter
    """

    def __init__(self, tokens_per_node: int = 64):
        self.tokens_per_node = tokens_per_node
        self._positions: List[int] = []
        self._owner: Dict[int, str] = {}
        self._nodes: Dict[str, str] = {}

    def add_node(self, node: str, datacenter: str = "dc0") -> None:
        """Claim `tokens_per_node` positions on the ring for this node.

        TODO:
        1. Return early if the node is already present.
        2. Record node -> datacenter in _nodes.
        3. For i in range(tokens_per_node):
             pos = md5_hash(f"{node}#{i}")
             while pos is already in _owner: pos = (pos + 1) % RING_SIZE
             bisect.insort(_positions, pos); _owner[pos] = node

        Why the probe loop: two tokens landing on the same position would make
        ownership ambiguous. Collisions are astronomically rare at 2^32 but
        cost nothing to handle.
        """
        raise NotImplementedError

    def remove_node(self, node: str) -> None:
        """Drop every token belonging to this node.

        TODO: filter _positions, delete the matching _owner entries, and
        remove the node from _nodes.
        """
        raise NotImplementedError

    @property
    def nodes(self) -> List[str]:
        return sorted(self._nodes)

    def coordinator(self, key: str) -> Optional[str]:
        """The first node clockwise from hash(key).

        TODO:
        1. Return None if the ring is empty.
        2. idx = bisect.bisect_left(_positions, md5_hash(key))
        3. Wrap: if idx == len(_positions), idx = 0
        4. Return _owner[_positions[idx]]
        """
        raise NotImplementedError

    def preference_list(self, key: str, n: int, distinct_dc: bool = False) -> List[str]:
        """The top-N *distinct physical* nodes clockwise from hash(key).

        This is the function the rest of Dynamo is built on. Get it wrong and
        you silently store three copies of the data on one machine.

        TODO:
        1. Return [] for an empty ring; clamp n to the number of physical nodes.
        2. Find the starting index as in coordinator().
        3. Walk positions clockwise (wrapping with modulo). For each position:
             - skip the node if it is already in the result
             - if distinct_dc, also skip it if its datacenter is already used,
               unless every datacenter has already been used (otherwise you
               loop forever on a single-DC cluster)
             - otherwise append it
        4. Stop once the result holds n nodes.

        Test: preference_list(key, 3) must return 3 different node names, and
        with distinct_dc=True across 3 datacenters it must return 3 different
        datacenters.
        """
        raise NotImplementedError

    def load_distribution(self, num_keys: int = 20_000) -> Dict[str, int]:
        """Count how many synthetic keys each node coordinates.

        TODO: hash f"key:{i}" for i in range(num_keys), tally by coordinator().
        """
        raise NotImplementedError

    def imbalance(self, num_keys: int = 20_000) -> float:
        """max_load / mean_load — 1.0 is perfect.

        TODO: compute from load_distribution(). Expect ~1.1-1.3 with 64 tokens
        and 4 nodes; try tokens_per_node = 1, 8, 512 and watch it tighten.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 5: Strategy 3 — Q equal-sized partitions
# ---------------------------------------------------------------------------

class PartitionedRing:
    """The scheme Dynamo settled on (section 6.2, "strategy 3").

    The ring is divided into Q fixed partitions once, at deploy time. Nodes are
    assigned whole partitions, so adding a node moves Q/S partitions and never
    moves a boundary. That is what makes bootstrapping and archival cheap: a
    partition is a file you can ship whole.
    """

    def __init__(self, num_partitions: int = 1024):
        self.num_partitions = num_partitions
        self.partition_size = RING_SIZE // num_partitions
        self._nodes: List[str] = []
        self._assignment: List[str] = []      # partition index -> node

    def partition_for(self, key: str) -> int:
        """TODO: md5_hash(key) // partition_size, modulo num_partitions."""
        raise NotImplementedError

    def add_node(self, node: str) -> None:
        """TODO: append to _nodes (if new) and call _rebalance()."""
        raise NotImplementedError

    def remove_node(self, node: str) -> None:
        """TODO: remove from _nodes and call _rebalance()."""
        raise NotImplementedError

    def _rebalance(self) -> None:
        """Assign partitions to nodes.

        TODO: round-robin the sorted node list over range(num_partitions), so
        every node gets exactly Q/S partitions. (Real Dynamo preserves existing
        ownership where it can; round-robin is fine for learning the shape.)
        """
        raise NotImplementedError

    def preference_list(self, key: str, n: int) -> List[str]:
        """TODO: walk partitions clockwise from partition_for(key), collecting
        distinct node names until you have n of them."""
        raise NotImplementedError

    def partitions_per_node(self) -> Dict[str, int]:
        """TODO: tally _assignment. Every node should be within 1 of Q/S."""
        raise NotImplementedError


def keys_moved(before: ConsistentHashRing, after: ConsistentHashRing,
               num_keys: int = 20_000) -> Tuple[int, float]:
    """How many keys changed coordinator between two ring states.

    TODO: compare coordinator() for f"key:{i}" across both rings. Adding the
    Nth node should move roughly 1/N of the keys — that is the property
    consistent hashing buys you over `hash(key) % num_nodes`.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, this should show:
      - load imbalance near 1.1-1.2 with 64 tokens per node
      - preference lists of 3 distinct machines
      - ~1/5 of keys moving when a 5th node joins
      - exactly Q/S partitions per node under PartitionedRing
    """
    ring = ConsistentHashRing(tokens_per_node=64)
    for i in range(4):
        ring.add_node(f"node{i}", datacenter=f"dc{i % 2}")
    print("distribution:", ring.load_distribution())
    print("imbalance:", ring.imbalance())
    print("preference list:", ring.preference_list("cart:user-42", 3))


if __name__ == "__main__":
    _demo()

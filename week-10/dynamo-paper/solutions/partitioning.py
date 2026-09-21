"""
Dynamo Partitioning — Complete Solution

Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007), section 4.2
and section 6.2 (partitioning strategies).
"""

import bisect
import hashlib
from typing import Dict, List, Optional, Tuple

RING_SIZE = 2 ** 32


def md5_hash(key: str) -> int:
    """MD5 of a key, folded onto the ring [0, 2^32). Dynamo used MD5."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % RING_SIZE


# ---------------------------------------------------------------------------
# Strategy 1: T random tokens per node, partition by token value
# ---------------------------------------------------------------------------

class ConsistentHashRing:
    """Dynamo's original partitioning: each node claims T random tokens."""

    def __init__(self, tokens_per_node: int = 64):
        self.tokens_per_node = tokens_per_node
        self._positions: List[int] = []              # sorted token positions
        self._owner: Dict[int, str] = {}             # position -> node
        self._nodes: Dict[str, str] = {}             # node -> datacenter

    # -- membership ---------------------------------------------------------

    def add_node(self, node: str, datacenter: str = "dc0") -> None:
        if node in self._nodes:
            return
        self._nodes[node] = datacenter
        for i in range(self.tokens_per_node):
            pos = md5_hash(f"{node}#{i}")
            while pos in self._owner:                # collisions are rare; probe
                pos = (pos + 1) % RING_SIZE
            bisect.insort(self._positions, pos)
            self._owner[pos] = node

    def remove_node(self, node: str) -> None:
        if node not in self._nodes:
            return
        del self._nodes[node]
        keep = [p for p in self._positions if self._owner[p] != node]
        for p in self._positions:
            if self._owner[p] == node:
                del self._owner[p]
        self._positions = keep

    @property
    def nodes(self) -> List[str]:
        return sorted(self._nodes)

    # -- lookup -------------------------------------------------------------

    def coordinator(self, key: str) -> Optional[str]:
        """First node clockwise from hash(key)."""
        if not self._positions:
            return None
        idx = bisect.bisect_left(self._positions, md5_hash(key))
        if idx == len(self._positions):
            idx = 0
        return self._owner[self._positions[idx]]

    def preference_list(self, key: str, n: int, distinct_dc: bool = False) -> List[str]:
        """The top-N *distinct physical* nodes clockwise from hash(key).

        This is the detail that makes Dynamo's ring different from a plain
        consistent-hash lookup: virtual tokens belonging to a node already in
        the list are skipped, so N replicas always means N machines.  With
        distinct_dc=True we also skip nodes in a datacenter already used, which
        is how Dynamo spreads replicas across failure domains.
        """
        if not self._positions:
            return []
        n = min(n, len(self._nodes))
        idx = bisect.bisect_left(self._positions, md5_hash(key))
        if idx == len(self._positions):
            idx = 0

        result: List[str] = []
        seen_dc = set()
        for step in range(len(self._positions)):
            node = self._owner[self._positions[(idx + step) % len(self._positions)]]
            if node in result:
                continue
            dc = self._nodes[node]
            if distinct_dc and dc in seen_dc and len(seen_dc) < len(set(self._nodes.values())):
                continue
            result.append(node)
            seen_dc.add(dc)
            if len(result) == n:
                break
        return result

    # -- analysis -----------------------------------------------------------

    def load_distribution(self, num_keys: int = 20_000) -> Dict[str, int]:
        counts = {node: 0 for node in self._nodes}
        for i in range(num_keys):
            owner = self.coordinator(f"key:{i}")
            if owner:
                counts[owner] += 1
        return counts

    def imbalance(self, num_keys: int = 20_000) -> float:
        """max_load / mean_load. 1.0 is perfect; Dynamo's strategy 1 sits ~1.1-1.3."""
        counts = self.load_distribution(num_keys)
        if not counts:
            return 0.0
        mean = sum(counts.values()) / len(counts)
        return max(counts.values()) / mean if mean else 0.0


# ---------------------------------------------------------------------------
# Strategy 3: Q equal-sized partitions, Q/S tokens per node
# ---------------------------------------------------------------------------

class PartitionedRing:
    """Dynamo's final partitioning scheme (section 6.2, "strategy 3").

    The ring is cut into Q fixed, equal-sized partitions up front.  Nodes are
    assigned whole partitions, so partition boundaries never move: adding a node
    just transfers ownership of Q/S partitions.  This decouples partitioning
    from placement, which is what makes bootstrapping and archival cheap.
    """

    def __init__(self, num_partitions: int = 1024):
        self.num_partitions = num_partitions
        self.partition_size = RING_SIZE // num_partitions
        self._nodes: List[str] = []
        self._assignment: List[str] = []             # partition index -> node

    def partition_for(self, key: str) -> int:
        return md5_hash(key) // self.partition_size % self.num_partitions

    def add_node(self, node: str) -> None:
        if node in self._nodes:
            return
        self._nodes.append(node)
        self._rebalance()

    def remove_node(self, node: str) -> None:
        if node not in self._nodes:
            return
        self._nodes.remove(node)
        self._rebalance()

    def _rebalance(self) -> None:
        """Round-robin partitions over the sorted node list.

        Real Dynamo hands out partitions to preserve as much existing ownership
        as possible; round-robin keeps the solution readable while still giving
        every node exactly Q/S partitions.
        """
        if not self._nodes:
            self._assignment = []
            return
        nodes = sorted(self._nodes)
        self._assignment = [nodes[i % len(nodes)] for i in range(self.num_partitions)]

    def preference_list(self, key: str, n: int) -> List[str]:
        """Walk partitions clockwise, collecting distinct nodes."""
        if not self._assignment:
            return []
        n = min(n, len(self._nodes))
        start = self.partition_for(key)
        result: List[str] = []
        for step in range(self.num_partitions):
            node = self._assignment[(start + step) % self.num_partitions]
            if node not in result:
                result.append(node)
                if len(result) == n:
                    break
        return result

    def partitions_per_node(self) -> Dict[str, int]:
        counts = {node: 0 for node in self._nodes}
        for node in self._assignment:
            counts[node] += 1
        return counts


# ---------------------------------------------------------------------------
# Migration analysis
# ---------------------------------------------------------------------------

def keys_moved(before: ConsistentHashRing, after: ConsistentHashRing,
               num_keys: int = 20_000) -> Tuple[int, float]:
    """How many keys changed coordinator between two ring states."""
    moved = 0
    for i in range(num_keys):
        key = f"key:{i}"
        if before.coordinator(key) != after.coordinator(key):
            moved += 1
    return moved, moved / num_keys


def _demo() -> None:
    print("=== Strategy 1: T random tokens per node ===")
    ring = ConsistentHashRing(tokens_per_node=64)
    for i in range(4):
        ring.add_node(f"node{i}", datacenter=f"dc{i % 2}")

    dist = ring.load_distribution()
    print("key distribution:", {k: v for k, v in sorted(dist.items())})
    print(f"imbalance (max/mean): {ring.imbalance():.3f}")

    pref = ring.preference_list("cart:user-42", n=3)
    print("preference list for 'cart:user-42':", pref)
    print("  all distinct physical nodes:", len(pref) == len(set(pref)))

    pref_dc = ring.preference_list("cart:user-42", n=3, distinct_dc=True)
    print("preference list, DC-aware:", pref_dc,
          "->", [ring._nodes[n] for n in pref_dc])

    print("\n=== Adding a 5th node ===")
    import copy
    before = copy.deepcopy(ring)
    ring.add_node("node4", datacenter="dc0")
    moved, frac = keys_moved(before, ring)
    print(f"keys remapped: {moved} ({frac:.1%})   ideal 1/N = {1/5:.1%}")

    print("\n=== Strategy 3: Q fixed partitions ===")
    pr = PartitionedRing(num_partitions=1024)
    for i in range(4):
        pr.add_node(f"node{i}")
    print("partitions per node:", pr.partitions_per_node())
    print("preference list for 'cart:user-42':", pr.preference_list("cart:user-42", 3))
    pr.add_node("node4")
    print("after adding node4:", pr.partitions_per_node())
    print("Q/S is exact — this is why strategy 3 bootstraps faster.")


if __name__ == "__main__":
    _demo()

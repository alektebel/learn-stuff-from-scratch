"""
Key-to-node assignment and rebalancing on top of a consistent-hashing ring.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 6
("Partitioning"), especially "Rebalancing Partitions" and "Request Routing".
Restated: a partitioner answers two questions - which node owns a key right
now, and what moves when membership changes. With consistent hashing, the
second is a *consequence* of the first: recompute the owner of every key and the
only keys that moved are the ones whose new owner differs. No node copies the
whole dataset when another joins.

This module also measures the two things a ring can and cannot promise:
  * `evenness` - how evenly *unique keys* are spread. Virtual nodes make this
    good (within `EVENNESS_BOUND`).
  * `load` - how much *work* each node gets, weighting a key by its access
    frequency. Evenness of keys does not save you from a hot key.

DESIGN DECISION - how is rebalancing expressed?
    Option A: track ownership ourselves and copy keys between nodes.
    Option B: the ring is the source of truth; a join/leave recomputes the
    mapping and returns the diff.
    Chosen: B. The correct amount to move (exactly the changed node's share)
    falls out of the ring rather than being a second rule that can disagree with
    it. Cost: `join`/`leave` are O(keys x log(tokens)) because they re-assign
    every key; a production system migrates the keys it actually stored, not a
    fresh sample.

DESIGN DECISION - what is the evenness metric?
    The ratio of the busiest node's share to the mean share, `max / mean`.
    1.0 is a perfectly even ring; higher is more skewed. It is simple, has a
    stated bound, and is the quantity a hot spot violates.
    Chosen: `max / mean`, bound 1.25 with 256 virtual nodes. Cost: it ignores
    the *minimum*, so one starved node can hide behind seven even ones.

DESIGN DECISION - is load the same as key count?
    No. A partitioner that only balances key counts will happily put a key read
    a million times a second on one node. `load(keys, weights)` weights each key
    by its access count so the skew is visible.
    Chosen: separate `counts` (unique keys, balanced by the ring) and `load`
    (weighted, can be arbitrarily skewed). Cost: the ring cannot *fix* a hot
    key; the measurement is the deliverable, and the README says what would
    (split the key, replicate it, or cache it).
"""

from typing import Dict, Iterable, Mapping, Optional, Sequence, Set

from hashring import HashRing

__all__ = ["Partitioner", "DEFAULT_VNODES", "EVENNESS_BOUND"]

#: Virtual nodes per physical node by default.
DEFAULT_VNODES = 256

#: Peak-to-mean share a ring with `DEFAULT_VNODES` must stay under.
EVENNESS_BOUND = 1.25


class Partitioner:
    """Assigns keys to nodes and reports what membership changes move."""

    def __init__(self, nodes: Iterable[str] = (), vnodes: int = DEFAULT_VNODES) -> None:
        self.ring = HashRing(vnodes=vnodes)
        for node in nodes:
            self.ring.add_node(node)

    # -- read-only operations ----------------------------------------------

    def assign(self, keys: Sequence[str]) -> Dict[str, str]:
        """Map every key to its owning node. Pure: does not change the ring."""
        # TODO: Return {key: ring.node_for(key)} for every key. Read-only.
        raise NotImplementedError("Partitioner.assign")

    def counts(self, keys: Sequence[str]) -> Dict[str, int]:
        """Number of unique keys per node (0 for a node with none)."""
        # TODO: Start every current node at 0, then add one per assigned key so a node with no keys still appears.
        raise NotImplementedError("Partitioner.counts")

    @staticmethod
    def evenness(counts: Mapping[str, int]) -> float:
        """Peak-to-mean share: 1.0 is even, larger is more skewed."""
        # TODO: Peak-to-mean share: max(counts) / mean(counts). 1.0 is perfect; return 0.0 when the mean is 0.
        raise NotImplementedError("Partitioner.evenness")

    # -- membership changes -------------------------------------------------

    def join(self, node: str, keys: Sequence[str]) -> Set[str]:
        """Add `node`; return exactly the keys whose owner changed."""
        # TODO: Snapshot the owners, add the node, snapshot again, and return the set of keys whose owner changed. Only the new node's arcs should be affected.
        raise NotImplementedError("Partitioner.join")

    def leave(self, node: str, keys: Sequence[str]) -> Set[str]:
        """Remove `node`; return exactly the keys whose owner changed."""
        # TODO: Snapshot the owners, remove the node, snapshot again, and return the set of keys whose owner changed. It should equal the set the node owned.
        raise NotImplementedError("Partitioner.leave")

    # -- load, as opposed to key count -------------------------------------

    def load(self, keys: Sequence[str], weights: Optional[Mapping[str, int]] = None
             ) -> Dict[str, int]:
        """Access load per node: each key counts `weights[key]` (default 1)."""
        # TODO: Start every node at 0. For each key add weights.get(key, 1) (or 1 when weights is None) to its owner's total. This is why a hot key shows up: key counts stay even, weighted load does not.
        raise NotImplementedError("Partitioner.load")


def _demo() -> None:
    import random

    nodes = [f"node-{i}" for i in range(8)]
    rng = random.Random(20261010)
    keys = [f"{rng.getrandbits(64):016x}" for _ in range(20000)]

    p = Partitioner(nodes, vnodes=DEFAULT_VNODES)
    counts = p.counts(keys)
    print(f"key distribution over {len(nodes)} nodes x {DEFAULT_VNODES} vnodes")
    print(f"  evenness (peak/mean) = {p.evenness(counts):.3f}  "
          f"(bound {EVENNESS_BOUND})")
    print(f"  per-node keys        = {sorted(counts.values())}")

    before = p.assign(keys)
    moved = p.join("node-8", keys)
    after = p.assign(keys)
    print(f"join node-8: {len(moved)}/{len(keys)} keys moved ({len(moved) / len(keys):.1%}), "
          f"all to the new node: {all(after[k] == 'node-8' for k in moved)}")

    p2 = Partitioner(nodes, vnodes=DEFAULT_VNODES)
    owned = {k for k in keys if p2.ring.node_for(k) == "node-3"}
    left = p2.leave("node-3", keys)
    print(f"leave node-3: moved {len(left)} keys, exactly its {len(owned)} keys: "
          f"{left == owned}")

    hot = keys[0]
    weights = {key: 1 for key in keys}
    weights[hot] = 1_000_000
    loads = p.load(keys, weights)
    total = sum(loads.values())
    hot_node = p.ring.node_for(hot)
    print(f"hot key {hot[:8]}... on {hot_node}: {loads[hot_node] / total:.1%} of all "
          "accesses despite an even ring")
    print("  that is the limit of consistent hashing: it balances keys, not load")


if __name__ == "__main__":
    _demo()

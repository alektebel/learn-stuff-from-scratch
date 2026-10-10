"""
Consistent hashing: a ring with virtual nodes.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 6
("Partitioning"), the section on consistent hashing and the discussion of skew
and hot spots. Restated here in my own words: instead of `hash(key) % N`,
which sends almost every key to a new node as soon as N changes, map both nodes
and keys onto the same circular id space and give a key to the first node at or
after it clockwise. Joining or leaving moves only the arc the changed node owns.

A single point per node still leaves randomly sized arcs, and with few nodes one
node can own a huge arc. Each physical node is therefore placed at many ring
positions ("virtual nodes"); its arcs scatter across the ring and the law of
large numbers evens the load out. `partitioner.py` measures that evenness.

DESIGN DECISION - which hash function?
    Python's built-in `hash()` is salted per process (PYTHONHASHSEED), so the
    same key maps to different nodes after every restart or between machines: a
    write lands on one node and the read for it goes to another. A stable digest
    (SHA-256 here) is reproducible everywhere.
    Chosen: SHA-256, mapped to a 256-bit integer. Cost: slower than `hash()`,
    which is irrelevant next to the network hop a lookup saves.

DESIGN DECISION - how are the ring positions stored?
    A sorted array of (hash, node) plus `bisect` for "first position >= h",
    versus a balanced tree or a linear scan.
    Chosen: sorted array + bisect. Rebuild is O(V log V) for V total tokens
    (nodes x vnodes) and a lookup is O(log V); a scan would make every lookup
    O(V). Cost: adding a node rebuilds the whole array - fine because membership
    changes are rare and rebuild is deferred until the next lookup.

DESIGN DECISION - when is the ring rebuilt?
    Eagerly on every add/remove, or lazily before the first lookup after a
    change.
    Chosen: lazily, tracked by `_dirty`. A burst of membership changes costs one
    rebuild, and a membership change with no lookups in between costs nothing.
    Cost: the first lookup after a change pays the whole rebuild.

DESIGN DECISION - how many virtual nodes?
    1 per node is cheapest but, as the limit case shows, leaves a badly uneven
    ring with a handful of nodes; thousands cost memory and rebuild time.
    Chosen: 256 (the `DEFAULT_VNODES` in `partitioner.py`), which brings the
    peak-to-average share comfortably under the stated bound. Cost: 256 sorted
    positions per node.
"""

import bisect
import hashlib
from typing import Dict, List, Optional, Tuple

__all__ = ["HashRing", "_hash"]


def _hash(data: str) -> int:
    """A stable 256-bit hash of a string, independent of the process it runs in."""
    # TODO: Hash the UTF-8 bytes of the string with hashlib.sha256 and return the digest as one big integer. Do NOT use the built-in hash(): it is salted per process, so the ring would move every key on restart.
    raise NotImplementedError("_hash")


class HashRing:
    """A consistent-hashing ring of nodes, each placed at `vnodes` positions."""

    def __init__(self, vnodes: int = 256) -> None:
        if vnodes < 1:
            raise ValueError("vnodes must be at least 1")
        self.vnodes = vnodes
        self.nodes: set = set()
        self._tokens: List[Tuple[int, str]] = []
        self._hashes: List[int] = []
        self._dirty = True

    # -- membership ---------------------------------------------------------

    def add_node(self, node: str) -> None:
        """Place `node` at its virtual positions. Idempotent."""
        # TODO: If the node is not already a member, add it and mark the ring dirty so the next lookup rebuilds.
        raise NotImplementedError("HashRing.add_node")

    def remove_node(self, node: str) -> None:
        """Take `node` off the ring; its keys fall to the next node clockwise."""
        # TODO: If the node is a member, discard it and mark the ring dirty.
        raise NotImplementedError("HashRing.remove_node")

    def __contains__(self, node: str) -> bool:
        return node in self.nodes

    def __len__(self) -> int:
        return len(self.nodes)

    # -- the ring itself ----------------------------------------------------

    def _rebuild(self) -> None:
        """Recompute the sorted token array from the current node set."""
        # TODO: For every node, add `vnodes` positions hashing f'{node}#{replica}'. Sort the (hash, node) pairs. Keep the list of hashes for bisect. Clear the dirty flag.
        raise NotImplementedError("HashRing._rebuild")

    def tokens(self) -> List[Tuple[int, str]]:
        """The sorted (hash, node) positions, for inspection and teaching."""
        # TODO: Rebuild if dirty, then return a copy of the sorted (hash, node) list. Reading must not mutate the ring.
        raise NotImplementedError("HashRing.tokens")

    # -- lookup -------------------------------------------------------------

    def node_for(self, key: str) -> Optional[str]:
        """The node that owns `key`: the first token at or after its hash,
        wrapping around. Pure: it never changes the ring."""
        # TODO: Rebuild if dirty. bisect_left the key's hash in the sorted hashes; the owner is that token's node, or the first token if the index runs past the end (the ring wraps). Empty ring returns None.
        raise NotImplementedError("HashRing.node_for")

    def distribution(self, keys) -> Dict[str, int]:
        """How many of `keys` each node owns (every node appears, even at 0)."""
        counts = {node: 0 for node in self.nodes}
        for key in keys:
            node = self.node_for(key)
            if node is not None:
                counts[node] += 1
        return counts


def _demo() -> None:
    import random

    nodes = [f"node-{i}" for i in range(8)]
    rng = random.Random(20261010)
    keys = [f"{rng.getrandbits(64):016x}" for _ in range(20000)]

    print("consistent hashing: peak/mean share of 20000 keys over 8 nodes")
    for vnodes in (1, 4, 64, 256):
        ring = HashRing(vnodes=vnodes)
        for node in nodes:
            ring.add_node(node)
        counts = ring.distribution(keys)
        values = list(counts.values())
        mean = sum(values) / len(values)
        print(f"  vnodes={vnodes:>3}  peak/mean={max(values) / mean:.3f}  "
              f"low/mean={min(values) / mean:.3f}")

    before = HashRing(vnodes=256)
    for node in nodes:
        before.add_node(node)
    old = {key: before.node_for(key) for key in keys}
    before.add_node("node-8")
    moved = sum(1 for key in keys if before.node_for(key) != old[key])
    print(f"joining one node moved {moved / len(keys):.1%} of keys "
          f"(ideal 1/9 = {1 / 9:.1%}); modulo hashing would move almost all")


if __name__ == "__main__":
    _demo()

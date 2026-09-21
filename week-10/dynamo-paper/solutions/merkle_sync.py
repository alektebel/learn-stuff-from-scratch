"""
Merkle Trees & Anti-Entropy Replica Synchronisation — Complete Solution

Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007), section 4.7.
"""

import hashlib
from typing import Dict, Iterable, List, Optional, Set, Tuple

from partitioning import RING_SIZE, md5_hash
from vector_clock import VersionedValue, coalesce


def _digest(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
        h.update(b"\x00")
    return h.hexdigest()


class MerkleNode:
    __slots__ = ("lo", "hi", "hash", "left", "right", "num_keys")

    def __init__(self, lo: int, hi: int, hash_: str,
                 left: Optional["MerkleNode"] = None,
                 right: Optional["MerkleNode"] = None, num_keys: int = 0):
        self.lo, self.hi = lo, hi        # the ring range this node covers
        self.hash = hash_
        self.left, self.right = left, right
        self.num_keys = num_keys

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def __repr__(self) -> str:
        return f"<Merkle [{self.lo},{self.hi}) {self.hash[:8]} keys={self.num_keys}>"


class MerkleTree:
    """A hash tree over one key range, used to diff two replicas cheaply.

    Each leaf covers a slice of the ring and hashes the (key, version-clock)
    pairs that land in it.  Comparing two trees costs O(differences · log n)
    network round trips instead of shipping the whole key set: if two roots
    match, the replicas are identical and nothing is transferred.
    """

    def __init__(self, lo: int = 0, hi: int = RING_SIZE, depth: int = 6):
        self.lo, self.hi, self.depth = lo, hi, depth
        self.root: Optional[MerkleNode] = None

    # -- construction -------------------------------------------------------

    @staticmethod
    def _leaf_hash(items: List[Tuple[str, str]]) -> str:
        """Hash a leaf's (key, version-fingerprint) pairs, order-independent."""
        if not items:
            return _digest("EMPTY")
        return _digest(*[f"{k}={v}" for k, v in sorted(items)])

    @staticmethod
    def fingerprint(versions: List[VersionedValue]) -> str:
        """Identify a key's *state* without shipping the value itself."""
        return _digest(*sorted(repr(v.clock) for v in versions))

    def build(self, store: Dict[str, List[VersionedValue]]) -> MerkleNode:
        items: List[Tuple[int, str, str]] = []
        for key, versions in store.items():
            pos = md5_hash(key)
            if self.lo <= pos < self.hi:
                items.append((pos, key, self.fingerprint(versions)))
        items.sort()
        self.root = self._build(self.lo, self.hi, self.depth, items)
        return self.root

    def _build(self, lo: int, hi: int, depth: int,
               items: List[Tuple[int, str, str]]) -> MerkleNode:
        in_range = [(k, f) for pos, k, f in items if lo <= pos < hi]
        if depth == 0 or hi - lo <= 1:
            return MerkleNode(lo, hi, self._leaf_hash(in_range), num_keys=len(in_range))
        mid = (lo + hi) // 2
        left = self._build(lo, mid, depth - 1, items)
        right = self._build(mid, hi, depth - 1, items)
        return MerkleNode(lo, hi, _digest(left.hash, right.hash), left, right,
                          left.num_keys + right.num_keys)

    # -- diffing ------------------------------------------------------------

    def diff(self, other: "MerkleTree") -> Tuple[List[Tuple[int, int]], int]:
        """Ranges where the two trees disagree, plus the nodes compared.

        The node count is the interesting number: it is what the comparison
        actually costs on the wire.
        """
        if self.root is None or other.root is None:
            raise ValueError("build() both trees first")
        ranges: List[Tuple[int, int]] = []
        compared = 0

        def walk(a: MerkleNode, b: MerkleNode) -> None:
            nonlocal compared
            compared += 1
            if a.hash == b.hash:
                return                       # whole subtree is identical — stop
            if a.is_leaf or b.is_leaf:
                ranges.append((a.lo, a.hi))
                return
            walk(a.left, b.left)             # type: ignore[arg-type]
            walk(a.right, b.right)           # type: ignore[arg-type]

        walk(self.root, other.root)
        return ranges, compared


def keys_in_ranges(store: Dict[str, List[VersionedValue]],
                   ranges: Iterable[Tuple[int, int]]) -> Set[str]:
    bounds = list(ranges)
    return {key for key in store
            if any(lo <= md5_hash(key) < hi for lo, hi in bounds)}


class AntiEntropy:
    """The background repair loop each Dynamo node runs against its peers."""

    def __init__(self, depth: int = 6):
        self.depth = depth
        self.stats = {"syncs": 0, "nodes_compared": 0, "keys_transferred": 0}

    def synchronize(self, a_store: Dict[str, List[VersionedValue]],
                    b_store: Dict[str, List[VersionedValue]],
                    lo: int = 0, hi: int = RING_SIZE) -> Set[str]:
        """Make two replicas agree over [lo, hi). Returns the keys exchanged.

        Merging is a union of versions followed by coalesce(), so this is safe
        to run in any direction and any number of times: it can only ever move
        both stores toward the join of their versions, never lose one.
        """
        self.stats["syncs"] += 1
        tree_a, tree_b = MerkleTree(lo, hi, self.depth), MerkleTree(lo, hi, self.depth)
        tree_a.build(a_store)
        tree_b.build(b_store)

        ranges, compared = tree_a.diff(tree_b)
        self.stats["nodes_compared"] += compared
        if not ranges:
            return set()

        candidates = keys_in_ranges(a_store, ranges) | keys_in_ranges(b_store, ranges)
        transferred: Set[str] = set()
        for key in candidates:
            versions_a = a_store.get(key, [])
            versions_b = b_store.get(key, [])
            merged = coalesce(versions_a + versions_b)
            if coalesce(versions_a) != merged or coalesce(versions_b) != merged:
                transferred.add(key)
            a_store[key] = list(merged)
            b_store[key] = list(merged)
        self.stats["keys_transferred"] += len(transferred)
        return transferred


def _demo() -> None:
    from vector_clock import VectorClock

    def make(node: str, key: str, value: object, counter: int = 1) -> VersionedValue:
        clock = VectorClock()
        for _ in range(counter):
            clock = clock.increment(node)
        return VersionedValue(value, clock)

    print("=== Two replicas that agree ===")
    store_a: Dict[str, List[VersionedValue]] = {
        f"key:{i}": [make("node0", f"key:{i}", i)] for i in range(1000)
    }
    store_b = {k: list(v) for k, v in store_a.items()}

    tree_a, tree_b = MerkleTree(depth=8), MerkleTree(depth=8)
    tree_a.build(store_a)
    tree_b.build(store_b)
    print(f"root A == root B: {tree_a.root.hash == tree_b.root.hash}")
    ranges, compared = tree_a.diff(tree_b)
    print(f"identical replicas: {compared} node comparison, {len(ranges)} ranges to sync")
    print("1000 keys, 1 hash exchanged. This is the whole point of the tree.")

    print("\n=== One replica drifts (3 keys out of 1000) ===")
    store_b["key:7"] = [make("node1", "key:7", "updated", counter=2)]
    store_b["key:500"] = [make("node1", "key:500", "updated", counter=2)]
    del store_b["key:900"]                    # this one only exists on A

    engine = AntiEntropy(depth=8)
    transferred = engine.synchronize(store_a, store_b)
    print(f"nodes compared: {engine.stats['nodes_compared']} (out of {2**9 - 1} in the tree)")
    print(f"keys transferred: {sorted(transferred)}")

    tree_a, tree_b = MerkleTree(depth=8), MerkleTree(depth=8)
    tree_a.build(store_a)
    tree_b.build(store_b)
    print(f"roots match after sync: {tree_a.root.hash == tree_b.root.hash}")
    print(f"key:900 restored on B: {'key:900' in store_b}")
    print(f"key:7 now holds {len(store_a['key:7'])} versions on both sides: "
          f"{[v.value for v in store_a['key:7']]}")

    print("\n=== Concurrent divergence becomes siblings, not a lost write ===")
    store_c: Dict[str, List[VersionedValue]] = {"cart:1": [make("nodeX", "cart:1", {"a": 1})]}
    store_d: Dict[str, List[VersionedValue]] = {"cart:1": [make("nodeY", "cart:1", {"b": 1})]}
    engine.synchronize(store_c, store_d)
    print(f"after sync, both replicas hold {len(store_c['cart:1'])} siblings: "
          f"{[v.value for v in store_c['cart:1']]}")
    print("Anti-entropy never picks a winner — it only makes replicas agree on")
    print("the full set of versions, leaving reconciliation to the application.")

    print("\n=== Cost of tree depth ===")
    for depth in (4, 8, 12):
        engine = AntiEntropy(depth=depth)
        a = {f"k{i}": [make("n0", f"k{i}", i)] for i in range(2000)}
        b = {k: list(v) for k, v in a.items()}
        b["k42"] = [make("n1", "k42", "x", counter=2)]
        moved = engine.synchronize(a, b)
        print(f"  depth={depth:2d}  leaves={2**depth:5d}  "
              f"nodes compared={engine.stats['nodes_compared']:3d}  "
              f"keys transferred={len(moved)}")
    print("Deeper trees narrow the search but cost more to build and store —")
    print("Dynamo keeps one tree per key range per replica for exactly this reason.")


if __name__ == "__main__":
    _demo()

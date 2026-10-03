"""
Merkle Trees & Anti-Entropy — From Scratch
===========================================
Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007),
       section 4.7 ("Handling permanent failures: Replica synchronization").

Requires: partitioning.py, vector_clock.py.

Build the background repair layer to understand:
- Why comparing replicas key-by-key does not scale, and what a hash tree fixes
- What exactly goes into a leaf hash (and why it is not the value)
- Why anti-entropy must never pick a winner between concurrent versions
- The real cost of tree depth

Learning Path:
1. Implement MerkleTree.build over a key range
2. Implement MerkleTree.diff — descend only where hashes disagree
3. Implement AntiEntropy.synchronize using the diff ranges
4. Measure: identical replicas should cost exactly ONE hash comparison
5. Vary tree depth and watch the comparison count grow as log(leaves)

Background:
  Hinted handoff covers transient failures. It does nothing for a disk that
  died, a node rebuilt from scratch, or a hint holder that crashed before
  delivery. For those, replicas must be able to find their differences
  directly.

  A Merkle tree hashes the key range hierarchically: leaves hash the keys in a
  slice of the ring, internal nodes hash their children. Two replicas compare
  roots; if the roots match, the replicas are identical and one hash crossed
  the network for the entire dataset. If they differ, each side descends only
  into subtrees whose hashes disagree, so the traffic is proportional to the
  number of *differences*, not the number of keys.

  A leaf hashes each key's *version fingerprint* — a digest of its vector
  clocks — not the value. That keeps the tree small and, more importantly,
  makes it insensitive to representation: two replicas holding the same
  version must produce the same leaf hash.

  Anti-entropy is a union, not a choice. When two replicas hold concurrent
  versions the result is both of them, as siblings. Picking one here would
  reintroduce exactly the lost update that vector clocks exist to prevent.
"""

import hashlib
from typing import Dict, Iterable, List, Optional, Set, Tuple

from partitioning import RING_SIZE, md5_hash
from vector_clock import VersionedValue, coalesce


def _digest(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
        h.update(b"\x00")          # separator: prevents "ab"+"c" == "a"+"bc"
    return h.hexdigest()


class MerkleNode:
    __slots__ = ("lo", "hi", "hash", "left", "right", "num_keys")

    def __init__(self, lo: int, hi: int, hash_: str,
                 left: Optional["MerkleNode"] = None,
                 right: Optional["MerkleNode"] = None, num_keys: int = 0):
        self.lo, self.hi = lo, hi
        self.hash = hash_
        self.left, self.right = left, right
        self.num_keys = num_keys

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


# ---------------------------------------------------------------------------
# Step 1-2: The tree
# ---------------------------------------------------------------------------

class MerkleTree:
    """A hash tree over the ring range [lo, hi)."""

    def __init__(self, lo: int = 0, hi: int = RING_SIZE, depth: int = 6):
        self.lo, self.hi, self.depth = lo, hi, depth
        self.root: Optional[MerkleNode] = None

    @staticmethod
    def fingerprint(versions: List[VersionedValue]) -> str:
        """Identify a key's state without shipping its value.

        TODO: _digest over the sorted repr() of each version's clock. Sorting
        matters — two replicas may hold the same siblings in a different order
        and must still hash identically.
        """
        raise NotImplementedError

    @staticmethod
    def _leaf_hash(items: List[Tuple[str, str]]) -> str:
        """TODO: _digest("EMPTY") for an empty leaf, otherwise _digest over
        sorted f"{key}={fingerprint}" strings."""
        raise NotImplementedError

    def build(self, store: Dict[str, List[VersionedValue]]) -> MerkleNode:
        """Build the tree over the keys of `store` that fall in [lo, hi).

        TODO:
        1. For each key, compute md5_hash(key); keep it if lo <= pos < hi.
        2. Collect (pos, key, fingerprint(versions)) triples and sort them.
        3. self.root = self._build(lo, hi, depth, items); return it.
        """
        raise NotImplementedError

    def _build(self, lo: int, hi: int, depth: int,
               items: List[Tuple[int, str, str]]) -> MerkleNode:
        """Recursive construction.

        TODO:
        1. Select the items whose position falls in [lo, hi).
        2. Base case (depth == 0 or hi - lo <= 1): return a leaf whose hash is
           _leaf_hash of those items.
        3. Otherwise split at mid = (lo + hi) // 2, build both children, and
           return a node hashing _digest(left.hash, right.hash).
        """
        raise NotImplementedError

    def diff(self, other: "MerkleTree") -> Tuple[List[Tuple[int, int]], int]:
        """Ranges where the trees disagree, plus how many nodes were compared.

        TODO: walk both trees in lockstep.
          - equal hashes  -> return immediately, the whole subtree matches
          - either a leaf -> record (lo, hi) as a differing range
          - otherwise     -> recurse into both children
        Count every comparison; that count is the real network cost.

        Test: two identical 1000-key replicas must produce exactly 1 comparison
        and 0 ranges. If you see more, your hashes are not deterministic.
        """
        raise NotImplementedError


def keys_in_ranges(store: Dict[str, List[VersionedValue]],
                   ranges: Iterable[Tuple[int, int]]) -> Set[str]:
    """TODO: every key of `store` whose md5_hash falls inside any range."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 3: The repair loop
# ---------------------------------------------------------------------------

class AntiEntropy:
    """The background repair each node runs against its replica peers."""

    def __init__(self, depth: int = 6):
        self.depth = depth
        self.stats = {"syncs": 0, "nodes_compared": 0, "keys_transferred": 0}

    def synchronize(self, a_store: Dict[str, List[VersionedValue]],
                    b_store: Dict[str, List[VersionedValue]],
                    lo: int = 0, hi: int = RING_SIZE) -> Set[str]:
        """Make two replicas agree over [lo, hi). Returns the keys exchanged.

        TODO:
        1. Build a MerkleTree over each store and diff them.
        2. Return an empty set if there are no differing ranges.
        3. Collect the candidate keys from BOTH stores in those ranges — a key
           missing entirely from one side still needs to be copied.
        4. For each candidate: merged = coalesce(a_versions + b_versions).
           Record it as transferred if either side did not already equal the
           merge. Write merged to both stores.

        Properties worth verifying:
          - Idempotent: running it twice transfers nothing the second time.
          - Symmetric: which store you pass first must not matter.
          - Non-destructive: two concurrent versions come out as two siblings,
            never one.
        """
        raise NotImplementedError


def _demo() -> None:
    """Once implemented, confirm each of these:

    1. Two identical 1000-key replicas: roots match, ONE comparison, no traffic.
    2. Break three keys (two modified, one missing entirely): the sync should
       compare a few dozen tree nodes, not 1000 keys, and transfer exactly
       those three.
    3. Roots match again afterwards.
    4. Two replicas holding concurrent versions of the same key end up with two
       siblings on both sides — anti-entropy never picks a winner.
    5. Depth 4 / 8 / 12 over the same data: comparisons grow like log(leaves)
       while the keys transferred stay at 1.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

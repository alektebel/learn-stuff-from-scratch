"""
Vector Clocks & Sibling Reconciliation — From Scratch
=====================================================
Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007),
       section 4.4 ("Data Versioning") and Figure 3.

Build Dynamo's versioning layer to understand:
- Why last-write-wins loses data that a distributed cart cannot afford to lose
- How a vector clock distinguishes "newer than" from "concurrent with"
- The split between syntactic reconciliation (free) and semantic (app logic)
- Why the paper truncates clocks, and what that costs

Learning Path:
1. Implement VectorClock: increment, descends_from, compare, merge
2. Implement coalesce() — drop versions that another version supersedes
3. Implement reconcile() — collapse true siblings with an application merge
4. Reproduce Figure 3 from the paper (D1 -> D2 -> D3/D4 -> D5)
5. Implement truncation and think about the false concurrency it creates

Background:
  A vector clock is a map of node -> counter. The coordinator of a write
  increments its own entry. Clock A "descends from" clock B when every counter
  in B is <= the matching counter in A, meaning A saw everything B saw.

    A descends from B  and  B descends from A   -> same version
    A descends from B  only                     -> A is newer, drop B
    neither                                     -> concurrent: SIBLINGS

  Siblings are not an error. They are the honest answer to "two clients
  updated the same version at the same time and no ordering exists between
  them". Dynamo returns all of them and lets the application decide, because
  only the application knows that two shopping carts should be unioned rather
  than one picked.

  The "context" is the clock, handed to the client on get() and passed back on
  put(). It is what turns a blind write into an update of a specific version.
  Forget to pass it and you create a sibling instead of overwriting.
"""

import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

BEFORE = "BEFORE"          # self happened before other
AFTER = "AFTER"            # self happened after other
EQUAL = "EQUAL"
CONCURRENT = "CONCURRENT"  # neither dominates -> siblings


# ---------------------------------------------------------------------------
# Step 1: The clock
# ---------------------------------------------------------------------------

class VectorClock:
    """A map of node -> (counter, last_updated_ms).

    The timestamp exists only to support truncation: when the clock exceeds
    MAX_ENTRIES, the least-recently-updated entry is dropped. Dynamo caps this
    at 10 entries and accepts the resulting inaccuracy.
    """

    MAX_ENTRIES = 10

    def __init__(self, entries: Optional[Dict[str, Tuple[int, float]]] = None):
        self.entries: Dict[str, Tuple[int, float]] = dict(entries or {})

    def copy(self) -> "VectorClock":
        return VectorClock(dict(self.entries))

    def counter(self, node: str) -> int:
        """TODO: this node's counter, or 0 if absent."""
        raise NotImplementedError

    def increment(self, node: str, now: Optional[float] = None) -> "VectorClock":
        """Return a NEW clock with `node`'s counter bumped by one.

        TODO:
        1. Default `now` to time.time() * 1000.
        2. Copy self, set entries[node] = (old_counter + 1, now).
        3. Call _truncate() and return the copy.

        Keep clocks immutable — a version's clock must never change under it.
        """
        raise NotImplementedError

    def _truncate(self) -> None:
        """Drop the oldest entries once the clock exceeds MAX_ENTRIES.

        TODO: sort entries by their timestamp descending, keep the first
        MAX_ENTRIES. Think about what this does to correctness: a dropped entry
        reads as counter 0, so a clock that genuinely descended from another can
        start looking concurrent, producing a sibling that never existed.
        """
        raise NotImplementedError

    def descends_from(self, other: "VectorClock") -> bool:
        """True if self saw everything other saw.

        TODO: all(self.counter(node) >= counter for node, counter in other).
        """
        raise NotImplementedError

    def compare(self, other: "VectorClock") -> str:
        """Return EQUAL / AFTER / BEFORE / CONCURRENT.

        TODO: compute descends_from in both directions and map the four cases.
        """
        raise NotImplementedError

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Pointwise max — the clock of a value reconciled from both.

        TODO: for each node take the higher counter (and the later timestamp
        when counters tie), then truncate.
        """
        raise NotImplementedError

    def to_context(self) -> Dict[str, int]:
        """The opaque context handed back to the client. TODO: strip timestamps."""
        raise NotImplementedError

    @classmethod
    def from_context(cls, context: Dict[str, int],
                     now: Optional[float] = None) -> "VectorClock":
        """TODO: rebuild a clock from a client-supplied context."""
        raise NotImplementedError

    def __repr__(self) -> str:
        inner = ", ".join(f"{n}:{c}" for n, (c, _) in sorted(self.entries.items()))
        return f"[{inner}]"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return NotImplemented
        return self.to_context() == other.to_context()

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.to_context().items())))


class VersionedValue:
    """A (value, clock) pair — what Dynamo calls an object version."""

    __slots__ = ("value", "clock")

    def __init__(self, value: Any, clock: VectorClock):
        self.value = value
        self.clock = clock

    def __repr__(self) -> str:
        return f"VersionedValue({self.value!r}, {self.clock})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionedValue):
            return NotImplemented
        return self.value == other.value and self.clock == other.clock


# ---------------------------------------------------------------------------
# Step 2: Syntactic reconciliation
# ---------------------------------------------------------------------------

def coalesce(versions: Iterable[VersionedValue]) -> List[VersionedValue]:
    """Drop every version that another version strictly descends from.

    This needs no knowledge of what the values mean, which is why a storage
    node can do it on every local write and every read. Whatever survives with
    more than one entry is a genuine sibling set.

    TODO:
    1. Walk candidates, maintaining a list of survivors.
    2. For each candidate, compare against each survivor:
         BEFORE or EQUAL -> the candidate is dominated, skip it
         AFTER           -> that survivor is dominated, remove it
         CONCURRENT      -> keep both
    3. Append the candidate if nothing dominated it.

    Test: coalesce([D1, D2, D3, D4]) from Figure 3 must return exactly D3 and
    D4 — D1 and D2 are ancestors of both.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 3: Semantic reconciliation
# ---------------------------------------------------------------------------

def reconcile(versions: List[VersionedValue],
              merge_fn: Callable[[List[Any]], Any],
              node: str) -> VersionedValue:
    """Collapse siblings using application logic.

    TODO:
    1. coalesce() first — some "siblings" are just stale.
    2. If one version survives, return it unchanged.
    3. Otherwise merge all sibling clocks pointwise, increment at `node`, and
       pair that clock with merge_fn([sibling values]).

    The increment matters: without it the merged clock would be merely EQUAL to
    the join of the siblings, and a replica still holding an original could
    resurrect it as a concurrent version.
    """
    raise NotImplementedError


def merge_carts(carts: List[Dict[str, int]]) -> Dict[str, int]:
    """The paper's shopping-cart merge: union of items, highest quantity wins.

    TODO: build a dict taking max(qty) per SKU across all sibling carts.

    Note what this cannot do: a removal looks identical to "never added", so a
    deleted item can come back. The paper acknowledges exactly this. Modelling
    removals properly needs tombstones (an OR-Set), which is worth trying as an
    extension once the basic merge works.
    """
    raise NotImplementedError


def _demo() -> None:
    """Reproduce Figure 3 from the paper.

    Expected once implemented:
      D1 [Sx:1]                {'book': 1}
      D2 [Sx:2]                {'book': 1, 'pen': 1}
      D3 [Sx:2, Sy:1]          + mug      (Sy coordinates)
      D4 [Sx:2, Sz:1]          + lamp     (Sz coordinates)
      D3 vs D4 -> CONCURRENT
      coalesce(D1..D4) -> [D3, D4]
      D5 [Sx:3, Sy:1, Sz:1]    all four items, descends from both
    """
    d1 = VersionedValue({"book": 1}, VectorClock().increment("Sx"))
    d2 = VersionedValue({"book": 1, "pen": 1}, d1.clock.increment("Sx"))
    d3 = VersionedValue({**d2.value, "mug": 1}, d2.clock.increment("Sy"))
    d4 = VersionedValue({**d2.value, "lamp": 1}, d2.clock.increment("Sz"))
    print("D3 vs D4 ->", d3.clock.compare(d4.clock))
    print("coalesce ->", coalesce([d1, d2, d3, d4]))
    print("reconciled ->", reconcile([d3, d4], merge_carts, node="Sx"))


if __name__ == "__main__":
    _demo()

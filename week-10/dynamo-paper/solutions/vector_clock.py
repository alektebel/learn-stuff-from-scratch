"""
Vector Clocks & Sibling Reconciliation — Complete Solution

Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007), section 4.4.
"""

import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

BEFORE = "BEFORE"          # self happened before other
AFTER = "AFTER"            # self happened after other
EQUAL = "EQUAL"
CONCURRENT = "CONCURRENT"  # neither dominates -> siblings, needs reconciliation


class VectorClock:
    """A map of node -> (counter, last_updated_ms).

    Dynamo stores the timestamp alongside the counter purely so the clock can be
    truncated when it grows past a threshold (the paper uses 10 entries): the
    oldest (node, counter) pair is dropped.  Truncation can create false
    concurrency, which is why the paper calls it a practical compromise rather
    than a correct one.
    """

    MAX_ENTRIES = 10

    def __init__(self, entries: Optional[Dict[str, Tuple[int, float]]] = None):
        self.entries: Dict[str, Tuple[int, float]] = dict(entries or {})

    # -- construction -------------------------------------------------------

    def copy(self) -> "VectorClock":
        return VectorClock(dict(self.entries))

    def increment(self, node: str, now: Optional[float] = None) -> "VectorClock":
        """Bump this node's counter. Called by the coordinator of a write."""
        now = time.time() * 1000 if now is None else now
        counter, _ = self.entries.get(node, (0, now))
        clock = self.copy()
        clock.entries[node] = (counter + 1, now)
        clock._truncate()
        return clock

    def _truncate(self) -> None:
        if len(self.entries) <= self.MAX_ENTRIES:
            return
        # Drop the least-recently-updated entries.
        ordered = sorted(self.entries.items(), key=lambda kv: kv[1][1], reverse=True)
        self.entries = dict(ordered[: self.MAX_ENTRIES])

    # -- comparison ---------------------------------------------------------

    def counter(self, node: str) -> int:
        return self.entries.get(node, (0, 0.0))[0]

    def descends_from(self, other: "VectorClock") -> bool:
        """True if every counter in `other` is <= the matching counter here."""
        return all(self.counter(node) >= c for node, (c, _) in other.entries.items())

    def compare(self, other: "VectorClock") -> str:
        self_desc = self.descends_from(other)
        other_desc = other.descends_from(self)
        if self_desc and other_desc:
            return EQUAL
        if self_desc:
            return AFTER
        if other_desc:
            return BEFORE
        return CONCURRENT

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Pointwise max — the clock of a value reconciled from both."""
        merged: Dict[str, Tuple[int, float]] = dict(self.entries)
        for node, (counter, ts) in other.entries.items():
            if node not in merged or merged[node][0] < counter:
                merged[node] = (counter, ts)
            else:
                merged[node] = (merged[node][0], max(merged[node][1], ts))
        clock = VectorClock(merged)
        clock._truncate()
        return clock

    # -- serialization ------------------------------------------------------

    def to_context(self) -> Dict[str, int]:
        """The opaque 'context' Dynamo hands back to the client on get()."""
        return {node: counter for node, (counter, _) in self.entries.items()}

    @classmethod
    def from_context(cls, context: Dict[str, int], now: Optional[float] = None) -> "VectorClock":
        now = time.time() * 1000 if now is None else now
        return cls({node: (counter, now) for node, counter in context.items()})

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
    """A (value, clock) pair. Dynamo calls the value an 'object version'."""

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


def coalesce(versions: Iterable[VersionedValue]) -> List[VersionedValue]:
    """Drop versions that another version strictly descends from.

    This is *syntactic* reconciliation: it needs no knowledge of what the value
    means, and it is what a Dynamo node does before returning a read.  Whatever
    survives with more than one entry is a genuine set of siblings that only the
    application can merge.
    """
    survivors: List[VersionedValue] = []
    for candidate in versions:
        dominated = False
        for i, keeper in enumerate(list(survivors)):
            relation = candidate.clock.compare(keeper.clock)
            if relation in (BEFORE, EQUAL):
                dominated = True
                break
            if relation == AFTER:
                survivors[i] = None  # type: ignore[call-overload]
        survivors = [s for s in survivors if s is not None]
        if not dominated:
            survivors.append(candidate)
    return survivors


def reconcile(versions: List[VersionedValue],
              merge_fn: Callable[[List[Any]], Any],
              node: str) -> VersionedValue:
    """*Semantic* reconciliation: collapse siblings using application logic.

    The merged value's clock is the pointwise max of all sibling clocks, then
    incremented by the reconciling node, so it strictly descends from every
    sibling and future reads see a single version.
    """
    if not versions:
        raise ValueError("nothing to reconcile")
    siblings = coalesce(versions)
    if len(siblings) == 1:
        return siblings[0]
    merged_clock = siblings[0].clock
    for sibling in siblings[1:]:
        merged_clock = merged_clock.merge(sibling.clock)
    return VersionedValue(merge_fn([s.value for s in siblings]),
                          merged_clock.increment(node))


# ---------------------------------------------------------------------------
# The paper's worked example: a shopping cart that must never lose an "add"
# ---------------------------------------------------------------------------

def merge_carts(carts: List[Dict[str, int]]) -> Dict[str, int]:
    """Union of cart items, keeping the highest quantity seen for each SKU.

    This is deliberately add-biased: Dynamo's guarantee is that adds are never
    lost, and the paper is explicit that a removed item can resurface as a
    result.  A production cart would model removals as tombstones (an OR-Set)
    instead of a plain quantity map.
    """
    merged: Dict[str, int] = {}
    for cart in carts:
        for sku, qty in cart.items():
            merged[sku] = max(merged.get(sku, 0), qty)
    return merged


def _demo() -> None:
    print("=== Figure 3 from the paper: version evolution ===")
    # Sx writes a new object.
    d1 = VersionedValue({"book": 1}, VectorClock().increment("Sx"))
    print(f"D1 (Sx writes)         {d1.clock}  {d1.value}")

    # Sx updates it again.
    d2 = VersionedValue({"book": 1, "pen": 1}, d1.clock.increment("Sx"))
    print(f"D2 (Sx updates)        {d2.clock}  {d2.value}")

    # Two different coordinators handle concurrent updates to D2.
    d3 = VersionedValue({"book": 1, "pen": 1, "mug": 1}, d2.clock.increment("Sy"))
    d4 = VersionedValue({"book": 1, "pen": 1, "lamp": 1}, d2.clock.increment("Sz"))
    print(f"D3 (Sy updates D2)     {d3.clock}  {d3.value}")
    print(f"D4 (Sz updates D2)     {d4.clock}  {d4.value}")
    print(f"D3 vs D4 -> {d3.clock.compare(d4.clock)}")
    print(f"D2 vs D3 -> {d2.clock.compare(d3.clock)}  (D3 descends from D2)")

    print("\n=== Syntactic reconciliation (free, no app logic) ===")
    survivors = coalesce([d1, d2, d3, d4])
    print(f"coalesce(D1..D4) keeps {len(survivors)} versions: "
          f"{[v.clock for v in survivors]}")
    print("D1 and D2 vanish — D3 and D4 both descend from them.")

    print("\n=== Semantic reconciliation (the client merges the cart) ===")
    d5 = reconcile([d3, d4], merge_carts, node="Sx")
    print(f"D5 (Sx reconciles)     {d5.clock}  {d5.value}")
    print(f"D5 descends from D3: {d5.clock.descends_from(d3.clock)}")
    print(f"D5 descends from D4: {d5.clock.descends_from(d4.clock)}")
    print(f"coalesce(D3, D4, D5) keeps {len(coalesce([d3, d4, d5]))} version")

    print("\n=== Truncation ===")
    clock = VectorClock()
    for i in range(14):
        clock = clock.increment(f"node{i}", now=1000.0 + i)
    print(f"after 14 distinct coordinators: {len(clock.entries)} entries "
          f"(capped at {VectorClock.MAX_ENTRIES})")
    print(f"kept: {clock}")
    print("Dropping the oldest entries can make unrelated clocks look concurrent —")
    print("the paper accepts this; in practice Dynamo rarely saw >1 entry.")


if __name__ == "__main__":
    _demo()

"""
Grow-only and two-phase (PN) counters -- state-based CRDTs.

Sources
-------
  - van Steen & Tanenbaum, *Distributed Systems* (3rd ed.), ch. 7: a counter that
    every replica may increment locally and that still reaches one agreed total
    once all updates have propagated.
  - Shapiro, Preguica, Baquero, Zawirski, "Conflict-free Replicated Data Types",
    SSS 2011; and the long version INRIA RR-7687. A state-based CRDT is a join
    semilattice with a monotone update; merging is the least upper bound, so any
    order and any repetition of merges yields the same state.

Restated in my own words: each replica keeps its *own* contribution in a slot
named by its node id. `increment` only ever grows its own slot. `merge` takes,
per slot, the maximum of the two sides. Because `max` over a set of integers is
commutative, associative and idempotent, and because a replica's slot never
decreases, every replica that has seen the same set of increments reports the
same total regardless of the order the updates arrived.

A PN counter is two of these side by side: one grow-only counter for the positive
increments and one for the decrements. The value is their difference, so it can
fall below zero.

DESIGN DECISION -- per-node slots merged by max, or one integer merged by max?
A single integer cannot be merged with max: two replicas that each added 1 both
hold 1, and max(1, 1) = 1 loses a real increment. Summing them instead is not
idempotent: re-delivering the same message doubles the count. A slot per node is
the smallest state in which the merge is a true join. Cost: state is O(nodes),
and a departed node's slot is kept forever (a tombstone problem this module does
not solve).

DESIGN DECISION -- PN as two grow-only counters, or one signed value?
A signed value has no monotone join: -1 and +1 cannot be combined to satisfy
idempotence and order-independence. Keeping P and N as separate semilattices
keeps every operation inside the lattice, at the cost of two slots per node and
a value() subtraction. This is exactly the "two-phase" counter of the
literature.

DESIGN DECISION -- merge returns a new object, or mutates in place?
Returning a fresh object makes "merge is commutative/associative/idempotent"
something the checker can assert directly (`a.merge(b) == b.merge(a)`), instead of
having to clone both sides first. Cost: every merge allocates. In production one
would reap in place; here clarity of the laws wins.

Run `python3 gc_counter.py` for the demo measurement (convergence after merges).
"""

import random


class GCounter:
    """A grow-only counter: a slot per node, merged by pointwise maximum."""

    def __init__(self, node: str) -> None:
        """Start empty; `node` is the slot this replica is allowed to grow."""
        # TODO: Store the node id and an empty dict mapping node id -> that node's high-water mark.
        raise NotImplementedError("GCounter.__init__")

    def increment(self, by: int = 1) -> None:
        """Grow this replica's own slot by `by` (never below its current value)."""
        # TODO: Reject a negative amount; grow THIS replica's own slot (counts[self.node]) by `by`.
        raise NotImplementedError("GCounter.increment")

    def value(self) -> int:
        """The observed total: the sum of every node's high-water mark."""
        # TODO: Sum every node's slot: that total is the only thing the counter promises.
        raise NotImplementedError("GCounter.value")

    def merge(self, other: "GCounter") -> "GCounter":
        """Join: for every node keep the larger of the two slots seen so far."""
        # TODO: Join: return a NEW GCounter whose slots are the pointwise MAX of the two sides.
        raise NotImplementedError("GCounter.merge")

    def state(self) -> tuple:
        """A canonical, comparable view of the logical state (for the laws)."""
        # TODO: Return a canonical comparable view, e.g. tuple(sorted(self.counts.items())).
        raise NotImplementedError("GCounter.state")


class PNCounter:
    """A counter that goes both ways: a GCounter for + and one for -."""

    def __init__(self, node: str) -> None:
        """Two grow-only counters, both owned by this node."""
        # TODO: Hold two independent GCounter instances: one for increments, one for decrements.
        raise NotImplementedError("PNCounter.__init__")

    def increment(self, by: int = 1) -> None:
        """Record `by` positive steps in the positive counter."""
        # TODO: Add `by` to the positive counter.
        raise NotImplementedError("PNCounter.increment")

    def decrement(self, by: int = 1) -> None:
        """Record `by` negative steps in the negative counter."""
        # TODO: Add `by` to the NEGATIVE counter (do not subtract locally: keep the lattice monotone).
        raise NotImplementedError("PNCounter.decrement")

    def value(self) -> int:
        """The difference; negative means the counter went down overall."""
        # TODO: positive.value() minus negative.value(); this may be negative.
        raise NotImplementedError("PNCounter.value")

    def merge(self, other: "PNCounter") -> "PNCounter":
        """Join each side independently; the difference is then well defined."""
        # TODO: Merge each of the two counters independently and return a new PNCounter.
        raise NotImplementedError("PNCounter.merge")

    def state(self) -> tuple:
        """Canonical view: the two grow-only states in a fixed order."""
        # TODO: Return (positive.state(), negative.state()).
        raise NotImplementedError("PNCounter.state")


def _demo() -> None:
    """Measure convergence: 5 replicas, random ops, merges until fixed point."""
    rng = random.Random(7)
    nodes = [f"node-{i}" for i in range(5)]

    # G-Counter: 5 replicas each increment a few times.
    counters = [GCounter(n) for n in nodes]
    ops = 0
    for _ in range(40):
        rng.choice(counters).increment(rng.randint(1, 9))
        ops += 1
    merged = counters[0]
    for c in counters[1:]:
        merged = merged.merge(c)
    print(f"G-Counter: {ops} increments over {len(nodes)} replicas -> total {merged.value()}")

    # PN-Counter: same, but with decrements mixed in.
    pn = [PNCounter(n) for n in nodes]
    for _ in range(60):
        c = rng.choice(pn)
        (c.increment if rng.random() < 0.5 else c.decrement)(rng.randint(1, 9))
    pmerged = pn[0]
    for c in pn[1:]:
        pmerged = pmerged.merge(c)
    print(f"PN-Counter: 60 ops mixed +/- -> value {pmerged.value()} (can be negative)")

    # Re-merging the same state cannot change the answer (idempotence).
    print(f"G-Counter idempotent: {merged.merge(merged).value() == merged.value()}")


if __name__ == "__main__":
    _demo()

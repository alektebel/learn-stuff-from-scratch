"""
A last-writer-wins (LWW) register -- a state-based CRDT with a total order.

Sources
-------
  - van Steen & Tanenbaum, *Distributed Systems* (3rd ed.), ch. 7: replicas that
    assign each update a globally comparable stamp and let the highest stamp win.
  - Shapiro et al., "Conflict-free Replicated Data Types", SSS 2011 / INRIA
    RR-7687: the LWW register is their running example of a CRDT whose merge is
    a join once every write carries a totally ordered timestamp.

Restated in my own words: a write stores the value together with the pair
(timestamp, writer). The timestamp comes from a logical clock (see the sibling
module on Lamport clocks); the writer is the node id that issued the write. To
merge two registers we keep the one with the larger pair, comparing the writer id
when the timestamps tie. Because lexicographic comparison of (timestamp, writer)
is a total order, "keep the maximum" is commutative, associative and idempotent,
and every replica that has seen the same writes reads the same value.

DESIGN DECISION -- tie-break by node id, or by arrival order?
Arrival order is not a property of the value: two replicas receive the same two
writes in opposite orders and would disagree forever. A fixed tie-break by node
id makes the winner a function of the writes alone, so the register converges.
Cost: the choice is arbitrary -- the "loser" of a genuine simultaneous write is
silently discarded, and there is no way to recover it. If losing a concurrent
write matters, use a multi-value register or an OR-set instead; that is the
trade this design makes on purpose.

DESIGN DECISION -- store the pair (timestamp, writer) as the stamp, or only the
timestamp? Only the timestamp leaves ties unresolved and merge non-commutative
(the classic bug: `>` becomes order-dependent). Storing the writer too turns the
stamp into a key in a total order, so the maximum is unique. Cost: one extra
string per register and node ids must be unique.

Run `python3 lww_register.py` for the demo measurement (convergence after merges).
"""

import random


class LWWRegister:
    """A register holding one value; the write with the greatest stamp wins."""

    def __init__(self, node: str) -> None:
        """`node` is the id this replica stamps its own writes with."""
        # TODO: Store node, value None, a timestamp of -1 (never written) and an empty writer id.
        raise NotImplementedError("LWWRegister.__init__")

    def set(self, value, ts: int) -> None:
        """Write `value` as of logical time `ts`, stamped with this node's id."""
        # TODO: Write value, timestamp and THIS node's id as the writer.
        raise NotImplementedError("LWWRegister.set")

    def read(self):
        """The current winning value, or None if no write has been seen."""
        # TODO: Return the stored value (None until the first write).
        raise NotImplementedError("LWWRegister.read")

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        """Keep the write with the greater (timestamp, writer); ties lose to self."""
        # TODO: Return a NEW register holding the write with the greater (timestamp, writer), comparing writer when timestamps tie.
        raise NotImplementedError("LWWRegister.merge")

    def state(self) -> tuple:
        """Canonical view: the stamp and the value, in comparison order."""
        # TODO: Return (timestamp, writer, value).
        raise NotImplementedError("LWWRegister.state")


def _demo() -> None:
    """Measure who wins after concurrent and tied writes are merged."""
    rng = random.Random(11)
    nodes = ["alpha", "beta", "gamma", "delta"]
    replicas = [LWWRegister(n) for n in nodes]

    # Each replica writes a few times, some at the SAME logical timestamp.
    for step in range(6):
        for r in replicas:
            if rng.random() < 0.7:
                r.set(f"{r.node}:{step}", step)
    # A deliberate collision: every node writes at timestamp 99.
    for r in replicas:
        r.set(f"tie:{r.node}", 99)

    merged = replicas[0]
    for r in replicas[1:]:
        merged = merged.merge(r)
    print(f"{len(nodes)} replicas, 7 writes each -> winner {merged.read()!r} "
          f"(stamp {merged.state()[:2]})")
    print(f"tie-break is order-independent: "
          f"{merged.read() == replicas[0].merge(replicas[-1]).merge(merged).read()}")


if __name__ == "__main__":
    _demo()

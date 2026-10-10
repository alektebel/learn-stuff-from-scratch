"""
network.py -- a deterministic, in-process network for the replication simulation.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 5
("Replication"). Every mechanism in that chapter -- leader-based replication,
quorum reads and writes, replication lag -- is defined against a network that can
lose, delay, reorder and partition messages. DDIA says this in as many words: a
node may never assume that a message it sent arrived, that replies come back in
order, or that two nodes can talk at all.

Restated in my own words: the replication layer must stay correct for *every*
interleaving of sends and deliveries, not for the one that happens to occur. That
is only learnable if the interleaving can be reproduced, so this module is
seeded: the same seed always produces the same arrival order.

DDIA names the failure this module is built around -- a **network partition**
splits the replicas into groups that cannot see each other. A system that keeps
accepting writes in both halves has forked; this module gives the learner the
medium in which to observe that.

DESIGN DECISION -- threads and sockets, or a queue and a logical clock?
    A real network would use threads, sockets and `select`. Rejected: a failure
    would then be a timing accident nobody can reproduce, which teaches nothing.
    Chosen: a min-heap of `(deliver_at, sequence, src, dst, payload)` plus a
    logical `now` that `step()` and `flush()` advance.
    Cost: there is no real blocking or back-pressure. A "slow" node is one we
    paused or gave a longer delay, not one that is filling a socket buffer.

DESIGN DECISION -- who owns the randomness?
    The global `random`, or an instance bought by this object. Chosen: one
    `random.Random(seed)` owned by the network. The global module is seeded by
    the interpreter and shared with everything else, so results would depend on
    import order and on `PYTHONHASHSEED`.
    Cost: two networks with the same seed draw the same delays, so a test that
    wants different timing must pass a different seed.

DESIGN DECISION -- is a partition modelled by dropping or by queueing?
    Chosen: a message that crosses a partition boundary is **dropped** (counted
    in `dropped`), and healing does not resurrect it. Real partitions lose
    whatever was in flight. Cost: `catch_up`/read-repair has to be explicit,
    because there is no hidden retransmission.
"""

import heapq
import random
from typing import Any, List, Optional

__all__ = ["Network"]


class Network:
    """A message queue with a logical clock, replication delays and partitions."""

    def __init__(self, seed: int = 0, min_delay: int = 1, max_delay: int = 3,
                 drop: float = 0.0) -> None:
        self.rng = random.Random(seed)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.drop = drop
        self.now = 0
        self.sent = 0
        self.dropped = 0
        self._seq = 0
        self._queue: List[tuple] = []          # (deliver_at, seq, src, dst, payload)
        self._nodes: dict = {}                 # id -> object with receive(src, msg)
        self._groups: Optional[List[set]] = None   # None = fully connected

    # -- membership ---------------------------------------------------------

    def register(self, node_id: str, node: Any) -> None:
        self._nodes[node_id] = node

    def set_partition(self, groups) -> None:
        """Only nodes inside the same group can exchange messages."""
        self._groups = [set(group) for group in groups]

    def heal(self) -> None:
        """Remove every partition: the network is fully connected again."""
        self._groups = None

    def _connected(self, a: str, b: str) -> bool:
        # TODO: Two nodes can talk when there is no partition, or when some group in `self._groups` contains BOTH ids. Return a bool.
        raise NotImplementedError("Network._connected")

    # -- sending and delivering --------------------------------------------

    def send(self, src: str, dst: str, payload: Any, delay: Optional[int] = None) -> None:
        """Queue a message. `delay=None` draws one from the seeded RNG.

        A message crossing a partition boundary, or lost to `drop`, is discarded
        here; it is never delivered and never retried.
        """
        # TODO: Drop the message (bump `self.dropped`) if `_connected(src, dst)` is False, and again with probability `self.drop`. Otherwise draw `delay = self.rng.randint(min_delay, max_delay)` when none is given, then push `(self.now + delay, self._seq, src, dst, payload)` onto the heap with `heapq.heappush`, bumping `self.sent` and `self._seq`.
        raise NotImplementedError("Network.send")

    def pending(self) -> int:
        """How many messages are still on the wire."""
        return len(self._queue)

    # -- the clock ----------------------------------------------------------

    def deliver_due(self) -> None:
        """Deliver every message whose delivery time has come, in queue order."""
        # TODO: Pop from the heap while the earliest `deliver_at <= self.now`, collecting deliveries; then call `receive(src, payload)` on each destination that is registered. The heap's second field (sequence) keeps equal-time messages in send order.
        raise NotImplementedError("Network.deliver_due")

    def step(self) -> None:
        """Advance one tick and deliver everything now due."""
        # TODO: Advance the logical clock one tick (`self.now += 1`) and then deliver everything now due.
        raise NotImplementedError("Network.step")

    def flush(self) -> None:
        """Advance time to each delivery in turn until nothing is in flight.

        This is the deterministic equivalent of "wait for the network to settle";
        it is what a synchronous RPC would hide from the caller.
        """
        # TODO: While the queue is non-empty, jump `self.now` to the earliest `deliver_at` and deliver due messages. This is the deterministic 'wait for the network to settle'.
        raise NotImplementedError("Network.flush")


def _demo() -> None:
    """Show delivery by time, overtaking, and a partition dropping traffic."""

    class Sink:
        def __init__(self) -> None:
            self.inbox: List[tuple] = []

        def receive(self, src, payload) -> None:
            self.inbox.append((src, payload))

    net = Network(seed=20261010, min_delay=1, max_delay=3)
    a, b = Sink(), Sink()
    net.register("a", a)
    net.register("b", b)
    net.send("a", "b", "slow", delay=7)
    net.send("a", "b", "fast", delay=1)
    net.flush()
    print("arrival order with explicit delays:", [m for _, m in b.inbox])

    net.set_partition([["a"], ["b"]])
    before = net.dropped
    net.send("a", "b", "crosses-the-partition")
    net.flush()
    print(f"partition dropped {net.dropped - before} message(s); "
          f"b holds {[m for _, m in b.inbox]}")
    net.heal()
    net.send("a", "b", "after-heal")
    net.flush()
    print("after heal, b holds:", [m for _, m in b.inbox])


if __name__ == "__main__":
    _demo()

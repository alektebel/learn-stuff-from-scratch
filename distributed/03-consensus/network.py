"""
network.py -- a deterministic, in-process network for the Raft simulation.

Sources
-------
* Raft paper, "In Search of an Understandable Consensus Algorithm" (Ongaro &
  Ousterhout), section 5: Raft assumes an **asynchronous** network in which
  messages may be lost, delayed, duplicated or reordered. Correctness must never
  depend on any ordering or on a bound on delivery time; those are only liveness
  assumptions.
* van Steen & Tanenbaum, *Distributed Systems*, ch. 8: what the communication
  layer actually promises. A process puts a message "on the wire"; when (or
  whether) it arrives is the network's business.

Restated in my own words: a Raft node can never assume that a reply arrives
before the next request, or that a message sent earlier arrives earlier. Every
message is independent and may come in any order, so the protocol has to be
correct for every interleaving.

This module makes that concrete with a seeded, single-threaded queue. Every send
is stamped with a delivery time. Messages are delivered in `(deliver_time,
sequence)` order, so the whole simulation is reproducible from a seed. A
partition drops every message that crosses group boundaries; a crashed node
drops everything addressed to it (in-flight messages are simply lost).

DESIGN DECISION -- how are messages "delivered"?
  An explicit priority queue of `(deliver_at, seq, src, dst, payload)` plus a
  `step()` that advances a logical clock one tick and hands every due message to
  its destination's `receive()`.

  Alternative: real threads and sockets. Rejected -- a failing safety property
  would not be reproducible, so a learner could never find the bug by rerunning.

  Cost: there is no blocking, no back-pressure and no partial message. A "lost"
  message is one we never enqueue; a "delayed" one is one with a larger delivery
  time. That is enough to reproduce every interleaving Raft must survive.

DESIGN DECISION -- who owns the randomness?
  The network owns one `random.Random(seed)` for delays and drops; each Raft node
  owns a separate one for its election timeout. No use of the global `random`,
  so results do not depend on `PYTHONHASHSEED` or on import order.

  Cost: two nodes with the same seed would time out identically; the cluster
  constructor offsets each node's seed.
"""

import heapq
import random


class Network:
    """A message queue with a logical clock, delays, partitions and crashes."""

    def __init__(self, seed=0, min_delay=1, max_delay=3, drop=0.0, reorder=False):
        # TODO: Store the seed, delays, drop rate and reorder flag; make your own random.Random(seed); start now=0, an empty heap queue, an empty node registry, and no partition (None).
        raise NotImplementedError("Network.__init__")

    # -- membership --------------------------------------------------------

    def register(self, node_id, node):
        # TODO: Remember id -> node, so deliver_due can call node.receive().
        raise NotImplementedError("Network.register")

    def crash(self, node_id):
        """The node stops running: it sends and receives nothing more."""
        # TODO: Add the node id to the set of stopped nodes; it stops sending and receiving.
        raise NotImplementedError("Network.crash")

    def restart(self, node_id):
        # TODO: Remove the node id from the stopped set.
        raise NotImplementedError("Network.restart")

    def set_partition(self, groups):
        """groups is a list of collections; only nodes in the same group talk."""
        # TODO: Store the groups as a list of sets; two nodes may talk only if some group contains both.
        raise NotImplementedError("Network.set_partition")

    def heal(self):
        # TODO: Forget the groups: everyone is connected again.
        raise NotImplementedError("Network.heal")

    def _connected(self, a, b):
        # TODO: False if either endpoint is stopped. If there is no partition, True. Otherwise True only when one group contains both a and b.
        raise NotImplementedError("Network._connected")

    # -- sending and delivering -------------------------------------------

    def send(self, src, dst, msg, delay=None):
        """Queue a message. `delay=None` draws a delay from the seeded RNG.

        An explicit `delay` is for tests that want to pin the arrival order.
        """
        # TODO: Drop the message if the endpoints are not connected, or if the drop roll fires. Pick a delay: the explicit one, else a seeded randint between min_delay and max_delay (add a spike when reorder is on). Push (now+delay, seq, src, dst, msg) so the heap orders by arrival time.
        raise NotImplementedError("Network.send")

    def pending(self):
        # TODO: How many messages are still queued.
        raise NotImplementedError("Network.pending")

    # -- the clock ---------------------------------------------------------

    def deliver_due(self):
        """Deliver every message whose delivery time has come, in queue order."""
        # TODO: Pop every message whose delivery time is <= now, in heap order, and hand it to its destination's receive(src, msg).
        raise NotImplementedError("Network.deliver_due")

    def step(self):
        """Advance one tick and deliver everything now due."""
        # TODO: Advance now by one and deliver everything due.
        raise NotImplementedError("Network.step")


def _demo():
    """Send messages with explicit delays and show that arrival is by delay."""
    delivered = []

    class Sink:
        def __init__(self, name, net):
            self.name = name
            self.net = net

        def receive(self, src, msg):
            delivered.append((self.net.now, self.name, msg))

    net = Network(seed=1, min_delay=1, max_delay=3)
    for name in ("a", "b"):
        net.register(name, Sink(name, net))
    net.send("a", "b", "slow", delay=7)
    net.send("a", "b", "fast", delay=1)
    while net.pending():
        net.step()
    order = [msg for _, _, msg in delivered]
    print("delivery order (explicit delays):", order)
    assert order == ["fast", "slow"], order

    # A partition drops cross-group traffic; a heal restores it.
    net.send("a", "b", "before-partition")
    net.set_partition([["a"], ["b"]])
    net.send("a", "b", "crosses-partition")
    while net.pending():
        net.step()
    print("after partition:", [msg for _, _, msg in delivered])
    assert delivered[-1][2] == "before-partition"

    # With reordering on, a later send can overtake an earlier one.
    net2 = Network(seed=7, min_delay=1, max_delay=6, reorder=True)
    arrival = []
    for name in ("a", "b"):
        net2.register(name, Sink(name, net2))
    for i in range(8):
        net2.send("a", "b", f"m{i}")
    while net2.pending():
        net2.step()
    arrival = [m for (_, name, m) in delivered if name == "b"][-8:]
    print("reordered arrivals:", arrival)
    assert arrival != [f"m{i}" for i in range(8)], "reordering never happened"


if __name__ == "__main__":
    _demo()

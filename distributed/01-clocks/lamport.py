"""
Lamport clocks and the causal order of events
=============================================

Source: Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017),
chapter 8, "The Trouble with Distributed Systems" (unreliable clocks; logical clocks;
the ordering of events). Also: Maarten van Steen and Andrew S. Tanenbaum,
*Distributed Systems* (3rd ed.), chapter 6, "Coordination" (logical clocks and
Lamport timestamps).

In a distributed system there is no shared clock you can trust, so "which of these
two events happened first?" cannot be answered with time-of-day. A Lamport clock
replaces wall time with a counter that every process advances on each event and
merges on each message. It buys exactly one guarantee:

    if a happened before b  (a -> b),  then  C(a) < C(b)

where a -> b means: a and b are in the same process and a came first, or a is the
send of a message that b receives. This is the *causal* order: it captures what could
possibly have influenced what, not how many seconds apart two events were.

    A:  a1 ---------- a2(send m) ----------------- a3
    B:                      b1(receive m) --------- b2  ---
    C:                              c1(receive n) --------

    C(a1) < C(a2) < C(b1) < C(b2) < C(c1)

DESIGN DECISION - a scalar counter, not a timestamp
A Lamport clock is deliberately NOT a wall clock: it measures causality, not elapsed
time. The cost is that it cannot distinguish concurrency from causality. If
C(a) < C(b) you know b did not causally precede a, but you do NOT know that a caused
b: they may be independent events running on two processes that never talked. Worst of
all, two concurrent events always get *some* order from the counter, so a naive user
reads a total order into genuinely unordered events. Recovering the missing information
is precisely what a vector clock (vector.py) is for; the wall-clock limit case lives in
wall.py.

DESIGN DECISION - sending is an event
A send is something that happens, so it ticks the sender's clock and the message carries
the resulting value. The receiver does max(local, sent) + 1. If sending did not tick,
two sends with no event in between would share a timestamp, and C(a) < C(b) would fail
for two causally ordered sends. The +1 on receive (rather than just the max) is what
makes the receive strictly after the send even when the receiver's clock had run ahead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class LamportClock:
    """A single scalar logical clock owned by one process."""

    def __init__(self, value: int = 0) -> None:
        self.value = value

    def tick(self) -> int:
        """A local event: advance the counter and return the new value."""
        # TODO: A local event: `self.value += 1` and return the new value.
        raise NotImplementedError("LamportClock.tick")

    def send(self) -> int:
        """A send is an event: tick and stamp the message with the new value."""
        # TODO: Sending is itself an event, so it is just a tick; the returned value is the message's timestamp.
        raise NotImplementedError("LamportClock.send")

    def receive(self, sent: int) -> int:
        """A receive moves past both our own time and the message's, by one."""
        # TODO: On receive set `self.value = max(self.value, sent) + 1` and return it. The max keeps the receiver ahead of both its own history and the message; the +1 makes the receive strictly after the send.
        raise NotImplementedError("LamportClock.receive")


@dataclass
class Event:
    """One thing that happened at one process, with its Lamport timestamp."""

    process: str
    kind: str                      # "local", "send", or "receive"
    clock: int
    peer: Optional[str] = None     # the other end of a send/receive
    msg_id: Optional[int] = None   # ties a receive back to its send

    def __repr__(self) -> str:  # pragma: no cover - demo formatting
        peer = f" {self.peer}" if self.peer else ""
        return f"<{self.process} {self.kind}{peer} ts={self.clock}>"


@dataclass
class Message:
    """A message in flight: its sender, receiver and Lamport timestamp."""

    sender: str
    receiver: str
    timestamp: int
    msg_id: int


class Simulation:
    """Replays a scripted message stream over named processes.

    A script is a list of tuples:

        ("local",  "A")          a local event at A
        ("send",   "A", "B")     A sends B a message stamped with A's clock
        ("deliver", "B")         B receives the next queued message

    Delivery is explicit so a check can force a receiver to deliver late, early, or in
    a chosen order; the network itself is not the thing under test.
    """

    def __init__(self) -> None:
        self.clocks: Dict[str, LamportClock] = {}
        self.inbox: Dict[str, List[Message]] = {}
        self.events: List[Event] = []
        self.sent: Dict[int, Event] = {}
        self.received: Dict[int, Event] = {}
        self._next_msg = 1

    def register(self, name: str) -> LamportClock:
        self.clocks.setdefault(name, LamportClock())
        self.inbox.setdefault(name, [])
        return self.clocks[name]

    def local(self, name: str) -> Event:
        # TODO: Tick the process's clock and append an Event(name, 'local', timestamp).
        raise NotImplementedError("Simulation.local")

    def send(self, src: str, dst: str) -> Event:
        # TODO: Tick the sender, build a Message carrying that timestamp, queue it in the receiver's inbox and record a send Event with a fresh msg_id.
        raise NotImplementedError("Simulation.send")

    def deliver(self, dst: str) -> Event:
        # TODO: Pop the receiver's oldest queued message, call `receive(ts)` on its clock and record a receive Event tied to the same msg_id (so a check can pair it with the send).
        raise NotImplementedError("Simulation.deliver")

    def run(self, script) -> "Simulation":
        for step in script:
            op = step[0]
            if op == "local":
                self.local(step[1])
            elif op == "send":
                self.send(step[1], step[2])
            elif op == "deliver":
                self.deliver(step[1])
            else:  # pragma: no cover - guards a typo in a check script
                raise ValueError(f"unknown operation {op!r}")
        return self

    def message_pairs(self) -> List[Tuple[Event, Event]]:
        """(send, receive) pairs for every message that was actually delivered."""
        return [(self.sent[i], self.received[i])
                for i in sorted(self.sent) if i in self.received]

    def history(self, name: str) -> List[Event]:
        return [e for e in self.events if e.process == name]


if __name__ == "__main__":
    sim = Simulation()
    sim.run([
        ("local", "A"),
        ("send", "A", "B"),
        ("local", "B"),
        ("deliver", "B"),
        ("send", "B", "C"),
        ("deliver", "C"),
    ])
    pairs = sim.message_pairs()
    preserved = sum(1 for s, r in pairs if s.clock < r.clock)
    print("event stream (process, kind, Lamport timestamp):")
    for e in sim.events:
        print(f"  {e.process} {e.kind:<7} ts={e.clock}")
    print(f"send precedes receive on {preserved}/{len(pairs)} messages; "
          f"max timestamp = {max(e.clock for e in sim.events)}")

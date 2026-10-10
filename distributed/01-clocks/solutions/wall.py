"""
Unsynchronised wall clocks and why they disagree with causality
==============================================================

Source: Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017),
chapter 8, "The Trouble with Distributed Systems" (unreliable clocks: drifting quartz,
NTP, and why timestamps from different machines cannot be compared). Also: Maarten van
Steen and Andrew S. Tanenbaum, *Distributed Systems* (3rd ed.), chapter 6, on clock
synchronisation and the limits of physical time.

Every machine has a physical clock that reads a slightly different "now". Left alone
they drift; even NTP leaves a skew. So if two machines stamp events with their local
wall clock, a message can arrive *later in real time* yet carry an *earlier* timestamp
on the receiving side than on the sending side. Sorting events by wall time then puts
the effect before its cause.

This file is the limit case for the logical clocks in `lamport.py` and `vector.py`: it
constructs, deterministically, a causally ordered pair whose wall timestamps are
inverted. The point is not that wall clocks are useless (we measure durations with
them); the point is that a timestamp on a message is not a global order.

DESIGN DECISION - model a clock as true time plus a fixed offset
An unsynchronised clock's error is modelled as a constant skew per process. Real skew
drifts and jumps with NTP corrections, but a constant offset is the smallest model that
already breaks wall-clock ordering, and it is reproducible: no sleeps, no randomness.
The cost is that this says nothing about drift rates or how skew is estimated; it only
shows that *any* nonzero skew can invert a causal pair.

DESIGN DECISION - track true time and wall time side by side
Each event carries both the real time it happened and the reading of that process's
clock. Keeping both lets a check assert the receive is genuinely later in true time
while its wall stamp is earlier, which isolates the skew (the bug) from any mistake in
the simulation (the logic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class WallClock:
    """A physical clock that reads true time plus a constant offset (its skew)."""

    name: str
    offset: float = 0.0

    def now(self, true_time: float) -> float:
        return true_time + self.offset


@dataclass
class WallEvent:
    process: str
    kind: str                 # "local", "send", or "receive"
    true_time: float          # when it really happened
    wall_time: float          # what that process's clock read
    peer: Optional[str] = None
    msg_id: Optional[int] = None


@dataclass
class WallMessage:
    sender: str
    receiver: str
    true_time: float
    wall_time: float
    msg_id: int


class WallSimulation:
    """Replays a scripted stream stamped with unsynchronised wall clocks."""

    def __init__(self) -> None:
        self.clocks: Dict[str, WallClock] = {}
        self.inbox: Dict[str, List[WallMessage]] = {}
        self.events: List[WallEvent] = []
        self.sent: Dict[int, WallEvent] = {}
        self.received: Dict[int, WallEvent] = {}
        self._next_msg = 1

    def register(self, name: str, offset: float = 0.0) -> WallClock:
        self.clocks[name] = WallClock(name, offset)
        self.inbox.setdefault(name, [])
        return self.clocks[name]

    def local(self, name: str, true_time: float) -> WallEvent:
        event = WallEvent(name, "local", true_time, self.clocks[name].now(true_time))
        self.events.append(event)
        return event

    def send(self, src: str, dst: str, true_time: float) -> WallEvent:
        wall = self.clocks[src].now(true_time)
        msg_id = self._next_msg
        self._next_msg += 1
        self.inbox.setdefault(dst, [])
        self.inbox[dst].append(WallMessage(src, dst, true_time, wall, msg_id))
        event = WallEvent(src, "send", true_time, wall, peer=dst, msg_id=msg_id)
        self.events.append(event)
        self.sent[msg_id] = event
        return event

    def deliver(self, dst: str, true_time: float) -> WallEvent:
        if not self.inbox.get(dst):
            raise IndexError(f"{dst} has no pending message to deliver")
        message = self.inbox[dst].pop(0)
        event = WallEvent(dst, "receive", true_time, self.clocks[dst].now(true_time),
                          peer=message.sender, msg_id=message.msg_id)
        self.events.append(event)
        self.received[message.msg_id] = event
        return event

    def run(self, script) -> "WallSimulation":
        for step in script:
            op = step[0]
            if op == "local":
                self.local(step[1], step[2])
            elif op == "send":
                self.send(step[1], step[2], step[3])
            elif op == "deliver":
                self.deliver(step[1], step[2])
            else:  # pragma: no cover - guards a typo in a check script
                raise ValueError(f"unknown operation {op!r}")
        return self

    def message_pairs(self) -> List[Tuple[WallEvent, WallEvent]]:
        return [(self.sent[i], self.received[i])
                for i in sorted(self.sent) if i in self.received]

    def history(self, name: str) -> List[WallEvent]:
        return [e for e in self.events if e.process == name]


def unsynchronised_clocks_disagree() -> Tuple[WallEvent, WallEvent]:
    """Return (send, receive) for a causally ordered pair whose wall stamps invert.

    A sends at true time 10 with a correct clock (wall 10). B receives at true time 11
    but its clock runs 5 seconds slow, so B stamps the receive 11 - 5 = 6 < 10. Sorted
    by wall time the receive comes first, which is the false order this limit case is
    about.
    """
    sim = WallSimulation()
    sim.register("A", offset=0.0)
    sim.register("B", offset=-5.0)
    sim.run([("send", "A", "B", 10.0), ("deliver", "B", 11.0)])
    return sim.message_pairs()[0]


if __name__ == "__main__":
    send, receive = unsynchronised_clocks_disagree()
    inverted = receive.wall_time < send.wall_time
    listed = sorted((send, receive), key=lambda e: e.wall_time)
    print("one message between two unsynchronised clocks:")
    print(f"  send    true={send.true_time:>5}  wall={send.wall_time:>5}")
    print(f"  receive true={receive.true_time:>5}  wall={receive.wall_time:>5}")
    print(f"  wall-time order says: {listed[0].kind} then {listed[1].kind}"
          f"  (true-time order says send then receive)")
    print(f"  causally ordered pair with inverted wall stamps: {inverted}")

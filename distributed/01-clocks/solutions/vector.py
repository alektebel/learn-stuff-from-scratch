"""
Vector clocks, happens-before and concurrency
=============================================

Source: Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017),
chapter 8 ("The Trouble with Distributed Systems"; the section that distinguishes
Lamport timestamps from version vectors when detecting concurrent writes). Also:
Maarten van Steen and Andrew S. Tanenbaum, *Distributed Systems* (3rd ed.),
chapter 6, "Coordination" (vector timestamps and the happens-before relation).

A vector clock is one counter *per process*, carried by every process. A process
increments only its own component on a local event; a message carries the sender's
whole vector; the receiver merges it component-by-component (element-wise maximum) and
then ticks its own component. The result is strictly more information than a Lamport
scalar: from two vectors you can decide all four cases, not just "less than".

    a -> b      iff  a <= b componentwise and a != b      (strictly dominated)
    a || b      iff  neither a <= b nor b <= a            (concurrent)

The two events from `lamport.py` that got an arbitrary total order now come out
concurrent, which is the truth: neither could have influenced the other.

DESIGN DECISION - a dict keyed by process id, missing keys read as zero
Keeping the vector as {process: count} makes "merge" and "compare" one pass over the
union of keys, and makes a process that has never run (an empty vector, all zeros) a
first-class value rather than a special case. `{}` is the clock of a process before its
first event and the identity for merge. The cost: every comparison allocates or iterates
over the union of keys, and unbounded process ids grow the vector without bound (which
is why real systems garbage-collect old entries).

DESIGN DECISION - classify returns four answers, not two
before/after is not enough once concurrency exists. Equality matters too: two identical
vectors mean the events are the *same* causal position, not that one precedes the other.
Returning the string "concurrent" for the incomparable case, and "equal" for identical
vectors, keeps the caller from silently collapsing three distinct situations into a
boolean. The cost is that callers must handle four cases instead of a `True`/`False`.

DESIGN DECISION - receive merges before it ticks
If a receiver ticked its own component first and merged afterwards, its component could
end up only equal to the sender's, and the receive would not strictly dominate the send.
Merging first and ticking after guarantees happens_before(send, receive) unconditionally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

BEFORE = "before"
AFTER = "after"
CONCURRENT = "concurrent"
EQUAL = "equal"

VectorLike = Union["VectorClock", Dict[str, int]]


class VectorClock:
    """One process's vector clock, as {process_id: counter}."""

    def __init__(self, initial: Optional[Dict[str, int]] = None) -> None:
        self.clock: Dict[str, int] = dict(initial or {})

    def copy(self) -> "VectorClock":
        return VectorClock(self.clock)

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    def tick(self, pid: str) -> int:
        """A local event at `pid`: advance only that component."""
        self.clock[pid] = self.clock.get(pid, 0) + 1
        return self.clock[pid]

    def send(self, pid: str) -> int:
        """A send is an event: tick the sender; the whole vector goes on the wire."""
        return self.tick(pid)

    def merge(self, other: VectorLike) -> "VectorClock":
        """Element-wise maximum; a component missing on either side counts as zero."""
        for pid, value in _as_dict(other).items():
            if value > self.clock.get(pid, 0):
                self.clock[pid] = value
        return self

    def receive(self, pid: str, other: VectorLike) -> int:
        """Merge the message's vector, then tick our own component."""
        self.merge(other)
        return self.tick(pid)

    def happens_before(self, other: VectorLike) -> bool:
        return happens_before(self, other)

    def concurrent_with(self, other: VectorLike) -> bool:
        return concurrent(self, other)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (VectorClock, dict)):
            return NotImplemented
        return self.clock == _as_dict(other)

    def __repr__(self) -> str:  # pragma: no cover - demo formatting
        return f"VectorClock({self.clock!r})"


def _as_dict(vc: VectorLike) -> Dict[str, int]:
    if isinstance(vc, VectorClock):
        return vc.clock
    return dict(vc)


def _dominates(a: Dict[str, int], b: Dict[str, int]) -> bool:
    """True if every component of a is <= the matching component of b (missing = 0)."""
    return all(value <= b.get(pid, 0) for pid, value in a.items())


def happens_before(a: VectorLike, b: VectorLike) -> bool:
    """a -> b iff a is dominated by b and they are not equal."""
    da, db = _as_dict(a), _as_dict(b)
    return _dominates(da, db) and not _dominates(db, da)


def concurrent(a: VectorLike, b: VectorLike) -> bool:
    """a || b iff neither dominates the other: they are incomparable."""
    da, db = _as_dict(a), _as_dict(b)
    return not _dominates(da, db) and not _dominates(db, da)


def classify(a: VectorLike, b: VectorLike) -> str:
    """One of BEFORE, AFTER, CONCURRENT, EQUAL for the pair (a, b)."""
    da, db = _as_dict(a), _as_dict(b)
    if da == db:
        return EQUAL
    if _dominates(da, db):
        return BEFORE
    if _dominates(db, da):
        return AFTER
    return CONCURRENT


@dataclass
class VEvent:
    """One event, with its process's whole vector clock at that moment."""

    process: str
    kind: str
    clock: Dict[str, int]
    peer: Optional[str] = None
    msg_id: Optional[int] = None


@dataclass
class VMessage:
    sender: str
    receiver: str
    timestamp: Dict[str, int]
    msg_id: int


class VSimulation:
    """Same scripted-stream shape as `lamport.Simulation`, but with vector clocks.

    This is scaffolding: it only sequences the calls to `VectorClock`. The relation you
    are asked to write lives in `happens_before` / `concurrent` / `classify`.
    """

    def __init__(self) -> None:
        self.clocks: Dict[str, VectorClock] = {}
        self.inbox: Dict[str, List[VMessage]] = {}
        self.events: List[VEvent] = []
        self.sent: Dict[int, VEvent] = {}
        self.received: Dict[int, VEvent] = {}
        self._next_msg = 1

    def register(self, name: str) -> VectorClock:
        self.clocks.setdefault(name, VectorClock())
        self.inbox.setdefault(name, [])
        return self.clocks[name]

    def local(self, name: str) -> VEvent:
        self.register(name).tick(name)
        event = VEvent(name, "local", dict(self.clocks[name].clock))
        self.events.append(event)
        return event

    def send(self, src: str, dst: str) -> VEvent:
        clock = self.register(src)
        clock.tick(src)
        msg_id = self._next_msg
        self._next_msg += 1
        self.register(dst)
        self.inbox[dst].append(VMessage(src, dst, dict(clock.clock), msg_id))
        event = VEvent(src, "send", dict(clock.clock), peer=dst, msg_id=msg_id)
        self.events.append(event)
        self.sent[msg_id] = event
        return event

    def deliver(self, dst: str) -> VEvent:
        clock = self.register(dst)
        if not self.inbox[dst]:
            raise IndexError(f"{dst} has no pending message to deliver")
        message = self.inbox[dst].pop(0)
        clock.merge(message.timestamp)
        clock.tick(dst)
        event = VEvent(dst, "receive", dict(clock.clock), peer=message.sender,
                       msg_id=message.msg_id)
        self.events.append(event)
        self.received[message.msg_id] = event
        return event

    def run(self, script) -> "VSimulation":
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

    def message_pairs(self) -> List[Tuple[VEvent, VEvent]]:
        return [(self.sent[i], self.received[i])
                for i in sorted(self.sent) if i in self.received]

    def history(self, name: str) -> List[VEvent]:
        return [e for e in self.events if e.process == name]


if __name__ == "__main__":
    sim = VSimulation()
    sim.run([
        ("local", "A"), ("local", "A"), ("send", "A", "C"),
        ("local", "B"), ("send", "B", "C"),
        ("deliver", "C"), ("deliver", "C"),
    ])
    a_events = sim.history("A")
    b_events = sim.history("B")
    c_events = sim.history("C")
    verdict = classify(a_events[-1].clock, b_events[-1].clock)
    print("classifications in the stream:")
    print(f"  last A event vs last B event : {verdict}")
    print(f"  C receive #1 vs C receive #2 : "
          f"{classify(c_events[0].clock, c_events[1].clock)}")
    print(f"  vector clocks: A={a_events[-1].clock} B={b_events[-1].clock} "
          f"C={c_events[-1].clock}")

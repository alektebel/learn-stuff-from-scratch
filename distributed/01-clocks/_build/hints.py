"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "lamport.py": {
  "LamportClock.tick": "A local event: `self.value += 1` and return the new value.",
  "LamportClock.send": "Sending is itself an event, so it is just a tick; the returned value is the message's timestamp.",
  "LamportClock.receive": "On receive set `self.value = max(self.value, sent) + 1` and return it. The max keeps the receiver ahead of both its own history and the message; the +1 makes the receive strictly after the send.",
  "Simulation.local": "Tick the process's clock and append an Event(name, 'local', timestamp).",
  "Simulation.send": "Tick the sender, build a Message carrying that timestamp, queue it in the receiver's inbox and record a send Event with a fresh msg_id.",
  "Simulation.deliver": "Pop the receiver's oldest queued message, call `receive(ts)` on its clock and record a receive Event tied to the same msg_id (so a check can pair it with the send).",
 },
 "vector.py": {
  "VectorClock.tick": "Advance only this process's own component: `self.clock[pid] = self.clock.get(pid, 0) + 1`.",
  "VectorClock.send": "A send is an event: tick your own component. The whole vector (a copy) is the message timestamp.",
  "VectorClock.merge": "Element-wise maximum into self: for each pid in the other vector keep the larger of the two, a missing component counting as 0.",
  "VectorClock.receive": "Merge the message's vector FIRST, then tick your own component. Ticking first would let the receive only equal the send instead of strictly dominating it.",
  "happens_before": "True iff every component of a is <= the matching component of b (missing = 0) and at least one is strictly smaller. Equal vectors are NOT before each other.",
  "concurrent": "True iff neither vector is <= the other: each has a component the other lacks, so neither could have caused the other.",
  "classify": "EQUAL if the two are identical, BEFORE if a <= b, AFTER if b <= a, otherwise CONCURRENT. Check the sub-cases in that order.",
 },
 "wall.py": {
  "WallClock.now": "Wall time is true time plus this clock's offset: `true_time + self.offset`.",
  "unsynchronised_clocks_disagree": "Build the deterministic skew scenario: register A with offset 0 and B with a NEGATIVE offset, send at an earlier true time than the delivery, and return the (send, receive) pair. The receive must be later in true time yet carry an earlier wall stamp.",
 },
}

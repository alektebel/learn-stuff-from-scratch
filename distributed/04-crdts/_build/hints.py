"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "gc_counter.py": {
  "GCounter.__init__": "Store the node id and an empty dict mapping node id -> that node's high-water mark.",
  "GCounter.increment": "Reject a negative amount; grow THIS replica's own slot (counts[self.node]) by `by`.",
  "GCounter.value": "Sum every node's slot: that total is the only thing the counter promises.",
  "GCounter.merge": "Join: return a NEW GCounter whose slots are the pointwise MAX of the two sides.",
  "GCounter.state": "Return a canonical comparable view, e.g. tuple(sorted(self.counts.items())).",
  "PNCounter.__init__": "Hold two independent GCounter instances: one for increments, one for decrements.",
  "PNCounter.increment": "Add `by` to the positive counter.",
  "PNCounter.decrement": "Add `by` to the NEGATIVE counter (do not subtract locally: keep the lattice monotone).",
  "PNCounter.value": "positive.value() minus negative.value(); this may be negative.",
  "PNCounter.merge": "Merge each of the two counters independently and return a new PNCounter.",
  "PNCounter.state": "Return (positive.state(), negative.state()).",
 },
 "lww_register.py": {
  "LWWRegister.__init__": "Store node, value None, a timestamp of -1 (never written) and an empty writer id.",
  "LWWRegister.set": "Write value, timestamp and THIS node's id as the writer.",
  "LWWRegister.read": "Return the stored value (None until the first write).",
  "LWWRegister.merge": "Return a NEW register holding the write with the greater (timestamp, writer), comparing writer when timestamps tie.",
  "LWWRegister.state": "Return (timestamp, writer, value).",
 },
 "or_set.py": {
  "ORSet.__init__": "Store node, a local clock at 0, a dict element -> set of tags, and a set of tombstoned tags.",
  "ORSet._tag": "Bump the local clock and return a globally unique tag: (self.node, self._clock).",
  "ORSet.add": "Give the element a fresh tag and add it to that element's tag set.",
  "ORSet.remove": "Tombstone every tag currently held for the element; do NOT delete them from the add set.",
  "ORSet.contains": "True if the element has any tag that is not tombstoned.",
  "ORSet.elements": "The set of elements for which contains() is true.",
  "ORSet.merge": "Return a NEW set: union the tags per element and union the tombstones.",
  "ORSet.state": "Return (frozenset of (element, tag) pairs, frozenset of tombstoned tags).",
 },
}

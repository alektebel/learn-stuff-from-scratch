"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
 # --- lamport.py ---
 ("receive ignores the receiver's own clock", "lamport.py",
  "        self.value = max(self.value, sent) + 1\n",
  "        self.value = sent + 1\n",
  "1"),
 ("send does not tick (sending is not an event)", "lamport.py",
  '    def send(self) -> int:\n        """A send is an event: tick and stamp the message with the new value."""\n        return self.tick()',
  '    def send(self) -> int:\n        """A send is an event: tick and stamp the message with the new value."""\n        return self.value',
  "1"),
 # --- vector.py ---
 ("merge adds vectors instead of taking the component-wise max", "vector.py",
  "        for pid, value in _as_dict(other).items():\n            if value > self.clock.get(pid, 0):\n                self.clock[pid] = value\n        return self",
  "        for pid, value in _as_dict(other).items():\n            self.clock[pid] = self.clock.get(pid, 0) + value\n        return self",
  "5"),
 ("happens-before compares component sums (orders concurrent events)", "vector.py",
  'def happens_before(a: VectorLike, b: VectorLike) -> bool:\n    """a -> b iff a is dominated by b and they are not equal."""\n    da, db = _as_dict(a), _as_dict(b)\n    return _dominates(da, db) and not _dominates(db, da)',
  'def happens_before(a: VectorLike, b: VectorLike) -> bool:\n    """a -> b iff a is dominated by b and they are not equal."""\n    da, db = _as_dict(a), _as_dict(b)\n    return sum(da.values()) < sum(db.values())',
  "4"),
 ("domination crashes on an empty clock (max of nothing)", "vector.py",
  'def _dominates(a: Dict[str, int], b: Dict[str, int]) -> bool:\n    """True if every component of a is <= the matching component of b (missing = 0)."""\n    return all(value <= b.get(pid, 0) for pid, value in a.items())',
  'def _dominates(a: Dict[str, int], b: Dict[str, int]) -> bool:\n    """True if every component of a is <= the matching component of b (missing = 0)."""\n    return max(a.values()) <= max(b.values())',
  "6"),
 # --- wall.py ---
 ("the two wall clocks are synchronised, hiding the skew", "wall.py",
  '    sim.register("B", offset=-5.0)',
  '    sim.register("B", offset=0.0)',
  "8"),
]

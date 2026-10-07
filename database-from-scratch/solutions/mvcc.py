"""
MVCC and isolation levels
=========================

Every write creates a new version instead of overwriting. A version records the commit
timestamp of the transaction that wrote it. A reader picks, for each key, the newest
version visible to it, and what "visible" means is exactly what an isolation level is.

Concurrency here is simulated: one thread interleaves the operations of several
transactions in a chosen order (a *schedule*). That makes every anomaly reproducible.

Levels (weakest to strongest) and what this engine does for each:

  READ_UNCOMMITTED  reads see the newest write of any transaction, committed or not
  READ_COMMITTED    each read sees the newest COMMITTED version at the moment of the read
  SNAPSHOT          all reads see the database as of the transaction's start; at commit,
                    first-committer-wins: abort if any key we write was committed by
                    someone else after our start
  SERIALIZABLE      SNAPSHOT plus read validation: abort if any key we READ, or any key
                    falling in a range we SCANNED, was committed by someone else after
                    our start

DESIGN DECISION - how to get SERIALIZABLE
Two-phase locking blocks; Postgres' SSI tracks read-write dependency cycles precisely.
Chosen: optimistic backward validation of the read set, which is simpler and provably
serializable, at the price of false aborts (it aborts some schedules SSI would allow).
Measure the price: count aborts at each level on the same workload.

Writes are optimistic at every level: no locks, conflicts are found at commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

TOMBSTONE = object()  # a committed delete


class Isolation(Enum):
    READ_UNCOMMITTED = 0
    READ_COMMITTED = 1
    SNAPSHOT = 2
    SERIALIZABLE = 3


class SerializationFailure(Exception):
    """The transaction must be retried: committing it would break its isolation level."""


@dataclass
class Version:
    value: object
    commit_ts: int


@dataclass
class Txn:
    store: "MVCCStore"
    isolation: Isolation
    start_ts: int
    id: int
    writes: dict = field(default_factory=dict)        # key -> value or TOMBSTONE
    reads: set = field(default_factory=set)            # keys read
    ranges: list = field(default_factory=list)         # (lo, hi) scanned
    status: str = "active"

    # -- reads ----------------------------------------------------------------------------
    def _visible(self, key) -> object:
        if key in self.writes:
            return self.writes[key]
        s = self.store
        if self.isolation is Isolation.READ_UNCOMMITTED:
            dirty = s._latest_uncommitted(key, exclude=self.id)
            if dirty is not None:
                return dirty
        as_of = s._clock if self.isolation in (Isolation.READ_UNCOMMITTED, Isolation.READ_COMMITTED) else self.start_ts
        for v in reversed(s._versions.get(key, [])):
            if v.commit_ts <= as_of:
                return v.value
        return TOMBSTONE

    def read(self, key) -> Optional[object]:
        self._check_active()
        self.reads.add(key)
        v = self._visible(key)
        return None if v is TOMBSTONE else v

    def scan(self, lo, hi) -> dict:
        """All live keys with lo <= key < hi, as this transaction sees them."""
        self._check_active()
        self.ranges.append((lo, hi))
        keys = {k for k in self.store._versions if lo <= k < hi}
        keys |= {k for k in self.writes if lo <= k < hi}
        if self.isolation is Isolation.READ_UNCOMMITTED:
            keys |= {k for t in self.store._active.values() if t is not self for k in t.writes if lo <= k < hi}
        out = {}
        for k in sorted(keys):
            v = self._visible(k)
            if v is not TOMBSTONE:
                out[k] = v
        return out

    # -- writes ---------------------------------------------------------------------------
    def write(self, key, value) -> None:
        self._check_active()
        self.writes[key] = value

    def delete(self, key) -> None:
        self.write(key, TOMBSTONE)

    # -- end ------------------------------------------------------------------------------
    def commit(self) -> int:
        self._check_active()
        s = self.store
        if self.isolation in (Isolation.SNAPSHOT, Isolation.SERIALIZABLE):
            for key in self.writes:
                if s._last_commit_ts(key) > self.start_ts:
                    self._finish("aborted")
                    raise SerializationFailure(f"write-write conflict on {key!r} (first committer wins)")
        if self.isolation is Isolation.SERIALIZABLE:
            for key in self.reads:
                if s._last_commit_ts(key) > self.start_ts:
                    self._finish("aborted")
                    raise SerializationFailure(f"{key!r} was read, then changed by a later commit")
            for lo, hi in self.ranges:
                for key in s._versions:
                    if lo <= key < hi and s._last_commit_ts(key) > self.start_ts:
                        self._finish("aborted")
                        raise SerializationFailure(f"range [{lo!r}, {hi!r}) changed under the scan ({key!r})")
        s._clock += 1
        for key, value in self.writes.items():
            s._versions.setdefault(key, []).append(Version(value, s._clock))
        self._finish("committed")
        return s._clock

    def abort(self) -> None:
        if self.status == "active":
            self._finish("aborted")

    def _finish(self, status: str) -> None:
        self.status = status
        self.store._active.pop(self.id, None)
        self.store.stats[status] += 1

    def _check_active(self) -> None:
        if self.status != "active":
            raise RuntimeError(f"transaction {self.id} is {self.status}")


class MVCCStore:
    def __init__(self):
        self._versions: dict = {}   # key -> [Version], ascending commit_ts
        self._clock = 0             # last commit timestamp handed out
        self._next_id = 1
        self._active: dict = {}     # id -> Txn, in begin order
        self.stats = {"committed": 0, "aborted": 0}

    def begin(self, isolation: Isolation = Isolation.SNAPSHOT) -> Txn:
        t = Txn(self, isolation, start_ts=self._clock, id=self._next_id)
        self._next_id += 1
        self._active[t.id] = t
        return t

    def _last_commit_ts(self, key) -> int:
        versions = self._versions.get(key)
        return versions[-1].commit_ts if versions else 0

    def _latest_uncommitted(self, key, exclude: int):
        for t in reversed(list(self._active.values())):
            if t.id != exclude and key in t.writes:
                return t.writes[key]
        return None

    def load(self, data: dict) -> None:
        """Commit initial data in one transaction."""
        t = self.begin(Isolation.READ_COMMITTED)
        for k, v in data.items():
            t.write(k, v)
        t.commit()

    def snapshot(self) -> dict:
        """Latest committed state (for tests)."""
        out = {}
        for k, versions in self._versions.items():
            if versions[-1].value is not TOMBSTONE:
                out[k] = versions[-1].value
        return out


if __name__ == "__main__":
    for level in Isolation:
        s = MVCCStore()
        s.load({"x": 10})
        a, b = s.begin(level), s.begin(level)
        xa, xb = a.read("x"), b.read("x")  # both read before either writes
        a.write("x", xa + 1)
        b.write("x", xb + 1)
        a.commit()
        try:
            b.commit()
            outcome = f"x = {s.snapshot()['x']}  (lost update)" if s.snapshot()["x"] == 11 else "ok"
        except SerializationFailure as e:
            outcome = f"second commit aborted: {e}"
        print(f"{level.name:17s} {outcome}")

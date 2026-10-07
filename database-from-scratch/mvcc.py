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

DESIGN DECISION - where the versions live
A version store is a key -> version-chain index plus the chains. Chosen: put that index
in the same B+tree the rest of the engine uses (`btree.py`), keyed by an order-preserving
encoding of the user key; the tree value is the pickled chain of (commit_ts, value).
A point read is then one tree descent; a range scan is one descent plus a walk over the
linked leaves, and `keys_touched` counts exactly the tree entries that walk reads. No
longer an in-memory dict scanned with `key in d`.

Writes are optimistic at every level: no locks, conflicts are found at commit.
"""

from __future__ import annotations

import os
import pickle
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from btree import BTree
from pager import Pager

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


# ---------------------------------------------------------------------------
# Key and version encodings
#
# Keys are arbitrary str or bytes in the API but the B+tree deals in short byte strings.
# _enc is order-preserving and prefix-free: a tag byte keeps the two key types apart,
# 0x00 is escaped as 0x00 0xff, and 0x00 0x00 terminates. Lexicographic order of the
# encoded keys is therefore the order of the original keys, which is what makes a tree
# range scan answer a range query.
# ---------------------------------------------------------------------------

def _enc(key) -> bytes:
    if isinstance(key, bytes):
        tag, raw = b"b", key
    elif isinstance(key, str):
        tag, raw = b"s", key.encode("utf-8")
    else:
        raise TypeError(f"MVCC keys must be str or bytes, got {type(key).__name__}")
    return tag + raw.replace(b"\x00", b"\x00\xff") + b"\x00\x00"


def _dec(enc: bytes):
    tag, out, i = enc[:1], bytearray(), 1
    while i < len(enc):
        if enc[i] == 0:
            if enc[i + 1] == 0:
                break
            out.append(0)
            i += 2
        else:
            out.append(enc[i])
            i += 1
    raw = bytes(out)
    return raw.decode("utf-8") if tag == b"s" else raw


def _dump_value(value) -> bytes:
    return b"\x00" if value is TOMBSTONE else b"\x01" + pickle.dumps(value, protocol=4)


def _load_value(blob: bytes):
    return TOMBSTONE if blob[:1] == b"\x00" else pickle.loads(blob[1:])


def _dump_versions(versions) -> bytes:
    return pickle.dumps([(ts, _dump_value(v)) for ts, v in versions], protocol=4)


def _load_versions(blob: bytes):
    return [(ts, _load_value(v)) for ts, v in pickle.loads(blob)]


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
        # TODO: Own writes first. READ_UNCOMMITTED also sees other active transactions' writes. Otherwise return the newest version with commit_ts <= the read timestamp: the current clock for READ_(UN)COMMITTED, start_ts for SNAPSHOT/SERIALIZABLE. No version: TOMBSTONE.
        raise NotImplementedError("Txn._visible")

    def read(self, key) -> Optional[object]:
        self._check_active()
        self.reads.add(key)
        v = self._visible(key)
        return None if v is TOMBSTONE else v

    def scan(self, lo, hi) -> dict:
        """All live keys with lo <= key < hi, as this transaction sees them."""
        # TODO: Record the range (SERIALIZABLE needs it). Candidate keys: committed keys in range, own writes in range, and for READ_UNCOMMITTED others' uncommitted writes. Keep those whose visible value is not TOMBSTONE.
        raise NotImplementedError("Txn.scan")

    # -- writes ---------------------------------------------------------------------------
    def write(self, key, value) -> None:
        self._check_active()
        self.writes[key] = value

    def delete(self, key) -> None:
        self.write(key, TOMBSTONE)

    # -- end ------------------------------------------------------------------------------
    def commit(self) -> int:
        # TODO: SNAPSHOT/SERIALIZABLE: abort if a key we WRITE was committed after start_ts. SERIALIZABLE also: abort if a key we READ, or any key in a range we SCANNED, was. Then advance the clock and append one Version per write.
        raise NotImplementedError("Txn.commit")

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
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(tempfile.mkdtemp(prefix="mvcc-"), "versions.db")
        self.tree = BTree(Pager(path, cache_pages=256))  # the version index lives in the B+tree
        self.keys_touched = 0       # tree entries read by the last lookups/scans
        self._clock = 0             # last commit timestamp handed out
        self._next_id = 1
        self._active: dict = {}     # id -> Txn, in begin order
        self.stats = {"committed": 0, "aborted": 0}

    def reset_counters(self) -> None:
        self.keys_touched = 0
        p = self.tree.pager
        p.disk_reads = p.cache_hits = p.disk_writes = 0

    def begin(self, isolation: Isolation = Isolation.SNAPSHOT) -> Txn:
        t = Txn(self, isolation, start_ts=self._clock, id=self._next_id)
        self._next_id += 1
        self._active[t.id] = t
        return t

    def _versions_of(self, key) -> list:
        """The committed version chain for one key, ascending by commit_ts."""
        blob = self.tree.get(_enc(key))
        self.keys_touched += 1
        return _load_versions(blob) if blob is not None else []

    def _put_version(self, key, ts: int, value) -> None:
        versions = self._versions_of(key)
        versions.append((ts, value))
        self.tree.put(_enc(key), _dump_versions(versions))

    def _scan_versions(self, lo, hi) -> list:
        """Walk the B+tree version index for lo <= key < hi, in key order."""
        # TODO: Encode lo and hi, descend the tree to the first leaf at lo, then walk entries and the next-leaf pointers until hi. Decode each key and its version chain and return (key, [(commit_ts, value), ...]); tombstones are versions too, so keep them. Count every tree entry read in keys_touched: a narrow range must read few keys, not the whole store.
        raise NotImplementedError("MVCCStore._scan_versions")

    def _last_commit_ts(self, key) -> int:
        versions = self._versions_of(key)
        return versions[-1][0] if versions else 0

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
        for key, versions in self._scan_versions(None, None):
            if versions and versions[-1][1] is not TOMBSTONE:
                out[key] = versions[-1][1]
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

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

DESIGN DECISION - durability of the versions
A version lives in the B+tree, but that tree is a cache of pages, not a log: a crash can
lose or tear it. Chosen: in durable mode the same WAL as `wal.py` is the truth. Writing a
key appends a "vput" record (the commit timestamp is not known yet); committing appends a
"commit" record carrying the new timestamp and syncs the log BEFORE the version is applied
to the tree. Recovery rebuilds the index by replaying only "vput" records whose transaction
also has a "commit" record, in commit order. Cost: the log grows until a checkpoint, and a
replay is idempotent (a version already present at that timestamp is replaced, not
duplicated) so replaying over a checkpoint is safe.
"""

from __future__ import annotations

import os
import pickle
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from btree import BTree
from pager import Pager
from wal import WAL, read_records

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


def _committed_versions(wal_path: str):
    """Committed versions from the WAL, in commit order: (enc_key, commit_ts, value_blob).

    A "vput" record is written when a key is written, before the transaction commits, so
    the log can hold the versions of a transaction that later aborts or never finishes.
    Only a surviving "commit" record makes them eligible for redo; a transaction with no
    commit record is ignored entirely.
    """
    pending: dict = {}
    out = []
    for rec in read_records(wal_path):
        kind, tx = rec["t"], rec["tx"]
        if kind == "vput":
            pending.setdefault(tx, []).append((bytes.fromhex(rec["k"]), bytes.fromhex(rec["v"])))
        elif kind == "commit":
            for enc_key, blob in pending.pop(tx, []):
                out.append((enc_key, rec["ts"], blob))
    return out


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
        for ts, value in reversed(s._versions_of(key)):
            if ts <= as_of:
                return value
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
        keys = {k for k, _ in self.store._scan_versions(lo, hi)}
        keys |= {k for k in self.writes if lo <= k < hi}
        if self.isolation is Isolation.READ_UNCOMMITTED:
            keys |= {k for t in self.store._active.values() if t is not self
                     for k in t.writes if lo <= k < hi}
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
        if self.store._durable:
            # Write-ahead the raw value now; its commit timestamp is added by the commit
            # record, so recovery can ignore this if the transaction never commits.
            self.store._wal.append({"t": "vput", "tx": self.id,
                                    "k": _enc(key).hex(), "v": _dump_value(value).hex()})

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
                for key, _versions in s._scan_versions(lo, hi):
                    if lo <= key < hi and s._last_commit_ts(key) > self.start_ts:
                        self._finish("aborted")
                        raise SerializationFailure(f"range [{lo!r}, {hi!r}) changed under the scan ({key!r})")
        if s._durable:
            # The commit point: the timestamp record reaches the log before any version
            # is applied to the tree, so recovery can tell committed versions apart.
            s._wal.append({"t": "commit", "tx": self.id, "ts": s._clock + 1})
            s._wal.sync()
        s._clock += 1
        for key, value in self.writes.items():
            s._put_version(key, s._clock, value)
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
    def __init__(self, path: Optional[str] = None, durable: bool = False):
        if path is None:
            path = os.path.join(tempfile.mkdtemp(prefix="mvcc-"), "versions.db")
        self._durable = durable
        self._data = path         # last checkpoint (durable mode only)
        self.keys_touched = 0     # tree entries read by the last lookups/scans
        self._clock = 0           # last commit timestamp handed out
        self._next_id = 1
        self._active: dict = {}   # id -> Txn, in begin order
        self.stats = {"committed": 0, "aborted": 0}
        if durable:
            self._work = path + ".work"
            self._wal_path = path + ".wal"
            self._recover()
        else:
            self.tree = BTree(Pager(path, cache_pages=256))  # version index lives in the B+tree
        self.keys_touched = 0

    def _recover(self) -> None:
        """Durable mode: rebuild the committed version index from the checkpoint plus the WAL.

        Sets self.tree, self._clock, self._next_id and self._wal. The work file starts from
        the last checkpoint (or empty): a crash can leave it torn, so only data.db is trusted.
        Replaying is idempotent, so a version already checkpointed is replaced, not duplicated.
        """
        stale = self._data + ".new"
        if os.path.exists(stale):
            os.remove(stale)  # a checkpoint that crashed before its rename never happened
        if os.path.exists(self._data):
            shutil.copyfile(self._data, self._work)
        elif os.path.exists(self._work):
            os.remove(self._work)
        self.tree = BTree(Pager(self._work, cache_pages=256))
        self._clock = 0
        for enc_key, ts, blob in _committed_versions(self._wal_path):
            self._set_version_enc(enc_key, ts, _load_value(blob))
            if ts > self._clock:
                self._clock = ts
        self._next_id = 1
        for rec in read_records(self._wal_path):
            if rec["tx"] >= self._next_id:
                self._next_id = rec["tx"] + 1
        self._wal = WAL(self._wal_path)
        self.keys_touched = 0

    def _set_version_enc(self, enc_key: bytes, ts: int, value) -> None:
        """Idempotent redo of one committed version, keeping the chain in commit_ts order."""
        blob = self.tree.get(enc_key)
        versions = _load_versions(blob) if blob is not None else []
        for i, (old_ts, _old) in enumerate(versions):
            if old_ts == ts:
                versions[i] = (ts, value)
                break
        else:
            versions.append((ts, value))
        versions.sort(key=lambda item: item[0])
        self.tree.put(enc_key, _dump_versions(versions))

    def crash(self) -> None:
        """Simulate a process crash: drop in-memory state without checkpointing."""
        if self._durable:
            self._wal.close()
        self.tree.pager.close()

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
        """Walk the B+tree version index for lo <= key < hi.

        Returns [(key, [(commit_ts, value), ...])] in key order, tombstones included, so
        callers can pick the version their isolation level makes visible. `keys_touched`
        counts the tree entries the walk actually reads: a narrow range reads the few
        keys in it, not the whole store.
        """
        lo_b = _enc(lo) if lo is not None else None
        hi_b = _enc(hi) if hi is not None else None
        out = []
        for enc_key, blob in self.tree.scan(lo_b, hi_b):
            out.append((_dec(enc_key), _load_versions(blob)))
            self.keys_touched += 1
        return out

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

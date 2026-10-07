"""
Write-ahead log and crash recovery
==================================

A transaction is durable when its COMMIT record is on disk, not when the data pages are.
The data file is only rewritten at checkpoints; between checkpoints the log is the truth.

Record framing:  [length u32][crc32 u32][payload: JSON]
A crash can leave a torn record at the tail (half-written length, payload, or CRC).
Reading stops at the first record that is short or whose CRC does not match: everything
before it is trusted, nothing after it is.

DESIGN DECISION - redo-only, no-steal
Uncommitted writes are buffered in the transaction and never reach the log or the data
file. So recovery never has to undo anything: it replays the operations of transactions
whose COMMIT record survived, in log order, and ignores the rest. The cost: a transaction's
writes must fit in memory. (ARIES chooses steal/no-force and pays with undo logging.)

DESIGN DECISION - checkpoint by full copy and atomic rename
Writing B-tree pages in place at checkpoint time is not crash-safe: a crash halfway
leaves a tree whose pages come from two different moments, and a split can be half
applied. Chosen: the live tree runs on a scratch copy (`work.db`); a checkpoint flushes
it, copies it to `data.db.new`, fsyncs, renames over `data.db`, then truncates the log.
A crash before the rename leaves the old `data.db` plus the full log. Cost: O(database
size) per checkpoint. (SQLite's rollback journal and Postgres' full-page writes are the
cheaper answers to the same torn-page problem.)

Redo must be idempotent: replaying a log over a data file that already contains some of
its effects (the crash happened after rename but before truncate) must give the same
result. put and delete are idempotent; "increment" would not be.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import zlib
from typing import Iterator, Optional

from btree import BTree
from pager import Pager

HEADER = struct.Struct("<II")  # length, crc32


class WAL:
    def __init__(self, path: str):
        self.path = path
        self._fh = open(path, "ab")

    def append(self, record: dict) -> None:
        # TODO: Frame the JSON payload as [length u32][crc32 u32][payload] (HEADER.pack) and write it. Do not fsync here: sync() is the commit point.
        raise NotImplementedError("WAL.append")

    def sync(self) -> None:
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def truncate(self) -> None:
        self._fh.close()
        with open(self.path, "wb") as fh:
            fh.flush()
            os.fsync(fh.fileno())
        self._fh = open(self.path, "ab")

    def close(self) -> None:
        self._fh.close()


def read_records(path: str) -> Iterator[dict]:
    """Yield records up to (not including) the first torn or corrupt one."""
    # TODO: Walk the file: read a header, check the whole payload is present, check its CRC, parse it. Stop silently at the first record that fails any of those.
    raise NotImplementedError("read_records")


def committed_operations(path: str) -> list[tuple[str, bytes, Optional[bytes]]]:
    """Operations of committed transactions, in commit order: ("put", k, v) / ("del", k, None)."""
    # TODO: Buffer each transaction's ops by tx id; when its commit record appears, append its ops to the output. Transactions without a commit record are ignored.
    raise NotImplementedError("committed_operations")


class Transaction:
    def __init__(self, db: "DurableKV", tx: int):
        self._db, self.tx = db, tx
        self._writes: dict[bytes, Optional[bytes]] = {}  # key -> value, None = delete
        self.done = False

    def get(self, key: bytes) -> Optional[bytes]:
        if key in self._writes:
            return self._writes[key]  # read your own writes
        return self._db._tree.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        self._writes[key] = value

    def delete(self, key: bytes) -> None:
        self._writes[key] = None

    def commit(self) -> None:
        # TODO: Append begin, one record per write (hex-encode bytes), commit; sync() the log; only then apply the writes to the tree.
        raise NotImplementedError("Transaction.commit")

    def abort(self) -> None:
        self.done = True  # nothing was written anywhere: no-steal makes abort free


class DurableKV:
    """A key-value store that survives crashes: data.db (last checkpoint) + wal.log."""

    def __init__(self, directory: str):
        self.dir = directory
        os.makedirs(directory, exist_ok=True)
        self._data = os.path.join(directory, "data.db")
        self._work = os.path.join(directory, "work.db")
        self._wal_path = os.path.join(directory, "wal.log")
        self._recover()
        self._wal = WAL(self._wal_path)

    def _recover(self) -> None:
        """Rebuild the live tree from the last checkpoint plus the log.

        Sets self._pager, self._tree, self.recovered_ops and self._next_tx."""
        # TODO: Discard a stale data.db.new; start the work file from data.db (or empty); open pager + tree on it; replay committed_operations; pick _next_tx above every tx id seen (and the one saved at checkpoint); drop any torn tail from the log.
        raise NotImplementedError("DurableKV._recover")

    def _rewrite_wal_without_tail(self) -> None:
        """Drop a torn tail so new records are not appended after garbage."""
        good = list(read_records(self._wal_path))
        with open(self._wal_path, "wb") as fh:
            for rec in good:
                payload = json.dumps(rec, separators=(",", ":")).encode()
                fh.write(HEADER.pack(len(payload), zlib.crc32(payload)) + payload)
            fh.flush()
            os.fsync(fh.fileno())

    def _apply(self, ops) -> None:
        for kind, k, v in ops:
            if kind == "put":
                self._tree.put(k, v)
            else:
                self._tree.delete(k)

    def begin(self) -> Transaction:
        tx = self._next_tx
        self._next_tx += 1
        return Transaction(self, tx)

    def get(self, key: bytes) -> Optional[bytes]:
        return self._tree.get(key)

    def items(self) -> list[tuple[bytes, bytes]]:
        return list(self._tree.scan())

    def checkpoint(self) -> None:
        # TODO: Save next_tx in the metadata, flush the work file, copy it to data.db.new, fsync it, os.replace it over data.db, fsync the directory, then truncate the log. Order matters: why?
        raise NotImplementedError("DurableKV.checkpoint")

    def close(self) -> None:
        self._wal.close()
        self._pager.close()


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp()
    db = DurableKV(d)
    for i in range(5):
        t = db.begin()
        t.put(f"k{i}".encode(), f"v{i}".encode())
        t.commit()
    t = db.begin()
    t.put(b"never", b"committed")  # crash before commit
    db._wal.close()  # simulate the crash: no checkpoint, no close
    size = os.path.getsize(os.path.join(d, "wal.log"))
    with open(os.path.join(d, "wal.log"), "ab") as fh:
        fh.write(b"\x40\x00\x00\x00garbage")  # a torn record at the tail
    db2 = DurableKV(d)
    print(f"recovered {db2.recovered_ops} ops from a {size}-byte log: {db2.items()}")

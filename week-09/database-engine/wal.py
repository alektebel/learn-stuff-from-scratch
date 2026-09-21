"""
Write-Ahead Log — crash recovery. Complete Solution.

A B+tree write touches several pages. A crash between them leaves a tree that
is neither the old one nor the new one: a leaf split where the leaf was written
and the parent was not, and now half the keys are unreachable. Nothing in
btree.py can detect that afterwards, let alone fix it.

The WAL is the answer, and it is one rule:

    WRITE-AHEAD RULE: the log record describing a change must be DURABLE on
    disk before the changed page is.

That single ordering constraint is what buys you atomicity and durability. Not
a clever data structure — an ordering.

DESIGN DECISION — log the pages, or log the operations?
  PHYSICAL logging records "page 7 bytes 100-140 became X". Replay is
  idempotent and trivially correct, but a record is as big as the change.
  LOGICAL logging records "insert key 42 into table t". Records are tiny, but
  replay must re-execute the operation, which requires the database to be in
  exactly the right state — and after a crash you cannot be sure it is.
  CHOSEN: PHYSIOLOGICAL logging, which is what ARIES and every real engine
  uses: logical WITHIN a page, physical ACROSS pages. Each record names one
  page and describes the change to it logically. Replay is per-page and
  idempotent, and records stay small.

DESIGN DECISION — what does "committed" mean?
  CHOSEN: the COMMIT record is durable in the log. Not "the pages are written"
  — that is far too slow, because it turns one sequential log write into
  several random page writes. The data pages can be written whenever, which is
  the point: the log is sequential and fast, page writes are random and slow,
  and the WAL lets you do the fast thing on the critical path.
  This is why `fsync` on commit is the thing that dominates transaction
  latency, and why group commit (batching many transactions into one fsync)
  exists.

DESIGN DECISION — redo only, or redo and undo?
  Redo-only is simpler: never write an uncommitted page to disk, then recovery
  just replays committed records. But "never write an uncommitted page" means a
  long transaction must hold every page it touched in memory, which is a
  buffer-pool-sized limit on transaction size.
  CHOSEN: redo AND undo, as ARIES does — dirty pages may be written at any
  time, and recovery has two phases: REDO everything to reconstruct the state
  at the crash, then UNDO the transactions that never committed. The famous
  counter-intuitive part is that redo replays even the LOSERS' records first.
  It has to: you cannot undo a change that is not there.

Learning Path:
1. WriteAheadLog.append and flush — and keep `buffer` and `durable` separate,
   because the gap between them IS the bug you are guarding against
2. Database.write — log record FIRST, then change the page
3. Database.commit — force the log; do NOT force the pages
4. Database.flush_page — the write-ahead rule, in two lines
5. Database.recover — analysis, then redo EVERYTHING, then undo the losers
6. abort with compensation log records, so a crash during rollback resumes
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

BEGIN, UPDATE, COMMIT, ABORT, CHECKPOINT, CLR = (
    "BEGIN", "UPDATE", "COMMIT", "ABORT", "CHECKPOINT", "CLR")


class LogRecord:
    """One entry. `lsn` is its position and its identity.

    `prev_lsn` chains a transaction's own records backwards, so undo can walk
    one transaction without scanning the whole log. `before` and `after` are
    what make a record reversible — undo needs `before`, redo needs `after`,
    and a record with only one of them supports only one direction.
    """

    __slots__ = ("lsn", "kind", "txn", "page_id", "key", "before", "after",
                 "prev_lsn", "undo_next")

    def __init__(self, lsn: int, kind: str, txn: Optional[int] = None,
                 page_id: Optional[int] = None, key: Any = None,
                 before: Any = None, after: Any = None,
                 prev_lsn: Optional[int] = None,
                 undo_next: Optional[int] = None):
        self.lsn, self.kind, self.txn = lsn, kind, txn
        self.page_id, self.key = page_id, key
        self.before, self.after = before, after
        self.prev_lsn, self.undo_next = prev_lsn, undo_next

    def to_json(self) -> str:
        return json.dumps({s: getattr(self, s) for s in self.__slots__})

    @classmethod
    def from_json(cls, line: str) -> "LogRecord":
        return cls(**json.loads(line))

    def __repr__(self) -> str:
        core = f"#{self.lsn} {self.kind}"
        if self.txn is not None:
            core += f" t{self.txn}"
        if self.page_id is not None:
            core += f" p{self.page_id} {self.key}={self.before!r}->{self.after!r}"
        return f"<{core}>"


class WriteAheadLog:
    """An append-only log with an explicit durability boundary.

    `buffer` holds records written but not yet forced; `durable` is what would
    survive a crash right now. Keeping those separate is the whole point — a
    WAL where every write is immediately durable teaches you nothing, because
    the bug you are guarding against is precisely the gap between them.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.durable: List[LogRecord] = []
        self.buffer: List[LogRecord] = []
        self.next_lsn = 1
        self.flushed_lsn = 0
        self.stats = {"appends": 0, "flushes": 0, "records_forced": 0,
                      "bytes_forced": 0}

    def append(self, kind: str, **fields: Any) -> LogRecord:
        record = LogRecord(self.next_lsn, kind, **fields)
        self.next_lsn += 1
        self.buffer.append(record)
        self.stats["appends"] += 1
        return record

    def flush(self, upto_lsn: Optional[int] = None) -> None:
        """Force records to disk. THIS is the expensive operation.

        One flush costs an fsync — hundreds of microseconds on an SSD,
        milliseconds on a spinning disk — regardless of how many records it
        covers. That flat cost is why group commit exists: batching 100
        transactions into one flush makes each one ~100x cheaper to commit.
        """
        raise NotImplementedError

    def crash(self) -> List[LogRecord]:
        """Simulate power loss: the unflushed buffer evaporates."""
        lost = self.buffer
        self.buffer = []
        return lost

    def records(self) -> List[LogRecord]:
        return list(self.durable)


class Database:
    """A page store with a WAL in front of it.

    The pages here are dicts rather than the byte pages of pager.py — the
    recovery protocol is what this file is about, and byte packing would bury
    it. Swapping in a real Page changes nothing about the algorithm.
    """

    def __init__(self, log: Optional[WriteAheadLog] = None):
        self.log = log or WriteAheadLog()
        self.pages: Dict[int, Dict[Any, Any]] = {}
        self.page_lsn: Dict[int, int] = {}      # last LSN applied to each page
        self.disk: Dict[int, Dict[Any, Any]] = {}   # what actually survives
        self.disk_page_lsn: Dict[int, int] = {}
        self.active: Dict[int, int] = {}        # txn -> its last LSN
        self.next_txn = 1
        self.stats = {"page_writes": 0, "redos": 0, "undos": 0,
                      "losers_undone": 0}

    # -- transactions -------------------------------------------------------

    def begin(self) -> int:
        raise NotImplementedError

    def write(self, txn: int, page_id: int, key: Any, value: Any) -> None:
        """Log first, then change the page. The order is the entire protocol."""
        raise NotImplementedError

    def read(self, page_id: int, key: Any) -> Any:
        raise NotImplementedError

    def commit(self, txn: int) -> None:
        """Force the log up to the COMMIT record. Pages need not be written.

        A transaction is committed the moment its COMMIT record is durable —
        even though not one of its data pages may have reached disk. Recovery
        is what makes that promise good, and it is the trade the whole design
        rests on: one sequential log write on the critical path instead of
        several random page writes.
        """
        raise NotImplementedError

    def abort(self, txn: int) -> None:
        """Roll back by walking prev_lsn and applying `before` values.

        Each undo writes a COMPENSATION LOG RECORD (CLR) describing what the
        undo did. CLRs are redo-only and carry `undo_next`, so a crash DURING
        a rollback does not restart the rollback from the beginning — recovery
        picks up where it left off. Without them, a crash during recovery can
        leave you undoing an undo, forever.
        """
        raise NotImplementedError

    def _record(self, lsn: int) -> Optional[LogRecord]:
        for record in self.log.durable + self.log.buffer:
            if record.lsn == lsn:
                return record
        return None

    # -- durability ---------------------------------------------------------

    def flush_page(self, page_id: int) -> None:
        """Write one page to disk, honouring the write-ahead rule.

        The two lines below are the rule itself. Flushing the log first is not
        an optimisation or a nicety; skip it and a crash can leave a page on
        disk whose describing record was never written, which is a change that
        recovery cannot see and therefore cannot undo. That is unrecoverable
        corruption, from two lines in the wrong order.
        """
        raise NotImplementedError

    def checkpoint(self) -> None:
        """Flush everything and note it, so recovery need not read the whole log.

        Without checkpoints, recovery time grows without bound with uptime — a
        database up for a year replays a year of log. The checkpoint record is
        the promise that everything before it is already on disk.
        """
        raise NotImplementedError

    def crash(self) -> Tuple[int, int]:
        """Power loss. Memory is gone; disk and the DURABLE log remain."""
        lost_records = len(self.log.crash())
        lost_pages = len(self.pages)
        self.pages = {}
        self.page_lsn = {}
        self.active = {}
        return lost_records, lost_pages

    # -- recovery -----------------------------------------------------------

    def recover(self) -> Dict[str, Any]:
        """ARIES, in three passes.

        ANALYSIS  find where to start and which transactions were in flight
        REDO      replay EVERY update since then, winners and losers alike
        UNDO      roll back the losers, newest LSN first

        The counter-intuitive pass is REDO: it replays the losers too. It has
        to. Undo works by restoring `before` values, and you cannot restore a
        page to its pre-change state unless the change is actually there. So
        recovery first makes the database exactly what it was at the instant of
        the crash — including the garbage — and only then removes the garbage.
        """
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these six things:

    1. Commit is a log write. Five writes, one commit, and count the DATA pages
       written. It should be zero.

    2. Crash before any page is written, then recover. All five committed rows
       come back from the log alone.

    3. A committed transaction and an in-flight one crashed together, where the
       in-flight one's page HAPPENED to be flushed. Recovery must redo it and
       then undo it — show both, and explain why redo has to replay the losers.

    4. The rule violated. Put a page on disk without forcing its log record,
       crash, and recover. The change is on disk with no record of it, so
       recovery cannot see it and therefore cannot undo it. Two lines in the
       wrong order, and the database is silently wrong forever.

    5. Checkpoints. Records replayed at 100, 1,000 and 5,000 log records, with
       and without checkpointing. Without them, recovery time grows with
       UPTIME rather than with data size.

    6. Group commit. 100 transactions at batch sizes 1, 10 and 100, counting
       fsyncs. An fsync costs the same whether it covers one record or a
       hundred, so batching multiplies throughput by the batch size — at the
       cost of a little latency each.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

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
        limit = upto_lsn if upto_lsn is not None else self.next_lsn
        forced = [r for r in self.buffer if r.lsn <= limit]
        if not forced:
            return
        self.durable.extend(forced)
        self.buffer = [r for r in self.buffer if r.lsn > limit]
        self.flushed_lsn = max(self.flushed_lsn, forced[-1].lsn)
        self.stats["flushes"] += 1
        self.stats["records_forced"] += len(forced)
        self.stats["bytes_forced"] += sum(len(r.to_json()) for r in forced)
        if self.path:
            with open(self.path, "a") as handle:
                for record in forced:
                    handle.write(record.to_json() + "\n")
                handle.flush()
                os.fsync(handle.fileno())

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
        txn = self.next_txn
        self.next_txn += 1
        record = self.log.append(BEGIN, txn=txn, prev_lsn=None)
        self.active[txn] = record.lsn
        return txn

    def write(self, txn: int, page_id: int, key: Any, value: Any) -> None:
        """Log first, then change the page. The order is the entire protocol."""
        if txn not in self.active:
            raise RuntimeError(f"transaction {txn} is not active")
        page = self.pages.setdefault(page_id, {})
        record = self.log.append(UPDATE, txn=txn, page_id=page_id, key=key,
                                 before=page.get(key), after=value,
                                 prev_lsn=self.active[txn])
        self.active[txn] = record.lsn
        page[key] = value
        self.page_lsn[page_id] = record.lsn

    def read(self, page_id: int, key: Any) -> Any:
        return self.pages.get(page_id, {}).get(key)

    def commit(self, txn: int) -> None:
        """Force the log up to the COMMIT record. Pages need not be written.

        A transaction is committed the moment its COMMIT record is durable —
        even though not one of its data pages may have reached disk. Recovery
        is what makes that promise good, and it is the trade the whole design
        rests on: one sequential log write on the critical path instead of
        several random page writes.
        """
        record = self.log.append(COMMIT, txn=txn, prev_lsn=self.active[txn])
        self.log.flush(record.lsn)
        del self.active[txn]

    def abort(self, txn: int) -> None:
        """Roll back by walking prev_lsn and applying `before` values.

        Each undo writes a COMPENSATION LOG RECORD (CLR) describing what the
        undo did. CLRs are redo-only and carry `undo_next`, so a crash DURING
        a rollback does not restart the rollback from the beginning — recovery
        picks up where it left off. Without them, a crash during recovery can
        leave you undoing an undo, forever.
        """
        lsn = self.active.get(txn)
        while lsn is not None:
            record = self._record(lsn)
            if record is None:
                break
            if record.kind == UPDATE:
                if record.before is None:
                    self.pages[record.page_id].pop(record.key, None)
                else:
                    self.pages[record.page_id][record.key] = record.before
                clr = self.log.append(CLR, txn=txn, page_id=record.page_id,
                                      key=record.key, after=record.before,
                                      prev_lsn=self.active[txn],
                                      undo_next=record.prev_lsn)
                self.active[txn] = clr.lsn
                self.stats["undos"] += 1
            lsn = record.prev_lsn
        self.log.append(ABORT, txn=txn, prev_lsn=self.active.get(txn))
        self.active.pop(txn, None)

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
        self.log.flush(self.page_lsn.get(page_id, 0))       # WRITE-AHEAD RULE
        self.disk[page_id] = dict(self.pages[page_id])
        self.disk_page_lsn[page_id] = self.page_lsn.get(page_id, 0)
        self.stats["page_writes"] += 1

    def checkpoint(self) -> None:
        """Flush everything and note it, so recovery need not read the whole log.

        Without checkpoints, recovery time grows without bound with uptime — a
        database up for a year replays a year of log. The checkpoint record is
        the promise that everything before it is already on disk.
        """
        for page_id in list(self.pages):
            self.flush_page(page_id)
        record = self.log.append(CHECKPOINT)
        self.log.flush(record.lsn)

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
        log = self.log.records()

        # -- analysis --
        start = 0
        for index, record in enumerate(log):
            if record.kind == CHECKPOINT:
                start = index + 1
        committed = {r.txn for r in log if r.kind == COMMIT}
        aborted = {r.txn for r in log if r.kind == ABORT}
        began = {r.txn for r in log if r.kind == BEGIN}
        losers = began - committed - aborted

        self.pages = {pid: dict(page) for pid, page in self.disk.items()}
        self.page_lsn = dict(self.disk_page_lsn)

        # -- redo: everything, in LSN order, winners and losers alike --
        redone = 0
        for record in log[start:]:
            if record.kind not in (UPDATE, CLR):
                continue
            page = self.pages.setdefault(record.page_id, {})
            if self.page_lsn.get(record.page_id, 0) >= record.lsn:
                continue                 # already on disk; redo is idempotent
            page[record.key] = record.after
            self.page_lsn[record.page_id] = record.lsn
            redone += 1
        self.stats["redos"] += redone

        # -- undo: the losers, newest first --
        undone = 0
        to_undo = [r for r in log if r.kind == UPDATE and r.txn in losers]
        for record in sorted(to_undo, key=lambda r: -r.lsn):
            page = self.pages.setdefault(record.page_id, {})
            if record.before is None:
                # Undoing an INSERT removes the row. Setting it to None would
                # leave a key that a scan still sees — a tombstone nobody asked
                # for, and a difference a `SELECT count(*)` would notice.
                page.pop(record.key, None)
            else:
                page[record.key] = record.before
            undone += 1
        self.stats["undos"] += undone
        self.stats["losers_undone"] += len(losers)

        for page_id in list(self.pages):
            self.disk[page_id] = dict(self.pages[page_id])
        self.active = {}
        return {"scanned": len(log) - start, "redone": redone, "undone": undone,
                "committed": sorted(committed), "losers": sorted(losers)}


def _demo() -> None:
    print("=" * 72)
    print("WRITE-AHEAD LOG — one ordering rule, and what it buys")
    print("=" * 72)

    print("\n1. Commit is a log write, not a page write")
    print("-" * 72)
    db = Database()
    t = db.begin()
    for n in range(5):
        db.write(t, page_id=1, key=f"k{n}", value=n)
    db.commit(t)
    print(f"  5 writes committed: {db.stats['page_writes']} data pages written, "
          f"{db.log.stats['flushes']} log flush")
    print("  Not one data page reached disk. The transaction is durable anyway,")
    print("  because the COMMIT record is — and recovery is the promise that")
    print("  makes that safe.")

    print("\n2. Crash before the pages are written")
    print("-" * 72)
    lost_records, lost_pages = db.crash()
    print(f"  crash: {lost_pages} in-memory pages gone, "
          f"{lost_records} unflushed log records gone")
    print(f"  on disk before recovery: {db.disk}")
    result = db.recover()
    print(f"  recovery scanned {result['scanned']} records, "
          f"redid {result['redone']}, undid {result['undone']}")
    print(f"  after recovery: {db.pages}")
    assert db.pages[1] == {f"k{n}": n for n in range(5)}
    print("  All five committed writes are back, reconstructed entirely from")
    print("  the log. The data pages were never written before the crash.")

    print("\n3. A committed transaction and an in-flight one, crashed together")
    print("-" * 72)
    db = Database()
    winner = db.begin()
    db.write(winner, 1, "balance:alice", 100)
    db.write(winner, 1, "balance:bob", 50)
    db.commit(winner)

    loser = db.begin()
    db.write(loser, 1, "balance:alice", 0)          # a transfer, half done
    db.write(loser, 2, "balance:carol", 100)
    db.flush_page(2)                                # a dirty page happens to spill
    print(f"  page 2 was flushed while its transaction was still open — disk "
          f"now holds {db.disk[2]}")
    print("  That is allowed, and it is why UNDO has to exist at all.")

    db.crash()
    result = db.recover()
    print(f"  recovery: committed {result['committed']}, "
          f"losers {result['losers']}, redone {result['redone']}, "
          f"undone {result['undone']}")
    print(f"  final state: {db.pages}")
    assert db.pages[1]["balance:alice"] == 100, "the loser's write must be undone"
    assert db.pages[1]["balance:bob"] == 50, "the winner's write must survive"
    assert "balance:carol" not in db.pages.get(2, {}), \
        "a flushed page from an uncommitted transaction must be rolled back"
    print("  Alice is back to 100 and Carol's row is gone, even though Carol's")
    print("  page had already reached disk. Redo put the garbage back so that")
    print("  undo could take it away — that is why redo replays the losers.")

    print("\n4. The rule, violated")
    print("-" * 72)
    good = Database()
    t = good.begin()
    good.write(t, 1, "x", "new")
    good.flush_page(1)
    print(f"  obeying the rule: page flushed, "
          f"{good.log.stats['flushes']} log flush(es) happened first, "
          f"{len(good.log.durable)} records durable")

    bad = Database()
    t = bad.begin()
    bad.write(t, 1, "x", "new")
    bad.disk[1] = dict(bad.pages[1])        # page out, log NOT forced
    bad.disk_page_lsn[1] = bad.page_lsn[1]
    lost = bad.log.crash()
    print(f"  breaking the rule: page reached disk, then a crash lost "
          f"{len(lost)} unflushed record(s)")
    result = bad.recover()
    print(f"  recovery sees {result['scanned']} records and finds "
          f"{len(result['losers'])} loser(s); disk still says "
          f"{bad.disk[1]}")
    print("  The change is on disk and there is NO record of it. Recovery")
    print("  cannot undo what it cannot see. The database is now silently")
    print("  wrong, and no later operation will ever notice.")
    print("  Two lines in the wrong order. That is the whole failure mode.")

    print("\n5. Checkpoints bound recovery time")
    print("-" * 72)
    print(f"    {'log records':>13}{'checkpoint':>13}{'records replayed':>19}")
    for total in (100, 1000, 5000):
        for use_checkpoint in (False, True):
            d = Database()
            t = d.begin()
            for n in range(total):
                d.write(t, 1, f"k{n}", n)
                if use_checkpoint and n % 50 == 49:
                    d.commit(t)
                    d.checkpoint()
                    t = d.begin()
            d.commit(t)
            d.crash()
            replayed = d.recover()["scanned"]
            print(f"    {total:>13}{'yes' if use_checkpoint else 'no':>13}"
                  f"{replayed:>19}")
    print("  Without checkpoints, recovery time grows with UPTIME rather than")
    print("  with data size — a database up for a year replays a year of log.")
    print("  The checkpoint interval is therefore a direct trade of steady-state")
    print("  write throughput against how long you are down after a crash.")

    print("\n6. Group commit: why the fsync count is the throughput ceiling")
    print("-" * 72)
    print(f"    {'transactions':>14}{'batch size':>12}{'fsyncs':>9}"
          f"{'per txn':>10}")
    for batch in (1, 10, 100):
        d = Database()
        txns = []
        for n in range(100):
            t = d.begin()
            d.write(t, 1, f"k{n}", n)
            txns.append(t)
            if len(txns) >= batch:
                for pending in txns:
                    d.log.append(COMMIT, txn=pending)
                    d.active.pop(pending, None)
                d.log.flush()               # ONE fsync for the whole batch
                txns = []
        print(f"    {100:>14}{batch:>12}{d.log.stats['flushes']:>9}"
              f"{d.log.stats['flushes'] / 100:>10.2f}")
    print("  An fsync costs the same whether it covers one record or a hundred.")
    print("  Batching does not make any transaction faster — each one waits a")
    print("  little longer — but it multiplies THROUGHPUT by the batch size.")
    print("  Latency traded for throughput, at a knob.")

    print("\n" + "=" * 72)
    print("Next: mvcc.py lets these transactions run at the same time.")
    print("=" * 72)


if __name__ == "__main__":
    _demo()

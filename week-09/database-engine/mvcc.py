"""
MVCC — many transactions at once. Complete Solution.

Locking gets concurrency wrong in a specific, expensive way: a reader blocks a
writer. Reports block the application. The fix that every serious engine
reached independently is to stop overwriting rows.

DESIGN DECISION — locks, or versions?
  Two-phase locking is correct and simple to state, and its cost is that a
  reader holding a shared lock stops a writer from making progress. On a
  read-heavy workload — which is nearly all of them — that is the whole
  bottleneck.
  CHOSEN: MULTI-VERSION concurrency control. An UPDATE does not overwrite; it
  writes a NEW version and marks the old one dead as of this transaction. A
  reader then picks the version that was live when its transaction started, and
  never waits for anybody. The slogan is exact: **readers never block writers,
  writers never block readers.**
  The bill arrives elsewhere, and this file makes you look at it: old versions
  accumulate, someone has to collect them, and the collector cannot run while
  any transaction might still need what it would collect.

DESIGN DECISION — how is a version's lifetime recorded?
  CHOSEN: PostgreSQL's scheme, because it is the most legible. Every version
  carries (xmin, xmax): the transaction that created it and the transaction
  that deleted it. Visibility is then a pure function of those two numbers and
  the reader's snapshot — no locks, no waiting, no shared state to coordinate.
  REJECTED: an undo log with in-place updates, as InnoDB and Oracle do. Rows
  stay compact and there is no bloat in the table itself, but a reader of an
  old snapshot must reconstruct its version by walking the undo chain
  backwards. The trade is real: Postgres pays in table bloat, InnoDB pays in
  read amplification for long transactions. Neither is free.

DESIGN DECISION — which isolation level is the default?
  This file implements the levels so you can see what each one ADMITS, because
  the useful way to hold isolation levels in your head is not "how strict" but
  "which specific anomaly does this one still allow".
  The one to internalise is at the bottom: **snapshot isolation does not
  prevent write skew**, and write skew looks exactly like the kind of
  constraint people assume a transaction protects. It is not an obscure corner;
  it is the reason `SERIALIZABLE` exists and the reason `SELECT ... FOR UPDATE`
  appears in code written by people who have been burned.

Learning Path:
1. Snapshot.committed_before_me — the visibility rule, and remember that
   `active` matters as much as the horizon
2. MVCCStore.read — walk the version chain, newest first
3. MVCCStore.write — append a version, mark the old one dead, and refuse on a
   concurrent commit (first committer wins)
4. _snapshot_for — one line, and it is the whole difference between read
   committed and repeatable read
5. vacuum, and then measure what one idle transaction does to it
6. _check_serializable — track the READ set too, and watch write skew disappear
"""

from typing import Any, Dict, List, Optional, Set, Tuple

READ_UNCOMMITTED = "read uncommitted"
READ_COMMITTED = "read committed"
REPEATABLE_READ = "repeatable read"      # snapshot isolation, in practice
SERIALIZABLE = "serializable"

ACTIVE, COMMITTED, ABORTED = "active", "committed", "aborted"


class Version:
    """One version of one row.

    xmin  the transaction that created this version
    xmax  the transaction that deleted it, or None if it is still live
    """

    __slots__ = ("key", "value", "xmin", "xmax")

    def __init__(self, key: Any, value: Any, xmin: int, xmax: Optional[int] = None):
        self.key, self.value, self.xmin, self.xmax = key, value, xmin, xmax

    def __repr__(self) -> str:
        return (f"<{self.key}={self.value!r} xmin={self.xmin} "
                f"xmax={self.xmax if self.xmax is not None else '-'}>")


class Snapshot:
    """What a transaction can see: a horizon, plus who was in flight at it.

    `active` is the crucial half and the one people forget. Transaction 40 may
    have a LOWER id than you and still be invisible, because it had not
    committed when your snapshot was taken. A snapshot is not "everything below
    N" — it is "everything below N that had already committed", and the
    difference is exactly the set of concurrent transactions.
    """

    __slots__ = ("xid", "xmax", "active")

    def __init__(self, xid: int, xmax: int, active: Set[int]):
        self.xid, self.xmax, self.active = xid, xmax, set(active)

    def committed_before_me(self, xid: Optional[int],
                            status: Dict[int, str]) -> bool:
        raise NotImplementedError


class Transaction:
    __slots__ = ("xid", "isolation", "snapshot", "writes", "reads", "status")

    def __init__(self, xid: int, isolation: str, snapshot: Snapshot):
        self.xid, self.isolation, self.snapshot = xid, isolation, snapshot
        self.writes: Set[Any] = set()
        self.reads: Set[Any] = set()
        self.status = ACTIVE

    def __repr__(self) -> str:
        return f"<t{self.xid} {self.isolation} {self.status}>"


class SerializationError(Exception):
    """The engine refused rather than corrupt. Retry the whole transaction.

    Every MVCC application needs a retry loop, and this exception is why. An
    engine that never raised it would have to block instead, which is the cost
    MVCC exists to avoid.
    """


class MVCCStore:
    """A versioned key-value store with pluggable isolation."""

    def __init__(self, default_isolation: str = REPEATABLE_READ):
        self.versions: Dict[Any, List[Version]] = {}
        self.status: Dict[int, str] = {}
        self.transactions: Dict[int, Transaction] = {}
        self.active: Set[int] = set()
        self.next_xid = 1
        self.default_isolation = default_isolation
        self.stats = {"versions_created": 0, "conflicts": 0,
                      "dead_versions": 0, "vacuumed": 0, "reads": 0}

    # -- lifecycle ----------------------------------------------------------

    def begin(self, isolation: Optional[str] = None) -> Transaction:
        raise NotImplementedError

    def commit(self, txn: Transaction) -> None:
        raise NotImplementedError

    def abort(self, txn: Transaction) -> None:
        raise NotImplementedError

    # -- reads --------------------------------------------------------------

    def _snapshot_for(self, txn: Transaction) -> Snapshot:
        """Read committed takes a FRESH snapshot per statement; the stricter
        levels reuse the one from BEGIN.

        That one line is the entire difference between read committed and
        repeatable read, and it is the whole of the non-repeatable-read
        anomaly: run the same SELECT twice under read committed and a
        transaction that committed in between becomes visible.
        """
        raise NotImplementedError

    def read(self, txn: Transaction, key: Any) -> Optional[Any]:
        raise NotImplementedError

    def scan(self, txn: Transaction) -> Dict[Any, Any]:
        raise NotImplementedError

    # -- writes -------------------------------------------------------------

    def write(self, txn: Transaction, key: Any, value: Any) -> None:
        """Never overwrite. Mark the old version dead and append a new one.

        FIRST COMMITTER WINS: if a concurrent transaction already wrote this
        key and committed, this transaction cannot proceed — its snapshot is
        stale, so its new value would be computed from data it never saw. That
        is exactly the lost-update anomaly, and refusing here is what prevents
        it.

        Note that this protection comes from the SNAPSHOT, not from the write
        path. Under read committed the snapshot is retaken per statement, so
        the concurrent commit is already visible, nothing conflicts, and the
        overwrite silently discards the other transaction's increment. That is
        the real reason to reach for repeatable read.
        """
        raise NotImplementedError

    def delete(self, txn: Transaction, key: Any) -> bool:
        raise NotImplementedError

    # -- serializable -------------------------------------------------------

    def _check_serializable(self, txn: Transaction) -> None:
        """Serializable snapshot isolation, in its simplest form.

        SI misses write skew because two transactions can READ overlapping data
        and WRITE disjoint data — no write-write conflict ever occurs, so
        nothing complains. The fix is to track the read set as well and abort
        when a concurrent transaction wrote something this one read.

        This is a coarse approximation of what PostgreSQL's SSI actually does
        (it detects dangerous *structures* of read-write dependencies, and
        aborts far less often). It is enough to make the anomaly disappear and
        to show you what the guarantee costs: more aborts, and therefore a
        retry loop you must write.
        """
        raise NotImplementedError

    # -- housekeeping -------------------------------------------------------

    def oldest_snapshot(self) -> int:
        return min(self.active) if self.active else self.next_xid

    def vacuum(self) -> int:
        """Remove versions no active snapshot could possibly need.

        The horizon is the OLDEST active transaction. One transaction left open
        — a forgotten `BEGIN` in a psql window, an idle-in-transaction
        connection — pins that horizon and every dead version behind it stays.
        This is not a theoretical concern; it is the single most common way a
        PostgreSQL instance runs out of disk, and section 5 measures it.
        """
        raise NotImplementedError

    def total_versions(self) -> int:
        return sum(len(chain) for chain in self.versions.values())


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. A reader and a writer running at the same time, neither waiting. Show
       the reader's answer before the write, after the write, and after the
       COMMIT — it does not change — and then a fresh transaction seeing the
       new value.

    2. The anomaly table: dirty read, non-repeatable read, lost update and
       write skew, against all four isolation levels. Write one small function
       per anomaly that ATTEMPTS it and reports whether it happened. Do not
       hard-code the table; the point is that each cell is measured.

    3. Write skew in full. Two doctors, each checking that the other is still
       on call, each going off call. Both commit with no conflict and nobody is
       on call. Repeatable read — the default in most engines — allows this.

    4. The same scenario at SERIALIZABLE, where one transaction is refused.
       Say what that costs: an abort, and therefore a retry loop you must
       write.

    5. Vacuum with one transaction left open. Run several rounds of updates and
       show vacuum freeing NOTHING, because the oldest snapshot pins the
       horizon. Then commit that one transaction and watch everything free at
       once. This is the mechanism behind most PostgreSQL disk-space incidents.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

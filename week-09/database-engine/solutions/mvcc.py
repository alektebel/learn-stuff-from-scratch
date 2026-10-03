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
        if xid is None:
            return False
        if xid == self.xid:
            return True                      # my own writes are visible to me
        if xid >= self.xmax or xid in self.active:
            return False                     # started at or after my snapshot
        return status.get(xid) == COMMITTED


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
        xid = self.next_xid
        self.next_xid += 1
        snapshot = Snapshot(xid, xid, self.active)
        txn = Transaction(xid, isolation or self.default_isolation, snapshot)
        self.transactions[xid] = txn
        self.status[xid] = ACTIVE
        self.active.add(xid)
        return txn

    def commit(self, txn: Transaction) -> None:
        if txn.isolation == SERIALIZABLE:
            self._check_serializable(txn)
        self.status[txn.xid] = COMMITTED
        txn.status = COMMITTED
        self.active.discard(txn.xid)

    def abort(self, txn: Transaction) -> None:
        self.status[txn.xid] = ABORTED
        txn.status = ABORTED
        self.active.discard(txn.xid)

    # -- reads --------------------------------------------------------------

    def _snapshot_for(self, txn: Transaction) -> Snapshot:
        """Read committed takes a FRESH snapshot per statement; the stricter
        levels reuse the one from BEGIN.

        That one line is the entire difference between read committed and
        repeatable read, and it is the whole of the non-repeatable-read
        anomaly: run the same SELECT twice under read committed and a
        transaction that committed in between becomes visible.
        """
        if txn.isolation in (READ_COMMITTED, READ_UNCOMMITTED):
            return Snapshot(txn.xid, self.next_xid, self.active)
        return txn.snapshot

    def read(self, txn: Transaction, key: Any) -> Optional[Any]:
        self.stats["reads"] += 1
        txn.reads.add(key)
        snapshot = self._snapshot_for(txn)
        for version in reversed(self.versions.get(key, [])):
            if txn.isolation == READ_UNCOMMITTED:
                # No visibility check at all: you see other transactions'
                # uncommitted work, which is the dirty-read anomaly by
                # definition. Included so you can watch it happen once.
                if version.xmax is None:
                    return version.value
                continue
            if not snapshot.committed_before_me(version.xmin, self.status):
                continue
            if snapshot.committed_before_me(version.xmax, self.status):
                continue                     # deleted, and the delete is visible
            return version.value
        return None

    def scan(self, txn: Transaction) -> Dict[Any, Any]:
        return {key: value for key in self.versions
                if (value := self.read(txn, key)) is not None}

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
        chain = self.versions.setdefault(key, [])
        # The snapshot a WRITE checks against is the same one a read would use,
        # which is what makes read committed genuinely weaker: its snapshot is
        # fresh, so a concurrent commit is already visible and there is nothing
        # to conflict with. It simply overwrites — and that is the lost update.
        snapshot = self._snapshot_for(txn)
        for version in reversed(chain):
            if version.xmax is not None and version.xmax != txn.xid:
                continue
            writer = version.xmin
            if (writer != txn.xid and self.status.get(writer) == COMMITTED
                    and not snapshot.committed_before_me(writer, self.status)):
                self.stats["conflicts"] += 1
                raise SerializationError(
                    f"t{txn.xid} cannot write {key!r}: t{writer} committed a "
                    f"change to it after t{txn.xid}'s snapshot was taken")
            if writer != txn.xid and writer in self.active:
                self.stats["conflicts"] += 1
                raise SerializationError(
                    f"t{txn.xid} cannot write {key!r}: t{writer} holds an "
                    f"uncommitted change to it")
            version.xmax = txn.xid
            self.stats["dead_versions"] += 1
            break

        chain.append(Version(key, value, txn.xid))
        self.stats["versions_created"] += 1
        txn.writes.add(key)

    def delete(self, txn: Transaction, key: Any) -> bool:
        if self.read(txn, key) is None:
            return False
        for version in reversed(self.versions[key]):
            if version.xmax is None:
                version.xmax = txn.xid
                self.stats["dead_versions"] += 1
                txn.writes.add(key)
                return True
        return False

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
        for other in self.transactions.values():
            if other.xid == txn.xid or other.status != COMMITTED:
                continue
            if txn.snapshot.committed_before_me(other.xid, self.status):
                continue                     # committed before we started
            if txn.reads & other.writes:
                self.stats["conflicts"] += 1
                raise SerializationError(
                    f"t{txn.xid} read {sorted(txn.reads & other.writes)} which "
                    f"t{other.xid} wrote concurrently — this pair could not "
                    f"have run one after the other")

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
        horizon = self.oldest_snapshot()
        removed = 0
        for key, chain in list(self.versions.items()):
            keep = []
            for version in chain:
                dead = (version.xmax is not None
                        and self.status.get(version.xmax) == COMMITTED
                        and version.xmax < horizon)
                aborted = self.status.get(version.xmin) == ABORTED
                if dead or aborted:
                    removed += 1
                else:
                    keep.append(version)
            if keep:
                self.versions[key] = keep
            else:
                del self.versions[key]
        self.stats["vacuumed"] += removed
        return removed

    def total_versions(self) -> int:
        return sum(len(chain) for chain in self.versions.values())


def _demo() -> None:
    print("=" * 74)
    print("MVCC — readers never block writers, and what that costs")
    print("=" * 74)

    print("\n1. A write creates a version; it does not overwrite one")
    print("-" * 74)
    store = MVCCStore()
    setup = store.begin()
    store.write(setup, "x", "v1")
    store.commit(setup)

    reader = store.begin()
    writer = store.begin()
    store.write(writer, "x", "v2")
    print(f"  reader t{reader.xid} sees {store.read(reader, 'x')!r} "
          f"while t{writer.xid} holds an uncommitted 'v2'")
    store.commit(writer)
    print(f"  after t{writer.xid} commits, t{reader.xid} STILL sees "
          f"{store.read(reader, 'x')!r}")
    print(f"  a new transaction sees {store.read(store.begin(), 'x')!r}")
    print(f"  versions of 'x' on disk: {store.versions['x']}")
    print("  Neither transaction ever waited. That is the entire proposition.")

    print("\n2. What each isolation level admits")
    print("-" * 74)
    print(f"    {'level':<18}{'dirty read':>12}{'non-repeatable':>16}"
          f"{'lost update':>14}{'write skew':>13}")

    def dirty_read(level):
        s = MVCCStore()
        t0 = s.begin(); s.write(t0, "k", 1); s.commit(t0)
        r = s.begin(level); w = s.begin()
        s.write(w, "k", 2)
        return s.read(r, "k") == 2

    def non_repeatable(level):
        s = MVCCStore()
        t0 = s.begin(); s.write(t0, "k", 1); s.commit(t0)
        r = s.begin(level)
        first = s.read(r, "k")
        w = s.begin(); s.write(w, "k", 2); s.commit(w)
        return s.read(r, "k") != first

    def lost_update(level):
        s = MVCCStore()
        t0 = s.begin(); s.write(t0, "n", 100); s.commit(t0)
        a, b = s.begin(level), s.begin(level)
        va, vb = s.read(a, "n"), s.read(b, "n")
        s.write(a, "n", va + 10); s.commit(a)
        try:
            s.write(b, "n", vb + 10); s.commit(b)
        except SerializationError:
            return False
        return s.read(s.begin(), "n") == 110      # one increment vanished

    def write_skew(level):
        s = MVCCStore()
        t0 = s.begin()
        s.write(t0, "alice_on_call", True)
        s.write(t0, "bob_on_call", True)
        s.commit(t0)
        a, b = s.begin(level), s.begin(level)
        # Each checks the SAME invariant: at least one doctor stays on call.
        a_ok = s.read(a, "bob_on_call")
        b_ok = s.read(b, "alice_on_call")
        try:
            if a_ok:
                s.write(a, "alice_on_call", False)
            s.commit(a)
            if b_ok:
                s.write(b, "bob_on_call", False)
            s.commit(b)
        except SerializationError:
            return False
        final = s.begin()
        return not s.read(final, "alice_on_call") and not s.read(final, "bob_on_call")

    for level in (READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE):
        row = [dirty_read(level), non_repeatable(level),
               lost_update(level), write_skew(level)]
        cells = "".join(("YES" if bad else "no").rjust(w)
                        for bad, w in zip(row, (12, 16, 14, 13)))
        print(f"    {level:<18}{cells}")
    print("  YES means the anomaly HAPPENS at that level. Read the last column")
    print("  twice: repeatable read — snapshot isolation, the default in most")
    print("  engines and the one people reach for — still admits write skew.")

    print("\n3. Write skew, in full, because it is the one that bites")
    print("-" * 74)
    store = MVCCStore()
    t0 = store.begin()
    store.write(t0, "alice_on_call", True)
    store.write(t0, "bob_on_call", True)
    store.commit(t0)
    print("  Invariant: at least one doctor must remain on call.")
    print("  Both feel ill at the same moment and each opens a transaction.")

    a, b = store.begin(REPEATABLE_READ), store.begin(REPEATABLE_READ)
    print(f"  t{a.xid} checks 'is Bob on call?'   -> "
          f"{store.read(a, 'bob_on_call')}  ... so it is safe to go off call")
    print(f"  t{b.xid} checks 'is Alice on call?' -> "
          f"{store.read(b, 'alice_on_call')}  ... so it is safe to go off call")
    store.write(a, "alice_on_call", False)
    store.write(b, "bob_on_call", False)
    store.commit(a)
    store.commit(b)
    final = store.begin()
    print(f"  both commit with NO conflict. Final state: alice="
          f"{store.read(final, 'alice_on_call')}, bob="
          f"{store.read(final, 'bob_on_call')}")
    print("  Nobody is on call. Each transaction was individually correct and")
    print("  each read data the other then changed — but they wrote DIFFERENT")
    print("  keys, so first-committer-wins never fired. Snapshot isolation has")
    print("  no idea anything went wrong, and neither will your logs.")
    print("  The fixes: SERIALIZABLE, or SELECT ... FOR UPDATE on the row you")
    print("  are making a decision about, or a constraint the database checks.")

    print("\n4. The same scenario at SERIALIZABLE")
    print("-" * 74)
    store = MVCCStore()
    t0 = store.begin()
    store.write(t0, "alice_on_call", True)
    store.write(t0, "bob_on_call", True)
    store.commit(t0)
    a, b = store.begin(SERIALIZABLE), store.begin(SERIALIZABLE)
    store.read(a, "bob_on_call")
    store.read(b, "alice_on_call")
    store.write(a, "alice_on_call", False)
    store.write(b, "bob_on_call", False)
    store.commit(a)
    try:
        store.commit(b)
        print("  both committed — the check did not fire")
    except SerializationError as error:
        print(f"  t{b.xid} REFUSED: {error}")
    final = store.begin()
    print(f"  final state: alice={store.read(final, 'alice_on_call')}, "
          f"bob={store.read(final, 'bob_on_call')} — the invariant holds")
    print("  The price is visible: an abort, and therefore a retry loop you have")
    print("  to write. Serializable does not make concurrency free; it converts")
    print("  a silent wrong answer into a loud, retryable error.")

    print("\n5. The bill: one idle transaction pins the whole horizon")
    print("-" * 74)
    store = MVCCStore()
    t0 = store.begin()
    for n in range(20):
        store.write(t0, f"row{n}", 0)
    store.commit(t0)

    forgotten = store.begin()           # someone typed BEGIN and went to lunch
    store.read(forgotten, "row0")

    print(f"    {'updates':>9}{'versions':>10}{'vacuum frees':>14}"
          f"{'still held':>12}")
    for round_number in range(1, 6):
        for n in range(20):
            t = store.begin()
            store.write(t, f"row{n}", round_number)
            store.commit(t)
        freed = store.vacuum()
        print(f"    {round_number * 20:>9}{store.total_versions():>10}"
              f"{freed:>14}{store.total_versions() - 20:>12}")

    print(f"  With t{forgotten.xid} still open, vacuum frees nothing: the oldest")
    print(f"  snapshot is {store.oldest_snapshot()} and every dead version is")
    print("  newer than it, so every one of them might still be needed.")
    store.commit(forgotten)
    freed = store.vacuum()
    print(f"  Committing that one transaction lets vacuum free {freed} versions "
          f"at once,")
    print(f"  taking the table from {freed + store.total_versions()} versions "
          f"back to {store.total_versions()}.")
    print("  This is the mechanism behind most PostgreSQL disk-space incidents.")
    print("  It is never the writes that bloat the table — it is one connection")
    print("  sitting idle-in-transaction while they happen.")

    print("\n" + "=" * 74)
    print("Next: sql.py parses the language all of this is hiding behind.")
    print("=" * 74)


if __name__ == "__main__":
    _demo()

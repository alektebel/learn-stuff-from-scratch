"""
Progress checker for the database-engine templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Pager
# ---------------------------------------------------------------------------

def check_slotted_page() -> None:
    from pager import HEADER, PAGE_SIZE, SLOT, Page

    page = Page(0)
    assert page.slot_count == 0 and page.free_space > PAGE_SIZE - 100

    a = page.insert(b"alice")
    b = page.insert(b"bob")
    c = page.insert(b"carol")
    assert (a, b, c) == (0, 1, 2), f"slots must be handed out in order, got {(a, b, c)}"
    assert page.read(1) == b"bob"

    page.delete(1)
    assert page.read(1) is None, "a deleted slot reads as None, not as an error"
    assert page.read(2) == b"carol", (
        "deleting slot 1 renumbered the surviving slots. It must not: an index "
        "entry pointing at (page, 2) has to keep meaning slot 2 after its "
        "neighbour is deleted. Renumbering on delete invalidates every index "
        "entry after the hole, which is silent corruption rather than an error.")

    before = page.free_space
    recovered = page.compact()
    assert recovered > 0, "compaction must reclaim the deleted record's bytes"
    assert page.free_space == before + recovered
    assert page.read(2) == b"carol", "compaction must preserve slot ids"
    assert page.read(1) is None, "and must keep the hole a hole"

    # Exact capacity, for two record sizes. A page holds as many records as
    # fit once EACH ONE is charged for its bytes plus its slot directory entry.
    for size in (8, 100, 1000):
        full = Page(1)
        count = 0
        while full.insert(bytes(size)) is not None:
            count += 1
        expected = (PAGE_SIZE - HEADER.size) // (size + SLOT.size)
        assert count == expected, (
            f"{count} records of {size} bytes fit in a {PAGE_SIZE}-byte page; "
            f"exactly {expected} should. Each record costs its own bytes PLUS "
            f"a {SLOT.size}-byte slot directory entry, and free_space has to "
            "charge for both. Counting only the bytes lets one record too many "
            "in, and the slot array then writes over the record data — a "
            "silent overwrite rather than an overflow error, which is why the "
            "off-by-one here is worth an exact assertion.")
        assert full.insert(bytes(size)) is None, (
            "a full page must return None, not raise")
        _, _, free_start, free_end = full.header
        assert free_start <= free_end, (
            f"the slot array ends at {free_start} and the records begin at "
            f"{free_end} — they have CROSSED")


def check_buffer_pool() -> None:
    from pager import BufferPool, DiskManager, Page

    disk = DiskManager()
    for _ in range(50):
        disk.allocate()
    pool = BufferPool(disk, capacity=4)

    for page_id in (0, 1, 2, 3):
        pool.fetch(page_id)
    assert pool.stats["misses"] == 4 and pool.stats["hits"] == 0
    pool.fetch(0)
    assert pool.stats["hits"] == 1, "a resident page must be a hit"

    pool.fetch(9)
    assert len(pool.frames) == 4, (
        f"the pool holds {len(pool.frames)} frames with capacity 4 — eviction "
        "did not happen")
    assert 1 not in pool.frames, (
        "page 1 was the least recently used (0 was touched again) and should "
        "have been the victim. If a different page went, the recency order is "
        "not being maintained on HIT as well as on miss.")

    dirty = DiskManager()
    for _ in range(10):
        dirty.allocate()
    pool = BufferPool(dirty, capacity=2)
    page = pool.fetch(0)
    page.insert(b"important")
    dirty.stats["writes"] = 0
    pool.fetch(1)
    pool.fetch(2)
    assert dirty.stats["writes"] >= 1, (
        "an evicted DIRTY page must be written back before its frame is "
        "reused. Dropping it loses the write silently.")

    pinned_disk = DiskManager()
    for _ in range(10):
        pinned_disk.allocate()
    pool = BufferPool(pinned_disk, capacity=2)
    held = pool.fetch(0)
    held.pins += 1
    pool.fetch(1)
    pool.fetch(2)
    assert 0 in pool.frames, (
        "a PINNED page was evicted. A B+tree split holds a parent and two "
        "children at once; evicting one mid-split writes a half-updated tree "
        "and corrupts the database in a way nothing can detect afterwards.")


# ---------------------------------------------------------------------------
# B+tree
# ---------------------------------------------------------------------------

def check_btree_basics() -> None:
    from btree import BPlusTree

    tree = BPlusTree(order=4)
    for n in range(1, 41):
        tree.put(n, f"v{n}")

    assert tree.get(1) == "v1" and tree.get(40) == "v40"
    assert tree.get(999) is None, "a missing key returns None, not an error"
    tree.put(20, "updated")
    assert tree.get(20) == "updated", "putting an existing key updates in place"
    assert len([k for k, _ in tree.items()]) == 40, "the update must not duplicate"

    assert tree.height >= 3, (
        f"40 keys at order 4 gave height {tree.height}. Nodes are not splitting "
        "— a node may hold at most `order` keys.")
    assert tree.stats["splits"] > 0

    problems = tree.check_invariants()
    assert not problems, f"invariants broken: {problems}"

    keys = [k for k, _ in tree.items()]
    assert keys == sorted(keys), (
        "walking the leaf chain did not produce sorted order. Either a split "
        "forgot to relink next_leaf, or the new sibling was linked in the "
        "wrong direction.")


def check_btree_split_and_range() -> None:
    from btree import BPlusTree

    tree = BPlusTree(order=4)
    for n in range(200):
        tree.put(n, n)
    assert tree.check_invariants() == [], tree.check_invariants()

    found = list(tree.range(50, 60))
    assert [k for k, _ in found] == list(range(50, 61)), (
        f"range(50, 60) returned {[k for k, _ in found]}. It must be inclusive "
        "at both ends and must follow the leaf chain past the first leaf.")
    assert list(tree.range(1000, 2000)) == []

    tree.stats["pages_read"] = 0
    list(tree.range(50, 150))
    range_pages = tree.stats["pages_read"]
    tree.stats["pages_read"] = 0
    for n in range(50, 151):
        tree.get(n)
    lookup_pages = tree.stats["pages_read"]
    assert range_pages < lookup_pages / 3, (
        f"a range scan read {range_pages} pages and 101 individual lookups read "
        f"{lookup_pages}. The range should be far cheaper: one descent, then a "
        "walk along the leaf chain. If they are close, range() is re-descending "
        "from the root for every key and the leaf links are doing nothing.")

    wide = BPlusTree(order=250)
    for n in range(20000):
        wide.put(n, n)
    assert wide.height <= 3, (
        f"20,000 keys at order 250 gave height {wide.height}, expected 2 or 3. "
        "Fanout is the base of the logarithm and it is the entire reason "
        "databases use a B-tree rather than a binary tree.")


def check_btree_delete() -> None:
    from btree import BPlusTree
    import random

    tree = BPlusTree(order=4)
    for n in range(50):
        tree.put(n, n)
    assert tree.delete(25) is True
    assert tree.delete(25) is False, "deleting a missing key returns False"
    assert tree.get(25) is None
    assert tree.check_invariants() == [], tree.check_invariants()

    for n in range(50):
        tree.delete(n)
    assert list(tree.items()) == [], "everything was deleted"
    assert tree.height == 1, (
        f"height is {tree.height} after deleting every key. When the root ends "
        "up with no keys and one child, that child becomes the new root — the "
        "exact mirror of the root split.")

    rng = random.Random(11)
    tree = BPlusTree(order=5)
    reference = {}
    for _ in range(2000):
        key = rng.randint(0, 300)
        if rng.random() < 0.65:
            tree.put(key, key * 10)
            reference[key] = key * 10
        else:
            tree.delete(key)
            reference.pop(key, None)
    problems = tree.check_invariants()
    assert not problems, f"after random churn: {problems}"
    assert dict(tree.items()) == reference, (
        "the tree and a plain dict disagree after random inserts and deletes. "
        "A B+tree that is subtly wrong still answers most queries correctly, "
        "which is exactly what makes it dangerous — compare against a dict.")


# ---------------------------------------------------------------------------
# WAL
# ---------------------------------------------------------------------------

def check_wal_commit() -> None:
    from wal import Database

    db = Database()
    txn = db.begin()
    for n in range(5):
        db.write(txn, page_id=1, key=f"k{n}", value=n)
    assert db.stats["page_writes"] == 0, "writing must not touch a data page"
    db.commit(txn)
    assert db.stats["page_writes"] == 0, (
        "COMMIT wrote data pages. It must not: a transaction is durable when "
        "its COMMIT record is on disk, and forcing pages on commit turns one "
        "sequential log write into several random page writes.")
    assert db.log.stats["flushes"] >= 1, "commit must FORCE the log"
    assert db.read(1, "k3") == 3


def check_wal_recovery() -> None:
    from wal import Database

    db = Database()
    winner = db.begin()
    db.write(winner, 1, "alice", 100)
    db.write(winner, 1, "bob", 50)
    db.commit(winner)

    loser = db.begin()
    db.write(loser, 1, "alice", 0)
    db.write(loser, 2, "carol", 100)
    db.flush_page(2)                      # a dirty page spills before commit

    db.crash()
    result = db.recover()

    assert db.pages[1]["alice"] == 100, (
        f"alice is {db.pages[1]['alice']} after recovery, expected 100. The "
        "uncommitted transaction's write must be UNDONE.")
    assert db.pages[1]["bob"] == 50, "the committed transaction must survive"
    assert "carol" not in db.pages.get(2, {}), (
        "carol's row was written by a transaction that never committed, and its "
        "page had already reached disk. Recovery must REDO it (so it is there "
        "to be undone) and then UNDO it. Skipping redo for losers leaves you "
        "unable to undo a change that is not in memory.")
    assert result["undone"] > 0
    assert result["losers"] == [loser], f"losers should be [{loser}]"
    assert result["redone"] >= 3, (
        f"redo replayed only {result['redone']} records. Four updates were "
        "logged and one of their pages was already on disk, so three must be "
        "replayed — INCLUDING the uncommitted transaction's. Redo replays the "
        "losers too: you cannot restore a page to its pre-change state unless "
        "the change is actually there. Recovery first reconstructs the exact "
        "state at the crash, garbage included, and only then removes it.")


def check_wal_rule_and_checkpoints() -> None:
    from wal import Database

    db = Database()
    txn = db.begin()
    db.write(txn, 1, "x", "new")
    before = db.log.stats["flushes"]
    db.flush_page(1)
    assert db.log.stats["flushes"] > before, (
        "flush_page wrote a data page without forcing the log first. That is "
        "the WRITE-AHEAD RULE, and breaking it is unrecoverable: a change "
        "reaches disk with no record describing it, so recovery cannot see it "
        "and therefore cannot undo it. Two lines in the wrong order.")

    short = Database()
    txn = short.begin()
    for n in range(500):
        short.write(txn, 1, f"k{n}", n)
    short.commit(txn)
    short.crash()
    without = short.recover()["scanned"]

    checkpointed = Database()
    txn = checkpointed.begin()
    for n in range(500):
        checkpointed.write(txn, 1, f"k{n}", n)
        if n % 50 == 49:
            checkpointed.commit(txn)
            checkpointed.checkpoint()
            txn = checkpointed.begin()
    checkpointed.commit(txn)
    checkpointed.crash()
    with_checkpoints = checkpointed.recover()["scanned"]

    assert with_checkpoints < without / 10, (
        f"recovery scanned {with_checkpoints} records with checkpoints and "
        f"{without} without. A checkpoint is the promise that everything before "
        "it is already on disk, so recovery starts AFTER the last one. Without "
        "that, recovery time grows with uptime rather than with data size.")


# ---------------------------------------------------------------------------
# MVCC
# ---------------------------------------------------------------------------

def check_mvcc_visibility() -> None:
    from mvcc import MVCCStore, REPEATABLE_READ

    store = MVCCStore()
    setup = store.begin()
    store.write(setup, "x", "v1")
    store.commit(setup)

    reader = store.begin(REPEATABLE_READ)
    writer = store.begin()
    store.write(writer, "x", "v2")
    assert store.read(reader, "x") == "v1", (
        "the reader saw an UNCOMMITTED value — that is a dirty read")
    assert store.read(writer, "x") == "v2", "a transaction sees its own writes"

    store.commit(writer)
    assert store.read(reader, "x") == "v1", (
        "the reader's answer changed after a concurrent COMMIT. Under snapshot "
        "isolation its snapshot was taken at BEGIN and must not move. If it "
        "changed, read() is consulting the current state rather than the "
        "snapshot's active set.")
    assert store.read(store.begin(), "x") == "v2", "a NEW transaction sees v2"

    # The case that needs the ACTIVE set, not just the horizon: a transaction
    # that started BEFORE ours and committed AFTER our snapshot. Its id is
    # lower than ours, so a horizon comparison alone says "visible" — and it
    # must not be.
    early = store.begin()                       # lower xid...
    late = store.begin()                        # ...than this reader
    store.write(early, "y", "written-by-early")
    store.commit(early)                         # commits AFTER late's snapshot
    assert store.read(late, "y") is None, (
        "a transaction with a LOWER id than the reader committed after the "
        "reader's snapshot was taken, and the reader saw it. Visibility is not "
        "'everything below my xid' — it is 'everything below my xid that had "
        "ALREADY COMMITTED', and the difference is exactly the set of "
        "transactions that were in flight. Snapshot.active is that set.")
    assert len(store.versions["x"]) == 2, (
        "there should be two versions of x. A write must APPEND a version, not "
        "overwrite one — that is the whole of multi-version.")


def check_mvcc_anomalies() -> None:
    from mvcc import (MVCCStore, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE,
                      SerializationError)

    # Lost update: allowed at read committed, prevented at repeatable read.
    def lost_update(level):
        store = MVCCStore()
        setup = store.begin(); store.write(setup, "n", 100); store.commit(setup)
        a, b = store.begin(level), store.begin(level)
        va, vb = store.read(a, "n"), store.read(b, "n")
        store.write(a, "n", va + 10); store.commit(a)
        try:
            store.write(b, "n", vb + 10); store.commit(b)
        except SerializationError:
            return False
        return store.read(store.begin(), "n") == 110

    assert lost_update(READ_COMMITTED), (
        "a lost update did NOT happen at read committed. It should: read "
        "committed retakes its snapshot per statement, so the concurrent commit "
        "is already visible, nothing conflicts, and the overwrite discards the "
        "other increment. If your write path always checks the BEGIN snapshot, "
        "read committed is silently as strong as repeatable read.")
    assert not lost_update(REPEATABLE_READ), (
        "repeatable read allowed a lost update. First-committer-wins must "
        "refuse a write whose snapshot predates a committed change to that key.")

    # Write skew: allowed at snapshot isolation, prevented at serializable.
    def write_skew(level):
        store = MVCCStore()
        setup = store.begin()
        store.write(setup, "alice", True)
        store.write(setup, "bob", True)
        store.commit(setup)
        a, b = store.begin(level), store.begin(level)
        store.read(a, "bob")
        store.read(b, "alice")
        try:
            store.write(a, "alice", False); store.commit(a)
            store.write(b, "bob", False); store.commit(b)
        except SerializationError:
            return False
        final = store.begin()
        return not store.read(final, "alice") and not store.read(final, "bob")

    assert write_skew(REPEATABLE_READ), (
        "write skew did not occur at repeatable read. It SHOULD — the two "
        "transactions write different keys, so no write-write conflict ever "
        "fires. This is the anomaly snapshot isolation admits, and a store "
        "that prevents it here is over-aborting rather than being correct.")
    assert not write_skew(SERIALIZABLE), (
        "SERIALIZABLE allowed write skew. Preventing it needs the READ set: "
        "abort when a concurrent transaction wrote something this one read.")


def check_mvcc_vacuum() -> None:
    from mvcc import MVCCStore

    store = MVCCStore()
    setup = store.begin()
    for n in range(10):
        store.write(setup, f"r{n}", 0)
    store.commit(setup)

    idle = store.begin()               # someone typed BEGIN and walked away
    store.read(idle, "r0")

    for round_number in range(3):
        for n in range(10):
            txn = store.begin()
            store.write(txn, f"r{n}", round_number)
            store.commit(txn)
    held = store.total_versions()
    assert store.vacuum() == 0, (
        "vacuum freed versions while an older transaction was still open. The "
        "horizon is the OLDEST active snapshot; anything newer might still be "
        "needed. Freeing past it is a read returning a version that no longer "
        "exists.")

    store.commit(idle)
    freed = store.vacuum()
    assert freed > 0, (
        "vacuum freed nothing even after every transaction finished. Dead "
        "versions must be reclaimed once no snapshot can see them, or the "
        "store grows without bound.")
    assert store.total_versions() < held, (
        f"still holding {store.total_versions()} of {held} versions")
    assert store.total_versions() == 10, (
        "exactly the 10 live versions should remain")


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

def check_tokenizer() -> None:
    from sql import SQLError, tokenize

    assert tokenize("SELECT")[0].kind == "KEYWORD"
    assert tokenize("select")[0].value == "SELECT", "keywords are case-insensitive"
    tokens = tokenize("SELECTED")
    assert tokens[0].kind == "IDENT" and tokens[0].value == "SELECTED", (
        f"SELECTED lexed as {tokens[0]}. It is ONE identifier. Match the "
        "longest word first and THEN ask whether the whole word is a keyword; "
        "classifying as you scan makes SELECTED into SELECT + ED and the parse "
        "error that follows points at completely the wrong place.")

    assert [t.value for t in tokenize("a <= b")][1] == "<=", (
        "'<=' lexed as two tokens. Two-character operators must come before "
        "their one-character prefixes in the alternation.")
    assert tokenize("'it''s'")[0].value == "it's", "'' is an escaped quote"
    assert tokenize("3.5")[0].value == 3.5 and tokenize("3")[0].value == 3
    assert len(tokenize("SELECT 1 -- a comment\n")) == 3, "comments are skipped"
    try:
        tokenize("SELECT $")
        raise AssertionError("an unexpected character must raise SQLError")
    except SQLError:
        pass


def check_parser() -> None:
    from sql import (BinOp, Column, CreateIndex, CreateTable, Delete, Insert,
                     Literal, Parser, SQLError, Select, Update, parse)

    tree = Parser("1 + 2 * 3").expression()
    assert isinstance(tree.right, BinOp) and tree.right.op == "*", (
        f"parsed as {tree!r}. '*' binds tighter than '+'.")
    tree = Parser("a = 1 AND b = 2 OR c = 3").expression()
    assert tree.op == "OR" and tree.left.op == "AND", (
        f"parsed as {tree!r}. AND binds tighter than OR, so this groups as "
        "((a=1 AND b=2) OR c=3).")
    assert Parser("(1 + 2) * 3").expression().op == "*", "parentheses win"
    tree = Parser("a = 1 OR b = 2 AND c = 3").expression()
    assert tree.op == "OR" and tree.right.op == "AND", (
        f"parsed as {tree!r}, expected (a=1 OR (b=2 AND c=3)). Written in this "
        "order the two operators can only be told apart by PRECEDENCE — with "
        "AND and OR at the same level, left-associativity gives "
        "((a=1 OR b=2) AND c=3), which is a different query with a different "
        "answer. The reverse order, `AND ... OR`, happens to parse the same "
        "either way, so it cannot detect this.")

    statement = parse("SELECT name, age FROM users WHERE age > 25 "
                      "ORDER BY age DESC LIMIT 10")
    assert isinstance(statement, Select)
    assert statement.table == "users" and statement.limit == 10
    assert statement.order_by[0][1] is True, "DESC must set the descending flag"
    assert len(statement.columns) == 2

    assert isinstance(parse("INSERT INTO t (a, b) VALUES (1, 2), (3, 4)"), Insert)
    assert len(parse("INSERT INTO t (a, b) VALUES (1, 2), (3, 4)").rows) == 2
    assert isinstance(parse("UPDATE t SET a = a + 1 WHERE b = 2"), Update)
    assert isinstance(parse("DELETE FROM t WHERE a IS NULL"), Delete)
    assert isinstance(parse("CREATE TABLE t (id INT PRIMARY KEY, n TEXT)"),
                      CreateTable)
    assert parse("CREATE TABLE t (id INT PRIMARY KEY, n TEXT)").primary_key == "id"
    assert isinstance(parse("CREATE INDEX i ON t (n)"), CreateIndex)

    joined = parse("SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id")
    assert len(joined.joins) == 1, "the JOIN clause must be parsed"
    assert joined.alias == "u", "`FROM users u` sets a table alias"

    grouped = parse("SELECT city, COUNT(*) FROM t GROUP BY city HAVING COUNT(*) > 2")
    assert grouped.group_by and grouped.having is not None

    for bad in ("SELECT name users", "SELECT FROM users",
                "SELECT * FROM t WHERE age >"):
        try:
            parse(bad)
            raise AssertionError(f"{bad!r} must not parse")
        except SQLError as error:
            assert "column" in str(error), (
                f"the error for {bad!r} was {error!r}. Every message should "
                "name the column and what was expected — that is the whole "
                "argument for a hand-written parser.")


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def check_iterator_model() -> None:
    from executor import Filter, Limit, Project, SeqScan, Sort, run

    rows = [{"id": n, "v": n % 100} for n in range(10000)]

    plan = Limit(Filter(SeqScan("t", rows), lambda r: r["v"] > 50), 5)
    result = run(plan)
    assert len(result) == 5
    assert plan.total_rows_read() < 500, (
        f"a LIMIT 5 over a filter over 10,000 rows read {plan.total_rows_read()} "
        "rows. In the pull model the scan stops as soon as the LIMIT stops "
        "calling next(). If it read everything, an operator is materialising "
        "its whole output instead of yielding one row at a time.")

    sorted_plan = Limit(Sort(SeqScan("t", rows), [(lambda r: r["v"], False)]), 5)
    run(sorted_plan)
    assert sorted_plan.total_rows_read() >= 10000, (
        "a LIMIT above a SORT still has to read everything — the smallest row "
        "could be the last one scanned. If this read fewer, Sort is emitting "
        "before it has consumed its input, and the order will be wrong.")

    projected = run(Project(SeqScan("t", rows[:3]),
                            [("doubled", lambda r: r["id"] * 2)]))
    assert projected == [{"doubled": 0}, {"doubled": 2}, {"doubled": 4}]

    paged = run(Limit(SeqScan("t", rows), 3, offset=10))
    assert [r["id"] for r in paged] == [10, 11, 12], (
        f"OFFSET 10 LIMIT 3 returned {[r['id'] for r in paged]}")


def check_joins_and_aggregates() -> None:
    from executor import (Aggregate, Distinct, HashJoin, NestedLoopJoin,
                          SeqScan, run)

    users = [{"id": n, "name": f"u{n}"} for n in range(300)]
    orders = [{"oid": n, "user_id": n % 300, "total": n} for n in range(300)]

    nested = NestedLoopJoin(SeqScan("orders", orders), users,
                            lambda o, u: o["user_id"] == u["id"])
    hashed = HashJoin(SeqScan("orders", orders), users, "user_id", "id")
    nested_rows = sorted(run(nested), key=lambda r: r["oid"])
    hash_rows = sorted(run(hashed), key=lambda r: r["oid"])
    assert nested_rows == hash_rows, "both joins must give the same answer"
    assert len(hash_rows) == 300
    assert hashed.rows_in < nested.rows_in / 100, (
        f"the hash join examined {hashed.rows_in} rows and the nested loop "
        f"{nested.rows_in}. A hash join is O(N + M): build a table from one "
        "side, then probe once per row of the other. If they are close, the "
        "hash table is being rebuilt or scanned rather than looked up.")

    rows = [{"city": ["a", "b", "c"][n % 3], "v": n} for n in range(30)]
    grouped = run(Aggregate(SeqScan("t", rows), ["city"],
                            [("n", "COUNT", None), ("total", "SUM", "v"),
                             ("biggest", "MAX", "v")]))
    assert len(grouped) == 3
    by_city = {row["city"]: row for row in grouped}
    assert by_city["a"]["n"] == 10 and by_city["a"]["total"] == sum(range(0, 30, 3))
    assert by_city["c"]["biggest"] == 29

    total = run(Aggregate(SeqScan("t", rows), [], [("n", "COUNT", None)]))
    assert total == [{"n": 30}], f"COUNT(*) with no GROUP BY gave {total}"

    unique = run(Distinct(SeqScan("t", [{"a": 1}, {"a": 1}, {"a": 2}])))
    assert len(unique) == 2


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def check_cost_model() -> None:
    from planner import (Statistics, cost_index_scan, cost_seq_scan,
                         crossover_selectivity)
    from sql import BinOp, Column, Literal

    rows = [{"id": n, "age": 18 + n % 60} for n in range(50000)]
    stats = Statistics(rows)
    assert stats.row_count == 50000
    assert stats.distinct["age"] == 60 and stats.distinct["id"] == 50000

    equality = BinOp("=", Column("age"), Literal(25))
    estimate = stats.selectivity(equality)
    assert abs(estimate - 1 / 60) < 1e-9, (
        f"selectivity of `age = 25` estimated at {estimate:.5f}; the textbook "
        "estimate is 1/n_distinct = 1/60.")
    combined = stats.selectivity(BinOp("AND", equality,
                                       BinOp("=", Column("id"), Literal(1))))
    assert abs(combined - estimate * (1 / 50000)) < 1e-12, (
        "AND must multiply the two selectivities — the independence assumption, "
        "which is exactly the thing that fails in production")

    crossover = crossover_selectivity(stats)
    assert 0.001 < crossover < 0.10, (
        f"crossover came out at {crossover:.4f}. Expect a low single-digit "
        "percentage: an index scan pays RANDOM_PAGE_COST per matching row, a "
        "sequential scan pays SEQ_PAGE_COST per page.")

    below = crossover / 2
    above = min(1.0, crossover * 3)
    assert cost_index_scan(stats, below).cost < cost_seq_scan(stats, below).cost, (
        "below the crossover the index must be cheaper")
    assert cost_index_scan(stats, above).cost > cost_seq_scan(stats, above).cost, (
        "above the crossover the sequential scan must be cheaper. If the index "
        "always wins, its per-row term is missing RANDOM_PAGE_COST — and that "
        "term is the entire reason the crossover exists.")


def check_planner_choices() -> None:
    import executor
    from planner import Planner, Table
    from sql import parse

    import random
    rng = random.Random(5)
    rows = [{"id": n, "age": rng.randint(18, 78),
             "city": rng.choice(["lisbon", "porto", "faro"])}
            for n in range(20000)]
    users = Table("users", rows)
    users.create_index("age")
    users.create_index("id")
    planner = Planner({"users": users})

    # id is unique, so `id = 500` is 1/20000 selectivity — comfortably below
    # any sane crossover. age has only ~60 distinct values, which is 1.7% and
    # sits ABOVE it; that pair is the whole lesson.
    narrow = planner.plan(parse("SELECT id FROM users WHERE id = 500"))
    assert "IndexScan" in narrow.explain(), (
        "`id = 500` on a unique indexed column is 1/20,000 selectivity — the "
        "most index-friendly query there is. If this picks a sequential scan, "
        "cost_index_scan is over-charging or n_distinct is not being used:\n"
        + narrow.explain())

    middling = planner.plan(parse("SELECT id FROM users WHERE age = 25"))
    assert "SeqScan" in middling.explain(), (
        "`age = 25` is ~1.7% of the table, which is ABOVE the crossover — an "
        "index scan would make 340 random heap fetches at 4x the cost of a "
        "sequential page. The planner should decline. Getting this right is "
        "more interesting than getting the easy case right:\n"
        + middling.explain())

    wide = planner.plan(parse("SELECT id FROM users WHERE age > 20"))
    assert "SeqScan" in wide.explain(), (
        "`age > 20` matches nearly the whole table, so an index scan would "
        "fetch almost every page in random order. The planner must reject it:\n"
        + wide.explain())

    orders = Table("orders", [{"oid": n, "user_id": n % 20000, "total": n}
                              for n in range(20000)])
    both = Planner({"users": users, "orders": orders})
    plan = both.plan(parse("SELECT id, total FROM users JOIN orders "
                           "ON id = user_id WHERE age = 25"))
    executor.run(plan)

    join_node = None

    def find(node):
        nonlocal join_node
        if "Join" in type(node).__name__:
            join_node = node
        for child in node.children:
            find(child)

    find(plan)
    assert join_node is not None, "the query should produce a join operator"
    assert join_node.rows_in < 2000, (
        f"the join saw {join_node.rows_in} rows. The `age = 25` filter mentions "
        "only `users`, so it must be applied BELOW the join — otherwise the "
        "join processes all 20,000 rows to produce the same few hundred. Split "
        "the WHERE on AND and place each conjunct with the table it belongs to.")


# ---------------------------------------------------------------------------
# Capstone
# ---------------------------------------------------------------------------

def check_database() -> None:
    from database import Database, DatabaseError

    db = Database()
    db.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT, age INT, "
               "city TEXT)")
    inserted = db.execute("INSERT INTO users (id, name, age, city) VALUES "
                          "(1, 'alice', 30, 'lisbon'), (2, 'bob', 25, 'porto'), "
                          "(3, 'carol', 35, 'lisbon')")
    assert inserted == 3

    rows = db.execute("SELECT name, age FROM users WHERE age > 26 "
                      "ORDER BY age DESC")
    assert [r["name"] for r in rows] == ["carol", "alice"], (
        f"got {[r.get('name') for r in rows]}")

    grouped = db.execute("SELECT city, COUNT(*) FROM users GROUP BY city")
    counts = {row["city"]: row["count"] for row in grouped}
    assert counts == {"lisbon": 2, "porto": 1}, f"got {counts}"

    db.execute("UPDATE users SET age = age + 1 WHERE name = 'alice'")
    assert db.execute("SELECT age FROM users WHERE name = 'alice'")[0]["age"] == 31

    before = len(db.execute("SELECT id FROM users"))
    db.execute("BEGIN")
    db.execute("INSERT INTO users (id, name, age, city) VALUES "
               "(9, 'erin', 40, 'braga')")
    assert len(db.execute("SELECT id FROM users")) == before + 1
    db.execute("ROLLBACK")
    assert len(db.execute("SELECT id FROM users")) == before, (
        "ROLLBACK left the inserted row visible. The heap and the version store "
        "both have to be rolled back here — a real engine needs only the "
        "second, because the heap IS the version store.")

    db.execute("DELETE FROM users WHERE name = 'bob'")
    assert len(db.execute("SELECT id FROM users")) == before - 1

    try:
        db.execute("SELECT * FROM nonexistent")
        raise AssertionError("selecting from a missing table must raise")
    except DatabaseError:
        pass

    plan = db.explain(__import__("sql").parse("SELECT id FROM users"), run=False)
    assert "SeqScan" in plan, f"EXPLAIN produced:\n{plan}"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("pager.py", "slotted pages, and stable slot ids", check_slotted_page),
    ("pager.py", "buffer pool: LRU, dirty pages, pins", check_buffer_pool),
    ("btree.py", "insert, split, and the root growing", check_btree_basics),
    ("btree.py", "range scans along the leaf chain", check_btree_split_and_range),
    ("btree.py", "delete: borrow, merge, shrink", check_btree_delete),
    ("wal.py", "commit is a log write", check_wal_commit),
    ("wal.py", "redo the losers, then undo them", check_wal_recovery),
    ("wal.py", "the write-ahead rule, and checkpoints",
     check_wal_rule_and_checkpoints),
    ("mvcc.py", "snapshots and version visibility", check_mvcc_visibility),
    ("mvcc.py", "which anomaly each level admits", check_mvcc_anomalies),
    ("mvcc.py", "vacuum, and the horizon that pins it", check_mvcc_vacuum),
    ("sql.py", "tokeniser: longest match, then classify", check_tokenizer),
    ("sql.py", "precedence climbing and every statement", check_parser),
    ("executor.py", "the pull model, and what blocks it", check_iterator_model),
    ("executor.py", "joins, aggregates, distinct", check_joins_and_aggregates),
    ("planner.py", "selectivity, cost, and the crossover", check_cost_model),
    ("planner.py", "index vs scan, and predicate pushdown",
     check_planner_choices),
    ("database.py", "SQL end to end", check_database),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}Database Engine From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue

        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you built a database.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the database templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import os
import pathlib
import random
import shutil
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def tmpdir() -> str:
    return tempfile.mkdtemp(prefix="dbfs-check-")


# ---------------------------------------------------------------------------
# Steps 1-2: pager.py
# ---------------------------------------------------------------------------

def check_pager_roundtrip() -> None:
    from pager import PAGE_SIZE, Pager

    path = os.path.join(tmpdir(), "p.db")
    p = Pager(path)
    pages = [p.allocate() for _ in range(5)]
    assert pages == [1, 2, 3, 4, 5], f"allocate() should hand out 1, 2, 3...; got {pages} (page 0 is the header)"
    for n in pages:
        p.write(n, bytes([n]) * PAGE_SIZE)
    p.set_meta({"root": 3})
    try:
        p.write(1, b"short")
        raise AssertionError("write() accepted a page that is not exactly page_size bytes")
    except ValueError:
        pass
    p.close()
    assert os.path.getsize(path) == 6 * PAGE_SIZE, f"file should be 6 pages, is {os.path.getsize(path)} bytes"
    q = Pager(path)
    assert q.num_pages == 6
    assert q.get_meta() == {"root": 3}, "metadata did not survive reopen"
    for n in pages:
        assert q.read(n) == bytes([n]) * PAGE_SIZE, f"page {n} did not survive close/reopen: flush() must write dirty pages"


def check_pager_cache() -> None:
    from pager import PAGE_SIZE, Pager

    path = os.path.join(tmpdir(), "c.db")
    p = Pager(path, cache_pages=3)
    pages = [p.allocate() for _ in range(8)]
    for n in pages:
        p.write(n, bytes([n]) * PAGE_SIZE)
    # 8 dirty pages through a 3-page cache: evicted dirty pages must be written back
    for n in pages:
        assert p.read(n) == bytes([n]) * PAGE_SIZE, (
            f"page {n} lost after eviction: a dirty page must be written to disk before it is dropped")
    hits_before = p.cache_hits
    p.read(pages[-1])
    assert p.cache_hits == hits_before + 1, "reading the most recently used page should be a cache hit"
    p.read(pages[-3]), p.read(pages[-2]), p.read(pages[-1])
    reads = p.disk_reads
    p.read(pages[0])
    assert p.disk_reads == reads + 1, "reading a page evicted long ago should go to disk"
    assert len(p._cache) <= 3, f"cache holds {len(p._cache)} pages, capacity is 3"


# ---------------------------------------------------------------------------
# Steps 3-6: btree.py
# ---------------------------------------------------------------------------

def _tree(cache_pages=64):
    from btree import BTree
    from pager import Pager
    path = os.path.join(tmpdir(), "t.db")
    return BTree(Pager(path, cache_pages=cache_pages)), path


def check_btree_basic() -> None:
    t, _ = _tree()
    assert t.get(b"missing") is None
    t.put(b"b", b"2")
    t.put(b"a", b"1")
    t.put(b"c", b"3")
    assert (t.get(b"a"), t.get(b"b"), t.get(b"c")) == (b"1", b"2", b"3")
    t.put(b"b", b"20")
    assert t.get(b"b") == b"20", "put() on an existing key must overwrite, not add a duplicate"
    assert list(t.scan()) == [(b"a", b"1"), (b"b", b"20"), (b"c", b"3")]


def check_btree_splits() -> None:
    t, _ = _tree()
    rng = random.Random(3)
    keys = [f"k{i:06d}".encode() for i in range(6000)]
    rng.shuffle(keys)
    for k in keys:
        t.put(k, k[::-1])
    for k in rng.sample(keys, 500):
        assert t.get(k) == k[::-1], f"{k!r} lost after splits"
    got = [k for k, _ in t.scan()]
    assert got == sorted(keys), "scan() is not in key order, or keys were lost in a split"
    h = t.height()
    assert 2 <= h <= 4, f"6000 small keys in 4 KB pages should give height 2-4, got {h}"
    t.pager.disk_reads = t.pager.cache_hits = 0
    t.get(keys[0])
    touched = t.pager.disk_reads + t.pager.cache_hits
    assert touched == h, f"one lookup read {touched} pages; it should read exactly height ({h})"


def check_btree_scan_delete() -> None:
    t, _ = _tree()
    for i in range(3000):
        t.put(f"{i:05d}".encode(), b"v")
    rng = [k for k, _ in t.scan(b"01000", b"01010")]
    assert rng == [f"{i:05d}".encode() for i in range(1000, 1010)], f"scan(lo, hi) wrong: {rng[:3]}..."
    assert t.delete(b"01005") is True and t.delete(b"01005") is False
    assert t.get(b"01005") is None
    assert len(list(t.scan(b"01000", b"01010"))) == 9
    for i in range(0, 3000, 2):
        t.delete(f"{i:05d}".encode())
    left = [k for k, _ in t.scan()]
    assert left == [f"{i:05d}".encode() for i in range(1, 3000, 2) if i != 1005], "deletes corrupted the tree"


def check_btree_variable_size() -> None:
    """Limit case: split by count fails when big entries cluster in one half."""
    t, path = _tree()
    rng = random.Random(11)
    ref = {}
    for i in range(3000):
        k = f"{rng.randrange(10**6):07d}".encode()
        v = bytes(rng.choice([1, 3, 500, 510]))
        t.put(k, v)
        ref[k] = v
    assert list(t.scan()) == sorted(ref.items()), "variable-size entries corrupted the tree"
    # Deterministic worst case: large entries sort first, small ones after, then one more
    # large one. Splitting at n//2 entries puts 8 large entries (> 4 KB) in the left half.
    w, _ = _tree()
    for i in range(7):
        w.put(f"a{i:02d}".encode(), b"L" * 510)
    for i in range(20):
        w.put(f"z{i:02d}".encode(), b"s")
    w.put(b"a07", b"L" * 510)
    assert [k for k, _ in w.scan()][:8] == [f"a{i:02d}".encode() for i in range(8)], (
        "large entries clustered in one half were lost: split where the BYTES cross half, not the count")
    t.pager.close()
    from btree import BTree
    from pager import Pager
    t2 = BTree(Pager(path))
    assert list(t2.scan()) == sorted(ref.items()), "tree did not survive close/reopen (is the root in metadata?)"


# ---------------------------------------------------------------------------
# Steps 7-10: wal.py
# ---------------------------------------------------------------------------

def check_wal_framing() -> None:
    from wal import WAL, read_records

    path = os.path.join(tmpdir(), "w.log")
    w = WAL(path)
    recs = [{"t": "put", "tx": i, "k": "6b", "v": "76" * i} for i in range(20)]
    for r in recs:
        w.append(r)
    w.sync()
    w.close()
    data = open(path, "rb").read()
    assert list(read_records(path)) == recs
    # cut the file at every byte: the result must always be an intact prefix
    for cut in range(len(data)):
        with open(path, "wb") as fh:
            fh.write(data[:cut])
        got = list(read_records(path))
        assert got == recs[:len(got)], f"cut at byte {cut}: read_records returned a non-prefix"
    # corrupt one hex digit of a value in the middle. The payload is still valid JSON, so
    # only the CRC can tell: everything from that record on must be distrusted
    mid = data.index(b'"v":"7676', len(data) // 2) + 6
    with open(path, "wb") as fh:
        fh.write(data[:mid] + b"7" + data[mid + 1:])
    got = list(read_records(path))
    assert got == recs[:len(got)] and len(got) < len(recs), (
        "a corrupted payload was accepted: compare the CRC of every payload before trusting it")


def check_commit_and_reopen() -> None:
    from wal import DurableKV

    d = tmpdir()
    db = DurableKV(d)
    t = db.begin()
    t.put(b"a", b"1")
    t.put(b"b", b"2")
    assert t.get(b"a") == b"1", "a transaction must read its own uncommitted writes"
    assert db.get(b"a") is None, "uncommitted writes must not be visible outside the transaction"
    t.commit()
    t = db.begin()
    t.delete(b"a")
    t.commit()
    t = db.begin()
    t.put(b"lost", b"x")      # never committed
    db._wal.close()           # crash: no checkpoint, no close
    db2 = DurableKV(d)
    assert db2.items() == [(b"b", b"2")], f"after crash expected only committed state, got {db2.items()}"


def check_crash_anywhere() -> None:
    """Property: truncate the log at random points; recovery yields exactly the committed prefix."""
    from wal import DurableKV, read_records

    rng = random.Random(5)
    d = tmpdir()
    db = DurableKV(d)
    states = [{}]
    for i in range(40):
        t = db.begin()
        cur = dict(states[-1])
        for _ in range(rng.randint(1, 4)):
            k = f"k{rng.randrange(15)}".encode()
            if rng.random() < 0.25:
                t.delete(k)
                cur.pop(k, None)
            else:
                v = os.urandom(rng.randint(1, 30)).hex().encode()
                t.put(k, v)
                cur[k] = v
        t.commit()
        states.append(cur)
    db._wal.close()
    log = open(os.path.join(d, "wal.log"), "rb").read()
    for cut in sorted(rng.sample(range(len(log) + 1), 120)) + [len(log)]:
        c = tmpdir()
        with open(os.path.join(c, "wal.log"), "wb") as fh:
            fh.write(log[:cut])
        commits = sum(1 for r in read_records(os.path.join(c, "wal.log")) if r["t"] == "commit")
        got = dict(DurableKV(c).items())
        assert got == states[commits], (
            f"log cut at byte {cut}: {commits} commits survive, but recovered state matches neither "
            "that prefix: are you replaying uncommitted transactions, or applying a torn tail?")


def check_checkpoint() -> None:
    from wal import DurableKV

    d = tmpdir()
    db = DurableKV(d)
    for i in range(50):
        t = db.begin()
        t.put(f"k{i}".encode(), b"v")
        t.commit()
    db.checkpoint()
    assert os.path.getsize(os.path.join(d, "wal.log")) == 0, "checkpoint must truncate the log"
    t = db.begin()
    t.put(b"after", b"cp")
    t.commit()
    db._wal.close()
    # a crashed later checkpoint left a half-written copy behind
    with open(os.path.join(d, "data.db.new"), "wb") as fh:
        fh.write(b"\x00" * 100)
    db2 = DurableKV(d)
    assert len(db2.items()) == 51 and db2.get(b"after") == b"cp", (
        "after checkpoint + crash, expected 50 checkpointed keys plus 1 from the log")
    assert not os.path.exists(os.path.join(d, "data.db.new")), "a stale data.db.new must be discarded"
    t = db2.begin()
    t.put(b"k0", b"new")
    t.commit()
    assert db2.get(b"k0") == b"new", "transaction ids after recovery must keep working"


# ---------------------------------------------------------------------------
# Steps 11-13: mvcc.py
# ---------------------------------------------------------------------------

def check_snapshot_reads() -> None:
    from mvcc import Isolation, MVCCStore

    s = MVCCStore()
    s.load({"x": 1})
    snap = s.begin(Isolation.SNAPSHOT)
    rc = s.begin(Isolation.READ_COMMITTED)
    w = s.begin()
    w.write("x", 2)
    assert snap.read("x") == 1 and rc.read("x") == 1, "nobody may see an uncommitted write (except READ_UNCOMMITTED)"
    w.commit()
    assert snap.read("x") == 1, "SNAPSHOT must keep reading the database as of its start"
    assert rc.read("x") == 2, "READ_COMMITTED must see the latest committed value at each read"
    late = s.begin(Isolation.SNAPSHOT)
    assert late.read("x") == 2
    d = s.begin()
    d.delete("x")
    d.commit()
    assert s.begin().read("x") is None and late.read("x") == 2, "a delete is a new version, not an erase"


def check_first_committer_wins() -> None:
    from mvcc import Isolation, MVCCStore, SerializationFailure

    s = MVCCStore()
    s.load({"x": 1, "y": 1})
    a, b = s.begin(Isolation.SNAPSHOT), s.begin(Isolation.SNAPSHOT)
    a.write("x", 10)
    b.write("x", 20)
    a.commit()
    try:
        b.commit()
        raise AssertionError("SNAPSHOT: two concurrent writers of the same key both committed")
    except SerializationFailure:
        pass
    assert s.snapshot()["x"] == 10 and b.status == "aborted"
    c, d = s.begin(Isolation.SNAPSHOT), s.begin(Isolation.SNAPSHOT)
    c.write("x", 1)
    d.write("y", 2)
    c.commit()
    d.commit()  # disjoint writes never conflict


def check_serializable_validation() -> None:
    from mvcc import Isolation, MVCCStore, SerializationFailure

    s = MVCCStore()
    s.load({"a": 1, "r:1": 1})
    t = s.begin(Isolation.SERIALIZABLE)
    t.read("a")
    t.write("b", 1)
    u = s.begin()
    u.write("a", 2)
    u.commit()
    try:
        t.commit()
        raise AssertionError("SERIALIZABLE committed although a key it read changed after its start")
    except SerializationFailure:
        pass
    t = s.begin(Isolation.SERIALIZABLE)
    t.scan("r:", "r:~")
    t.write("c", 1)
    u = s.begin()
    u.write("r:2", 1)  # a phantom inserted into the scanned range
    u.commit()
    try:
        t.commit()
        raise AssertionError("SERIALIZABLE ignored an insert into a range it scanned (phantom)")
    except SerializationFailure:
        pass


# ---------------------------------------------------------------------------
# Step 14: anomalies.py
# ---------------------------------------------------------------------------

EXPECTED = {
    #                      RU     RC     SI     SER
    "dirty read":          (True, False, False, False),
    "non-repeatable read": (True, True, False, False),
    "phantom":             (True, True, False, False),
    "lost update":         (True, True, False, False),
    "write skew":          (True, True, True, False),
}


def check_anomaly_matrix() -> None:
    from anomalies import ANOMALIES
    from mvcc import Isolation

    levels = list(Isolation)
    wrong = []
    for name, expected in EXPECTED.items():
        for level, want in zip(levels, expected):
            got = ANOMALIES[name](level)
            if got != want:
                wrong.append(f"{name} at {level.name}: {'OCCURS' if got else 'prevented'}, "
                             f"expected {'OCCURS' if want else 'prevented'}")
    assert not wrong, "\n".join(wrong) + (
        "\nIf an anomaly is 'prevented' at a weak level, your schedule may let one transaction "
        "see the other's write before acting (e.g. a dirty read hiding a write skew): "
        "do all the reads before any write.")


# ---------------------------------------------------------------------------
# Steps 15-17: table.py
# ---------------------------------------------------------------------------

def _users(cls):
    from mvcc import MVCCStore
    s = MVCCStore()
    users = cls(s, "users", "id", indexes=("city",))
    t = s.begin()
    for i in range(600):
        users.insert(t, {"id": i, "name": f"u{i}", "city": ["Madrid", "Lyon", "Oslo"][i % 3]})
    t.commit()
    return s, users


def check_table_index() -> None:
    from table import Table

    s, users = _users(Table)
    t = s.begin()
    try:
        users.insert(t, {"id": 3, "name": "dup", "city": "Rome"})
        raise AssertionError("insert accepted a duplicate primary key")
    except KeyError:
        pass
    users.update(t, 4, {"city": "Lisbon"})
    users.delete(t, 5)
    t.commit()
    r = s.begin()
    users.keys_touched = 0
    by_index = users.find(r, "city", "Lisbon")
    touched_index = users.keys_touched
    users.keys_touched = 0
    by_scan = [u for u in users.find(r, "name", "u4")]
    touched_scan = users.keys_touched
    assert [u["id"] for u in by_index] == [4], f"index lookup returned {by_index}"
    assert [u["id"] for u in by_scan] == [4]
    assert touched_index <= 2 and touched_scan >= 599, (
        f"index lookup touched {touched_index} keys, full scan {touched_scan}: the index is not being used")
    madrid = users.find(r, "city", "Madrid")
    assert len(madrid) == 200 and all(u["city"] == "Madrid" for u in madrid)
    assert all(u["id"] != 5 for u in users.find(r, "city", "Lyon")), "deleted row still in the index"


def check_table_atomic() -> None:
    from table import Table

    s, users = _users(Table)
    t = s.begin()
    users.update(t, 1, {"city": "Lisbon"})
    t.abort()  # e.g. the application raised halfway through
    r = s.begin()
    assert users.find(r, "city", "Lisbon") == [], "aborted update left an index entry behind"
    assert [u["id"] for u in users.find(r, "city", "Lyon")][:1] == [1], "aborted update removed the old index entry"


def check_async_index() -> None:
    from table import AsyncIndexTable

    s, users = _users(AsyncIndexTable)
    users.propagate()
    assert users.lag == 0
    t = s.begin()
    users.update(t, 1, {"city": "Lisbon"})
    t.commit()
    assert users.lag > 0, "an async index must queue the change, not apply it in the transaction"
    r = s.begin()
    assert users.find(r, "city", "Lisbon") == [], "the new value should not be visible through the index yet"
    stale = [u for u in users.find(r, "city", "Lyon") if u["id"] == 1]
    assert stale and stale[0]["city"] == "Lyon", (
        "before propagation the index should still return row 1 under its OLD value: that stale read is the trade")
    users.propagate()
    r = s.begin()
    assert [u["id"] for u in users.find(r, "city", "Lisbon")] == [1]
    assert all(u["id"] != 1 for u in users.find(r, "city", "Lyon"))


# ---------------------------------------------------------------------------
# Step 18: the MVCC version store on the B+tree
# ---------------------------------------------------------------------------

def check_mvcc_btree_backed() -> None:
    from mvcc import MVCCStore, TOMBSTONE, _enc, _dec

    # The version index is keyed by _enc(key), and the B+tree answers a range query by
    # comparing those encoded bytes. That only works if _enc is order-preserving AND
    # prefix-free: if two keys' encodings compare "one is a prefix of the other", a scan
    # splits or bounds them wrongly. A naive `tag + raw` encoding is order-preserving too,
    # so no assertion through the scan/read API can catch a missing 0x00 escape — assert
    # the encoding directly instead.
    tricky_str = ["", "\x00", "a\x00", "a\x00b", "\x00\x00", "\x00\x00\x00",
                  "a\x00\x00b", "héllo", "日本語", "z"]
    tricky_bytes = [b"", b"\x00", b"a\x00", b"a\x00b", b"\x00\x00",
                    b"k\x00", b"\xff\x00\xfe"]
    for k in tricky_str:
        enc = _enc(k)
        assert isinstance(enc, (bytes, bytearray)), f"_enc({k!r}) returned {type(enc).__name__}, not bytes"
        dec = _dec(enc)
        assert dec == k and type(dec) is str, f"round-trip broke for str key {k!r}: got {dec!r}"
    for k in tricky_bytes:
        enc = _enc(k)
        assert isinstance(enc, (bytes, bytearray)), f"_enc({k!r}) returned {type(enc).__name__}, not bytes"
        dec = _dec(enc)
        assert dec == k and type(dec) is bytes, f"round-trip broke for bytes key {k!r}: got {dec!r}"

    # Order-preserving: sorting the keys must give the same sequence as sorting their
    # encodings, within each key type (a tag byte keeps str and bytes apart).
    for keys in (tricky_str, tricky_bytes, [f"row:{i:04d}" for i in range(20)]):
        by_key = sorted(keys)
        by_enc = sorted(keys, key=_enc)
        assert by_key == by_enc, (
            f"_enc is not order-preserving: sorted(keys)={by_key!r} but sorted by encoding={by_enc!r}")

    # Prefix-free: no encoded key may be a byte-prefix of another (and no two keys may
    # collide). This is exactly what forces the 0x00 escape and the 0x00 0x00 terminator.
    prefix_set = ["a", "ab", "a\x00", "a\x00b", b"k\x00"]
    encs = [_enc(k) for k in prefix_set]
    assert len(set(encs)) == len(encs), f"_enc is not injective: {encs!r}"
    for i in range(len(encs)):
        for j in range(len(encs)):
            if i != j:
                assert not encs[j].startswith(encs[i]), (
                    f"_enc({prefix_set[i]!r})={encs[i]!r} is a prefix of "
                    f"_enc({prefix_set[j]!r})={encs[j]!r}: the encoding is not prefix-free")

    s = MVCCStore()
    n = 600
    t = s.begin()
    for i in range(n):
        t.write(f"row:{i:04d}", i)
    t.commit()

    # The version index is a real multi-level B+tree, not an in-memory dict.
    assert s.tree.height() >= 2, (
        f"{n} committed versions fit in one leaf (height {s.tree.height()}): "
        "the version store is not going through btree.py")

    # A point read is one tree descent: it must not touch every key.
    s.reset_counters()
    r = s.begin()
    assert r.read("row:0000") == 0
    point = s.keys_touched
    assert point <= 1, f"a point read touched {point} tree entries; it should be one lookup"

    # A narrow range scan reads only the keys inside it, not the whole store.
    s.reset_counters()
    narrow_hits = r.scan("row:0100", "row:0105")
    narrow = s.keys_touched
    assert sorted(narrow_hits) == [f"row:{i:04d}" for i in range(100, 105)], f"scan returned {sorted(narrow_hits)}"
    assert narrow <= 12, f"a 5-key range scan touched {narrow} tree entries: the scan is not using the ordered index"

    # A full scan walks all the linked leaves, so its tree work scales with the data.
    s.reset_counters()
    everything = r.scan("row:", "row:~")
    full = s.keys_touched
    assert len(everything) == n, f"full scan saw {len(everything)} of {n} keys"
    assert full >= n, f"full scan touched {full} tree entries; it should read at least one per key"

    # The B+tree holds every version, tombstones included, so a delete is a new version
    # the range validation can see, not an erase.
    d = s.begin()
    d.delete("row:0000")
    d.commit()
    versions = dict(s._scan_versions(None, None))["row:0000"]
    assert len(versions) == 2 and versions[-1][1] is TOMBSTONE, (
        "the B+tree version index dropped the tombstone: a delete must be a new version")
    assert s.begin().read("row:0000") is None


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("pager.py", "pages survive close/reopen", check_pager_roundtrip),
    ("pager.py", "LRU buffer pool, dirty write-back", check_pager_cache),
    ("btree.py", "get / put / overwrite", check_btree_basic),
    ("btree.py", "splits: 6000 keys, height = pages read", check_btree_splits),
    ("btree.py", "range scan and delete", check_btree_scan_delete),
    ("btree.py", "variable-size entries, reopen", check_btree_variable_size),
    ("wal.py", "framing: torn and corrupt records", check_wal_framing),
    ("wal.py", "commit, crash, reopen", check_commit_and_reopen),
    ("wal.py", "crash at 120 random points", check_crash_anywhere),
    ("wal.py", "checkpoint and crashed checkpoint", check_checkpoint),
    ("mvcc.py", "snapshot vs read-committed reads", check_snapshot_reads),
    ("mvcc.py", "first committer wins", check_first_committer_wins),
    ("mvcc.py", "serializable: read and range validation", check_serializable_validation),
    ("anomalies.py", "anomaly x isolation-level matrix", check_anomaly_matrix),
    ("table.py", "primary key, secondary index vs scan", check_table_index),
    ("table.py", "index changes roll back with the row", check_table_atomic),
    ("table.py", "async index: the stale-read window", check_async_index),
    ("mvcc.py", "version store on the B+tree: point vs range work", check_mvcc_btree_backed),
]


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
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Database From Scratch — progress check{RESET}")
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
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built a small database.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

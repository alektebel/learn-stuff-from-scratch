"""
Pager — pages, a file, and a buffer pool. Complete Solution.

Everything above this file thinks in rows and queries. Everything below it is a
file and a disk. The pager is the translation, and almost every design decision
in a database is downstream of one fact: reading 4 KB costs the same as reading
4 bytes, so the unit of everything is a PAGE.

DESIGN DECISION — fixed-size pages, or variable-size records on disk?
  Variable-size is the obvious encoding: write each row where it fits. It is
  also unworkable. Updating a row to be one byte longer means moving everything
  after it; free space fragments into unusable slivers; and nothing can be
  addressed by arithmetic, so every pointer becomes a byte offset that changes
  whenever anything before it does.
  CHOSEN: fixed-size pages (4096 bytes here, as in PostgreSQL and SQLite).
  Page N lives at byte N * PAGE_SIZE, so addressing is multiplication. Rows are
  variable-size WITHIN a page, using a slot directory — which is where the
  variable-size problem gets solved, at a scale small enough to solve it.
  REJECTED: a log-structured layout with no in-place updates. Legitimate, and
  it is what an LSM tree does — see the extension at the end of btree.py.

DESIGN DECISION — where does the free space inside a page go?
  Rows are variable length and get deleted, so a page needs its own allocator.
  CHOSEN: the SLOTTED PAGE. A header at the front, an array of (offset, length)
  slots growing forwards, and row bytes growing backwards from the end. They
  meet in the middle, and "is there room" is one subtraction. Deleting a row
  frees its slot without moving anything; the slot ID stays valid, which is what
  lets an index point at (page, slot) and survive a neighbour being deleted.
  REJECTED: packing rows end to end with no directory. Compact, and then a
  delete invalidates every index entry after it.

DESIGN DECISION — how big is the buffer pool, and what does it evict?
  The pool is what makes a database faster than a file. Its size is the single
  most consequential knob in any real deployment.
  CHOSEN: LRU, because it is what you would write first and because its FAILURE
  is the lesson. The demo below shows a sequential scan larger than the pool
  evicting the entire working set to cache pages it will never look at again.
  Real systems answer this with LRU-K, clock-sweep, or a scan-resistant ring
  buffer; you cannot appreciate why until you have watched plain LRU do it.
"""

import io
import os
import struct
from typing import Dict, List, Optional, Tuple

PAGE_SIZE = 4096
HEADER = struct.Struct("<HHHH")        # page_type, slot_count, free_start, free_end

PAGE_FREE = 0
PAGE_LEAF = 1
PAGE_INTERNAL = 2
PAGE_OVERFLOW = 3

SLOT = struct.Struct("<HH")            # offset, length


class Page:
    """One slotted page. Bytes in, bytes out — nothing here knows what a row is."""

    __slots__ = ("page_id", "data", "dirty", "pins")

    def __init__(self, page_id: int, data: Optional[bytearray] = None):
        self.page_id = page_id
        self.data = data if data is not None else bytearray(PAGE_SIZE)
        self.dirty = False
        self.pins = 0
        if data is None:
            self.init(PAGE_LEAF)

    # -- header -------------------------------------------------------------

    def init(self, page_type: int) -> None:
        HEADER.pack_into(self.data, 0, page_type, 0, HEADER.size, PAGE_SIZE)
        self.dirty = True

    @property
    def header(self) -> Tuple[int, int, int, int]:
        return HEADER.unpack_from(self.data, 0)

    def _set_header(self, page_type: int, slot_count: int,
                    free_start: int, free_end: int) -> None:
        HEADER.pack_into(self.data, 0, page_type, slot_count, free_start, free_end)
        self.dirty = True

    @property
    def page_type(self) -> int:
        return self.header[0]

    @page_type.setter
    def page_type(self, value: int) -> None:
        _, slots, start, end = self.header
        self._set_header(value, slots, start, end)

    @property
    def slot_count(self) -> int:
        return self.header[1]

    @property
    def free_space(self) -> int:
        """Bytes available for ONE more record, slot directory entry included.

        The slot array grows forwards from free_start and the records grow
        backwards from free_end. Their gap is the free space, minus the slot
        this record would need.
        """
        _, _, start, end = self.header
        return max(0, end - start - SLOT.size)

    # -- records ------------------------------------------------------------

    def insert(self, record: bytes) -> Optional[int]:
        """Append a record; return its slot id, or None if it does not fit."""
        page_type, slots, start, end = self.header
        if len(record) > self.free_space:
            return None
        end -= len(record)
        self.data[end:end + len(record)] = record
        SLOT.pack_into(self.data, start, end, len(record))
        self._set_header(page_type, slots + 1, start + SLOT.size, end)
        return slots

    def read(self, slot: int) -> Optional[bytes]:
        """None means the slot was deleted — a tombstone, not an error."""
        if not 0 <= slot < self.slot_count:
            raise IndexError(f"slot {slot} out of range on page {self.page_id}")
        offset, length = SLOT.unpack_from(self.data, HEADER.size + slot * SLOT.size)
        if length == 0:
            return None
        return bytes(self.data[offset:offset + length])

    def delete(self, slot: int) -> None:
        """Zero the slot's length. The bytes stay until the page is compacted.

        The slot ITSELF is not removed. An index entry pointing at (page, 7)
        must keep meaning slot 7 after slot 3 is deleted, so slot ids can never
        be renumbered by a delete. This is why a database's "row id" survives
        its neighbours and why VACUUM is a separate, deliberate operation.
        """
        page_type, slots, start, end = self.header
        if not 0 <= slot < slots:
            raise IndexError(f"slot {slot} out of range")
        offset, _ = SLOT.unpack_from(self.data, HEADER.size + slot * SLOT.size)
        SLOT.pack_into(self.data, HEADER.size + slot * SLOT.size, offset, 0)
        self.dirty = True

    def records(self) -> List[Tuple[int, bytes]]:
        out = []
        for slot in range(self.slot_count):
            record = self.read(slot)
            if record is not None:
                out.append((slot, record))
        return out

    def compact(self) -> int:
        """Reclaim the dead bytes. Returns bytes recovered.

        Rewrites the live records against the end of the page and rebuilds the
        slot array — keeping every live slot at its ORIGINAL id, because indexes
        point at those ids. This is VACUUM at page scale, and the reason it
        cannot simply run all the time is that it needs the page exclusively.
        """
        live = [(slot, self.read(slot)) for slot in range(self.slot_count)]
        before = self.free_space
        page_type = self.page_type
        count = self.slot_count
        self.data[HEADER.size:] = bytes(PAGE_SIZE - HEADER.size)
        end = PAGE_SIZE
        start = HEADER.size
        for slot, record in live:
            position = HEADER.size + slot * SLOT.size
            if record is None:
                SLOT.pack_into(self.data, position, 0, 0)
            else:
                end -= len(record)
                self.data[end:end + len(record)] = record
                SLOT.pack_into(self.data, position, end, len(record))
            start = max(start, position + SLOT.size)
        self._set_header(page_type, count, start, end)
        return self.free_space - before


class DiskManager:
    """The file. Reads and writes whole pages, counts every one of them."""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.file = open(path, "r+b") if path and os.path.exists(path) else (
            open(path, "w+b") if path else io.BytesIO())
        self.stats = {"reads": 0, "writes": 0, "allocations": 0, "fsyncs": 0}

    @property
    def num_pages(self) -> int:
        self.file.seek(0, os.SEEK_END)
        return self.file.tell() // PAGE_SIZE

    def read_page(self, page_id: int) -> bytearray:
        self.file.seek(page_id * PAGE_SIZE)
        raw = self.file.read(PAGE_SIZE)
        self.stats["reads"] += 1
        if len(raw) < PAGE_SIZE:
            raw = raw + bytes(PAGE_SIZE - len(raw))
        return bytearray(raw)

    def write_page(self, page_id: int, data: bytes) -> None:
        self.file.seek(page_id * PAGE_SIZE)
        self.file.write(data)
        self.stats["writes"] += 1

    def allocate(self) -> int:
        """Extend the file by one page — INITIALISED, not zeroed.

        A page of zeros is not an empty page. Its header would read
        free_start=0 and free_end=0, so free_space computes as negative and the
        first insert silently refuses. Every page that exists must carry a
        valid header from the moment it exists.
        """
        page_id = self.num_pages
        blank = Page(page_id)
        blank.init(PAGE_FREE)
        self.write_page(page_id, blank.data)
        self.stats["allocations"] += 1
        return page_id

    def sync(self) -> None:
        self.file.flush()
        if hasattr(self.file, "fileno"):
            os.fsync(self.file.fileno())
        self.stats["fsyncs"] += 1

    def close(self) -> None:
        self.file.close()


class BufferPool:
    """A fixed number of pages held in memory, with LRU eviction.

    This is the whole reason a database is faster than a file, and the reason a
    database with too little memory falls off a cliff rather than degrading
    gracefully — see hit_rate against pool size in the demo.
    """

    def __init__(self, disk: DiskManager, capacity: int = 16):
        self.disk = disk
        self.capacity = capacity
        self.frames: Dict[int, Page] = {}
        self.clock = 0
        self.access: Dict[int, int] = {}
        self.stats = {"hits": 0, "misses": 0, "evictions": 0,
                      "dirty_writebacks": 0, "pinned_skips": 0}

    def fetch(self, page_id: int) -> Page:
        self.clock += 1
        if page_id in self.frames:
            self.stats["hits"] += 1
            self.access[page_id] = self.clock
            return self.frames[page_id]

        self.stats["misses"] += 1
        if len(self.frames) >= self.capacity:
            self._evict()
        page = Page(page_id, self.disk.read_page(page_id))
        self.frames[page_id] = page
        self.access[page_id] = self.clock
        return page

    def new_page(self, page_type: int = PAGE_LEAF) -> Page:
        page_id = self.disk.allocate()
        if len(self.frames) >= self.capacity:
            self._evict()
        page = Page(page_id)
        page.init(page_type)
        self.frames[page_id] = page
        self.access[page_id] = self.clock
        return page

    def _evict(self) -> None:
        """Evict the least recently used UNPINNED page.

        The pin is not a nicety. A B-tree split holds a parent and two children
        at once; evicting one mid-split writes a half-updated tree to disk and
        the database is corrupt in a way no later operation can detect.
        """
        victims = sorted((used, pid) for pid, used in self.access.items()
                         if self.frames[pid].pins == 0)
        if not victims:
            self.stats["pinned_skips"] += 1
            self.capacity += 1        # grow rather than corrupt; a real pool blocks
            return
        _, page_id = victims[0]
        page = self.frames.pop(page_id)
        del self.access[page_id]
        self.stats["evictions"] += 1
        if page.dirty:
            self.disk.write_page(page_id, page.data)
            self.stats["dirty_writebacks"] += 1

    def flush(self, page_id: Optional[int] = None) -> None:
        targets = [page_id] if page_id is not None else list(self.frames)
        for pid in targets:
            page = self.frames.get(pid)
            if page and page.dirty:
                self.disk.write_page(pid, page.data)
                page.dirty = False

    @property
    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return self.stats["hits"] / total if total else 0.0


class pinned:
    """`with pinned(pool, page):` — hold a page across an operation."""

    def __init__(self, pool: BufferPool, *pages: Page):
        self.pages = pages

    def __enter__(self):
        for page in self.pages:
            page.pins += 1
        return self.pages[0] if len(self.pages) == 1 else self.pages

    def __exit__(self, *exc):
        for page in self.pages:
            page.pins -= 1
        return False


def _demo() -> None:
    print("=" * 72)
    print("PAGER — pages, a file, and the memory in front of it")
    print("=" * 72)

    print("\n1. A slotted page: variable-size rows in a fixed-size box")
    print("-" * 72)
    page = Page(0)
    print(f"  page size {PAGE_SIZE}, header {HEADER.size}, "
          f"usable {page.free_space + SLOT.size}")
    for name in (b"alice", b"bob", b"a much longer row than the others"):
        slot = page.insert(name)
        print(f"  insert {len(name):>3} bytes -> slot {slot}, "
              f"{page.free_space} free")

    page.delete(1)
    print(f"  delete slot 1 -> read(1) is {page.read(1)}, and slot 2 is still "
          f"{page.read(2)[:12]!r}...")
    print("  Deleting did NOT renumber slot 2. An index entry pointing at slot 2")
    print("  must survive its neighbour being deleted, which is why slot ids are")
    print("  stable and why reclaiming the bytes is a separate operation:")
    print(f"  free before compaction {page.free_space}, "
          f"recovered {page.compact()} bytes, now {page.free_space}")

    print("\n2. How many rows fit, and why row width is a storage decision")
    print("-" * 72)
    print(f"    {'row bytes':>10}{'rows/page':>12}{'overhead':>12}")
    for width in (16, 64, 200, 1000, 2000, 2100):
        p = Page(0)
        n = 0
        while p.insert(bytes(width)) is not None:
            n += 1
        used = n * (width + SLOT.size) + HEADER.size
        print(f"    {width:>10}{n:>12}{1 - n * width / PAGE_SIZE:>11.1%}")
    print("  Look at the last two rows. One hundred extra bytes takes a page")
    print("  from two rows to one and its waste from 2% to 49%, because rows do")
    print("  not span pages. Row width interacts with page size in STEPS, and a")
    print("  schema change that adds a column can double your storage.")

    print("\n3. The buffer pool is the whole speedup")
    print("-" * 72)
    disk = DiskManager()
    for _ in range(200):
        disk.allocate()

    print(f"    {'pool pages':>11}{'hit rate':>10}{'disk reads':>12}")
    import random
    for capacity in (4, 8, 16, 32, 64, 128):
        d = DiskManager()
        for _ in range(200):
            d.allocate()
        d.stats["reads"] = 0
        pool = BufferPool(d, capacity)
        rng = random.Random(7)
        for _ in range(4000):
            # Zipf-ish: most traffic on a small hot set, as real workloads are
            pool.fetch(int(200 * (rng.random() ** 3)))
        print(f"    {capacity:>11}{pool.hit_rate:>9.1%}{d.stats['reads']:>12}")
    print("  Doubling memory does not double the hit rate — it moves you along a")
    print("  curve whose knee is set by the working set, not by the data size.")

    print("\n4. The failure that motivates every real eviction policy")
    print("-" * 72)
    d = DiskManager()
    for _ in range(500):
        d.allocate()
    pool = BufferPool(d, 32)
    rng = random.Random(1)                      # ONE generator, drawn from
    for _ in range(2000):                       # build a hot working set
        pool.fetch(rng.randint(0, 20))
    hits_before = pool.stats["hits"]
    for _ in range(500):
        pool.fetch(rng.randint(0, 20))
    warm = (pool.stats["hits"] - hits_before) / 500
    resident = sorted(pool.frames)[:5]

    # A reporting query that scans the whole table, the way a real one runs:
    # periodically, interleaved with the transactional workload.
    hot_hits = hot_total = 0
    after_scan = None
    for _ in range(5):
        for page_id in range(500):
            pool.fetch(page_id)
        if after_scan is None:
            after_scan = sorted(pool.frames)[:5]
        before = pool.stats["hits"]
        for _ in range(100):
            pool.fetch(rng.randint(0, 20))
        hot_hits += pool.stats["hits"] - before
        hot_total += 100
    recovered = hot_hits / hot_total

    print(f"  hot working set warm at {warm:.1%} hit rate, resident pages "
          f"{resident}")
    print(f"  after a 500-page scan, resident pages are {after_scan}")
    print(f"  with a scan every 100 transactions the hot set runs at "
          f"{recovered:.1%},")
    print(f"  down from {warm:.1%} — and the scan itself gets nothing out of the")
    print("  cache either, because it never revisits a page. Both workloads are")
    print("  worse off than if the scan had bypassed the pool entirely.")
    print("  A scan is the worst possible input to LRU: perfect recency, zero")
    print("  reuse. LRU-K, clock-sweep and scan-resistant ring buffers all exist")
    print("  because of exactly this experiment.")

    print("\n" + "=" * 72)
    print("Next: btree.py puts an ordered index on top of these pages.")
    print("=" * 72)


if __name__ == "__main__":
    _demo()

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

Learning Path:
1. Page.insert / read / delete — the slotted page, and why a delete must NOT
   renumber the surviving slots
2. Page.compact — reclaim the dead bytes, keeping every live slot at its
   original id
3. BufferPool.fetch / _evict — LRU over a fixed number of frames
4. Measure the hit rate against pool size, then watch a sequential scan destroy
   it — that experiment is the reason LRU-K and clock-sweep exist
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
        raise NotImplementedError

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
        raise NotImplementedError

    # -- records ------------------------------------------------------------

    def insert(self, record: bytes) -> Optional[int]:
        """Append a record; return its slot id, or None if it does not fit."""
        raise NotImplementedError

    def read(self, slot: int) -> Optional[bytes]:
        """None means the slot was deleted — a tombstone, not an error."""
        raise NotImplementedError

    def delete(self, slot: int) -> None:
        """Zero the slot's length. The bytes stay until the page is compacted.

        The slot ITSELF is not removed. An index entry pointing at (page, 7)
        must keep meaning slot 7 after slot 3 is deleted, so slot ids can never
        be renumbered by a delete. This is why a database's "row id" survives
        its neighbours and why VACUUM is a separate, deliberate operation.
        """
        raise NotImplementedError

    def records(self) -> List[Tuple[int, bytes]]:
        raise NotImplementedError

    def compact(self) -> int:
        """Reclaim the dead bytes. Returns bytes recovered.

        Rewrites the live records against the end of the page and rebuilds the
        slot array — keeping every live slot at its ORIGINAL id, because indexes
        point at those ids. This is VACUUM at page scale, and the reason it
        cannot simply run all the time is that it needs the page exclusively.
        """
        raise NotImplementedError


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
        raise NotImplementedError

    def new_page(self, page_type: int = PAGE_LEAF) -> Page:
        raise NotImplementedError

    def _evict(self) -> None:
        """Evict the least recently used UNPINNED page.

        The pin is not a nicety. A B-tree split holds a parent and two children
        at once; evicting one mid-split writes a half-updated tree to disk and
        the database is corrupt in a way no later operation can detect.
        """
        raise NotImplementedError

    def flush(self, page_id: Optional[int] = None) -> None:
        raise NotImplementedError

    @property
    def hit_rate(self) -> float:
        raise NotImplementedError


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
    """Once the checks pass, write a demo that PRINTS these four things:

    1. A slotted page filling up. Insert three rows of different sizes, delete
       the middle one, and show that the LAST one still reads back from its
       original slot. Then compact and show the bytes come back.

    2. Rows per page for widths 16, 64, 200, 1000, 2000 and 2100 bytes, with
       the wasted fraction. The last two are the point: one hundred extra
       bytes takes a page from two rows to one and its waste from 2% to 49%,
       because rows do not span pages.

    3. Hit rate against pool size on a skewed workload — most traffic to a
       small hot set, as real workloads are. Doubling memory does not double
       the hit rate; find the knee.

    4. The experiment that motivates every real eviction policy. Warm a hot
       working set to ~100%, then interleave a full-table scan with the
       transactional traffic and measure the hot hit rate again. The scan
       evicts everything valuable to cache pages it will never revisit, and
       gets nothing itself. Use ONE random generator for the whole demo —
       constructing random.Random(1) inside the loop returns the same number
       every time and quietly turns this experiment into a no-op.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

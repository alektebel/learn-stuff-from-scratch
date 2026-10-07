"""
Pager — fixed-size pages on disk behind an LRU buffer pool
==========================================================

Every disk-based database reads and writes the file in fixed-size pages, never in rows.
The pager is the only code that touches the file; everything above it asks for page N.

Page 0 is the header: it holds a small JSON metadata dict (the B-tree keeps its root
page number there). Pages 1.. are data pages.
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict

PAGE_SIZE = 4096
MAGIC = b"DBFS"


class Pager:
    def __init__(self, path: str, page_size: int = PAGE_SIZE, cache_pages: int = 64):
        self.path = path
        self.page_size = page_size
        self.cache_pages = cache_pages
        self._cache: OrderedDict[int, bytearray] = OrderedDict()  # page_no -> data, LRU order
        self._dirty: set[int] = set()
        self.disk_reads = self.disk_writes = self.cache_hits = 0
        exists = os.path.exists(path) and os.path.getsize(path) > 0
        self._fh = open(path, "r+b" if exists else "w+b")
        if exists:
            size = os.path.getsize(path)
            if size % page_size:
                raise ValueError(f"{path}: size {size} is not a multiple of page_size {page_size}")
            self._num_pages = size // page_size
            header = self._read_from_disk(0)
            if header[:4] != MAGIC:
                raise ValueError(f"{path}: bad magic, not a database file")
        else:
            self._num_pages = 1
            self._write_header({})

    # -- metadata in page 0 ------------------------------------------------------------
    def _write_header(self, meta: dict) -> None:
        body = json.dumps(meta).encode()
        if len(body) + 8 > self.page_size:
            raise ValueError("metadata does not fit in the header page")
        page = bytearray(self.page_size)
        page[:4] = MAGIC
        page[4:8] = len(body).to_bytes(4, "little")
        page[8:8 + len(body)] = body
        self.write(0, bytes(page))

    def get_meta(self) -> dict:
        page = self.read(0)
        n = int.from_bytes(page[4:8], "little")
        return json.loads(page[8:8 + n]) if n else {}

    def set_meta(self, meta: dict) -> None:
        self._write_header(meta)

    # -- pages ---------------------------------------------------------------------------
    @property
    def num_pages(self) -> int:
        return self._num_pages

    def allocate(self) -> int:
        # TODO: Hand out the next page number (page 0 is the header) and make it exist: write a zero page.
        raise NotImplementedError("Pager.allocate")

    def _read_from_disk(self, page_no: int) -> bytearray:
        self._fh.seek(page_no * self.page_size)
        data = self._fh.read(self.page_size)
        self.disk_reads += 1
        if len(data) < self.page_size:  # allocated but never flushed
            data = data + bytes(self.page_size - len(data))
        return bytearray(data)

    def _write_to_disk(self, page_no: int, data: bytes) -> None:
        self._fh.seek(page_no * self.page_size)
        self._fh.write(data)
        self.disk_writes += 1

    def _evict_if_needed(self) -> None:
        # TODO: While over capacity, drop the LEAST recently used page. If it is dirty, write it to disk first, or the change is lost.
        raise NotImplementedError("Pager._evict_if_needed")

    def read(self, page_no: int) -> bytes:
        # TODO: Cache hit: count it, mark the page most-recently-used, return it. Miss: read from disk, cache it, evict if over capacity.
        raise NotImplementedError("Pager.read")

    def write(self, page_no: int, data: bytes) -> None:
        # TODO: Enforce exactly page_size bytes. Put the page in the cache as most-recently-used and remember it is dirty. Evict if needed.
        raise NotImplementedError("Pager.write")

    def flush(self) -> None:
        # TODO: Write every dirty page, then fsync. Make sure the file is num_pages * page_size long even if some pages were never dirty.
        raise NotImplementedError("Pager.flush")

    def close(self) -> None:
        self.flush()
        self._fh.close()


if __name__ == "__main__":
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "demo.db")
    p = Pager(path, cache_pages=4)
    pages = [p.allocate() for _ in range(10)]
    for n in pages:
        p.write(n, bytes([n]) * PAGE_SIZE)
    for _ in range(3):
        for n in pages[:3]:
            p.read(n)
    p.close()
    print(f"10 pages through a 4-page cache: disk writes {p.disk_writes}, cache hits {p.cache_hits}")

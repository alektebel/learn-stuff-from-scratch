"""
B+tree — an ordered index on top of the pager
=============================================

Keys and values are bytes. Every node is one page. Leaves hold (key, value) pairs and
a pointer to the next leaf, so a range scan walks sideways instead of re-descending.
Internal nodes hold separator keys and child page numbers: child i holds keys < keys[i],
the last child holds keys >= keys[-1].

Node layout (little-endian):
  byte 0      node type: 1 = leaf, 2 = internal
  bytes 1-2   number of entries n
  leaf:       bytes 3-6 next leaf page (0 = none), then n x [klen u16][key][vlen u16][value]
  internal:   bytes 3-6 first child, then n x [klen u16][key][child u32]

DESIGN DECISION - split by count or by bytes?
Splitting at n//2 entries is the textbook rule and is wrong for variable-size entries:
a node can overflow with its large entries all in one half, and that half still does
not fit in a page. Chosen: split where the cumulative byte size crosses half.

DESIGN DECISION - rebalance on delete?
Real B-trees merge or borrow when a node falls below half full. Chosen: no. A deleted
key is removed from its leaf and nothing else changes; leaves may become under-full or
empty. Lookups stay correct; space is not reclaimed. Cost stated, not hidden.
"""

from __future__ import annotations

import struct
from typing import Iterator, Optional

from pager import Pager

LEAF, INTERNAL = 1, 2
MAX_KEY = 64
MAX_VALUE = 512


def _encode_leaf(entries: list[tuple[bytes, bytes]], next_leaf: int) -> bytes:
    out = bytearray(struct.pack("<BHI", LEAF, len(entries), next_leaf))
    for k, v in entries:
        out += struct.pack("<H", len(k)) + k + struct.pack("<H", len(v)) + v
    return bytes(out)


def _encode_internal(keys: list[bytes], children: list[int]) -> bytes:
    out = bytearray(struct.pack("<BHI", INTERNAL, len(keys), children[0]))
    for k, c in zip(keys, children[1:]):
        out += struct.pack("<H", len(k)) + k + struct.pack("<I", c)
    return bytes(out)


def _decode(page: bytes):
    kind, n, first = struct.unpack_from("<BHI", page, 0)
    pos = 7
    if kind == LEAF:
        entries = []
        for _ in range(n):
            (kl,) = struct.unpack_from("<H", page, pos); pos += 2
            k = page[pos:pos + kl]; pos += kl
            (vl,) = struct.unpack_from("<H", page, pos); pos += 2
            v = page[pos:pos + vl]; pos += vl
            entries.append((bytes(k), bytes(v)))
        return LEAF, entries, first
    if kind == INTERNAL:
        keys, children = [], [first]
        for _ in range(n):
            (kl,) = struct.unpack_from("<H", page, pos); pos += 2
            keys.append(bytes(page[pos:pos + kl])); pos += kl
            (c,) = struct.unpack_from("<I", page, pos); pos += 4
            children.append(c)
        return INTERNAL, keys, children
    raise ValueError(f"corrupt node type {kind}")


def _split_point(sizes: list[int]) -> int:
    """Index i such that items[:i] and items[i:] are both non-empty and the split falls
    where the cumulative size first reaches half of the total."""
    # TODO: Walk the sizes accumulating bytes; split where the running total first reaches half the total. Both sides must be non-empty.
    raise NotImplementedError("_split_point")


class BTree:
    def __init__(self, pager: Pager):
        self.pager = pager
        meta = pager.get_meta()
        if "root" in meta:
            self.root = meta["root"]
        else:
            self.root = pager.allocate()
            self._write(self.root, _encode_leaf([], 0))
            pager.set_meta({**meta, "root": self.root})

    # -- page helpers ---------------------------------------------------------------------
    def _write(self, page_no: int, body: bytes) -> None:
        if len(body) > self.pager.page_size:
            raise AssertionError("node does not fit in a page; split logic is wrong")
        self.pager.write(page_no, body + bytes(self.pager.page_size - len(body)))

    def _read(self, page_no: int):
        return _decode(self.pager.read(page_no))

    def _fits(self, body: bytes) -> bool:
        return len(body) <= self.pager.page_size

    # -- lookups --------------------------------------------------------------------------
    def _find_leaf(self, key: bytes):
        """Descend from the root; return (leaf page, its entries, its next-leaf pointer)."""
        # TODO: From the root, follow child i where i is the number of separator keys <= key. Stop at a leaf; return (page, entries, next).
        raise NotImplementedError("BTree._find_leaf")

    def get(self, key: bytes) -> Optional[bytes]:
        # TODO: Find the leaf, then look for the exact key in its entries.
        raise NotImplementedError("BTree.get")

    def scan(self, lo: Optional[bytes] = None, hi: Optional[bytes] = None) -> Iterator[tuple[bytes, bytes]]:
        """Yield (key, value) with lo <= key < hi, in key order."""
        # TODO: Find the leaf where lo would live, then walk entries and follow next-leaf pointers until a key >= hi.
        raise NotImplementedError("BTree.scan")

    def height(self) -> int:
        # TODO: Count levels by following the first child down to a leaf.
        raise NotImplementedError("BTree.height")

    # -- insert ---------------------------------------------------------------------------
    def put(self, key: bytes, value: bytes) -> None:
        # TODO: Insert recursively from the root. If the ROOT splits, allocate a new internal root with one separator and two children, and store its page in the pager metadata.
        raise NotImplementedError("BTree.put")

    def _insert(self, page_no: int, key: bytes, value: bytes):
        # TODO: Leaf: insert or overwrite in order; if the encoded node does not fit, split by bytes and return (first key of right leaf, right page). Internal: recurse, insert the returned separator and child, split if needed: the middle key moves UP and stays in neither half.
        raise NotImplementedError("BTree._insert")

    # -- delete ---------------------------------------------------------------------------
    def delete(self, key: bytes) -> bool:
        # TODO: Remove the key from its leaf and rewrite the leaf. No rebalancing (see the design decision above). Return whether the key existed.
        raise NotImplementedError("BTree.delete")


if __name__ == "__main__":
    import os
    import random
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "bt.db")
    t = BTree(Pager(path, cache_pages=256))
    keys = [f"user:{i:07d}".encode() for i in range(50_000)]
    random.Random(1).shuffle(keys)
    for k in keys:
        t.put(k, b"x" * 40)
    print(f"50k keys: height {t.height()}, pages {t.pager.num_pages}")
    t.pager.disk_reads = t.pager.cache_hits = 0
    t.get(b"user:0031337")
    print(f"one lookup touched {t.pager.disk_reads + t.pager.cache_hits} pages (= height)")

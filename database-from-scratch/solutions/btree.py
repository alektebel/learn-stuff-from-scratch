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
    half, acc = sum(sizes) / 2, 0
    for i, s in enumerate(sizes):
        acc += s
        if acc >= half:
            return min(max(i + 1, 1), len(sizes) - 1)
    return len(sizes) - 1


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
        page_no = self.root
        while True:
            kind, a, b = self._read(page_no)
            if kind == LEAF:
                return page_no, a, b
            keys, children = a, b
            i = 0
            while i < len(keys) and key >= keys[i]:
                i += 1
            page_no = children[i]

    def get(self, key: bytes) -> Optional[bytes]:
        _, entries, _ = self._find_leaf(key)
        for k, v in entries:
            if k == key:
                return v
        return None

    def scan(self, lo: Optional[bytes] = None, hi: Optional[bytes] = None) -> Iterator[tuple[bytes, bytes]]:
        """Yield (key, value) with lo <= key < hi, in key order."""
        _, entries, nxt = self._find_leaf(lo if lo is not None else b"")
        while True:
            for k, v in entries:
                if lo is not None and k < lo:
                    continue
                if hi is not None and k >= hi:
                    return
                yield k, v
            if not nxt:
                return
            _, entries, nxt = self._read(nxt)

    def height(self) -> int:
        h, page_no = 1, self.root
        while True:
            kind, _, children = self._read(page_no)
            if kind == LEAF:
                return h
            h, page_no = h + 1, children[0]

    # -- insert ---------------------------------------------------------------------------
    def put(self, key: bytes, value: bytes) -> None:
        if not (0 < len(key) <= MAX_KEY) or len(value) > MAX_VALUE:
            raise ValueError(f"key must be 1..{MAX_KEY} bytes and value <= {MAX_VALUE} bytes")
        split = self._insert(self.root, key, value)
        if split is not None:  # the root split: the tree grows one level, at the top
            sep, right = split
            new_root = self.pager.allocate()
            self._write(new_root, _encode_internal([sep], [self.root, right]))
            self.root = new_root
            self.pager.set_meta({**self.pager.get_meta(), "root": new_root})

    def _insert(self, page_no: int, key: bytes, value: bytes):
        kind, a, b = self._read(page_no)
        if kind == LEAF:
            entries, nxt = a, b
            for i, (k, _) in enumerate(entries):
                if k == key:
                    entries[i] = (key, value)
                    break
            else:
                entries.append((key, value))
                entries.sort(key=lambda e: e[0])
            body = _encode_leaf(entries, nxt)
            if self._fits(body):
                self._write(page_no, body)
                return None
            i = _split_point([4 + len(k) + len(v) for k, v in entries])
            right = self.pager.allocate()
            self._write(right, _encode_leaf(entries[i:], nxt))
            self._write(page_no, _encode_leaf(entries[:i], right))
            return entries[i][0], right  # first key of the right leaf is copied up
        keys, children = a, b
        i = 0
        while i < len(keys) and key >= keys[i]:
            i += 1
        split = self._insert(children[i], key, value)
        if split is None:
            return None
        sep, new_child = split
        keys.insert(i, sep)
        children.insert(i + 1, new_child)
        body = _encode_internal(keys, children)
        if self._fits(body):
            self._write(page_no, body)
            return None
        m = min(max(_split_point([6 + len(k) for k in keys]), 1), len(keys) - 2)
        up = keys[m]  # the middle key moves up; it is NOT kept in either half
        right = self.pager.allocate()
        self._write(right, _encode_internal(keys[m + 1:], children[m + 1:]))
        self._write(page_no, _encode_internal(keys[:m], children[:m + 1]))
        return up, right

    # -- delete ---------------------------------------------------------------------------
    def delete(self, key: bytes) -> bool:
        page_no, entries, nxt = self._find_leaf(key)
        kept = [(k, v) for k, v in entries if k != key]
        if len(kept) == len(entries):
            return False
        self._write(page_no, _encode_leaf(kept, nxt))
        return True


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

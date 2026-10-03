#!/usr/bin/env python3
"""Generate a real SQLite file, so DRILL.md's hexdump exercises have ground truth.

    python3 drill_fixtures.py          # annotated dumps, ready to paste
    python3 drill_fixtures.py --raw    # bytes only

Why this exists: any model asked to produce a hexdump from memory will produce
something plausible and wrong. The SQLite file format is fully documented and
byte-exact, so an exercise built on a REAL file has an answer you can check and
an examiner that cannot drift.

The rows below are chosen to make the record format visible in one page:
a 1-byte integer, a 2-byte integer, a NULL, a short string and one long enough
to be worth measuring. Read the dump against
https://www.sqlite.org/fileformat.html — section 1.3 for the header, 1.6 for
the b-tree page, and 2.1 for the record format.
"""

import argparse
import pathlib
import sqlite3
import subprocess
import sys

DB = pathlib.Path(__file__).parent / "drill.db"
PAGE = 4096

ANNOTATIONS = {
    0: [(0, 16, 'magic: "SQLite format 3\\0"'),
        (16, 2, "page size, big-endian"),
        (18, 1, "write format (1 = legacy, 2 = WAL)"),
        (19, 1, "read format"),
        (20, 1, "reserved bytes per page"),
        (24, 4, "file change counter"),
        (28, 4, "database size in pages"),
        (32, 4, "first freelist trunk page"),
        (36, 4, "freelist page count"),
        (40, 4, "schema cookie"),
        (56, 4, "text encoding (1 = UTF-8)")],
    1: [(0, 1, "page type: 0x0d = table b-tree LEAF, 0x05 = interior"),
        (1, 2, "first freeblock offset (0 = none)"),
        (3, 2, "number of cells"),
        (5, 2, "start of the cell CONTENT area — cells grow DOWN from the end"),
        (7, 1, "fragmented free bytes"),
        (8, None, "the cell pointer array: 2 bytes per cell, growing UP")],
}


def build() -> None:
    DB.unlink(missing_ok=True)
    c = sqlite3.connect(DB)
    c.execute("PRAGMA page_size = 4096")
    c.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT, n INTEGER)")
    c.executemany("INSERT INTO t VALUES (?,?,?)", [
        (1, "ana", 7),                 # n fits in one byte
        (2, "bo", 300),                # n needs two
        (3, "cy", None),               # NULL: serial type 0, ZERO bytes of payload
        (4, "delta-delta-delta", 1),   # a string long enough to measure
    ])
    c.commit()
    c.close()


def dump(page: int, length: int = 96) -> str:
    out = subprocess.run(["od", "-A", "d", "-t", "x1",
                          "-j", str(page * PAGE), "-N", str(length), str(DB)],
                         capture_output=True, text=True)
    return out.stdout.rstrip()


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", action="store_true", help="bytes only")
    parser.add_argument("--page", type=int, default=None, help="dump one page")
    args = parser.parse_args(argv)

    build()
    pages = [args.page] if args.page is not None else [0, 1]

    if args.raw:
        for p in pages:
            print(dump(p, 128))
        return 0

    print(f"{DB.name}: {DB.stat().st_size} bytes, {DB.stat().st_size // PAGE} pages "
          f"of {PAGE}\n")
    for p in pages:
        label = "file header + page 1 (the schema table)" if p == 0 else \
                f"page {p + 1} (1-indexed), the table b-tree"
        print(f"--- page index {p} — {label} " + "-" * 20)
        print(dump(p, 96))
        for offset, size, meaning in ANNOTATIONS.get(p, []):
            span = f"{offset}..{offset + size - 1}" if size else f"{offset}.."
            print(f"    {span:>10}  {meaning}")
        print()

    print("Questions worth asking against these bytes, none of which need a lecture:")
    print("  - byte 5..6 of the b-tree page is the content-area start. Compute the")
    print("    free space yourself and say whether it is contiguous.")
    print("  - row 3 has a NULL. Find it. What is its serial type and how many")
    print("    bytes of payload does it occupy?")
    print("  - the cell pointer array is ascending or descending in KEY order?")
    print("    Check, then say what that costs an insert in the middle.")
    print("  - insert a row with a 5000-byte string and diff the file. Which page")
    print("    appeared, and what is in the first four bytes of it?")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

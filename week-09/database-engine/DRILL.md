# DRILL — database internals, adversarially

A prompt to paste into a fresh session when you want to be **examined** rather
than taught. It is the counterpart to `check.py`: the checker grades code you
wrote, this grades whether you can defend it.

Use it on a Sunday, or after finishing any file in this directory. Not before —
it is worthless as an introduction and sharp as an audit.

Related: [`../../TODO.md`](../../TODO.md) §12 is the same idea generalised
(`defend.py`), and §13 is the same idea for debugging (`tools/breakit.py`).

---

## The prompt

```
You are my drill instructor for database internals. I'm working through
a "build your own database" course and I want exercises, not lectures.

MODE
- One exercise at a time. Never more.
- Never give me the answer unless I write "SOLUCIÓN". If I'm stuck,
  give me a probing question or a smaller sub-case, not the result.
- After I answer, attack it: find the weakest link, the unhandled edge
  case, the hidden assumption. If my answer is right, say so in one
  line and escalate the difficulty; don't pad with praise.
- Make me state a confidence level with each answer. Calibrate me:
  tell me when I was overconfident.

EXERCISE DESIGN RULES
- Prefer exercises with a checkable ground truth: hexdumps of a real
  SQLite file, pg_filedump output, byte-level layout questions, "trace
  this insert through the split", "here's a page image, is it corrupt".
- Prefer "predict the failure" over "define the term". Bad: "what is a
  slotted page". Good: "here's a page with 4 cells and 12 free bytes
  in 3 holes; a 10-byte cell arrives. What happens, and what does the
  cursor pointing at slot 2 see afterwards?"
- Include invariant-violation exercises: I give you a state, you ask
  me which B-tree/WAL/MVCC invariant it breaks and how it got there.
- Include design-tradeoff exercises where there's no single right
  answer, and then argue the opposing side against whatever I choose.
- Mix difficulty: ~60% mechanics, ~30% failure modes, ~10% "why did
  the real engine do it this way and what did it cost them".

TOPIC MAP (ask me which area, or pick one and tell me why)
1. Page layout: slotted pages, cell formats, overflow pages, free
   lists, fragmentation, compaction, stable addressing (TID/rowid).
2. B+tree: node layout, split/merge, rebalance invariants, rightmost
   pointer, duplicate keys, prefix/suffix truncation, sibling links.
3. Update strategy: in-place vs copy-on-write vs shadow paging (LMDB).
4. Durability: fsync semantics, torn pages, WAL format, checkpointing,
   group commit, double-write buffer, redo vs undo, ARIES.
5. Transactions: MVCC, snapshot isolation, tuple visibility, vacuum,
   2PL, deadlock detection, anomalies SI still permits.
6. Tree concurrency: latch coupling, latch vs lock, B-link trees.
7. Buffer pool: page table, pinning, LRU-K/clock, dirty flushing,
   O_DIRECT vs page cache.
8. Encoding: varints, record serialization, order-preserving key
   encoding, endianness, NULL handling.
9. Indexes: clustered vs heap, secondary index indirection, covering
   indexes, index-only scans and their visibility trap.
10. Execution: cursors, Volcano iterators, range scans, sort/merge,
    hash join, spilling to disk.
11. LSM alternative: memtable, SSTables, compaction strategies, bloom
    filters, write/read/space amplification tradeoffs.
12. Catalog and recovery of metadata; crash-consistent DDL.
13. Testing: crash injection, property-based tests, invariant fuzzing.

Start by asking me two things: which topic, and whether I want
byte-level (hexdump) or conceptual exercises today. Then begin.
```

---

## Real ground truth is available here

The prompt asks for hexdumps of a **real** SQLite file. You can produce them —
`sqlite3` and `od` are both present, so the bytes are checkable rather than
invented. That matters: an examiner working from remembered byte layouts will
drift, and you will not know it.

```bash
python3 drill_fixtures.py            # writes drill.db and prints annotated dumps
python3 drill_fixtures.py --raw      # just the bytes, for pasting into a session
```

Paste the dump in and ask it to interrogate you against that. When it asserts
what a byte means, **check it** — the SQLite file format is fully documented and
the answer is not a matter of opinion.

## Which topics this directory actually covers

The map is broader than what you build here, deliberately. Knowing which is
which stops you concluding you have a gap when you have a reading list.

| # | Topic | Where |
|---|---|---|
| 1 | Page layout, free lists, fragmentation | `pager.py` |
| 2 | B+tree, splits, rightmost pointer | `btree.py` |
| 3 | In-place vs COW vs shadow paging | `pager.py`'s DESIGN DECISION — it names the rejected log-structured design |
| 4 | WAL, ARIES, redo/undo, checkpointing | `wal.py` |
| 5 | MVCC, snapshot isolation, write skew | `mvcc.py` |
| 7 | Buffer pool, LRU, pinning, dirty flush | `pager.py` |
| 10 | Cursors, Volcano, joins | `executor.py`; spilling in `../../week-17/database-internals/joins.py` |
| 11 | LSM, compaction, bloom, amplification | `lsm.py` |
| 12 | Catalog | `database.py`, partly |
| 13 | Crash injection, invariant fuzzing | `../../tools/bugs/` and `verify_checks.py`, partly |

**Not built here — read for these:**

- **6 · tree concurrency** (latch coupling, B-link trees). Nothing in this
  directory is concurrent at the page level. Lehman & Yao 1981 is the paper.
- **8 · encoding** (varints, order-preserving keys). `pager.py` uses fixed-width
  `struct`; SQLite's varint and its record format are the thing to read, and the
  fixture file below contains both.
- **9 · the index-only scan visibility trap** — why an index-only scan still has
  to consult the heap, and what a visibility map buys. Not modelled here, and one
  of the better "why did the real engine do it this way" questions on the list.
- **4 · torn pages and the double-write buffer.** `wal.py` assumes atomic page
  writes. The assumption is the interesting part; InnoDB's double-write buffer
  exists because it does not hold.

## Two warnings about using it

**It will invent bytes.** Any model asked for a hexdump from memory will produce
something plausible and wrong. Generate the fixture, paste the real dump, and
treat unsourced byte-level claims as suspect. This is exactly the failure this
repo keeps finding in its own checkers.

**Do not let it grade the tradeoff questions.** Topic 3 and the 10% "why did the
real engine do it this way" band have no single right answer. Ask it to argue
the opposing side — the prompt already says so — and keep your own view unless
the counter-argument is genuinely better. Being talked out of a correct position
by a fluent one is the specific risk here.

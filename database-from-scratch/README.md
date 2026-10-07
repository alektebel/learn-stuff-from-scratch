# Database From Scratch

A small, crash-safe, transactional key-value database with tables and secondary indexes,
in pure Python (standard library only), built one mechanism at a time.

It exists to close three gaps the rest of the repo leaves open: **indexing** (B+trees),
**ACID** (write-ahead logging, crash recovery, isolation levels) and **SQL vs NoSQL**
(what an atomic secondary index costs, and what you get without one). `dynamo-paper/` is the
NoSQL side of the comparison; this is the other side.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Disk I/O in pages | fixed-size pages, LRU buffer pool, dirty write-back | `pager.py` | 1-2 |
| Indexing | B+tree: splits, root growth, range scans over linked leaves | `btree.py` | 3-6 |
| Atomicity + durability | write-ahead log, CRC framing, redo recovery, checkpoints | `wal.py` | 7-10 |
| Isolation | MVCC with four isolation levels | `mvcc.py` | 11-13 |
| Isolation, observed | the anomaly × isolation-level matrix, produced by your engine | `anomalies.py` | 14 |
| SQL vs NoSQL | tables, atomic vs asynchronous secondary indexes | `table.py` | 15-17 |

## How to use this directory

The top-level files are **templates**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
working versions for when you are stuck, or to compare afterwards.

```bash
cd database-from-scratch
python3 check.py        # what to build next; stops at the first gap
python3 check.py 9      # one step
python3 check.py --all  # everything
```

`check.py` runs 17 checks against **your** code and never imports `solutions/`.

**The checker was itself tested.** Seven classic bugs were planted in copies of the solutions,
and each one has to be caught by its check:

| Planted bug | Caught by |
|---|---|
| evicting a dirty page without writing it back | step 2 |
| splitting nodes by entry count instead of bytes | step 6 |
| trusting log records without checking the CRC | step 7 |
| replaying transactions that never committed | step 9 |
| SNAPSHOT without first-committer-wins | step 12 |
| SERIALIZABLE without range validation (phantoms) | step 13 |
| an "async" index updated inside the transaction | step 17 |

Two of them initially slipped through. A randomised B-tree test almost never clusters
large entries in one half, and a corrupted byte usually broke the JSON before the missing
CRC check mattered. Steps 6 and 7 now build those cases deliberately.

## Design decisions, named

Each file opens with its decisions and what they cost. In short:

- **Split by bytes, not by count** (`btree.py`). With variable-size entries, splitting at
  `n // 2` can leave a half that does not fit in a page. Step 6 builds that case.
- **No rebalancing on delete** (`btree.py`). Lookups stay correct; space is not reclaimed.
- **Redo-only, no-steal logging** (`wal.py`). Uncommitted writes never reach disk, so
  recovery never undoes anything. Cost: a transaction must fit in memory.
- **Checkpoint by full copy and atomic rename** (`wal.py`). It avoids torn B-tree pages at
  O(database size) per checkpoint.
- **SERIALIZABLE by optimistic read validation** (`mvcc.py`). Simpler than SSI and provably
  serializable, with some false aborts.

## Questions to answer before reading the solutions

1. Why does `R + W > N` in `dynamo-paper/` not give you what SERIALIZABLE gives you here?
2. **Write skew survives SNAPSHOT isolation, even though each transaction sees a consistent
   snapshot. Why?** Your matrix in step 14 shows that it does; explaining it is the point.
3. Step 14 has a trap. An anomaly being *permitted* at a level does not mean every
   interleaving shows it. A dirty read can hide a write skew by letting the second
   transaction see the first one's write. Which interleaving avoids that?
4. In `checkpoint()`, what goes wrong if the log is truncated *before* the rename?
5. `AsyncIndexTable` returns a row under its old value after an update. Name a product
   feature where that is harmless, and one where it is a bug.

## Limits

- Concurrency is simulated: one thread interleaves transactions in a chosen order. That
  makes every anomaly reproducible; it says nothing about lock contention or throughput.
- The MVCC store is an in-memory dict, so a range scan inside it is O(n) internally.
  `keys_touched` counts the keys a B-tree-backed index would read, not what this toy does.
  Wiring MVCC onto the B-tree is the natural extension.
- Durability and MVCC are separate layers here. A real engine logs MVCC versions in the WAL.
- No SQL parser, query planner or joins. Indexes support equality lookups only.

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
| Isolation, indexed | the version store itself in the B+tree; point lookups vs indexed range scans | `mvcc.py` | 18 |
| Isolation, durable | MVCC versions and commit timestamps written to the WAL; recovery rebuilds them | `mvcc.py` | 19 |
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

`check.py` runs 19 checks against **your** code and never imports `solutions/`.

**The checker was itself tested.** Ten classic bugs were planted in copies of the solutions,
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
| the B-tree version index dropping tombstoned versions | step 18 |
| a key encoding that is order-preserving but not prefix-free | step 18 |
| recovery replaying MVCC versions of transactions that never committed | step 19 |

Three of them initially slipped through. A randomised B-tree test almost never clusters
large entries in one half, and a corrupted byte usually broke the JSON before the missing
CRC check mattered. Steps 6 and 7 now build those cases deliberately. The third, the
prefix-free encoding, slipped through because the naive encoding is still
order-preserving — only a direct assertion on `_enc`/`_dec` catches it.

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
- **Version chains behind the B+tree** (`mvcc.py`). The version store is the same index
  structure as everything else, keyed by an order-preserving encoding of the user key, so a
  point read is one descent and a range scan walks the linked leaves. Cost: version chains
  are read whole, and encoded keys are capped at `btree.MAX_KEY` bytes.
- **MVCC versions logged in the WAL** (`mvcc.py`). A durable store writes a `vput` record
  per write and a timestamped `commit` record, synced before the version reaches the tree;
  recovery rebuilds the index from the committed records alone. Cost: the log grows until
  the version index is checkpointed, and replay must be idempotent.

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
- The MVCC store is B+tree-backed, so its range scan is a descent plus a leaf walk.
  `keys_touched` now counts the tree entries that walk really reads: a narrow scan reads
  few.
- Durable MVCC versions are logged in the WAL, but the version index itself is not
  checkpointed: recovery replays the whole committed log into a fresh tree, so the log
  grows and startup is O(log). A checkpoint of the version index would close that.
- No SQL parser, query planner or joins. Indexes support equality lookups only.

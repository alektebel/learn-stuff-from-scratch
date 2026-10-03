# Database Engine From Scratch

Build a database from the disk upward: pages, a B+tree, a write-ahead log,
multi-version concurrency control, a SQL parser, a cost-based planner and an
iterator-model executor. Pure Python, no dependencies, ~115 functions to write.

## Why this directory exists

The repo already had replication ([`dynamo-paper/`](../../week-10/dynamo-paper/)) and
capacity ([`aws-from-scratch/`](../../week-01/aws-from-scratch/)) — both *above* a storage
engine. Dynamo's own README admits it: "the paper's pluggable storage engines
are replaced by a dict." This is that dict, built properly.

It also has a parser you already wrote ([`c-compiler/`](../../week-15/c-compiler/)) and no
query planner to point it at. Half a database was already here in pieces.

## What a database actually is

| Problem | Mechanism | File |
|---|---|---|
| Disk reads cost the same at 4 bytes and 4 KB | Fixed-size pages, slotted | `pager.py` |
| Memory is smaller than the data | A buffer pool, and an eviction policy | `pager.py` |
| Finding a row without reading them all | A B+tree with a huge fanout | `btree.py` |
| A crash mid-write | Write-ahead logging, redo then undo | `wal.py` |
| Readers blocking writers | Multi-version rows, snapshots | `mvcc.py` |
| Text to a tree | Tokeniser, recursive descent, precedence climbing | `sql.py` |
| Which plan to run | Selectivity estimates and a cost model | `planner.py` |
| Running a plan | Operators pulling one row at a time | `executor.py` |
| All of it at once | `database.py` |

---

## How to use this directory

The files at the top level are **templates**: every function has a docstring
explaining what to build and why, then `raise NotImplementedError`. You fill
them in. `solutions/` holds complete working versions for when you are stuck or
want to compare afterwards.

```bash
cd database-engine
python3 check.py            # what to build next
# ... implement the functions the checker points at ...
python3 check.py            # re-run; it stops at the first thing not yet done
```

`check.py` runs **18 graded checks** against **your** code (it never imports
`solutions/`). Each one names the file, the concept, and — when something is
wrong — what usually causes it:

```
  ✓  1. pager.py       slotted pages, and stable slot ids
  ·  2. pager.py       buffer pool: LRU, dirty pages, pins
      not implemented yet — pager.py:214 in fetch()

  1/18 passing, 1 to write

  Next: step 2 — buffer pool: LRU, dirty pages, pins (pager.py)
```

| Command | Does |
|---|---|
| `python3 check.py` | Run in order, stop at the first unimplemented step |
| `python3 check.py 5` | Run only step 5, while you iterate on it |
| `python3 check.py 5 8` | Run steps 5 through 8 |
| `python3 check.py --all` | Run everything, skipping nothing |
| `python3 <file>.py` | Run that file's own demo once it is implemented |

Work top to bottom — later files import earlier ones.

---

## Learning Path

### 1. `pager.py` — pages, and the memory in front of them

Fixed-size pages with a slot directory, a disk manager, and an LRU buffer pool.

**The rule that matters:** deleting a record must **not** renumber the surviving
slots. An index entry pointing at `(page, 7)` has to keep meaning slot 7 after
slot 3 is deleted. Renumbering on delete is silent corruption, not an error.

**Measured result:** hit rate against pool size, and then the experiment that
justifies every real eviction policy — a full-table scan interleaved with the
transactional workload drops the hot set from **100% to 79%**, and the scan
itself gets nothing out of the cache either. Both workloads end up worse off
than if the scan had bypassed the pool. LRU-K, clock-sweep and scan-resistant
ring buffers all exist because of that one measurement.

### 2. `btree.py` — the index

**The one number:** fanout is the base of the logarithm.

```
  order      keys   height   pages/lookup   vs scan
      4     20000        9            9.0     1111x
     32     20000        4            4.0      312x
    250     20000        2            2.0       80x
```

At order 250 — what a 4 KB page gives you — 100M rows is four levels, and the
top two are always cached. A balanced binary tree over the same data is 27
levels. That gap is the entire reason databases use a B-tree.

Build it in the MVP-then-limit-case order: insert into one leaf, split a leaf,
split an internal node, split the **root** (the only place the tree gets
taller), then delete with borrow-or-merge.

**The distinction to get right:** a leaf **copies** its middle key upward; an
internal node **moves** it. Get that backwards and lookups still mostly work,
which is what makes it dangerous — so `check_invariants()` compares against a
plain dict after every round of random churn.

### 3. `wal.py` — surviving a crash

One rule: **the log record describing a change must be durable before the
changed page is.** Not a data structure — an ordering.

**The counter-intuitive part:** recovery REDOes the uncommitted transactions
too, before undoing them. You cannot undo a change that is not there, so
recovery first reconstructs the exact state at the crash — garbage included —
and only then removes the garbage.

**Measured results:** committing five rows writes **zero** data pages;
checkpoints take recovery from replaying 5,002 records to replaying 2; and
group commit at batch size 100 costs **1 fsync instead of 100** for the same
work. Then break the rule deliberately and watch a change reach disk with no
record of it — unrecoverable corruption from two lines in the wrong order.

### 4. `mvcc.py` — many transactions at once

Readers never block writers, writers never block readers. The bill arrives as
old versions nobody can collect.

**The table to internalise**, and every cell of it is measured rather than
asserted:

| level | dirty read | non-repeatable | lost update | write skew |
|---|---|---|---|---|
| read uncommitted | YES | YES | YES | YES |
| read committed | no | YES | **YES** | YES |
| repeatable read | no | no | no | **YES** |
| serializable | no | no | no | no |

Read the last two rows twice. **Snapshot isolation — the default in most
engines — admits write skew.** Two doctors each check that the other is on call,
each goes off call, both commit with no conflict, and nobody is on call. They
wrote *different keys*, so first-committer-wins never fired.

**And the bill:** one forgotten `BEGIN` pins the vacuum horizon and every dead
version behind it stays. Committing that single idle transaction frees 100
versions at once. This is the mechanism behind most PostgreSQL disk incidents —
never the writes, always one connection sitting idle-in-transaction while they
happen.

### 5. `sql.py` — text to a tree

Recursive descent by hand, with precedence climbing.

**The trap everyone hits:** `SELECTED` must lex as one identifier, not `SELECT`
followed by `ED`. Match the longest word **first**, then ask whether that whole
word is a keyword — the same alternation-order bug as putting `//` after `/` in
a lexer, which
[`compiler-and-vgpu/frontend.py`](../../week-15/compiler-and-vgpu/frontend.py) shipped
with and had to fix.

**The point of the AST:** it says WHAT, never HOW. Nothing in the parse tree
mentions an index or a scan, which is precisely why an optimiser can exist.

### 6. `executor.py` — pulling one row at a time

**Measured result:** `LIMIT 5` over a filter over 100,000 rows reads 117 rows —
the scan stops because the LIMIT stopped pulling, and nothing below it knows a
limit exists. Put a `Sort` underneath and it reads all 100,000, because a sort
cannot emit its smallest row until it has seen the largest.

**Two properties, kept apart:**

| | blocking | bounded memory |
|---|---|---|
| Filter, Project, Limit, SeqScan | no | yes |
| Sort, HashJoin, Aggregate | yes | no |
| **Distinct** | **no** | **no** |

*Blocking* decides whether a LIMIT above you helps. *Bounded* decides whether
you can run at all on a large table. Distinct is the instructive row: a LIMIT
works fine above it, and `SELECT DISTINCT` on a high-cardinality column is
still an out-of-memory incident the EXPLAIN gave no sign of.

### 7. `planner.py` — choosing HOW

**The crossover**, computed from the price of a page rather than recalled:

```
computed crossover: 0.74% of the table

  selectivity     rows  index cost   seq cost  planner picks
        0.10%       50         216       1500  index
        0.74%      370        1500       1500  seq scan
        5.00%     2500       10041       1500  seq scan
```

Below it, use the index; above it, read the whole table. An index scan fetches
heap pages **randomly** and a random page costs 4x a sequential one. This is the
answer to "why is Postgres ignoring my index".

And the knob behind it: `random_page_cost` at 4.0 (spinning disk) puts the
crossover at 0.74%; at 1.1 (SSD) it moves to **2.69%**. Leaving the
spinning-disk default on flash is a real and common misconfiguration.

**Then the failure.** A column where 49,999 rows say `PT` and one says `ES`.
`n_distinct` is 2, so the planner believes each value covers half the table:

```
  WHERE               estimated     actual  plan chosen  table rows read
  country = 'PT'         50.00%    99.998%      SeqScan           50,000
  country = 'ES'         50.00%     0.002%      SeqScan           50,000
```

One row in fifty thousand matches and the planner reads all of them. The
estimate is wrong by **25,000x**, because `1/n_distinct` assumes even
distribution — and the columns people actually filter on (`country`, `status`,
`tenant_id`, `is_deleted`) are all skewed. This is also why a query can be fast
for months and then slow with nothing changed but the data.

### 8. `database.py` — capstone

Real SQL against everything above: `CREATE TABLE`, `INSERT`, `SELECT` with
`WHERE`/`ORDER BY`/`GROUP BY`/`JOIN`, `UPDATE`, `DELETE`, `BEGIN`/`COMMIT`/
`ROLLBACK`, and `EXPLAIN` that prints the planner's reasoning.

---

## The five failures worth being able to recognise

Each one is a mechanism in this directory, and each looks like something else
from the outside:

| Symptom | Actually |
|---|---|
| Query got slow, nothing changed | The statistics went stale; `1/n_distinct` is lying about a skewed column |
| Disk filling up, writes are normal | One idle-in-transaction connection is pinning the vacuum horizon |
| Two increments, one applied | Read committed retakes its snapshot per statement — that is a lost update |
| An invariant held by every transaction, violated anyway | Write skew; snapshot isolation does not prevent it |
| Corrupt after a power cut | A page reached disk before its log record did |

---

## Where this implementation stops

- **Nodes are objects, not packed page bytes.** The pager does real byte
  packing; the B+tree keeps nodes in memory keyed by page id and counts page
  reads explicitly. Serialising nodes is mechanical and would triple the file
  while hiding the number that matters.
- **No concurrency control on the B+tree itself.** Real engines use latch
  coupling or Blink-trees so several threads can descend at once. Everything
  here is single-threaded.
- **No LSM tree.** The whole directory assumes in-place updates to a B+tree.
  RocksDB, Cassandra and every write-heavy store make the opposite choice.
- **Recovery is simplified ARIES.** No fuzzy checkpoints, no nested top actions,
  and undo is a single pass rather than being driven by `undo_next`.
- **Serializable is coarse.** It aborts on any read-write overlap; PostgreSQL's
  SSI detects dangerous *structures* and aborts far less often.
- **No query rewriting**, no subqueries, no `EXISTS`, no window functions, no
  CTEs, no foreign keys, no `NOT NULL`, no type checking.

## Extensions worth trying

1. **Pack B+tree nodes into page bytes** and delete the in-memory `nodes` dict.
   The invariant checker is already there to tell you when you get it wrong.
2. **An LSM tree** — memtable, SSTables, levelled compaction — behind the same
   interface, then compare write and read amplification against the B+tree on
   identical traffic. This is the single biggest storage-engine decision there
   is and you would have both sides of it.
3. **Latch coupling** on the B+tree, and a stress test with several threads.
4. **A most-common-values list** in `Statistics`, and watch the skewed-column
   plan from section 7 fix itself.
5. **Top-N sort** — a bounded heap instead of sorting everything for
   `ORDER BY x LIMIT 10`. It reads the same rows and stores N of them; measure
   the memory, not the row count.
6. **Vectorised execution** — make `next()` return a batch of 1,024 rows and
   measure the speedup. It is the same amortisation argument as compiling the
   plan, one level cheaper.
7. **Wire it to [`dynamo-paper/`](../../week-10/dynamo-paper/)**: this engine as the
   storage layer under consistent hashing and quorums. That combination is,
   roughly, what a distributed SQL database is.

---

## Structure

```
database-engine/
├── README.md
├── check.py              # progress checker — run this first
├── pager.py              # templates with TODOs and DESIGN DECISION blocks
├── btree.py
├── wal.py
├── mvcc.py
├── sql.py
├── executor.py
├── planner.py
├── database.py           # capstone
└── solutions/            # complete, runnable implementations
```

```bash
cd solutions
python3 pager.py          # slotted pages, and a scan destroying the buffer pool
python3 btree.py          # fanout, range scans, delete, randomised torture
python3 wal.py            # commit without page writes, then crash and recover
python3 mvcc.py           # the anomaly table, write skew, and vacuum bloat
python3 sql.py            # the tokeniser trap and precedence climbing
python3 executor.py       # the pull model, and what blocks it
python3 planner.py        # the index/scan crossover, and a wrong estimate
python3 database.py       # SQL end to end
```

No dependencies beyond the Python 3 standard library.

## Related directories

- [`dynamo-paper/`](../../week-10/dynamo-paper/) — replication above a storage engine;
  this is the engine it replaced with a dict
- [`aws-from-scratch/`](../../week-01/aws-from-scratch/) — DynamoDB's partitioning and
  capacity model, and what all of this costs
- [`c-compiler/`](../../week-15/c-compiler/) — the same parsing problem, for a language
  with more of a type system
- [`system-design/`](../../reference/system-design/) — the patterns a database sits under
- [`PHILOSOPHY.md`](../../PHILOSOPHY.md) — why this repo is built the way it is

## When you want to be examined rather than taught

[`DRILL.md`](DRILL.md) is a prompt for a fresh session that gives you one
exercise at a time, refuses to answer unless you write `SOLUCIÓN`, attacks
whatever you say, and makes you state a confidence level so it can tell you when
you were overconfident.

`check.py` grades the code you wrote. That grades whether you can defend it.
Use it *after* a file, never before — it is worthless as an introduction and
sharp as an audit.

```bash
python3 drill_fixtures.py    # a real SQLite file, annotated, ready to paste
```

The fixtures matter: a model asked for a hexdump from memory produces something
plausible and wrong. The SQLite format is byte-exact and documented, so an
exercise built on a real file has an answer neither of you can drift away from.

## Sources

- Hellerstein, Stonebraker & Hamilton, **"Architecture of a Database System"**, FnTDB 2007 — read this first; it is the map for the whole directory.
- Mohan et al., **"ARIES"**, TODS 1992 — redo-then-undo, and why in that order.
- Berenson et al., **"A Critique of ANSI SQL Isolation Levels"**, SIGMOD 1995 — where write skew comes from.
- Graefe, **"Volcano"**, TKDE 1994 — the iterator model in `executor.py`.
- Selinger et al., SIGMOD 1979 — cost-based planning and the crossover in `planner.py`.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-9--database-engine)

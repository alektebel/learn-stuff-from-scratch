# Database Engine From Scratch — Solutions

Complete implementations of every template in the parent directory. Pure Python
3 standard library; the whole set runs in about fifteen seconds.

```bash
python3 pager.py  btree.py  wal.py  mvcc.py  sql.py  executor.py
python3 planner.py  database.py
```

## What each file demonstrates

### `pager.py`
Slot ids survive their neighbours being deleted, and the page's two regions
never cross:

```
insert   5 bytes -> slot 0, 4084 free
delete slot 1 -> read(1) is None, and slot 2 is still b'a much longe'...
free before compaction 4031, recovered 3 bytes, now 4034
```

Then the measurement that justifies every real eviction policy:

```
  hot working set warm at 100.0% hit rate, resident pages [0, 1, 2, 3, 4]
  after a 500-page scan, resident pages are [468, 469, 470, 471, 472]
  with a scan every 100 transactions the hot set runs at 79.0%
```

Both workloads end up worse than if the scan had bypassed the pool: the hot set
lost its cache, and the scan never revisits a page so it gained nothing.

**Implementation note that was a bug first:** `DiskManager.allocate` writes an
**initialised** page, not zeros. A zeroed page's header reads `free_start=0,
free_end=0`, so `free_space` computes as negative and the first insert silently
refuses. The checker's exact-capacity assertion is what found it.

### `btree.py`
```
  order      keys   height   pages/lookup   vs scan
      4     20000        9            9.0     1111x
    250     20000        2            2.0       80x
```

Range scans pay for the leaf chain: `range(4000, 4200)` costs **16** page reads
against **804** for the same 201 rows fetched individually.

Randomised churn with a `dict` as the oracle:

```
  round 3: 209 keys, height 4, invariants hold, contents match dict: True
```

Comparing against a plain dict is the cheapest possible oracle and it catches
what a spot-check of `get()` cannot — a wrong separator, a dropped leaf link, a
merge that lost a key.

### `wal.py`
```
5 writes committed: 0 data pages written, 1 log flush
```

Then a crash, and all five come back from the log alone. The three-line summary
of recovery is in the code and worth repeating: **redo replays the losers too**,
because you cannot undo a change that is not there.

```
  log records   checkpoint   records replayed
          5000           no               5002
          5000          yes                  2

  transactions  batch size   fsyncs   per txn
           100           1      100      1.00
           100         100        1      0.01
```

And the rule broken deliberately: a page reaches disk, its record is lost, and
recovery finds nothing to undo. The database is silently wrong forever.

### `mvcc.py`
Every cell of the anomaly table is produced by a function that *attempts* the
anomaly and reports whether it happened — none of it is hard-coded:

```
  level               dirty read  non-repeatable   lost update   write skew
  read committed              no             YES           YES          YES
  repeatable read             no              no            no          YES
  serializable                no              no            no           no
```

**Implementation note:** the write path checks `_snapshot_for(txn)`, not
`txn.snapshot`. That one choice is what makes read committed genuinely weaker —
its snapshot is retaken per statement, so a concurrent commit is already visible
and there is nothing to conflict with. Check the BEGIN snapshot in `write()` and
read committed becomes silently as strong as repeatable read, and the table
above loses its most useful row.

Then the bloat, measured with one transaction left open:

```
  updates  versions  vacuum frees  still held
      100       120             0         100
  Committing that one transaction lets vacuum free 100 versions at once
```

### `sql.py`
```
SELECT     -> KEYWORD('SELECT')
SELECTED   -> IDENT('SELECTED')
```

Longest match first, then classify. And errors that name a column:

```
SELECT name users     -> expected FROM at column 13, found 'users'
SELECT FROM users     -> expected a value at column 8, found 'FROM'
```

**Implementation note:** `table_alias()` accepts a bare `IDENT` after the table
name, which is only safe because keywords lex as `KEYWORD` rather than `IDENT`.
The tokeniser decision from the top of the file is what makes the alias rule two
lines instead of a lookahead table.

### `executor.py`
```
-> Limit 5  (in 5, out 5)
  -> Filter: age > 70  (in 117, out 5)
    -> SeqScan on users (100000 rows)  (in 117, out 117)
```

Add a `Sort` under the `Limit` and the same query reads all 100,000. Nested loop
against hash join on 2,000 rows each: 4,000,000 comparisons against 2,000, and
81x the wall-clock time.

`blocking` and `bounded` are separate attributes on purpose. `Distinct` is
neither blocking nor bounded, and conflating the two is how a `SELECT DISTINCT`
becomes an out-of-memory incident that the EXPLAIN gave no sign of.

### `planner.py`
```
computed crossover: 0.74% of the table

    random_page_cost   crossover
                 4.0       0.74%
                 1.1       2.69%
```

And the estimate failing:

```
  WHERE               estimated     actual  plan chosen  table rows read
  country = 'ES'         50.00%     0.002%      SeqScan           50,000
```

Predicate pushdown, measured both ways:

```
  plan                     rows through the join   total rows read
  filter pushed down                         839           101,678
  filter above the join                   50,000           150,839
```

**Implementation notes:**

- `_evaluate` compiles an expression to a callable **once per query**. Walking
  the AST inside the row loop is the standard way a toy executor ends up 50x
  slower than it needs to be — the same amortisation argument as vectorised
  execution, one level up.
- `_column_owners` refuses to resolve a column name that exists in two tables,
  so an ambiguous predicate stays above the join. Pushing a predicate to the
  wrong side is a **wrong answer**, not a slow one, so the safe direction is
  not to push.
- `_access_path` attaches this table's predicates directly to its scan rather
  than returning them for someone else to place. That placement *is* the
  pushdown; return them and they float above the join, which is what the first
  version of this file did.

### `database.py`
```
  SELECT id FROM events WHERE value = 6238
  -> IndexScan on events [(6238, -1) .. (6238, 20001)]
  note: index on events.value: estimated 2 rows (0.01%), cost 21 vs seq scan 600

  SELECT id FROM events WHERE value > 100
  -> Filter: (value > 100) -> SeqScan on events (20000 rows)
  note: index REJECTED: cost 79418 vs seq scan 600 — 99.0% of the table
```

Same table, same index, opposite decisions, and the note says which number
decided it.

## Implementation notes

- **`Page.delete` zeroes a slot's length and leaves the slot in place.** Slot
  ids are what indexes point at, so a delete may never renumber them. `compact`
  is the separate, deliberate operation that reclaims the bytes — VACUUM at page
  scale, and it needs the page exclusively, which is why it cannot just run all
  the time.
- **`BufferPool._evict` skips pinned pages.** A B+tree split holds a parent and
  two children at once; evicting one mid-split writes a half-updated tree that
  nothing can detect afterwards.
- **A leaf split COPIES its middle key up; an internal split MOVES it.** The key
  must remain findable in a leaf because leaves hold all the data; a separator
  kept in two places means two nodes claim the same boundary.
- **`_rebalance` prefers borrowing to merging.** Borrowing touches two nodes and
  cannot cascade; a merge touches three and can propagate to the root. Note that
  SQLite, InnoDB and PostgreSQL largely skip this entirely — an under-full page
  costs space, but a cascading merge is a latch convoy on a hot table. "Correct"
  and "what production does" differ here for a concurrency reason.
- **`Database.flush_page` forces the log first.** Two lines, in that order, and
  reversing them is unrecoverable corruption rather than a bug you can fix.
- **Undoing an INSERT removes the key rather than setting it to `None`.**
  Leaving a `None` behind is a tombstone nobody asked for, and a
  `SELECT count(*)` would notice.
- **`Snapshot.active` matters as much as the horizon.** A transaction with a
  *lower* id than yours can still be invisible, because it had not committed
  when your snapshot was taken.
- **`Database._plan` validates the tables before planning.** A missing table
  surfacing as a `KeyError` from inside the planner is the difference between
  "no such table: usres" and a stack trace, and only one of those is actionable.

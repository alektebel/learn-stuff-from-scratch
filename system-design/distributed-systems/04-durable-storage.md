# Category 4: Durable Storage Internals

Tracks 13–17. What actually happens under a database: write-ahead logs,
LSM trees, B-trees, distributed file systems, and indexes.

---

## Track 13: Write-Ahead Log (WAL)

### Problem
Make writes durable: after the system replies "ok", the write survives a
crash — process kill, power loss, half-written disk blocks.

### The Rule
**Log the change, fsync, then apply it.** Recovery = replay the log.

### Record Format
```
┌────────┬────────┬──────┬─────────┬──────────────┐
│ CRC32  │ length │ type │  LSN    │   payload    │
│  4B    │  4B    │ 1B   │  8B     │  len bytes   │
└────────┴────────┴──────┴─────────┴──────────────┘
```
- **CRC over (length,type,LSN,payload)**: detects torn/partial writes — a
  crash mid-append leaves a bad-CRC tail; recovery truncates at the first
  bad record. This is why the CRC is mandatory, not optional.
- **LSN** (log sequence number): byte offset or monotonically increasing id;
  everything else in the engine refers to "durable up to LSN x".

### The fsync Discipline
- `write()` puts bytes in the OS page cache — **not durable**. Only
  `fsync`/`fdatasync` is.
- fsync is the throughput ceiling (~0.5–2 ms on SSD). Fixes:
  - **Group commit**: batch all writes that arrived during the last fsync
    into the next one. Latency ≈ one fsync; throughput scales with batch size.
  - fsync the **directory** too after creating a new segment file, or the
    file itself may vanish after a crash.

### Segments, Checkpoints, Truncation
- Roll the log into fixed-size segments (e.g. 64 MB).
- **Checkpoint**: persist the applied state (or note "state durable up to
  LSN x"), then delete segments entirely below x. Without checkpoints the
  log grows forever and recovery time is unbounded.
- Recovery: load last checkpoint → replay segments from its LSN → truncate
  corrupt tail.

### Failure Modes
| Failure | Handling |
|---|---|
| Crash mid-record | CRC fails → truncate tail |
| Crash between write and fsync | record lost, but never acked — correct |
| Torn 4K block spanning records | CRC catches; per-block formats (Postgres full-page writes) for the paranoid |
| Log device full | reject writes early; alert well before |
| Corrupt middle of log (bad disk) | checksummed segments + replication (Track 7) — single-disk WAL can't fix this alone |

### Milestones
1. Append + replay with CRC framing; kill -9 tests truncate cleanly.
2. Group commit; measure writes/sec vs fsync-per-write (expect 10–100×).
3. Segments + checkpoint + truncation; bounded recovery time.
4. `torn-write` test harness: crash injection at every byte offset around a
   record boundary; recovery must never accept a half record.

---

## Track 14: LSM Tree

### Problem
Sustain high write throughput with acceptable read performance — the
storage engine behind RocksDB, Cassandra, LevelDB.

### Architecture
```
write ──► WAL (Track 13) ──► memtable (sorted map, in RAM)
                                  │ full → flush
                                  ▼
                         SSTable files (sorted, immutable)
          L0:  [sst][sst][sst]        ← overlapping ranges
          L1:  [  sst  ][  sst  ]     ← disjoint, 10× bigger
          L2:  [    sst    ][    sst    ]
                                  ▲
                      compaction merges downward

read(k): memtable → immutable memtables → L0 (each file) → L1 (one file) → …
```

### Components
- **Memtable**: skip list / sorted map; writes are O(log n) memory ops —
  this is where write speed comes from. Paired with the WAL for durability.
- **SSTable**: sorted key/value blocks + sparse index (every ~4 KB) + bloom
  filter, all immutable. Lookup: bloom → index → one block read.
- **Bloom filters**: ~10 bits/key gives ~1% false positives; kills the
  "read amplification for missing keys" problem.
- **Tombstones**: deletes are writes of a delete-marker; the value dies for
  real only when compaction reaches the bottom level.

### Compaction (the whole game)
- **Size-tiered**: merge similar-sized runs. Low write amplification, high
  space amplification (duplicates live long).
- **Leveled**: each level 10× the last, disjoint ranges; read touches ≤ 1
  file per level. Higher write amplification (~10 per level), low space amp.
- The three amplifications — **write, read, space** — cannot all be
  minimized; pick per workload (RUM conjecture).

### Failure Modes
| Failure | Handling |
|---|---|
| Crash during flush/compaction | new files are temp-named; atomic rename + manifest makes them visible; orphans GC'd |
| L0 pileup (write burst) | write stall/slowdown triggers when L0 count high — backpressure, not OOM |
| Compaction starves foreground I/O | rate-limit compaction bytes/sec |
| Reads slow for missing keys | bloom filters |
| Range tombstone floods | special-cased range deletes |

### Milestones
1. Memtable + WAL; reads merge memtable over nothing (single level).
2. Flush to SSTable with sparse index; reads check memtable → SSTables newest-first.
3. Bloom filters; measure negative-lookup latency before/after.
4. Leveled compaction with manifest + atomic installs; crash-injection tests.
5. Benchmarks: write throughput vs B-tree (Track 15), read p99 vs level count,
   write amplification measured from disk-bytes-written / user-bytes.

---

## Track 15: B-Tree

### Problem
The read-optimized counterpart: ordered index with O(log_B n) point reads and
efficient range scans, updated **in place** — the engine behind Postgres,
MySQL/InnoDB, SQLite.

### Structure (B+ tree)
```
            ┌──────[ 17 | 42 ]──────┐          internal: keys + child ptrs
            │          │            │
      [3|9|14]    [17|25|33]   [42|58|77]      leaves: keys + values,
        ◄────────────◄────────────►            linked for range scans
```
- Page-based: every node is one fixed-size page (4–16 KB) addressed by page
  id; a file is an array of pages. This maps directly onto disk I/O.
- High fanout (hundreds of keys/page) → 3–4 levels cover billions of keys;
  the top levels stay in the page cache.

### Operations
- **Search**: binary search within page, descend; O(height) page reads.
- **Insert**: into leaf; if full → **split** (allocate sibling, move upper
  half, push separator up; splits can cascade to a new root).
- **Delete**: from leaf; underflow → borrow from sibling or **merge**
  (most real engines just tolerate underflow, rebalancing lazily).
- **Range scan**: find start leaf, walk the leaf sibling links.

### Making It Crash-Safe
Two industry answers:
1. **WAL of page changes** (Track 13): log logical/physiological records,
   apply pages later; recovery replays (ARIES model, simplified).
2. **Copy-on-write** (LMDB/btrfs): never overwrite; write modified pages to
   fresh locations up to a new root; commit = atomically swap root pointer.
   Simpler recovery (nothing to replay), costs write amplification.
Build copy-on-write first — it's dramatically easier to get right.

### Concurrency (once single-threaded works)
- Latch crabbing: lock parent, lock child, release parent if child is "safe"
  (not about to split/merge).
- Or the COW shortcut: readers see the old root snapshot for free; one
  writer at a time.

### B-Tree vs LSM (interview staple, now measured by you)
| | B-tree | LSM |
|---|---|---|
| Point read | ≤ height page reads (great) | multi-level probe (bloom-mitigated) |
| Write | read-modify-write page + WAL | memtable append (great) |
| Range scan | leaf-linked, ordered on disk | merge across levels |
| Space | fragmentation in pages | duplicates until compaction |

### Milestones
1. Page manager: fixed-size pages, allocate/free, page cache with pinning.
2. Search + insert with splits; verify with 1M random inserts + full scan.
3. Range scans over leaf links.
4. Copy-on-write commits; kill -9 at random points — reopen must always see
   a consistent tree (old or new root, never mixed).
5. Benchmark vs your LSM: read-heavy, write-heavy, scan-heavy workloads.

---

## Track 16: Distributed File System (GFS-style)

### Problem
Store files far larger than one machine, tolerate constant disk/node failures,
and feed data-parallel compute (MapReduce, Track 22).

### Architecture
```
              ┌────────────── MASTER ──────────────┐
              │ namespace: /path → [chunk ids]      │  metadata only,
              │ chunk id → [replica locations]      │  replicated via
              │ leases, GC, rebalance               │  Raft (Track 7)
              └──────┬──────────────────────────────┘
        control      │        ▲ heartbeats + chunk reports
                     ▼        │
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ chunksrv │  │ chunksrv │  │ chunksrv │   64 MB chunks, 3 replicas,
   └──────────┘  └──────────┘  └──────────┘   checksummed blocks
        ▲   data flows client ↔ chunkservers directly
        │
     client (library: asks master for locations, caches them)
```

### Key Decisions
- **Big chunks (64 MB)**: metadata stays tiny (fits in master RAM), clients
  rarely talk to the master, sequential throughput dominates. Cost: hot small
  files and internal fragmentation.
- **Master handles metadata only**; data never flows through it. Clients
  cache chunk locations — the master is out of the read path.
- **Write path with leases**: master grants one replica a *lease* (primary);
  clients push data to all replicas (pipelined along the chain), then the
  primary assigns the serial order and tells secondaries to apply. Lease
  expiry (not perfect failure detection) bounds split-brain.
- **Replication repair**: chunkservers heartbeat with their chunk lists;
  master notices under-replicated chunks (missing heartbeats, bad checksums)
  and schedules re-replication, prioritized by how far below target.
- **Checksums per 64 KB block**, verified on every read — disks lie; a read
  that fails checksum is served from another replica and repaired.

### Consistency Model
Weak by design: record appends are atomic *at least once* (duplicates and
padding possible); applications use self-validating, self-identifying
records. Teaching point: you don't need POSIX to build search indexes —
relaxing consistency bought enormous simplicity and scale.

### Failure Modes
| Failure | Handling |
|---|---|
| Chunkserver dies | heartbeat timeout → re-replicate its chunks across the fleet |
| Master dies | Raft failover; state = ops log + checkpoints (Tracks 7+13) |
| Bit rot | block checksums on read + background scrubbing |
| Stale replica (missed mutations) | chunk version numbers; stale replicas excluded and GC'd |
| Hot file | more replicas for hot chunks; client-side read balancing |

### Milestones
1. Single master + one chunkserver: create/write/read a file of many chunks.
2. 3× replication with the lease/primary write protocol.
3. Kill a chunkserver under load → automatic re-replication, reads unaffected.
4. Checksums + scrubber; inject bit flips, verify detection and repair.
5. Replicated master; kill the master leader mid-write workload.

---

## Track 17: Indexes

### Problem
Find rows by something other than the primary key without scanning
everything, and understand what each index costs at write time.

### Hash Index
- In-memory `dict key → file offset` over an append-only data log
  (Bitcask model). O(1) point reads, no range scans; rebuild on restart via
  log scan or persisted hint files.
- Compaction merges log segments and drops overwritten values.

### Primary vs Secondary
- **Primary/clustered**: table stored in key order (the B-tree of Track 15) —
  the row *is* the leaf value.
- **Secondary**: separate index whose leaf value is the primary key
  (or a row pointer): `email → user_id`. Every secondary index adds a write
  + potential page split per row mutation — indexes are paid for at write time.
- **Non-unique secondaries**: value is a postings list of PKs.

### Composite & Covering
- Composite `(a, b, c)` supports prefixes: `a`, `a,b`, `a,b,c` — the
  **leftmost-prefix rule**; ordering within the index enables
  `WHERE a=? ORDER BY b` for free.
- **Covering index**: if the index contains every column the query needs,
  skip the table fetch entirely (index-only scan).
- Selectivity: index on `is_deleted` (2 values) is nearly useless; the
  planner needs cardinality estimates to choose — implement a trivial cost
  model: `cost = matching_entries × (1 + fetch_cost_if_not_covering)`.

### Distributed Secondary Indexes (ties into Track 9)
| Design | Write | Query by secondary key |
|---|---|---|
| **Local** (per-shard) index | 1 shard (fast, atomic with row) | scatter-gather to all shards |
| **Global** (index sharded by indexed value) | 2 shards → needs 2PC/async | 1 shard (fast) |
Async global indexes trade a staleness window for write latency — most
"global secondary indexes" (DynamoDB GSI) choose exactly this.

### Failure Modes
| Failure | Handling |
|---|---|
| Index/table divergence after crash | index updates go through the same WAL/txn as the row |
| Async global index lag | read-your-writes patch: check recent-writes buffer |
| Write amplification from many indexes | index budget; drop unused (track usage stats) |
| Hot index range (monotonic keys, e.g. timestamps) | hash-prefix or bucket the indexed value |

### Milestones
1. Bitcask-style hash index over an append log, with compaction.
2. Secondary index on the Track 15 B-tree; keep it transactionally consistent
   with the table through the WAL.
3. Composite + covering indexes; a micro query planner picks index vs scan by
   estimated cost; verify with `EXPLAIN`-style output.
4. Shard the table (Track 9); implement local indexes with scatter-gather
   query, then an async global index; measure both under load.

---

## What Carries Forward
- The WAL is under everything: LSM, B-tree, queue broker segments, Raft's
  persisted log.
- LSM/B-tree become the state machine storage for the Track 8 KV store.
- The DFS feeds MapReduce (Track 22); its master *is* a Track 8 KV in disguise.
- Local-vs-global index trade-off returns in distributed search (Track 23).

# Category 6: Production-Grade Data Systems

Tracks 22–25. Complete systems assembled from earlier building blocks:
batch processing, search, stream processing, and peer-to-peer storage.

---

## Track 22: MapReduce

### Problem
Process terabytes across a fleet with a programming model simple enough that
the framework — not the application — handles distribution, retries, and
stragglers.

### Programming Model
```
map(k1, v1)        → list<(k2, v2)>       # e.g. (doc, text) → (word, 1)
reduce(k2, [v2])   → list<v3>             # e.g. (word, [1,1,1]) → (word, 3)
```
The contract that makes distribution possible: map and reduce are **pure**
and the framework may re-execute them at will.

### Architecture & Data Flow
```
input on DFS (Track 16), split into M pieces
      │
 ┌────▼─────┐  map tasks (M)      intermediate files, partitioned by
 │ workers  │ ───────────────►    hash(k2) % R, sorted, on mapper's LOCAL disk
 └────┬─────┘
      │  shuffle: each reducer r fetches partition r from every mapper
 ┌────▼─────┐  reduce tasks (R)
 │ workers  │ ───────────────►    R output files on DFS, atomic rename
 └──────────┘
      coordinator: task states, assignment, heartbeats, re-execution
```
- **Shuffle is the heart**: mappers partition by `hash(k2) % R` and sort
  within each partition; reducers merge-sort the fetched runs so each key's
  values arrive grouped. Implement external merge sort — intermediate data
  exceeds RAM by design.
- **Combiner**: run reduce-like local aggregation on the mapper
  (`(word,1)×1000 → (word,1000)`) — legal when reduce is
  commutative+associative; slashes shuffle bytes.
- **Atomic output**: reducers write to temp files, rename on completion —
  re-executed tasks can't leave partial output (rename is the commit).

### Fault Tolerance
- Worker heartbeats → coordinator marks tasks on dead workers as idle,
  reschedules. Completed **map** tasks on a dead worker are re-run
  (intermediate data lived on its local disk); completed reduce tasks are
  not (output is on the DFS).
- **Stragglers**: near job end, speculatively run backup copies of the
  slowest tasks; first to finish wins (rename race is safe). This single
  trick routinely cuts tail latency 30%+.
- Coordinator crash: either restart the job (original design) or persist
  task state via Tracks 7/13.

### Milestones
1. Sequential: map + external sort + reduce in one process (word count).
2. Coordinator + workers over RPC (Track 4); M map / R reduce with shuffle.
3. Kill workers randomly mid-job → identical output every run.
4. Combiner + speculative execution; measure shuffle bytes and tail latency.
5. Run a two-job chain (word count → top-K) reading/writing the Track 16 DFS.

---

## Track 23: Distributed Search

### Problem
Full-text search over billions of documents: sub-100ms queries, ranked
results, index continuously updated.

### The Inverted Index
```
"quick brown fox" (doc 7)
tokenize → normalize (lowercase, stem) →
postings:
  quick → [(doc 7, tf=1, pos=[0]), (doc 12, ...), ...]   sorted by doc id
  brown → [(doc 7, tf=1, pos=[1]), ...]
  fox   → [(doc 3, ...), (doc 7, ...)]
```
- Query `quick AND fox` = intersect postings (galloping/skip-pointer
  intersection over sorted lists). OR = union; phrase queries check
  positions.
- **Ranking**: BM25 (tf-idf family) per term, summed; needs per-term
  document frequency and per-doc length — store them in the index.
- Compression matters: delta-encode doc ids + varints (Track 4's
  serialization); postings are the bulk of the index.

### Index Maintenance = LSM in Disguise
New docs go to an in-memory index segment; flush to immutable on-disk
segments; background **segment merges** compact them; deletes are tombstone
bitmaps applied at query time until merge. This is exactly Track 14 —
Lucene is an LSM of inverted indexes.

### Distributing It
```
            query
              │
        ┌─────▼─────┐  scatter to all shards
        │ aggregator │──────────────┐
        └─────▲─────┘               ▼
   shard 1 [docs 0-33%]   shard 2 [...]   shard 3 [...]   ← document-partitioned,
        each: top-K local results (id, score)                each shard = full
              │                                              index of its docs
        merge top-K, fetch snippets for final K only
```
- **Document partitioning** (each shard indexes a slice of docs) beats term
  partitioning (each shard owns some terms): multi-term queries stay local
  per shard, load spreads evenly. Every serious engine chose documents.
- Two-phase fetch: phase 1 returns ids+scores only (cheap); phase 2 fetches
  the full docs/snippets for the merged top K.
- Replicas per shard for throughput + availability; route with P2C (Track 11).
- Ingestion: docs flow through the Track 12 broker → indexer per shard
  (hash(doc_id) picks shard) → near-real-time refresh (flush the in-memory
  segment every ~1s).

### Failure Modes
| Failure | Handling |
|---|---|
| One shard slow → whole query slow | hedged requests to a replica after p95 deadline; or return partial results flagged `degraded` |
| Shard down | replica failover; partial results as last resort |
| Hot term (everyone searches the same thing) | query result cache (Track 10) with short TTL |
| Relevance regression after ranking change | offline evaluation set + A/B on interleaved results |
| Index/doc-store divergence | both fed from the same broker stream, idempotent by doc version |

### Milestones
1. Single-node index: tokenize, postings, AND/OR/phrase queries.
2. BM25 ranking + top-K heap; verify against a brute-force scorer.
3. Segments + merges + delete bitmaps; continuous indexing while querying.
4. Shard + aggregator with two-phase fetch; measure p99 vs shard count.
5. Hedged requests; kill/slow a shard under load, verify p99 and correctness.

---

## Track 24: Stream Processing

### Problem
Continuous computation over unbounded event streams — counts per window,
joins, sessionization — with correct results despite out-of-order events and
worker crashes.

### Dataflow Model
```
source (Track 12 broker) → operators (map/filter/keyBy/window/aggregate) → sink
   partitioned by key: keyBy(k) routes events to the operator instance
   owning k (consistent hashing again) — state is per-key, local, durable
```

### Event Time, Not Processing Time
Events arrive late and out of order (mobile clients, retries). Windowing on
arrival time gives different answers every run.
- **Event time**: each event carries its occurrence timestamp.
- **Watermark**: a flowing marker "no events with timestamp < W are still
  coming" — in practice a heuristic (`max_event_time_seen - allowed_lateness`),
  emitted by sources, min-combined across inputs.
- A tumbling window `[12:00, 12:05)` fires when the watermark passes 12:05,
  not when the wall clock does.
- **Late events** (after the watermark): drop, send to a side output, or
  re-fire the window with an update — an explicit product decision.

```
event time ─────────────────────────►
   e(12:01)  e(12:03)   e(12:02) ←late-ish   W=12:04   e(12:00) ←late, after W
   window [12:00,12:05) buffers state, fires at W ≥ 12:05
```

### Windows to Implement
Tumbling (fixed, non-overlapping), sliding/hopping (overlapping — store one
pane per slide, compose on fire), session (gap-based: merge windows when an
event bridges the gap — merging is the tricky part).

### Exactly-Once (the crown jewel)
At-least-once replay + deduplication is fine per operator, but multi-operator
state needs a consistent cut. **Chandy-Lamport style checkpoint barriers**
(Flink's algorithm):
```
1. coordinator injects barrier-n into all source partitions
2. each operator: on barrier from ALL inputs → snapshot local state
   (async to object store/DFS), forward barrier
3. all sinks ack barrier-n → checkpoint n complete; record source offsets
4. crash ⇒ restore all state from checkpoint n, rewind sources to its offsets
```
Result: internal state is exactly-once. **End-to-end** exactly-once
additionally needs transactional sinks (commit output atomically with the
checkpoint — the broker transactions from Track 12) or idempotent sinks
(keyed upserts).

### Backpressure
A slow operator must slow its upstreams, not OOM: bounded in-flight buffers
per link; sources ultimately pause consumption (the broker retains — that's
why a log broker, not a queue, feeds stream processors).

### Failure Modes
| Failure | Handling |
|---|---|
| Worker crash | restore from last checkpoint + rewind offsets |
| Out-of-order events | event time + watermarks |
| Stuck partition holds watermark back | idle-source timeout advances it (with correctness caveat) |
| Slow sink | backpressure to sources; lag alerting |
| Hot key | key salting + two-stage aggregation (partial → final) |
| State grows unbounded | window state GC after allowed-lateness horizon; TTL on keyed state |

### Milestones
1. Single-process pipeline: map/filter/keyBy/tumbling-window count from the
   Track 12 broker.
2. Event time + watermarks; verify identical results across shuffled replays.
3. Sliding + session windows with merge.
4. Barrier checkpoints + restore; kill workers randomly → counts exactly
   correct end-to-end (idempotent sink).
5. Backpressure test: throttle the sink, verify bounded memory and recovery.

---

## Track 25: Distributed Hash Table (Chord-style)

### Problem
A key/value store across thousands of peers with **no coordinator at all**:
any node can route any lookup in O(log N) hops; nodes join and leave
continuously.

### The Ring & Finger Tables
Nodes and keys hash onto the same 2^m ring (Track 9's ring, now
peer-to-peer). Key k belongs to `successor(k)` — the first node ≥ k.
```
finger[i] of node n = successor(n + 2^i),  i = 0..m-1

lookup(k) at n:
    if k ∈ (n, successor]: return successor
    else: forward to the finger closest below k     # halves distance → O(log N)
```
Each node knows only O(log N) others; no global membership anywhere.

### Join / Leave / Stabilization
Correctness rests on successor pointers only; fingers are an optimization.
- **Join**: new node n asks any node to `lookup(n)` → learns its successor;
  keys in `(predecessor, n]` transfer to n.
- **Stabilization** (periodic, gossip-flavored): ask your successor for its
  predecessor; if that node sits between you, adopt it as successor; notify
  it of yourself. This heals the ring lazily after any churn.
- **Successor lists** (r next successors, not just one): survive r-1
  simultaneous failures; the ring never partitions logically as long as one
  live successor is known.
- Fingers refresh lazily in the background — stale fingers cost hops, not
  correctness.

### Data Replication
Store each key on its successor **and the next r-1 successors**. On node
death, the next successor already has the data and simply owns it now.
Repair by anti-entropy between successors — Merkle trees over key ranges
make the diff cheap (compare roots; descend only into differing subtrees).
This is Dynamo/Cassandra's repair mechanism, built on Track 5's
convergence discipline (per-key LWW or vector clocks for conflicts).

### DHT vs the Track 9 Shard Map
| | Shard map + metadata store | DHT |
|---|---|---|
| Coordination | consensus cluster required | none |
| Lookup | O(1) (cached map) | O(log N) hops |
| Membership churn | operator-driven | continuous, automatic |
| Consistency | can be strong | eventual (typically) |
| Fits | datacenter databases | P2P, massive fleets, BitTorrent/IPFS/Cassandra's ring |

### Failure Modes
| Failure | Handling |
|---|---|
| Node vanishes silently | successor list + stabilization reroute; replicas serve data |
| Concurrent joins in one region | stabilization converges; keys re-transfer idempotently |
| Stale finger tables | extra hops only; periodic refresh |
| Network partition | each side forms a consistent sub-ring; merge on heal via stabilization + anti-entropy |
| Malicious nodes lying about the ring | out of scope here — that's Track 28 (BFT) territory |

### Milestones
1. Static ring: correct `lookup` via successors only (O(N) hops), N=32 nodes.
2. Finger tables; verify O(log N) hop counts empirically.
3. Join + stabilization under continuous churn (kill/add a node every second);
   lookups never return wrong owners after convergence.
4. Replication r=3 + Merkle anti-entropy; kill nodes, verify zero data loss.
5. Partition/heal test: rings merge, replicas reconcile, conflicts resolved
   per the Track 5 policy you chose.

---

## What Carries Forward
- MapReduce's "pure tasks + re-execution + atomic rename" discipline is the
  template for every batch system you'll meet (Spark lineage is the same bet).
- Search's segment model reinforces LSM thinking; its scatter-gather +
  hedging pattern is universal for fan-out reads.
- Stream checkpoint barriers are distributed snapshots — the same idea
  Jepsen-style consistency checking and backup systems rely on.
- The DHT closes the loop: Tracks 3 + 5 + 9 composed into a full system with
  no coordinator — the opposite pole from Raft, and the right tool when
  churn is high and consistency needs are low.

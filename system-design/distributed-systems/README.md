# Distributed Systems Design Tracks

Systems-design documentation for the distributed-systems curriculum inspired by
[builddistributedsystem.com/tracks](https://builddistributedsystem.com/tracks/) —
8 categories, 28 tracks, from message passing fundamentals to Byzantine fault
tolerance. Each design doc covers: the problem, the architecture, key components,
protocols and data flow, trade-offs, failure modes, and step-by-step
implementation milestones so you can build each system from scratch.

## How to Use These Docs

1. Read the design doc for a track **before** writing code — understand the
   architecture and failure modes first.
2. Follow the implementation milestones in order; each milestone is a working,
   testable increment.
3. After implementing, revisit the "Failure Modes" section and deliberately
   inject each failure to verify your handling.
4. Tracks build on each other — do the categories in order the first time
   through.

## The 8 Categories / 28 Tracks

### [1. Foundations — Message Passing & Networking](01-foundations.md)
| # | Track | You build |
|---|-------|-----------|
| 1 | The Messenger | A node protocol: JSON message handling, init, echo, async RPC |
| 2 | The Identifier | Globally-unique ID generation without coordination |
| 3 | The Gossiper | Broadcast: flooding → spanning tree → batched gossip |
| 4 | The Networker | TCP server, message framing, serialization, RPC/gRPC from scratch |

### [2. Agreement & State Management](02-agreement-and-state.md)
| # | Track | You build |
|---|-------|-----------|
| 5 | CRDTs | Conflict-free replicated counters, sets, registers |
| 6 | Leader Election | Heartbeats, terms, randomized election timeouts |
| 7 | Raft Log Replication | Replicated log with commit index and safety proofs |
| 8 | Linearizable KV | A consistent key/value store on top of the replicated log |

### [3. Scaling Building Blocks](03-scaling-building-blocks.md)
| # | Track | You build |
|---|-------|-----------|
| 9 | The Sharder | Consistent hashing, rebalancing, virtual nodes |
| 10 | The Cacher | Node-local cache → global cache → distributed cache |
| 11 | Load Balancers | L4 and L7 balancing, health checks, balancing algorithms |
| 12 | Message Queues | An append-only log broker: partitions, consumer groups, offsets |

### [4. Durable Storage Internals](04-durable-storage.md)
| # | Track | You build |
|---|-------|-----------|
| 13 | Write-Ahead Log | Append-only durability, fsync, checksums, recovery |
| 14 | LSM Tree | Memtable, SSTables, compaction, bloom filters |
| 15 | B-Tree | Page-based storage, splits/merges, range scans |
| 16 | Distributed File System | GFS-style chunk servers + metadata master |
| 17 | Indexes | Hash indexes, secondary indexes, covering indexes |

### [5. Workflow Coordination](05-workflow-coordination.md)
| # | Track | You build |
|---|-------|-----------|
| 18 | Distributed Transactions | Two-phase commit, sagas, outbox pattern |
| 19 | Job Scheduler | Cron-like scheduling, leases, exactly-once dispatch |
| 20 | DAG Pipelines | Dependency-ordered task execution with retries |
| 21 | Schema Migrations | Online migrations, dual writes, backfill, cutover |

### [6. Production-Grade Data Systems](06-production-systems.md)
| # | Track | You build |
|---|-------|-----------|
| 22 | MapReduce | Single-machine → distributed map/shuffle/reduce with fault tolerance |
| 23 | Distributed Search | Inverted index, sharded search, scatter-gather ranking |
| 24 | Stream Processing | Windowing, watermarks, exactly-once processing |
| 25 | Distributed Hash Table | Chord-style ring, finger tables, node join/leave |

### [7. Observability](07-observability.md)
| # | Track | You build |
|---|-------|-----------|
| 26 | Distributed Tracing & Observability | Trace context propagation, spans, metrics, log correlation |

### [8. Security & Byzantine Fault Tolerance](08-security-and-bft.md)
| # | Track | You build |
|---|-------|-----------|
| 27 | Security | mTLS, JWT auth, RBAC, encryption at rest and in transit |
| 28 | Byzantine Fault Tolerance | PBFT-style consensus tolerating malicious nodes |

## Recommended Order

```
Foundations (1-4)
    │
    ├──► Agreement & State (5-8)          ← consensus needs messaging
    │        │
    │        └──► Workflow Coordination (18-21)   ← txns need consensus concepts
    │
    ├──► Scaling Building Blocks (9-12)   ← sharding/caching need hashing + RPC
    │        │
    │        └──► Production Systems (22-25)      ← MapReduce/DHT need shards + queues
    │
    └──► Durable Storage (13-17)          ← independent; pairs well with KV store
             │
             └──► (revisit Linearizable KV with a real LSM under it)

Observability (26) and Security (27-28): weave into every track once basics work.
```

## Cross-Cutting Principles (apply to every track)

- **Design for partial failure.** Any message can be lost, delayed, duplicated,
  or reordered. Every handler must be safe under all four.
- **Idempotency before retries.** Never add a retry until the operation it
  retries is idempotent (see [`../idempotency_keys.py`](../idempotency_keys.py)).
- **Explicit timeouts everywhere.** Every blocking wait has a deadline; every
  deadline has a defined fallback behavior.
- **State machines, not flags.** Model node/connection/transaction state as an
  explicit enum with legal transitions; reject illegal ones loudly.
- **Determinism aids testing.** Inject clocks, RNGs, and network layers so
  simulation tests can replay failures deterministically (Maelstrom/Jepsen style).
- **Measure before optimizing.** Each doc's milestones end with a measurement
  step — throughput, latency percentiles, or convergence time.

## Related Material in This Repo

- [`../README.md`](../README.md) — system-design interview guide + runnable pattern templates
- [`../consistent_hash.py`](../consistent_hash.py), [`../message_queue.py`](../message_queue.py),
  [`../eventual_consistency.py`](../eventual_consistency.py) — small runnable versions of
  ideas covered in depth here
- [`../../http-server/`](../../http-server/), [`../../dns-server/`](../../dns-server/) — networking
  foundations
- [`../../distributed-training/`](../../distributed-training/) — distributed ML, which reuses
  collective-communication ideas from the Gossiper and Networker tracks

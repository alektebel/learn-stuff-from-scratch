# Category 3: Scaling Building Blocks

Tracks 9–12. The components that let one logical service run across many
machines: sharding, caching, load balancing, and asynchronous queues.

---

## Track 9: The Sharder — Consistent Hashing & Rebalancing

### Problem
Spread keys across N nodes so that (a) any node can compute where a key lives,
(b) adding/removing a node moves only ~1/N of the keys, and (c) no shard gets
disproportionately hot.

### Why Not `hash(key) % N`
Changing N remaps almost *every* key → a full cache flush / data migration on
every topology change. Consistent hashing fixes exactly this.

### The Hash Ring
```
        0/2^32
          │
   ┌──── n3-v2 ────┐          key k → hash(k) → walk clockwise
   │               │          → first virtual node → owner
 n1-v1           n2-v1
   │               │          each physical node appears as
   └──n2-v2───n1-v2┘          V virtual nodes (vnodes)
```
- **Virtual nodes** (100–256 per physical node) smooth out placement variance:
  without them, node ranges vary wildly in size; with them, load spread
  tightens to within a few percent.
- Adding a node claims V small arcs from many owners → migration load is
  spread across the whole cluster, not one donor.

### Alternative: Explicit Shard Map (what real databases do)
Pre-split the keyspace into many fixed shards (e.g. 1024), store
`shard → node` in a strongly-consistent metadata store (Track 8's KV!):
```
shard = hash(key) % 1024          # never changes
owner = shard_map[shard]          # changes on rebalance
```
| | Hash ring | Shard map |
|---|---|---|
| Coordination | none (deterministic) | metadata store required |
| Rebalance granularity | vnode arcs | individual shards |
| Custom placement (hot shard isolation) | hard | trivial — edit the map |
| Used by | Dynamo, Cassandra, memcached clients | Redis Cluster (slots), Vitess, CockroachDB |

Build the ring first, then the shard map with a rebalancer.

### Rebalancing Protocol (shard map)
Moving shard S from A to B without downtime:
```
1. mark S as MIGRATING(A→B) in the map
2. B pulls a snapshot of S from A; A forwards new writes to B (dual-write)
   or A logs writes and B replays the tail
3. when B is caught up: map[S] = B (atomic CAS in metadata store)
4. A serves a brief "moved" redirect for stragglers, then drops S
```
Clients cache the map and handle `MOVED shard → node` redirects
(the Redis Cluster pattern).

### Hot Shards
- Detect: per-shard QPS histogram; flag shards > k× median.
- Fix: split the hot shard's range, or salt hot keys across R replicas
  (see [`../hot_partition_mitigation.py`](../hot_partition_mitigation.py)).

### Failure Modes
| Failure | Handling |
|---|---|
| Node dies mid-migration | migration state is in the metadata store; restart or abort the move |
| Client has stale map | MOVED redirect + map refresh |
| Two rebalancers run | all map edits are CAS ops on the metadata store |
| Cascading overload after node loss | its shards spread over *all* survivors (vnodes/map), not one neighbor |

### Milestones
1. Hash ring with vnodes; measure key distribution stddev at V = 1, 16, 128.
2. Add/remove node; verify only ~K/N keys moved.
3. Shard map on a KV metadata store; MOVED redirects in the client.
4. Live migration with dual-write cutover; zero lost writes under load.
5. Hot-shard detector + split; verify p99 latency recovers.

---

## Track 10: The Cacher — From Node Cache to Distributed Cache

### Problem
Serve reads at memory speed while bounding staleness and surviving cache
node failures. Built in three stages: per-node cache → shared global cache →
sharded distributed cache.

### Stage 1 — Node-Local Cache
An in-process LRU with TTL (see [`../cache.py`](../cache.py)).
- **Cache-aside**: `get → miss → load from DB → set(ttl)`.
- Eviction: LRU for recency-skewed traffic; LFU/W-TinyLFU when scans pollute LRU.
- Problem: N app servers = N copies, N× DB load on invalidation, inconsistent
  views between servers.

### Stage 2 — Global Cache (one shared tier)
```
app servers ──► cache tier (Redis/memcached-like) ──miss──► DB
```
Consistency discipline (the part everyone gets wrong):
- **Invalidate, don't update** on write: `write DB → delete cache key`.
  Updating the cache races with concurrent writes (older value can land last).
- Even delete-after-write has a race (read misses, reads old DB value, write
  commits, delete runs, stale read fills cache). Mitigations: short TTL as a
  backstop; CAS-style versioned sets; or invalidation via DB changelog (CDC).
- **Stampede protection**: on hot-key miss, only one loader goes to the DB
  (per-key mutex / singleflight); others wait or serve stale
  (`stale-while-revalidate`).

### Stage 3 — Distributed Cache
Shard the cache tier with the Track 9 ring (client-side hashing — memcached
model: servers don't know about each other).
- **Replication for hot keys**: R copies, read from any, invalidate all.
- **Failure policy**: on node death, its arc misses fall through to the DB.
  Size the DB to survive `1/N` of cache traffic, or add a small L1 in-process
  cache in front to absorb the spike.
- **Thundering herd on restart**: a cold cache node takes 100% misses —
  warm it (replay hot keys) before putting it in rotation.

### Metrics That Matter
hit ratio (per key-class, not just global), p99 get latency, DB QPS
(the real protection target), evictions/sec, memory fragmentation.

### Failure Modes
| Failure | Handling |
|---|---|
| Stale data after write | delete-on-write + TTL backstop + CDC invalidation |
| Hot key stampede | singleflight + stale-while-revalidate |
| Cache node dies | consistent hashing limits blast radius to its arc |
| Cache tier fully down | load-shed at the DB: serve degraded results rather than melting it |
| Big value evicts everything | per-item size cap; separate pools per object class |

### Milestones
1. LRU+TTL node cache with cache-aside; measure hit ratio on a Zipf workload.
2. Global cache with delete-on-write; demonstrate (then mitigate) the
   stale-fill race in a test.
3. Singleflight stampede protection; verify one DB load per hot-key miss wave.
4. Shard with the ring; kill a node, measure DB QPS spike and recovery.
5. Add hot-key replication; verify p99 under a single-key flood.

---

## Track 11: Load Balancers

### Problem
Distribute client traffic over backend replicas, detect unhealthy backends,
and do it at two levels: L4 (TCP connections) and L7 (HTTP requests).

### L4 vs L7
| | L4 (transport) | L7 (application) |
|---|---|---|
| Balances | TCP connections / flows | individual HTTP requests |
| Sees | IPs and ports | paths, headers, cookies |
| Cost | very cheap (no parsing) | parse + re-serialize each request |
| Features | pass-through, DSR possible | routing rules, retries, sticky sessions, TLS termination |

Real stacks layer them: anycast/ECMP → L4 tier → L7 tier → services.

### Balancing Algorithms
- **Round robin**: baseline; ignores request cost variance.
- **Weighted RR**: capacity-aware static weights.
- **Least connections**: good for long-lived / variable-cost work.
- **Power of two choices (P2C)**: pick 2 random backends, send to the less
  loaded — near-optimal load spread with O(1) state, no global view needed.
  The default choice for distributed L7 fleets.
- **Consistent hash on key** (client IP, session, cache key): stickiness and
  cache locality — reuse the Track 9 ring.

### Health Checking
```
active:  probe /healthz every T; state machine per backend:
         HEALTHY ──k consecutive fails──► UNHEALTHY ──m passes──► HEALTHY
passive: count in-band errors/timeouts; eject outliers temporarily
```
- **Slow start**: a newly-healthy backend ramps from low weight — a cold
  JIT/cache instantly flooded at full weight fails again ("yo-yo").
- **Panic threshold**: if > X% of backends look unhealthy, ignore health and
  send everywhere — the checker is more likely wrong than 80% of the fleet.

### L7 Extras
- **Retries with budget**: retry idempotent requests on connect
  failure/5xx, but cap retries at a % of traffic — unbounded retries turn a
  brownout into an outage (retry storm).
- **Draining**: on deploy, stop new requests to a backend, let in-flight
  finish, then kill. Connection: `Connection: close` / GOAWAY for HTTP/2.
- **Timeouts**: separate connect / header / total budgets, always shorter
  than the client's.

### Failure Modes
| Failure | Handling |
|---|---|
| Backend dies mid-request | retry on a different backend (idempotent only) |
| Slow backend drags fleet p99 | least-conn/P2C route around it; passive ejection |
| Health-check flapping | hysteresis (k fails / m passes), slow start |
| LB itself is the SPOF | multiple LBs behind DNS/anycast; keep LBs stateless |
| Retry storm during brownout | retry budgets + circuit breaker ([`../circuit_breaker.py`](../circuit_breaker.py)) |

### Milestones
1. L4 TCP proxy: accept, connect upstream, bidirectional pipe with timeouts.
2. Round robin + least-conn + P2C; compare p99 under variable request cost.
3. Active + passive health checks with hysteresis and slow start.
4. L7 HTTP proxy: parse requests, per-route backends, sticky cookie.
5. Retry budget + draining; deploy-under-load test with zero failed requests.

---

## Track 12: Message Queues — An Append-Only Log Broker

### Problem
Decouple producers from consumers with a durable, ordered, replayable
message log (the Kafka model), supporting consumer groups, offset tracking,
and at-least-once (then effectively-once) delivery.

### Log-Based, Not Queue-Based
Classic queues (SQS/RabbitMQ) delete on ack; a log broker **retains**
messages and consumers track their own position:

```
topic "orders", partition 0:
offset: 0    1    2    3    4    5
      ┌────┬────┬────┬────┬────┬────┐
      │ m0 │ m1 │ m2 │ m3 │ m4 │ m5 │──► appends
      └────┴────┴────┴────┴────┴────┘
        ▲              ▲
     consumer B     consumer A     (independent offsets; replay = rewind)
```

### Partitioning & Ordering
- A topic = many partitions; **ordering is guaranteed only within a
  partition**. Producer picks partition by `hash(key) % P` → all events for
  one entity stay ordered.
- Parallelism = partition count; choose P generously up front (repartitioning
  breaks key→partition mapping).

### Consumer Groups
```
partitions:  p0   p1   p2   p3
group G:     c1   c1   c2   c2      ← each partition owned by exactly one
                                      consumer in the group
```
- Broker (or a group coordinator) assigns partitions; on consumer
  join/leave/death → **rebalance**.
- Offsets are committed back to the broker (itself a compacted topic).
  Commit *after* processing = at-least-once; commit *before* = at-most-once.

### Delivery Semantics
- **At-least-once** + idempotent consumers is the workhorse
  (see [`../idempotency_keys.py`](../idempotency_keys.py)).
- **Effectively-once**: idempotent producer (sequence number per
  producer/partition, broker dedupes) + transactional
  consume-transform-produce (offsets committed atomically with output).
- **DLQ**: after N failed processing attempts, park the message in
  `topic.dlq` with error metadata; never poison-pill the partition.

### Durability & Replication
Each partition is a Raft-style replicated log (Track 7) or ISR-based
(leader + in-sync replicas; ack when all ISR have it). Producer `acks=all`
vs `acks=leader` trades latency for durability. fsync policy: per-message
(slow, safe) vs periodic (fast, small loss window) — replication makes
periodic acceptable.

### Failure Modes
| Failure | Handling |
|---|---|
| Consumer crash after processing, before commit | redelivery → consumer idempotency |
| Rebalance storm (consumers flapping) | session timeouts + incremental/sticky rebalance |
| Slow consumer lag grows unbounded | lag metrics + alerts; scale consumers up to partition count |
| Poison message | retry cap + DLQ |
| Broker leader dies | replica promotion; producer retries (idempotent producer prevents dupes) |
| Disk full | retention enforcement (time/size), tiered storage |

### Milestones
1. Single-partition in-memory log: append, fetch-from-offset, consumer polls.
2. Durability: segment files + index, recovery scan on restart (uses Track 13's WAL ideas).
3. Partitions + key hashing; per-key ordering test.
4. Consumer groups with rebalance and committed offsets.
5. Replicated partitions + idempotent producer; kill-the-leader test with
   zero loss and zero duplicates end-to-end.

---

## What Carries Forward
- The ring/shard map routes cache keys (10), sticky sessions (11), DHT keys (25).
- The log broker is the backbone of stream processing (24), the outbox
  pattern (18), and CDC-driven cache invalidation (10).
- P2C and retry budgets reappear in every service-to-service client you build.

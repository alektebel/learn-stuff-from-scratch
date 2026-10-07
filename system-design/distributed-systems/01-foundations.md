# Category 1: Foundations — Message Passing & Networking

Tracks 1–4. Everything else in distributed systems is built on the ability to
send a message to another node and cope with the fact that it may never arrive.

---

## Track 1: The Messenger — Node Protocol & Async RPC

### Problem
Build a node that participates in a distributed system by exchanging JSON
messages over an abstract network (the Maelstrom model: messages arrive on
stdin, are sent on stdout, and the test harness plays the network). The node
must handle initialization, respond to echo requests, and support asynchronous
RPC with retries.

### Message Model
Every message has an envelope and a body:

```json
{
  "src":  "n1",
  "dest": "n2",
  "body": {
    "type":   "echo",
    "msg_id": 42,
    "echo":   "hello"
  }
}
```

Replies reference the request: `{"type": "echo_ok", "in_reply_to": 42, ...}`.

### Architecture
```
            stdin (one JSON msg per line)
               │
        ┌──────▼──────┐
        │  Reader loop │  parse → dispatch by body.type
        └──────┬──────┘
               │
   ┌───────────┼─────────────────┐
   │           │                 │
┌──▼───┐  ┌────▼─────┐  ┌────────▼────────┐
│ init │  │ handlers │  │ RPC reply router │  in_reply_to → pending future
└──┬───┘  └────┬─────┘  └────────┬────────┘
   │           │                 │
        ┌──────▼──────┐
        │ Writer (locked stdout, one msg per line) │
        └─────────────┘
```

Key components:
- **Node identity**: the `init` message assigns `node_id` and the full
  `node_ids` list. Nothing else may run before init completes.
- **msg_id allocator**: monotonically increasing counter per node. Combined
  with `src`, `(src, msg_id)` is globally unique — the foundation of RPC
  matching and deduplication.
- **RPC layer**: `rpc(dest, body) -> Future`. Store the future keyed by
  `msg_id`; the reply router completes it when a message with matching
  `in_reply_to` arrives.
- **Retry with backoff**: if no reply within timeout, resend with the *same*
  `msg_id` (so the receiver can dedupe) using exponential backoff + jitter:
  `delay = min(cap, base * 2^attempt) + rand(0, jitter)`.

### Design Decisions & Trade-offs
- **Single reader thread, handler thread pool**: handlers must not block the
  read loop, or a slow handler stalls all RPC replies (deadlock: handler waits
  on RPC whose reply can't be read).
- **At-least-once + idempotent handlers** rather than trying for exactly-once
  transport — exactly-once delivery is impossible; exactly-once *effect* is
  achieved by dedup at the receiver.
- **Locked writes**: concurrent handlers share stdout; interleaved partial
  lines corrupt the protocol. One mutex around "serialize + write + flush".

### Failure Modes
| Failure | Symptom | Handling |
|---|---|---|
| Reply lost | RPC future never completes | timeout → resend same msg_id |
| Request duplicated | handler runs twice | dedupe by `(src, msg_id)` seen-set |
| Handler blocks on RPC inside read loop | whole node freezes | never await in the reader thread |
| Out-of-order replies | wrong future completed | match strictly on `in_reply_to` |

### Milestones
1. Parse/emit the envelope; handle `init` → `init_ok`.
2. Handle `echo` → `echo_ok`.
3. Add the RPC layer with futures and timeouts.
4. Add retry with exponential backoff and receiver-side dedup.
5. Measure: sustained msgs/sec with 10 concurrent handlers, zero lost replies
   under a 10%-drop simulated network.

---

## Track 2: The Identifier — Globally Unique IDs

### Problem
Generate IDs that are unique across all nodes, forever, with **no
coordination** — even during network partitions. Every node must keep
generating.

### Candidate Designs
| Strategy | ID | Pros | Cons |
|---|---|---|---|
| Central counter | 1,2,3… | ordered, dense | SPOF, coordination, doesn't survive partitions |
| UUIDv4 | 128-bit random | zero coordination | large, unordered, index-hostile |
| `node_id + local counter` | `"n1-42"` | trivial, partition-safe | not time-ordered, needs stable node ids |
| Snowflake | `timestamp | node_id | sequence` | 64-bit, roughly time-ordered, k-sortable | clock skew hazards |

### Recommended: Snowflake Layout
```
 63          22          12           0
 ┌───────────┬───────────┬───────────┐
 │ 41b epoch │ 10b node  │ 12b seq   │
 │  millis   │    id     │ per-ms    │
 └───────────┴───────────┴───────────┘
```
- 41 bits of milliseconds since a custom epoch ≈ 69 years.
- 10 bits of node id = 1024 nodes (assigned at init — the only coordination,
  done once).
- 12 bits of sequence = 4096 IDs/ms/node; if exhausted, spin until next ms.

### The Clock Problem
Snowflake's correctness depends on the local clock never going backwards.
- Track `last_timestamp`; if `now < last_timestamp` (NTP step, VM migration),
  either **wait** it out (small skew) or **refuse to generate** (large skew).
  Never emit an ID with a reused (timestamp, seq) pair.
- Alternative: logical hybrid clocks (HLC) — `max(wall, last+1)` — keep IDs
  monotonic per node without waiting.

### Failure Modes
| Failure | Handling |
|---|---|
| Clock steps backwards | block or error; never reuse a timestamp |
| Two nodes get same node_id | catastrophic — assign ids from `init`'s `node_ids` index |
| 4096 ids in one ms exhausted | busy-wait for next millisecond |
| Partition | nothing to do — that's the point; no coordination needed |

### Milestones
1. `generate` → `generate_ok` returning `f"{node_id}-{counter}"`.
2. Swap to 64-bit Snowflake with the bit layout above.
3. Add backwards-clock detection and the spin-on-sequence-exhaustion path.
4. Verify: 3 nodes × 100k IDs under partition → zero duplicates (sort & scan).

---

## Track 3: The Gossiper — Broadcast & Gossip Protocols

### Problem
Every node receives values via `broadcast` messages; eventually **every node
must know every value**, even with message loss and partitions, while keeping
messages-per-broadcast and latency low.

### Evolution of the Design

**v1 — Flooding.** On receiving a new value, forward to every neighbor.
Correct, but O(N²) messages and re-broadcast storms. Needs a `seen` set to
stop echoing forever.

**v2 — Spanning tree.** The harness supplies a topology; only forward along
tree edges. O(N) messages per broadcast, but a single lost message
partitions the tree → some nodes never converge. Fix with per-neighbor
retry-until-ack:

```
on broadcast(v):
    if v in seen: reply ok; return
    seen.add(v)
    for nbr in tree_neighbors - {sender}:
        retry_until_ack(nbr, broadcast(v))     # async, backoff
    reply ok
```

**v3 — Batched gossip.** Instead of one message per value, each node
periodically (e.g. every 100–500 ms) sends its recent-values delta to a few
random peers and reconciles:

```
every T ms:
    for peer in sample(peers, fanout):
        send(peer, {type: "gossip", values: seen - known_by[peer]})
on gossip(values):
    seen |= values
    reply with (my seen - their values)         # anti-entropy, both directions
```

Track `known_by[peer]` (what you've confirmed each peer has) to shrink deltas.

### Tuning Knobs
- **Fanout** (peers per round) and **interval** trade latency vs. bandwidth.
  Infection-style spread reaches all N nodes in O(log N) rounds.
- **Batching window**: bigger batches amortize per-message overhead; the
  latency floor is roughly `interval × log_fanout(N)`.
- Target-style budgets (from the original challenge): <30 msgs/op with ≤
  ~5s convergence, then <20 msgs/op with relaxed latency — you tune interval
  and fanout to hit them.

### Failure Modes
| Failure | Handling |
|---|---|
| Message loss | anti-entropy exchange repairs missed values eventually |
| Partition | each side converges internally; full convergence on heal (keep gossiping to unreachable peers at low rate) |
| Re-broadcast storms | `seen` set + never forward back to sender |
| Hot node (star topology) | random peer sampling instead of fixed tree |

### Milestones
1. Single-node broadcast: store values, answer `read` with all seen.
2. Multi-node flooding with `seen`-set dedup.
3. Tree forwarding + retry-until-ack; pass a 100%-connectivity check under loss.
4. Batched gossip with `known_by` deltas; measure msgs/op and convergence time.
5. Chaos test: kill links for 10s, verify convergence within a few seconds of heal.

---

## Track 4: The Networker — TCP, Framing, Serialization, RPC

### Problem
Drop the simulated network: build real transport. A TCP echo server, then a
length-prefixed message protocol, then binary serialization, then a small
gRPC-style RPC framework on top.

### Layer 1 — TCP Server
```
listener ──accept──► per-connection handler (thread or event loop)
```
- TCP is a **byte stream, not a message stream**: one `send` may arrive as
  several `recv`s, or several sends as one. All framing bugs come from
  ignoring this.
- Handle: partial reads, connection reset, half-close, `TIME_WAIT`
  (use `SO_REUSEADDR`), and idle-connection timeouts.
- Concurrency models: thread-per-connection (simple, ~10k conns max) vs
  event loop + non-blocking sockets (epoll/kqueue; C10K+).

### Layer 2 — Message Framing
Length-prefix framing (the industry default):
```
┌──────────────┬──────────────────────┐
│ 4B big-endian│  payload (len bytes) │
│    length    │                      │
└──────────────┴──────────────────────┘
```
- Read loop: read exactly 4 bytes → parse len → read exactly len bytes.
  Both reads must loop until complete (`recv` may return fewer).
- Enforce a **max frame size** — otherwise one malicious/buggy 2GB length
  prefix OOMs the server.
- Alternatives: delimiter framing (`\n`, requires escaping) and
  self-describing formats — length-prefix is simplest and fastest.

### Layer 3 — Serialization
- Start with JSON (debuggable), then a binary format: field tags + wire types
  (protobuf's model) or a fixed schema struct packing.
- Concepts to implement: varint encoding, tagged fields for **forward/backward
  compatibility** (unknown tags are skipped, new fields are optional),
  and a schema-evolution rule: *never reuse or renumber a tag*.

### Layer 4 — RPC Framework (gRPC from first principles)
```
client stub                          server
  call(method, req)                    │
    │ frame{stream_id, method, bytes}  │
    ├──────────────────────────────────►  dispatch(method) → handler
    │ frame{stream_id, status, bytes}  │
    ◄──────────────────────────────────┤
  future.resolve(resp)
```
- **Stream/request IDs** multiplex many in-flight calls over one connection
  (what HTTP/2 gives gRPC).
- **Deadlines propagate**: client sends its deadline; server aborts work past
  it and returns `DEADLINE_EXCEEDED`.
- **Status codes** are part of the protocol (OK / NOT_FOUND / UNAVAILABLE /
  DEADLINE_EXCEEDED…), distinct from transport errors.
- Connection management: reconnect with backoff, heartbeat/keepalive frames to
  detect dead peers behind NAT/firewalls.

### Failure Modes
| Failure | Symptom | Handling |
|---|---|---|
| Partial read treated as full message | garbled frames, desync forever | read-exactly loops; kill connection on desync |
| Slow client | server buffers balloon | bounded write queues + backpressure or disconnect |
| Dead peer, no RST | requests hang | keepalive pings + idle timeout |
| Huge length prefix | OOM | max frame size, reject & close |
| Server restart | in-flight calls lost | client retries idempotent methods only, with backoff |

### Milestones
1. TCP echo server + client; prove correctness with a fragmenting proxy
   (splits every write into 1-byte chunks).
2. Length-prefixed framing with max-size enforcement.
3. Binary serialization with tagged fields; round-trip old-schema ↔ new-schema.
4. RPC layer: multiplexed calls, deadlines, status codes, reconnect.
5. Load test: 1k concurrent connections, measure p50/p99 latency and conns/sec.

---

## What Carries Forward
- `(src, msg_id)` dedup and retry-with-same-id → every later track's RPC layer.
- Gossip anti-entropy → CRDT sync (Track 5) and DHT stabilization (Track 25).
- Framing + serialization → the storage engines' on-disk formats (Tracks 13–15).
- Deadline propagation → distributed transactions and job scheduling (Tracks 18–19).

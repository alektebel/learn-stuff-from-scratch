# Category 2: Agreement & State Management

Tracks 5–8. How replicas agree on state: first without coordination (CRDTs),
then with coordination (leader election → Raft log replication → a
linearizable key/value store).

---

## Track 5: CRDTs — Conflict-Free Replicated Data Types

### Problem
Replicas accept writes independently (even under partition) and must converge
to the same value once they exchange state — with **no consensus, no leader,
no conflicts to resolve by hand**.

### The Core Idea
A state-based CRDT is a data type whose states form a *join-semilattice*:
there is a `merge(a, b)` that is **commutative, associative, and idempotent**.
If every replica eventually receives every other replica's state (gossip from
Track 3), all replicas converge. Order and duplication of merges don't matter.

### The Types to Build

**G-Counter (grow-only counter)**
```
state:  {node_id: count}          # each node increments only its own slot
value:  sum(state.values())
merge:  per-key max
```

**PN-Counter** — two G-Counters, `P` for increments, `N` for decrements;
`value = P.value() - N.value()`.

**G-Set / 2P-Set** — grow-only set (merge = union); 2P-Set adds a tombstone
set for removals. Limitation: an element removed can never be re-added.

**OR-Set (observed-remove set)** — each add gets a unique tag
(Track 2's IDs!); remove deletes only the tags it has *observed*. Re-add
works because it creates a new tag. This is the practical replicated set.

**LWW-Register** — value + timestamp; merge keeps the larger timestamp
(tiebreak by node id). Cheap, but concurrent writes silently drop one value —
acceptable for "last edit wins" semantics only.

### Op-Based vs State-Based
| | State-based (CvRDT) | Op-based (CmRDT) |
|---|---|---|
| Ship | whole state (or delta) | operations |
| Network needs | eventual delivery, any order, dupes OK | exactly-once *causal* delivery |
| Cost | large states, cheap requirements | small messages, needs reliable broadcast |

Build state-based first (works over Track 3's gossip unchanged), then add
**delta-CRDTs**: ship only the recently-changed portion, merge as usual.

### Causality: Vector Clocks
To *detect* concurrency (e.g., for multi-value registers):
```
VC: {node_id: counter}
a ≤ b  iff  ∀k: a[k] ≤ b[k]        # a happened-before b
a ∥ b  iff  neither ≤               # concurrent → keep both (siblings)
```
This is how Dynamo-style stores expose conflicts instead of dropping them.

### Failure Modes
| Failure | Handling |
|---|---|
| Lost gossip | idempotent merge → next round repairs |
| Partition | both sides accept writes; merge on heal, no conflicts by construction |
| Counter "decrement below zero" invariant | CRDTs can't enforce global invariants — that needs consensus (Track 7) |
| Unbounded tombstones (OR-Set) | garbage-collect tags once all replicas ack (requires a stability protocol) |

### Milestones
1. G-Counter over gossip: `add`/`read`, eventually-consistent totals.
2. PN-Counter; verify convergence under partition with concurrent +/-.
3. OR-Set with unique tags; test remove-then-re-add under partition.
4. Vector clocks; detect and surface concurrent LWW writes as siblings.
5. Delta-CRDT optimization; measure bytes/round vs full-state gossip.

---

## Track 6: Leader Election

### Problem
Exactly one node should act as coordinator at a time. Nodes crash and
recover; the network partitions. Electing *two* leaders must never corrupt
state; having *zero* leaders temporarily is acceptable (liveness hit, not
safety).

### Raft-Style Election (the design to build)
Node states and transitions:
```
              times out, starts election
   FOLLOWER ───────────────────────────► CANDIDATE
      ▲   ▲                                │  │
      │   │ discovers higher term          │  │ wins majority vote
      │   └────────────────────────────────┘  ▼
      └──────────────────────────────────── LEADER
              discovers higher term
```

Core mechanics:
- **Terms**: a monotonically increasing logical epoch. Every message carries
  the sender's term; seeing a higher term ⇒ step down to follower and adopt it.
- **Randomized election timeout** (e.g. 150–300 ms): followers that hear no
  heartbeat start an election. Randomization breaks split-vote livelock.
- **Vote rules**: one vote per term (persisted!), granted only if the
  candidate's log is at least as up-to-date as yours (matters in Track 7).
- **Majority quorum**: a candidate needs ⌈(N+1)/2⌉ votes. Two majorities in
  the same term are impossible → at most one leader per term.
- **Heartbeats**: leader sends empty AppendEntries every ~50 ms to suppress
  elections.

### Why Majority, Not "First to Claim"
A partition creates two groups. Only the group with a majority can elect;
the minority side stays leaderless (correct — it also can't commit writes).
This is the CP choice: consistency over availability for the minority side.

### Persistence Requirement
`currentTerm` and `votedFor` must be fsync'd **before** replying to a vote
request. A node that votes, crashes, restarts, and votes again in the same
term can create two leaders.

### Failure Modes
| Failure | Handling |
|---|---|
| Split vote | randomized timeouts; retry next term |
| Old leader isolated, keeps serving | it can't commit (no quorum); on heal it sees higher term and steps down. Reads need the same guard (lease or read-index) |
| Flapping node triggers constant elections | pre-vote phase: probe electability before incrementing term |
| Clock skew | irrelevant — terms are logical, timeouts are local-only |

### Milestones
1. States + terms + heartbeats: with no failures, node 0 becomes leader and stays.
2. Kill the leader → a new leader emerges within one timeout period.
3. Persist term/vote; crash-restart tests can't produce two leaders in a term.
4. Partition tests: minority never elects; heal → single leader at highest term.
5. Add pre-vote; measure elections/minute under a flapping node before/after.

---

## Track 7: Raft Log Replication

### Problem
The elected leader must replicate an ordered log of commands so that every
node applies the **same commands in the same order**, and committed entries
survive any minority of crashes.

### Log Structure
```
index:   1     2     3     4     5
       ┌────┬─────┬─────┬─────┬─────┐
       │t=1 │ t=1 │ t=2 │ t=3 │ t=3 │    each entry: (term, command)
       └────┴─────┴─────┴─────┴─────┘
                          ▲
                    commitIndex
```

### Replication Flow
```
client ──cmd──► LEADER
                 1. append (term, cmd) to own log
                 2. AppendEntries(prevLogIndex, prevLogTerm, entries, leaderCommit)
                    ──► each follower
                 3. follower: reject if log[prevLogIndex].term ≠ prevLogTerm
                              else truncate conflicts, append, ack
                 4. entry replicated on majority → commitIndex = index
                 5. apply to state machine, reply to client
```

Key invariants (the safety core):
- **Log Matching**: if two logs have the same (index, term), all prior
  entries are identical. Enforced by the `prevLogIndex/prevLogTerm` check.
- **Leader Completeness**: election restriction (Track 6's up-to-date vote
  rule) guarantees a new leader has every committed entry.
- **Commit rule**: a leader only advances commitIndex for entries **of its
  own term** (committing prior-term entries directly is the famous Figure 8
  bug); prior-term entries commit implicitly once a current-term entry does.

### Per-Follower Bookkeeping (leader side)
- `nextIndex[f]`: next entry to send; on reject, decrement and retry
  (optimization: follower returns its conflict term/first-index to skip back
  in one round trip).
- `matchIndex[f]`: highest replicated index; commitIndex = the median of
  matchIndexes (majority rule).

### What Must Hit Disk, When
`log[]`, `currentTerm`, `votedFor` — fsync **before** acking anything.
Batch: group commit multiple entries per fsync for throughput.

### Compaction
The log grows forever → snapshot the state machine at index i, discard
entries ≤ i, and add `InstallSnapshot` RPC for followers that fell behind
the snapshot horizon.

### Failure Modes
| Failure | Handling |
|---|---|
| Follower crash | leader retries AppendEntries forever; catch-up via nextIndex backoff |
| Leader crash after local append, before replicate | entry is uncommitted; new leader's log wins, old entry truncated |
| Divergent follower logs | log-matching check truncates the follower's conflicting suffix |
| Slow follower falls behind snapshot | InstallSnapshot |
| Duplicate client command on leader failover | client session table: (client_id, seq) → cached response |

### Milestones
1. Leader appends + replicates to followers; commit on majority ack.
2. Consistency check (prevLogIndex/Term) + conflict truncation.
3. Persistence + crash-restart of any minority preserves committed entries.
4. Commit-rule correctness: reproduce Figure 8 scenario in a test, verify no
   committed entry is ever lost.
5. Snapshots + InstallSnapshot; bounded disk usage under continuous load.

---

## Track 8: Linearizable Key/Value Store

### Problem
Expose `read(k)`, `write(k, v)`, and `cas(k, from, to)` with
**linearizability**: every operation appears to take effect atomically at
some point between its start and its response, consistent with real time.

### Architecture
```
client ──► any node ──forward──► leader ──► Raft log ──► apply to KV map
                                                     └──► reply to client
```
The state machine is just a hash map; all the difficulty is in the guarantees.

### Writes and CAS
Every mutation goes through the log (Track 7). CAS is why a log is needed at
all: `cas` must observe the *latest* committed value — the log's total order
provides exactly that. Apply is deterministic:

```
apply(entry):
    match entry.op:
        write(k,v):        kv[k] = v
        cas(k,from,to):    ok = (kv.get(k) == from); if ok: kv[k] = to
    session[entry.client].last = (entry.seq, result)     # dedup replay
```

### Reads — Three Designs, Increasing Cleverness
| Approach | Latency | Guarantee | Cost |
|---|---|---|---|
| Read through the log | 1 consensus round | linearizable | slow, log grows |
| **Read-index** | 1 heartbeat round | linearizable | leader confirms quorum leadership, waits until applied ≥ commitIndex, serves from map |
| Leader lease | local read | linearizable *iff clocks are bounded* | risky; needs clock-skew bound |

Build read-index. A follower can serve reads too: ask leader for the current
commitIndex (read-index), wait for local apply to catch up, then read.

### Exactly-Once Client Semantics
Client retries after leader failover can re-execute a write. Fix:
- client attaches `(client_id, seq)` to every command;
- state machine stores last seq + response per client;
- replayed commands return the cached response instead of re-applying.
This table is part of the state machine → included in snapshots.

### Verifying Linearizability
Don't trust — check. Record a concurrent history of (invoke, complete)
events and run a checker (Knossos/Porcupine-style, or Jepsen/Maelstrom's
built-in `lin-kv` workload). A single CAS-loop counter over 5 nodes under
partitions is the standard torture test.

### Failure Modes
| Failure | Handling |
|---|---|
| Stale read from deposed leader | read-index quorum check refuses |
| Client retry duplicates a write | session table dedup |
| Request to follower | forward to leader (or follower read-index reads) |
| Leader dies mid-request | client times out, retries against new leader; dedup makes it safe |

### Milestones
1. KV state machine over the Raft log: write/read/cas through the log.
2. Session table for exactly-once client semantics.
3. Read-index reads; measure read latency vs through-the-log.
4. Pass a linearizability checker under partitions + leader kills.
5. Throughput: batch log appends, pipeline AppendEntries; measure ops/sec.

---

## What Carries Forward
- The replicated-log + state-machine pattern is reused verbatim for: queue
  brokers (Track 12), job schedulers (Track 19), and txn coordinators (Track 18).
- CRDT merge discipline returns in DHT replica sync (Track 25) and
  multi-region caches (Track 10).
- The linearizable KV becomes the *metadata store* for the DFS master
  (Track 16) and the shard map (Track 9).

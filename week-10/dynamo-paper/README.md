# Dynamo From Scratch

Implement Amazon's Dynamo paper directly, in pure Python, one mechanism at a time.

> **DeCandia et al., "Dynamo: Amazon's Highly Available Key-value Store", SOSP 2007.**
> [Paper PDF](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)

Read the paper alongside the code. Every file names the section it implements, and the
goal is that after finishing you could re-derive the paper's design decisions rather
than just recite them.

## Goal

Dynamo is the origin of a whole family of systems — Cassandra, Riak, Voldemort, and
(loosely) DynamoDB. It is worth implementing because it makes one uncomfortable trade
explicit and then follows it all the way through:

**Availability is chosen over consistency, on the write path, deliberately.** A Dynamo
write is never rejected because replicas disagree. The cost is that reads can return
several conflicting versions, and the application — not the database — has to merge them.

Almost everything else in the paper follows from that decision.

## What Dynamo actually is

| Problem | Technique | Section | File |
|---|---|---|---|
| Partitioning | Consistent hashing with virtual nodes | 4.2 | `partitioning.py` |
| High availability for writes | Vector clocks, reconciled on read | 4.4 | `vector_clock.py` |
| Handling temporary failures | Sloppy quorum + hinted handoff | 4.6 | `hinted_handoff.py` |
| Recovering from permanent failures | Anti-entropy with Merkle trees | 4.7 | `merkle_sync.py` |
| Membership and failure detection | Gossip-based protocol | 4.8 | `gossip.py` |

That table is Table 1 from the paper. The quorum layer (`quorum.py`) sits between
partitioning and hinted handoff, and `dynamo_cluster.py` assembles the lot.

---

## How to use this directory

The files at the top level are **templates**: every function has a docstring
explaining what to build and why, then `raise NotImplementedError`. You fill
them in. `solutions/` holds complete working versions for when you are stuck or
want to compare afterwards.

```bash
cd dynamo-paper
python3 check.py            # what to build next
# ... implement the functions the checker points at ...
python3 check.py            # re-run; it stops at the first thing not yet done
```

`check.py` runs 17 graded checks against **your** code (it never imports
`solutions/`). Each one names the file, the concept, and — when something is
wrong — what usually causes it:

```
  ✓  1. partitioning.py      ring: add/remove/coordinator
  ✓  2. partitioning.py      preference lists (N distinct nodes)
  ·  3. partitioning.py      load balance and key migration
      not implemented yet — partitioning.py:140 in load_distribution()

  2/17 passing, 1 to write

  Next: step 3 — load balance and key migration (partitioning.py)
```

Useful invocations:

| Command | Does |
|---|---|
| `python3 check.py` | Run in order, stop at the first unimplemented step |
| `python3 check.py 5` | Run only step 5, while you iterate on it |
| `python3 check.py 5 8` | Run steps 5 through 8 |
| `python3 check.py --all` | Run everything, skipping nothing |
| `python3 <file>.py` | Run that file's own demo once it is implemented |

A check that has not been written yet shows as a grey `·` (a TODO, not a
failure). A red `✗` means your implementation is wrong, and the message says
how. Work top to bottom — later files import earlier ones.

---

## Learning Path

Work through the files in order. Each one runs on its own with `python3 <file>.py` and
prints an experiment; the later files import the earlier ones, so a broken step blocks
the next.

### 1. Partitioning — `partitioning.py`

Consistent hashing you may already know. The Dynamo-specific part is the **preference
list**: the first N *distinct physical* nodes clockwise from the key. Virtual tokens
mean a naive clockwise walk can hand you the same machine three times, which gives you
one copy of the data where you asked for three.

Also implement the paper's "strategy 3" (Q fixed partitions), and understand why they
abandoned random tokens: with moving boundaries, a joining node has to scan its peers'
entire keyspace to discover what it now owns.

**Check:** load imbalance ≈ 1.1–1.2 with 64 tokens/node; adding the 5th node moves ~1/5
of keys; `preference_list(key, 3)` returns three different machines.

### 2. Versioning — `vector_clock.py`

A vector clock is a map of `node -> counter`. The only operations that matter are
"descends from" and "concurrent with". Reproduce Figure 3 from the paper: D1 → D2 →
D3/D4 (concurrent) → D5 (reconciled).

Two kinds of reconciliation, and the distinction is the heart of the paper:

- **Syntactic** (`coalesce`) — drop versions another version supersedes. Free, needs no
  knowledge of the data, done by every node on every read and write.
- **Semantic** (`reconcile`) — merge genuine siblings using application logic. Only the
  application knows that two shopping carts should be unioned.

**Check:** `coalesce([D1, D2, D3, D4])` returns exactly D3 and D4. The merged D5
descends from both.

### 3. Quorums — `quorum.py`

N, R, W. `R + W > N` guarantees a read overlaps the last write — but only against a
strict quorum over the same N nodes, which the next file gives up.

**Check:** with N=3 R=2 W=2, killing one replica changes nothing; killing two makes
reads fail while writes still need rescuing. Two clients writing from the same context
produce two siblings, and no node is permitted to pick between them.

### 4. Availability — `hinted_handoff.py`

Walk past dead replicas until W healthy nodes accept the write, tagging the extras with
a hint saying who the data really belongs to. A background loop delivers hints home.

Do not skip step 5 of that file: construct the case where an **acknowledged write is
genuinely lost** (all owners down, then the hint holders die before delivery). Knowing
exactly where the guarantee ends is the point of implementing this yourself.

### 5. Durability — `merkle_sync.py`

Hinted handoff covers a reboot. It does nothing for a dead disk. Merkle trees let two
replicas find their differences in traffic proportional to the number of *differences*,
not the number of keys.

**Check:** two identical 1000-key replicas cost exactly **one** hash comparison. Break
three keys and the sync should touch a few dozen tree nodes and transfer three keys.
Concurrent versions come out as siblings on both sides — anti-entropy never picks a
winner.

### 6. Membership — `gossip.py`

Heartbeat counters merged by "higher wins" — conflict-free, no clock synchronisation
needed. Convergence is O(log S) rounds.

Failure detection is **local and never shared as fact**. Crash a node and watch peers
disagree for several rounds; that disagreement is the design. A globally agreed
membership view needs consensus, which is the availability cost the paper refuses.

**Check:** two groups with disjoint seed lists form two logical rings that never
discover each other — and both keep serving happily.

### 7. Capstone — `dynamo_cluster.py`

Assemble everything, reproduce the shopping-cart scenario end to end, then run the
availability experiment: identical injected failures across (3,2,2), (3,3,1) and
(3,1,3), sloppy versus strict.

You should be able to predict every cell of that table before running it.

---

## The three repair mechanisms

Each covers a different failure duration. This is the mental model to keep:

```
read repair       µs–ms      free, but only fixes keys someone actually reads
hinted handoff    seconds–minutes   covers a reboot or a brief partition
anti-entropy      hours–days        covers a dead disk or a lost hint
```

Cold data that nobody reads is invisible to the first two. That is the entire
justification for the Merkle trees.

---

## Common configurations from the paper

| N, R, W | Property | Used for |
|---|---|---|
| 3, 2, 2 | `R+W>N`, balanced | The common default |
| 3, 3, 1 | Always writeable, slow reads | The shopping cart service |
| 3, 1, 3 | Fast reads, fragile writes | Read-heavy, write-rare data |
| 3, 1, 1 | No overlap guarantee at all | Caches where staleness is fine |

Amazon ran the cart with W=1 on purpose: a write that waits for two machines waits for
whichever one happens to be garbage-collecting, and their SLA was written against the
99.9th percentile rather than the mean.

---

## Where this implementation stops

Deliberate omissions, so you know what you have *not* built:

- **No real network.** Everything is in-process; failures are a boolean flag. There are
  no partial writes, no message reordering, no partitions that heal asymmetrically.
- **No persistence.** The paper's pluggable storage engines (BDB, MySQL, an in-memory
  buffer with a persistence backend) are replaced by a dict.
- **No request coordination through a load balancer**, no client-driven partition-aware
  routing (section 5's "zero-hop DHT"), and no admission control.
- **Anti-entropy syncs whole stores** rather than per-range Merkle trees per replica pair.
- **`merge_carts` is add-biased**, so a removed item can resurface. The paper admits the
  same. Fixing it properly means tombstones and an OR-Set — a good extension.

---

## Extensions worth trying

1. **Replace `merge_carts` with a proper CRDT** (OR-Set or PN-Counter) and show that
   removals now survive reconciliation.
2. **Add real latency.** Give each node a random response delay and make the coordinator
   return after the first R responses rather than waiting for all N. Measure the 99.9th
   percentile — the paper's actual metric.
3. **Implement read-your-writes across a sloppy quorum** and find out why it does not
   hold.
4. **Per-range Merkle trees**: one tree per (node, key-range) pair, rebuilt incrementally
   on write rather than from scratch. Measure the difference on a million keys.
5. **Compare with the real thing.** Read the Cassandra source for `StorageProxy` and the
   `AbstractReplicationStrategy` hierarchy — the vocabulary maps almost one-to-one.

---

## Structure

```
dynamo-paper/
├── README.md
├── check.py              # progress checker — run this first
├── partitioning.py       # templates with TODOs
├── vector_clock.py
├── quorum.py
├── hinted_handoff.py
├── merkle_sync.py
├── gossip.py
├── dynamo_cluster.py     # capstone
└── solutions/            # complete, runnable implementations
```

Every solution file runs standalone:

```bash
cd solutions
python3 partitioning.py
python3 vector_clock.py
python3 quorum.py
python3 hinted_handoff.py
python3 merkle_sync.py
python3 gossip.py
python3 dynamo_cluster.py     # the capstone demo
```

No dependencies beyond the Python 3 standard library.

## Related directories

- [`system-design/`](../../reference/system-design/) — consistent hashing, caching and reliability
  patterns in isolation
- [`context-caching/`](../../week-03/context-caching/) — the same "make the expensive thing cheap"
  instinct applied to LLM inference

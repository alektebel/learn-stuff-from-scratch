# Dynamo From Scratch — Solutions

Complete, runnable implementations of every template in the parent directory. Pure
Python 3 standard library, no dependencies.

```bash
python3 partitioning.py      # ring, preference lists, strategy 1 vs strategy 3
python3 vector_clock.py      # Figure 3 from the paper, reproduced
python3 quorum.py            # N/R/W, siblings, read repair
python3 hinted_handoff.py    # sloppy quorum, and where it loses data
python3 merkle_sync.py       # anti-entropy cost measurements
python3 gossip.py            # convergence, local failure detection, seed splits
python3 dynamo_cluster.py    # capstone: cart scenario + availability table
```

Files import each other by name, so run them from inside this directory.

## What each file demonstrates

### `partitioning.py`

`ConsistentHashRing` (strategy 1: T random tokens per node) and `PartitionedRing`
(strategy 3: Q fixed partitions).

The function that matters is `preference_list`, which returns N *distinct physical*
nodes — skipping virtual tokens that belong to a node already selected, and optionally
spreading across datacenters. A plain clockwise walk would happily return the same
machine three times.

Output shows load imbalance ≈ 1.14 at 64 tokens/node, ~19% of keys moving when a 5th
node joins (ideal: 20%), and exactly Q/S partitions per node under strategy 3.

### `vector_clock.py`

`VectorClock` with `descends_from` / `compare` / `merge`, plus the two reconciliation
layers:

- `coalesce()` — syntactic, drops superseded versions, needs no application knowledge
- `reconcile()` — semantic, merges true siblings with an application function

The demo reproduces Figure 3 exactly: D1 `[Sx:1]` → D2 `[Sx:2]` → D3 `[Sx:2,Sy:1]` and
D4 `[Sx:2,Sz:1]` (concurrent) → D5 `[Sx:3,Sy:1,Sz:1]`, which descends from both.

Truncation is implemented too, capped at 10 entries as in the paper, with a note on the
false concurrency it can create.

### `quorum.py`

`StorageNode` (local store that appends siblings rather than overwriting) and
`Coordinator` (fan-out, ack counting, read repair).

The demo walks from healthy through one-replica-down (still fine) to
two-replicas-down (reads fail R=2), then shows two clients writing from the same context
producing siblings, then read repair silently fixing a replica that missed a write.

### `hinted_handoff.py`

`HintedNode` (separate hint area, delivery loop) and `SloppyCoordinator` (falls forward
past dead replicas).

The last section is the important one: with all three owners down, W=2 is satisfied
entirely by hints; kill the hint holders before delivery and the acknowledged write is
**gone**. Sloppy quorum buys availability with durability, and this is the receipt.

There is also a quieter lesson in the middle: the coordinator stops creating hints as
soon as W is met, so an owner can remain stale even after every hint is delivered.

### `merkle_sync.py`

`MerkleTree` (build, diff) and `AntiEntropy` (pairwise sync).

Measured output:

```
identical 1000-key replicas   ->  1 node comparison, 0 keys transferred
3 keys differ out of 1000     -> 39 node comparisons, 3 keys transferred
depth  4 /  8 / 12            ->  9 / 17 / 25 comparisons for one real diff
```

Comparison cost grows like log(leaves), not like the key count. Concurrent versions come
out of a sync as siblings on both sides — the merge is a union, never a choice.

### `gossip.py`

`GossipNode` (heartbeat table, local failure detection) and `GossipCluster` (rounds,
convergence measurement).

Shows O(log S) convergence at 8/32/128 nodes, a new node becoming universally known in
~7 rounds while roughly doubling its reach each round, peers disagreeing about a crashed
node for several rounds, and two seed-isolated groups forming permanently separate rings.

### `dynamo_cluster.py`

Everything wired together, plus the availability experiment. Sample output:

```
config                      sloppy W  write ok   read ok
N=3 R=2 W=2 (balanced)            27   100.0%    100.0%
     strict                        0    93.5%     93.5%
N=3 R=3 W=1 (fast write)           1   100.0%     57.0%
     strict                        0    99.8%     56.2%
N=3 R=1 W=3 (fast read)          202   100.0%    100.0%
     strict                        0    56.2%     99.8%
```

Same injected failures in every row. Sloppy quorum lifts write availability to ~100%
everywhere; R=3 collapses read availability to 57%; strict W=3 collapses writes
symmetrically. Numbers vary slightly with the seed but the shape is stable.

## Implementation notes

- **Clocks are immutable.** `increment` and `merge` return new `VectorClock` objects.
  A version's clock must never change under it.
- **`local_put` is idempotent.** It coalesces, so replaying a version is a no-op. This
  is what makes hint delivery and anti-entropy safe to retry blindly.
- **`_digest` separates its parts with a null byte**, so `"ab" + "c"` and `"a" + "bc"`
  cannot collide.
- **Leaf hashes cover version fingerprints, not values.** Two replicas holding the same
  version must produce the same hash regardless of value representation.
- **Gossip ticks all nodes before any node gossips.** Otherwise a node forwards
  information it has not yet aged, and convergence measurements come out wrong.
- **Sloppy reads count hint holders toward R but never read-repair them** — a fallback
  node must not quietly become a permanent replica.

# Partitioning and Rebalancing From Scratch

A consistent-hashing ring with virtual nodes, key-to-node assignment, and
rebalancing on join and leave, in pure Python (standard library only). It closes
the gap between "one machine holds the data" and the replication modules: with
data on several nodes, *which* node holds a key, and what moves when the set of
nodes changes.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 6
("Partitioning") — consistent hashing, rebalancing, and the skew/hot-spot
discussion. Everything here is restated from scratch; nothing is copied.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| The ring | consistent hashing, virtual nodes, `bisect` lookup | `hashring.py` | 1-2 |
| Assignment | key → node, evenness metric | `partitioner.py` | 3 |
| Rebalancing | join / leave move only the changed node's share | `partitioner.py` | 4-5 |
| Limit: few vnodes | one position per node leaves a badly uneven ring | `partitioner.py` | 6 |
| Limit: hot key | an even ring does not stop one key overloading one node | `partitioner.py` | 7 |

## How to use this directory

The top-level files are **templates**: each function keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`.
`solutions/` holds complete versions for when you are stuck, or to compare
afterwards.

```bash
cd distributed/05-partitioning
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py --all  # everything
```

`check.py` runs 7 checks against **your** code and never imports `solutions/`.
The checks use a fixed seed for their key set, so the numbers below are exactly
reproducible.

## The measurements

Run the solutions and predict each number before you look:

```
python3 solutions/hashring.py      # peak/mean share vs virtual-node count
```

| virtual nodes per node | peak/mean share of 20000 keys over 8 nodes |
|---|---|
| 1 | 2.488 |
| 4 | 1.854 |
| 64 | 1.347 |
| 256 | **1.134** |

`partitioner.py` also prints: joining a ninth node moves **11.2%** of keys
(ideal `1/9 = 11.1%`), and a single key read a million times puts **98.2%** of
all accesses on the one node that owns it.

## Design decisions, named

Each file opens with its decisions and their cost. In short:

- **Stable SHA-256, never the built-in `hash()`** (`hashring.py`). Python salts
  `hash()` per process, so a ring built with it sends the same key to a
  different node after every restart — a write and its read land on different
  nodes. Cost: a digest is slower than `hash()`, which never matters next to the
  network hop it saves.
- **Sorted array + `bisect`, rebuilt lazily** (`hashring.py`). A lookup is
  O(log V) and a burst of membership changes costs one rebuild. Cost: adding a
  node rebuilds all of V tokens, and the first lookup after a change pays it.
- **256 virtual nodes** (`partitioner.py`, `DEFAULT_VNODES`). With one position
  per node the peak share is 2.5x the mean; 256 brings it to 1.13. Cost: 256
  ring positions per node to store and hash.
- **Rebalancing is a diff, not a migration** (`partitioner.py`). The ring is the
  single source of truth: `join`/`leave` recompute owners and return the keys
  that changed. The correct amount to move falls out of the structure instead of
  being a second rule that can drift from it. Cost: it re-assigns a sample of
  keys, O(keys × log V), rather than migrating only what was stored.
- **Evenness (`max/mean`) and load (weighted) are separate** (`partitioner.py`).
  A ring balances *unique keys*; it does not balance *work*. Reporting both is
  the honest picture. Cost: the ring still cannot fix a hot key.

## Questions to answer before reading the solutions

1. `hash(key) % num_nodes` is one line. What exactly does it cost you when a
   node joins, in terms of keys moved, and why?
2. With one position per node, why does the ring stay uneven even with millions
   of keys, while 256 positions smooth out with far fewer keys?
3. After `node-3` leaves, its keys go to its successors on the ring. Why does
   step 5 still expect the *remaining* ring to be within the evenness bound?
4. The hot key is 98% of the load even though its node owns only ~12% of the
   keys. Name two ways a real system copes with that, and say which one this
   module deliberately does not implement.
5. Two processes build the same ring from the same node names. Why must they
   agree on every key, and what breaks if they do not? (Step 2 tests exactly
   this.)

## The checker was itself tested

Eight classic bugs were planted in copies of the solutions; each must be caught
by its check:

| Planted bug | Caught by |
|---|---|
| built-in `hash()` (salted per process) instead of a stable digest | step 1 |
| ring salted with `id(self)` so instances disagree | step 2 |
| virtual tokens not sorted before `bisect` | step 3 |
| `join` reports every key as moved | step 4 |
| `leave` reports every key as moved | step 5 |
| virtual nodes ignored (one position per node) | step 6 |
| `evenness` always returns 1.0 | step 6 |
| `load` counts keys equally, ignoring access weights | step 7 |

Every one is caught; the mutations live in `_build/mutations.py` and are run with
`.claude/skills/graded-module/scripts/mutate.py`.

## Limits

- **It balances keys, not load.** A hot key still overloads its node; step 7
  measures it rather than fixing it. Real fixes (splitting the key, replicating
  it, or caching on other nodes) are out of scope.
- **Rebalancing moves a sample, not stored data.** `join`/`leave` recompute a
  key list; a production system migrates the keys it actually holds and streams
  them without blocking reads. The *fraction* that moves is the point, not the
  transfer mechanism.
- **One data center, one ring.** No replication factor, quorum, or consistency
  across nodes — that is `distributed/02-replication-quorums`, which this
  module presupposes.
- **No failure detection, no consistent hashing successor maps, no gossip.**
  Membership is explicit `add_node`/`remove_node` calls.

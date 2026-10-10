# CRDTs From Scratch

Conflict-free replicated data types in pure Python (standard library only): a grow-only
counter, a two-phase (PN) counter, a last-writer-wins register and an observed-remove set,
each built as a **join semilattice** so that any two replicas that have seen the same
updates report the same state no matter what order the updates arrived in.

This is the convergence side of the distributed track. `distributed-01-clocks` supplies the
logical timestamps an LWW register needs; this module supplies the merge, and the point is
to feel *why* the merge laws (commutative, associative, idempotent) are the whole game: if
any one of them fails, the replicas never agree.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Grow-only counter | one slot per node, merged by pointwise `max` | `gc_counter.py` | 1 |
| Two-phase counter | a grow-only counter for `+` and one for `-`; value is the difference | `gc_counter.py` | 2 |
| Last-writer-wins register | each write stamped `(timestamp, node id)`; merge keeps the max | `lww_register.py` | 3-4 |
| Observed-remove set | every add carries a unique tag; removes tombstone only observed tags | `or_set.py` | 5-6 |
| The merge laws | commutative, associative, idempotent, fuzzed | all | 7 |
| Convergence | any exchange of merges reaches the same state | all | 8 |

## How to use this directory

The top-level files are **templates**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
working versions for when you are stuck, or to compare afterwards.

```bash
cd distributed/04-crdts
python3 check.py        # what to build next; stops at the first gap
python3 check.py 6      # one step
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`.

## Design decisions, named

Each file opens with its decisions and their cost. In short:

- **A slot per node, merged by `max`** (`gc_counter.py`). One integer merged by `max` loses
  a genuine increment (two replicas that each added 1 both hold 1); one integer merged by
  `+` is not idempotent (a re-delivered message double-counts). Cost: state grows with the
  number of nodes, and a departed node's slot is never reclaimed.
- **The PN counter is two grow-only counters**, not one signed value (`gc_counter.py`). A
  signed value has no monotone join, so merges are undefined; P and N stay inside the
  lattice. Cost: two slots per node and a subtraction at read time.
- **An LWW register breaks ties by node id** (`lww_register.py`). Arrival order is not a
  property of the value, so it cannot break a tie and still converge; `(timestamp, node
  id)` is a total order. Cost: the loser of a genuine simultaneous write is silently
  dropped — the reason multi-value registers and OR-sets exist.
- **Adds carry unique tags; removes tombstone the observed tags** (`or_set.py`). A
  per-element tombstone can never be un-set (a re-add is swallowed, and a concurrent add
  loses to a remove it never saw). Cost: tags and tombstones accumulate forever.
- **`merge` returns a new object** everywhere. It makes `a.merge(b) == b.merge(a)`
  assertable directly instead of after cloning. Cost: every merge allocates.

## Questions to answer before reading the solutions

1. The G-counter merges by `max` and the PN-counter merges each half by `max`. Why can
   neither the whole PN value nor a single signed number be merged by `max`?
2. An OR-set `remove` could simply delete the element's tags. Construct the pair of merges
   that then resurrects a removed element, and say which check builds that pair.
3. With a tie in the LWW register, the write with the larger node id wins. Give a workload
   where discarding the other concurrent write is the right call, and one where it is a
   bug.
4. The merge laws are checked by comparing `state()`, not `value()`. For a G-counter, find
   two states with the same `value()` that are not equal, and explain why comparing
   `value()` alone would hide an associativity bug.
5. Replicas in step 8 converge after random pairwise gossip *and* an all-to-all pass. Which
   of the three laws guarantees the random gossip cannot make the final state depend on
   the gossip order?

## The checker was itself tested

Six classic bugs were planted in copies of the solutions; each must be caught by its check:

| Planted bug | Caught by |
|---|---|
| G-counter merge sums the two slots instead of taking the max | step 1 |
| PN-counter `decrement` increments the positive side | step 2 |
| LWW merge compares only the timestamp (no node-id tie-break) | step 4 |
| OR-set `remove` deletes the observed tags instead of tombstoning them | step 6 |
| OR-set tags are not unique, so a re-add collides with an old tombstone | step 5 |
| OR-set merge keeps only its own tombstones (merge not commutative) | step 7 |

The first LWW mutation tried was changing `>` to `>=`. It was **not** caught, and that is a
lesson in itself: on two stamps that differ in timestamp or writer, `>` and `>=` are
identical, and when the whole stamp is equal the values are equal too, so the two merges
are behaviourally the same. The real bug is dropping the writer from the comparison — a
tie-break that depends on merge order.

## Limits

- **State-based CRDTs only.** Every merge ships the whole state. The delta-state variants
  (Almeida, Shoker and Baquero, 2018) send only the changed part; implementing them would
  close the O(state) cost of a merge but is a separate module.
- **No network.** Merges are applied directly, so delivery order, duplication and
  partitions are simulated by the checker, not by a transport. `distributed-02` and
  `distributed-03` are where that lives.
- **Tombstones and tags are never reclaimed.** `ORSet._removed` and departed-node counter
  slots grow without bound; real systems add causal-context or interval compaction.
- **The LWW register trusts the caller's clock.** It never generates a timestamp itself;
  `distributed-01-clocks` is the prerequisite that does.
- **No garbage. No transactions. No nesting.** Composing these into maps or JSON documents
  is left out on purpose, to keep each merge inspectable.

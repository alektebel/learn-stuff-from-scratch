# Replication and Quorums From Scratch

A single-leader log replicated to followers over a simulated, seeded network, read
back through **quorum reads and writes** with parameters R, W and N — and the two
limit cases that break the naive version: a partitioned minority that must *refuse*
rather than fork the log, and a slow follower that must lag without blocking the
acknowledgement. Pure Python, standard library only.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 5
("Replication") — leader-based replication and its lag, leaderless/Dynamo-style
quorum reads and writes, and the durability cost of a sloppy quorum. Everything
here is restated from scratch; nothing is copied.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| The medium | a seeded message queue: delays, ordering, partitions | `network.py` | 1-2 |
| The log | a replica log: contiguous positions, no forks, rollback | `replica.py` | 3-4 |
| The quorum rule | R + W > N overlaps; count the replicas | `quorum.py` | 5-6 |
| Durability | a W-replica write survives N-W losses | `quorum.py` | 7 |
| Limit: partition | a minority refuses instead of forking | `quorum.py` | 8 |
| Limit: slow follower | lag without blocking the quorum | `quorum.py` | 9 |

The acceptance criteria are: with `R + W > N` a read sees the last acknowledged
write; with `R + W <= N` a stale read is demonstrated; and an acknowledged write is
durable on a quorum. The two limit cases are the partition and the slow follower.

## How to use this directory

The top-level `network.py`, `replica.py` and `quorum.py` are **templates**: each
function you write keeps its signature and docstring, has a `TODO` with a hint, and
raises `NotImplementedError`. Constructors and membership plumbing are provided —
they are not the lesson. `solutions/` holds complete versions for when you are
stuck, or to compare afterwards.

```bash
cd distributed/02-replication-quorums
python3 check.py        # what to build next; stops at the first gap
python3 check.py 5      # one step
python3 check.py --all  # everything
```

`check.py` runs 9 checks against **your** code and never imports `solutions/`. The
network is seeded (`SEED = 20261010`), so every arrival order and every number below
is exactly reproducible.

## The measurements

Run the solutions and predict each line before you look:

```
python3 solutions/quorum.py     # the R+W>N table and the stale-read window
```

| R | W | N | `R + W > N` | read sees the last acknowledged write? |
|---|---|---|---|---|
| 2 | 2 | 3 | True | yes — the quorums must overlap |
| 1 | 3 | 3 | True | yes |
| 1 | 1 | 3 | False | no — demonstrated stale (`None`) |
| 2 | 2 | 5 | False | no |
| 1 | 4 | 5 | False | no |

`solutions/network.py` prints the arrival order with explicit delays
(`['fast', 'slow']`) and shows a partition dropping exactly the cross-group
message. `solutions/replica.py` shows a transform: appending at index 3 when the
log length is 2 is refused (`False`), and `truncate(1)` rolls `value(x)` back from
`(1, 'two')` to `(0, 'one')`.

## Design decisions, named

Each file opens with its decisions and their cost. In short:

- **A queue and a logical clock, not threads** (`network.py`). Reproducibility is
  the whole point: a timing failure you cannot rerun teaches nothing. Cost: no real
  blocking or back-pressure — a "slow" node is paused or delayed by fiat.
- **A partition drops, it does not queue** (`network.py`). Healing does not
  resurrect in-flight messages, exactly as a real partition loses them. Cost:
  read-repair/catch-up has to be explicit, because nothing is retransmitted.
- **A positional log, contiguous by construction** (`replica.py`). Refusing a gap
  means a lagging replica cannot silently grow a *forked* history; it forces the
  leader to run catch-up. Cost: the leader must resend the whole missing prefix.
- **Version = log index** (`quorum.py`). A write's identity is its position, so the
  quorum question is literally "how many replicas reached index i?" and no extra
  clock is needed. Cost: versions only mean something within one leader's log; a
  multi-leader design needs a Lamport/HLC timestamp.
- **A failed write rolls every copy back** (`quorum.py`). A minority must refuse,
  not retain a prefix the rest never saw. Cost: a transiently partitioned leader
  discards in-flight work it might have committed had it waited (Raft's terms are
  the general answer; this module stops at the refusal).
- **Repair is explicit (`catch_up`), not automatic** (`quorum.py`). The stale
  window of check 6 is observable *before* it closes, which is the lesson. Cost:
  real systems piggyback repair on reads; here you must ask for it.

## Questions to answer before reading the solutions

1. If `N = 5` and `W = 3`, what is the smallest R that guarantees a fresh read, and
   *why* is the argument an intersection count rather than anything about the
   protocol?
2. Why does the leader in check 8 refuse the write instead of keeping its entry for
   a later retry? What would the log look like on heal if it did not roll back, and
   which two replicas could then disagree forever?
3. Check 6 acknowledges a write with `W = 1`. Name the availability it buys and the
   durability it spends, and say which single crash would lose that write.
4. A slow follower is paused, not crashed. Why must the acknowledged write count
   only `W` replicas rather than wait for all `N`, and what does the follower need
   in order to rejoin?
5. `version = index` here. Sketch what has to change if two leaders each assign
   versions, and why a plain integer can no longer order their writes.

## The checker was itself tested

Ten classic bugs were planted in copies of the solutions; each must be caught by
its check. They live in `_build/mutations.py` and are run with
`.claude/skills/graded-module/scripts/mutate.py`.

| Planted bug | Caught by |
|---|---|
| delivery ordered by send time, ignoring the delay | step 1 |
| partitions ignored (everyone can talk) | step 2 |
| the log accepts gaps and double writes | step 3 |
| `truncate` drops the entry but keeps its value | step 4 |
| read returns the first response, not the newest version | step 5 |
| read ignores the requested quorum (`from_`) | step 6 |
| `commit_index` counts entries instead of positions | step 7 |
| a minority write is acknowledged without W replicas | step 8 |
| a refused write leaves the forked entry behind | step 8 |
| a write waits for every replica, not a quorum | step 9 |

All ten are caught.

## Limits

- **One leader, one log.** Writes go through a designated leader; the leader is an
  availability bottleneck and this module does not elect one (that is
  `distributed/03-consensus`). A partitioned leader cannot serve its clients.
- **No terms or epochs.** Rolling a failed write back is enough for "no fork while
  partitioned", but it says nothing about a *stale leader* rejoining after a new
  one took over. Raft's terms are the missing piece.
- **No hinted handoff / sloppy-quorum write set.** The write set is whoever is
  reachable; the module measures the durability cost rather than papering over it.
- **Integer versions, single number per key.** Last-write-wins by log index; no
  sibling reconciliation (vector clocks, CRDTs) and no per-key conflict handling.
- **No failure detector, no membership changes.** `partition`/`pause`/`crash` are
  explicit test hooks, not a gossip or heartbeat system.
- **The network is in-process and seeded.** It models delays, reordering and
  partitions; it does not model bandwidth, partial messages or real concurrency.
- **Clock skew is out of scope here.** Ordering without a shared clock is
  `distributed/01-clocks`, which this module presupposes.

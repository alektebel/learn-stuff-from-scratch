# Consensus (Raft) From Scratch

Leader election, log replication and commitment for a Raft cluster, running over a
deterministic in-process network. Pure Python 3, standard library only, no threads and no
sockets: the nodes and the message queue live in one process, and a seed reproduces every
interleaving.

It exists to close the gap between "I can describe Raft" and "I can get Raft right". The
dangerous part of consensus is not the happy path -- it is the partition, the delayed
message, the crashed leader that comes back. This module builds the happy path first and
then makes you construct the failures that force each extra rule.

## Sources

- **Raft paper** (Ongaro & Ousterhout), §5.1-5.4 and Figure 2: terms, the up-to-date vote
  rule, the log-matching property of `AppendEntries`, and the commit rule.
- **van Steen & Tanenbaum, *Distributed Systems*, ch. 8**: leader-based replication, the
  primary-backup commit rule, and why the network is the layer that partitions.

The content here is a restatement, not a copy. The file docstrings cite the section next
to the code that implements it.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| The medium | a seeded queue: per-message delay, reordering, partitions, crashes | `network.py` | 1-2 |
| Leader election | terms, randomised timeouts, the up-to-date vote rule | `raft.py` | 3, 6 |
| Log replication | `AppendEntries`, `prev_log_term`, next-index back-up, truncation | `raft.py` | 4, 7 |
| Commitment | an entry commits when a majority holds it **and** it is from the current term | `raft.py` | 8 |
| Apply channel | committed entries delivered to the state machine in index order, once | `raft.py` | 5 |
| Limit case: heal | an isolated leader rejoins, steps down, and its fork is truncated | `raft.py` | 9 |
| Limit case: delays | reordered/delayed/lost messages never break safety | `raft.py` | 10 |

## How to use this directory

The top-level `network.py` and `raft.py` are **templates**: each function you write keeps
its signature and docstring, has a `TODO` with a hint, and raises `NotImplementedError`.
`solutions/` holds working versions for when you are stuck.

```bash
cd distributed/03-consensus
python3 check.py        # what to build next; stops at the first gap
python3 check.py 6      # one step
python3 check.py --all  # everything
```

`check.py` runs 10 checks against **your** code and never imports `solutions/`.

## Design decisions, named

- **An explicit message queue instead of threads and sockets** (`network.py`). A failing
  safety property must be reproducible from a seed. Cost: no blocking and no partial
  sends; a "lost" message is one never enqueued.
- **Each node owns its own RNG** (`network.py`, `raft.py`). The network seeds its delays;
  each node seeds its election timeout. No global `random`, so results do not depend on
  `PYTHONHASHSEED` or import order. Cost: the cluster offsets each node's seed so two
  nodes do not time out identically.
- **One node class plus a small `Cluster` harness** (`raft.py`). The checks build a
  cluster in one line; the node itself only knows "call `net.send`".
- **Commit only a current-term entry by majority** (`raft.py`, `_advance_commit`). An
  older-term entry that is merely on a majority may still be overwritten later; only once
  an entry of the leader's own term is on a majority is it safe to also commit the
  preceding ones. This is the rule Raft's Figure 8 exists to justify.
- **Apply as an ordered, append-only list** (`raft.py`, `_apply`). Walking the index up one
  at a time gives ordering and exactly-once delivery by construction, and lets a check
  compare node histories directly.
- **`commit_state` simplified across a crash** (`raft.py`). Stable storage (term, vote,
  log) is kept, but the volatile state machine is assumed recovered on restart. A real
  restart rebuilds `commitIndex` from the leader and replays the log; that is listed under
  "where it stops".

## The checker was itself tested

Eight classic bugs were planted in copies of the solutions; each is caught by the check
named here.

| Planted bug | Caught by |
|---|---|
| delivery time ignored (arrivals follow send order) | step 1 |
| a partition does not drop cross-group messages | step 2 |
| committing without a majority | step 8 |
| a stale-log candidate granted the vote | step 6 |
| applying entries before they are committed | step 5 |
| a conflicting log suffix is not truncated | step 9 |
| a follower hearing a higher term does not step down | step 9 |
| committing past the last entry an `AppendEntries` carries | step 10 |

Two limit cases are checks a naive implementation fails, not decoration: step 9
deliberately isolates the leader and lets the majority commit a different entry at the
same index, and step 10 runs wide delays, reordering and drops while nodes crash and
restart.

## Questions to answer yourself (answers are not given)

1. Why can a leader not commit a *previous* term's entry simply because a majority holds
   it? Sketch the Figure 8 history.
2. Why does a follower delete its whole conflicting suffix instead of patching the one
   mismatching entry?
3. What goes wrong if every node uses the same election timeout?
4. Why must a candidate ignore a vote reply whose term is not its current term?
5. Why is `min(leader_commit, prev_log_index + len(entries))` necessary, rather than
   trusting `leader_commit` directly?

## Where it stops

Deliberately out of scope, so you do not walk past the boundary:

- **No log compaction or snapshots.** The log grows without bound; `InstallSnapshot` is
  not implemented.
- **No membership changes.** The cluster size is fixed at construction.
- **No on-disk persistence.** Stable storage is simulated by fields on the node object;
  crash recovery of the log itself is not exercised.
- **No client sessions or deduplication.** `propose` is fire-and-forget; a retried command
  is appended again.
- **No pre-vote and no leadership transfer.** A partitioned node can still disrupt the
  cluster with a higher-term election when it rejoins.
- **Liveness under a permanent partition is not guaranteed**, only safety. A minority can
  never commit, so if a majority never forms nothing progresses -- by design.

# Replication From Scratch

Leader-follower replication with failover, from the log algebra to split-brain
prevention. A leader accepts writes, copies its log to followers, commits once a
**majority** holds an entry, and when the leader dies the survivors elect the most
up-to-date replica. Synchronous and asynchronous replication are both implemented so the
latency/durability trade-off is measured, not asserted.

Standard-library only, deterministic, no threads or sleeps.

## Run it

```bash
cd system-design/replication
python3 check.py          # stop at the first unimplemented step
python3 check.py --all    # run every check
python3 check.py 8        # just step 8
```

A step that raises `NotImplementedError` is TODO, not a failure. Read the docstring in
its file, implement it, re-run. Compare with `solutions/` only after trying.

## The steps

| Step | File | What you implement |
|---|---|---|
| 1 | `log.py` | `last_term`: the term of the newest entry, `0` when empty |
| 2 | `log.py` | `is_up_to_date`: higher last term wins, then longer log (Raft §5.4.1) |
| 3 | `log.py` | `choose_leader`: most up-to-date candidate, ties by name |
| 4 | `log.py` | `quorum_index`: highest index held identically by a majority |
| 5 | `cluster.py` | `ReplicaSet.write` (sync): replicate to every reachable replica before ack |
| 6 | `cluster.py` | `ReplicaSet.write`: no majority, no acknowledgement |
| 7 | `cluster.py` | async mode: the leader ack's, followers lag, `sync()` catches them up |
| 8 | `cluster.py` | failover: a synced write survives, an async one does not |
| 9 | `cluster.py` | `ReplicaSet.elect`: the most up-to-date survivor leads |
| 10 | `cluster.py` | epoch fencing: the old leader's writes are refused |

Provided infrastructure in `cluster.py` (not graded): `crash`/`restart`,
`partition`/`heal`, `reachable`/`can_lead`, `read`, `_follow`/`_catch_up`/`sync`,
`failover`, and `FencedStore`'s constructor. You implement `elect`, `write`, and
`FencedStore.write`.

## The idea in one page

A **replicated log** is the data: an ordered list of `(term, command)` entries, the same
on every replica. The leader appends at the end; followers copy. Two questions decide
correctness:

- **Which log is more up-to-date?** Compare last term first, then length. A longer log is
  *not* better — another leader may have overwritten those entries under a newer term.
  Getting this backwards is the failover bug that loses committed writes.
- **When is an entry committed?** When a **majority** of replicas hold it. Not when the
  leader holds it. That is what makes `sync` survive losing any one node and `async`
  lose the most recent acks when the leader dies.

**Failover** elects the most up-to-date replica that can still reach a majority (a node
cut off from the majority cannot be elected, so two leaders cannot coexist). **Fencing**
finishes the job for a partitioned old leader that does not yet know it lost: every
election bumps a monotonic **epoch**, and a resource refuses an epoch older than the
newest it has seen, so the zombie leader cannot write.

## Design decisions

The file docstrings carry the full arguments; the short version:

- **Up-to-date rule.** `(last_term, length)`, term first. Cost: a replica with many
  uncommitted entries is passed over — correctly.
- **Commit.** Majority, checked per index, differing entries not counted together. Cost:
  sync latency waits for the slowest node in the majority.
- **Sync vs async.** Sync acks after a majority stores the write; async acks after the
  leader appends. Cost: async trades durability for latency; the module measures exactly
  how much is lost on failover.
- **Election eligibility.** Only a node that can reach a majority may lead. Cost: failover
  stalls while a majority is unreachable.
- **Follower repair.** Longest matching prefix, replace the rest; refuse to drop a
  committed entry. Cost: an uncommitted tail is discarded.
- **Fencing.** Monotonic epoch on every election; `FencedStore` rejects stale epochs.
  Cost: every write path must carry the token.

## Mutation table

`_build/mutations.py` plants 8 mistakes; `mutate.py` confirms each is caught by the step
that should catch it. All CAUGHT:

| Mistake | Caught by |
|---|---|
| up-to-date compares length, not term | 2 |
| `choose_leader` ranks the longest log first | 3 |
| commit index ignores the quorum | 4 |
| sync write acknowledges one replica | 6 |
| async replicates before acknowledging | 8 |
| election does not bump the epoch | 10 |
| election ignores majority reachability | 10 |
| fencing store ignores the epoch | 10 |

## Questions to answer yourself (there is no check for these)

- With 5 replicas, `sync` waits for a majority (3). What is the write latency if one
  follower is in another region, and how does a "quorum of the fast ones" (flexible Paxos)
  change the guarantee?
- The new leader after failover may hold **uncommitted** entries from an old term. Why
  must it wait for one entry from *its own* term before it can safely commit them?
  (Raft §5.4.2.)
- Async loses the last acks. What is the smallest change that bounds the loss window
  without paying full sync latency? (Hint: a bounded lag / semi-sync.)
- `read` here returns the committed prefix **on that replica**, so a follower can return
  stale data. How would you offer *read-your-writes* or *linearizable* reads, and what
  does each cost?
- The fencing token protects an external resource. Why can the old leader still corrupt
  the *log* if the resource is the log itself, and how does a majority-based commit rule
  prevent that?

## Limits (not implemented / deliberately simplified)

- No real network, timers, or message loss: replication is synchronous function calls, so
  elections are instant and there is no split vote. A real implementation needs
  randomized timeouts and `RequestVote`/`AppendEntries` RPCs.
- No log persistence, snapshots, or membership changes (joint consensus).
- No liveness/fairness guarantees: `elect` always succeeds if a majority is reachable.
- `commit_index` is a single cluster-wide value, not the per-replica applied index a real
  state machine would track.
- One file (`cluster.py`) holds both the leader's decisions and the follower plumbing; a
  real system separates them by RPC.

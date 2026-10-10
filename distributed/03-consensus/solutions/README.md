# Consensus (Raft) From Scratch — Solutions

Complete versions of the two templates in the parent directory. Pure Python 3, standard
library only, single process, no threads. Run them from inside this directory (they import
each other by name):

```bash
python3 network.py   # delays decide arrival order; a partition drops traffic
python3 raft.py      # elect a leader, replicate three commands, commit on all five
```

Expected output (the exact numbers follow from the fixed seeds):

```
$ python3 network.py
delivery order (explicit delays): ['fast', 'slow']
after partition: ['fast', 'slow', 'before-partition']
reordered arrivals: ['m2', 'm6', 'm7', 'm3', 'm0', 'm1', 'm4', 'm5']

$ python3 raft.py
elected leader: n4 term: 1
commits: 3 applied: ['x=1', 'y=2', 'x=3']
terms seen: [1]
conflicts: None None
elected in term 1, 3/3 commands committed on all 5 nodes
```

The reordered arrivals are not sorted: that is the point. `network.py` stamps each send
with its own delivery time, so a later message with a shorter delay overtakes an earlier
one, and the order is reproducible from the seed.

## What each file contains

- `network.py` — `Network`: a priority queue of `(deliver_at, seq, src, dst, msg)` with a
  logical clock, per-message delays, an optional reorder flag, a drop rate, partitions and
  crashes. `step()` advances the clock and delivers everything now due.
- `raft.py` — `LogEntry`, `RaftNode` (elections, `AppendEntries`, the commit rule, the
  apply channel) and `Cluster` (wire N nodes to a network and drive the clock), plus three
  safety inspections: `applied_conflict`, `committed_conflict`, `log_matching_violation`.

## Reading it with the checks

`check.py` is the specification. Each step adds one property:

1-2. the network honours delays and partitions;
3-5. election, replication/commit, and the apply channel;
6-8. a single leader per term, no divergent apply, no minority commit;
9-10. heal without divergence, and safety under delay/reorder/loss.

Everything is deterministic: the same seed gives the same election, the same terms and the
same apply history. If you change a seed and a check fails, that is a real bug, not noise.

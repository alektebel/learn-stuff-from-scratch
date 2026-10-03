# Raft From Scratch

Consensus, implemented one mechanism at a time, and tested against a network
that partitions, crashes and drops messages.

> **Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm",
> USENIX ATC 2014.** [Paper](https://raft.github.io/raft.pdf)

## Why this directory exists

[`dynamo-paper/`](../dynamo-paper/) deliberately refuses consensus. Its own
README says so: a globally agreed membership view "needs consensus, which is the
availability cost the paper refuses." This is the thing it was refusing.

The two are the clearest possible pair. Same partition, opposite answers:

| | Raft | Dynamo |
|---|---|---|
| minority write | refused — client told no | accepted, into a sloppy quorum |
| after healing | minority's writes deleted | both versions survive as siblings |
| conflicts | impossible by construction | the application merges them |
| the promise | one order, everywhere | eventual convergence |

Neither is better. A bank ledger wants the first; a shopping cart wants the
second. Having built both, you can say which you need and why.

## What you build

| File | The mechanism | Stubs |
|---|---|---|
| `log.py` | The replicated log, and the log matching property | 9 |
| `election.py` | Terms, votes, the election restriction, randomised timeouts | 7 |
| `replication.py` | nextIndex/matchIndex, and the commit rule | 8 |
| `cluster.py` | The whole thing, against a hostile network | 6 |

```bash
cd raft
python3 check.py          # 7 graded checks against YOUR code
```

---

## The one property

> **State machine safety.** If any server has applied an entry at index *i*,
> no other server ever applies a **different** entry at index *i*.

That is what Raft sells. Everything else — leaders, terms, the consistency
check — is machinery for keeping it true. `cluster.py` asserts it after **every
single operation**, not at the end, because a violation that later heals is
still a violation: a client was told something that turned out to be false.

---

## The four ideas, and their measurements

### 1. The log matching property does an inductive proof in three lines

> If two logs contain an entry with the same **index** and the same **term**,
> the logs are identical in all entries up to that index.

Two machines that have never communicated agree about their entire history
because *one* entry matched. It holds because agreement at index *i* can only
ever be created out of agreement at *i-1* — which is what `matches()` enforces.

```
  300 random divergences, each repaired by backing up one index at a time:
  0 followers left disagreeing with the leader. Worst case 10 rounds.
```

**A subtlety worth the whole exercise.** Generate those divergences with terms
the leader also used and the repair genuinely misbehaves — but such a log could
never exist, because one term has one leader. The demo gives the leader even
terms and the stale follower odd ones for exactly that reason. **Raft's
guarantees are about the logs the protocol can produce, not about arbitrary
logs**, and that distinction is easy to miss until a test fails.

### 2. One vote per term is the entire election safety argument

Two candidates cannot both hold a majority of the same set, because two
majorities always intersect and the server in the intersection voted once.
Notice what that does *not* depend on: clocks, message ordering, or timing.

And what randomising the timeout actually buys:

```
  jitter    split at least once    mean rounds to elect
       1                   100%                   13.00
       5                    45%                    1.80
      25                    11%                    1.12
      50                     5%                    1.06
```

Randomising does **not** eliminate split votes — nothing can, and FLP says why.
It makes a *repeat* vanishingly unlikely, so the expected number of rounds stays
near one. Raft trades a hard guarantee for a probabilistic one and is unusually
direct about saying so.

### 3. The commit rule is where people get it wrong

The obvious rule is "commit when a majority has it". **That rule is wrong.**
Figure 8 of the paper is the counterexample, and the demo builds it:

```
  majority only (WRONG)
    entry 2 is on 3 of 5 servers; COMMITTED
    -> SAFETY VIOLATED: committed, then deleted

  majority AND current term
    entry 2 is on 3 of 5 servers; not committed
    -> never committed — no promise was broken
```

An entry from an **old term** can sit on a majority and still be overwritten,
because a candidate with a shorter but more recent log can still win. The real
rule needs both clauses: a majority has it **and** it is from the leader's
current term. Older entries then commit indirectly, by the log matching
property.

Every test that does not include a leader change at exactly the wrong moment
passes with the wrong rule. That is what makes it the part people implement
incorrectly.

**And why a new leader appends a no-op**, which looks like a hack and is not:

```
  no-op appended: False   commit_index 0, blocked 3 times
  no-op appended: True    commit_index 4, blocked 0 times
```

Every server has every entry and the leader still cannot commit them, because
they are from an earlier term. One empty entry in the current term unblocks the
whole prefix.

### 4. Under partition, the minority is unavailable — not wrong

```
  s0 (the leader) is now in a MINORITY of 2.
  write 'd' -> REFUSED
  s0's own log grew to 6 entries but commit_index is still 4
```

The leader appends to its own log and never commits, so no client is told the
write succeeded — which is exactly why deleting those entries on healing breaks
no promise.

```
    run    ops  elections  failed  committed  refused  safety
      0     40          5       3          1       22  holds
      3     40          7       2         14        5  holds
      7     40          4       3          6       19  holds
```

320 operations of partitions, crashes, restarts and elections in random order,
with safety asserted after every one. **Read the `refused` column**: Raft spends
much of its time saying no, and that is the product working. Every refusal is a
client correctly told its write did not happen, rather than a write that will
quietly disappear later.

---

## The three things that must survive a crash

`current_term`, `voted_for`, and the log — written to stable storage **before**
any reply is sent. The demo shows what losing `voted_for` costs:

```
  vote for s1 in term 1: True
  vote for s2 in term 1: False   (already voted)
  after a crash that lost voted_for, vote for s2 in term 1: True
```

Two votes in one term, which is the single assumption the whole safety argument
rests on. It is the difference between an implementation that is correct and one
that is correct until a machine reboots at the wrong moment.

---

## Where this implementation stops

- **No real network and no threads.** Everything is driven step by step, so
  message reordering, duplication and delay are things you inject rather than
  things that happen. That is a real gap: the hardest Raft bugs are timing bugs.
- **No log compaction or snapshots.** A follower far behind is caught up one
  entry per round trip, which the demo measures and which real implementations
  fix with snapshots.
- **The one-index-at-a-time backup.** Real implementations have the follower
  return the first index of its conflicting *term* so whole terms are skipped.
- **No membership changes.** Adding and removing servers safely (joint
  consensus) is a section of the paper on its own, and it is where several
  production implementations have had bugs.
- **No client sessions**, so no exactly-once semantics for retried commands.
- **No read-only optimisations.** Every read here goes through the log; real
  systems use lease-based or read-index reads and the correctness argument for
  those is subtle.

## Extensions worth trying

1. **Snapshots.** Truncate the log, send state instead, and work out what
   happens when a snapshot arrives mid-append.
2. **Joint consensus** for membership changes. Then try changing membership
   *during* a partition and see why the naive version can elect two leaders.
3. **The conflicting-term optimisation**, and measure the round trips it saves
   against the demo's table.
4. **A real message queue with reordering and duplication**, driven by a random
   scheduler. Then run the chaos loop again — this is where the timing bugs
   live.
5. **Read-index reads**, and convince yourself the leader really is still the
   leader before serving one.
6. **Wire it under [`database-engine/`](../../week-09/database-engine/)**: a replicated
   write-ahead log, with Raft deciding the order. That combination is, roughly,
   what a distributed SQL database is.

---

## Structure

```
raft/
├── README.md
├── check.py              # progress checker — run this first
├── log.py                # templates with TODOs and DESIGN DECISION blocks
├── election.py
├── replication.py
├── cluster.py            # capstone
└── solutions/
```

```bash
cd solutions
python3 log.py            # the consistency check, and 300 repaired divergences
python3 election.py       # split votes against jitter, the restriction
python3 replication.py    # Figure 8, and why the no-op is required
python3 cluster.py        # partitions, crashes, and 320 chaos operations
```

No dependencies beyond the Python 3 standard library. Everything runs in a few
seconds.

## Related directories

- [`dynamo-paper/`](../dynamo-paper/) — the same partition, the opposite answer.
  Read them as a pair.
- [`database-engine/`](../../week-09/database-engine/) — the log this would replicate
- [`system-design/`](../../reference/system-design/) — where consensus sits among the other
  patterns
- [`aws-from-scratch/`](../../week-01/aws-from-scratch/) — DynamoDB's quorums, and what
  they cost
- [`PHILOSOPHY.md`](../../PHILOSOPHY.md) — why this repo is built the way it is

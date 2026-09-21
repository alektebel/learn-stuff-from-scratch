# Raft From Scratch — Solutions

Complete implementations of every template in the parent directory. Pure Python
3 standard library, no dependencies.

```bash
python3 log.py            # ~2s
python3 election.py       # ~3s
python3 replication.py    # ~2s
python3 cluster.py        # ~20s, 320 operations against a hostile network
```

## Implementation notes

- **`Log.matches` is the whole inductive proof.** Agreement at index *i* can only
  ever be created out of agreement at *i-1*, which is why two servers that have
  never communicated agree about their entire history the moment one entry
  matches. Everything else in `log.py` exists to keep that invariant true.
- **The backup loop decrements one index at a time.** Real implementations have
  the follower return the first index of its conflicting *term* so whole terms
  are skipped in one round trip; the demo measures the worst case here (10
  rounds) so the optimisation has a number to beat.
- **`voted_for` is per TERM, not per server.** One vote per term is the entire
  election safety argument: two majorities always intersect, and the server in
  the intersection voted once. Notice what that does not depend on — clocks,
  message ordering, or timing.
- **`current_term`, `voted_for` and the log are the three things that must
  survive a crash**, written before any reply is sent. The demo shows the cost of
  losing `voted_for`: two votes in one term, which is the single assumption the
  safety argument rests on.
- **The election restriction compares (lastLogTerm, lastLogIndex) as a pair**,
  term first. A longer log does not win; a more up-to-date one does.
- **`commit_index` advances only when a majority has the entry AND it is from
  the leader's current term.** The obvious rule — "a majority has it" — is
  wrong, and `replication.py`'s Figure 8 demo builds the counterexample. Every
  test that does not include a leader change at exactly the wrong moment passes
  with the wrong rule, which is what makes it the part people implement
  incorrectly.
- **A new leader appends a no-op** in its own term. It looks like a hack and is
  not: without it a leader can hold every entry on every server and still commit
  none of them, because they are all from earlier terms. The demo measures it —
  commit_index 0 against 4.
- **`Cluster.check_safety` always `setdefault`s** into its seen map. An earlier
  version short-circuited when the command was already recorded, which made it
  blind to exactly the disagreement it existed to detect. The only test that
  found it was the positive one: hand-build a violation and assert it is caught.
  A safety checker that has never caught anything is not evidence.
- **The randomised election timeout is a probabilistic guarantee, stated as
  one.** Randomising does not eliminate split votes — nothing can, and FLP says
  why. It makes a *repeat* vanishingly unlikely, which is a different and weaker
  claim than the rest of Raft makes.

## What the demos measure

`log.py` — 300 random divergences repaired by backing up one index at a time,
with 0 followers left disagreeing and a worst case of 10 rounds. The subtlety
worth the whole exercise is in how those divergences are *generated*: give the
leader and the stale follower overlapping terms and the repair genuinely
misbehaves, but such a log could never exist, because one term has one leader.
The demo gives the leader even terms and the follower odd ones for exactly that
reason. **Raft's guarantees are about the logs the protocol can produce, not
about arbitrary logs.**

`election.py` — one vote per term enforced across concurrent candidates; the
election restriction rejecting a longer-but-staler log; and a jitter sweep
(1/5/25/50) showing split-vote frequency falling 100% → 5% and mean rounds to
elect falling 13.0 → 1.06.

`replication.py` — nextIndex/matchIndex convergence; Figure 8 built twice, once
under each commit rule, reporting whether the entry was **committed** before
being destroyed (the wrong rule violates safety; the right one never promised
anything); and the no-op measurement.

`cluster.py` — a leader pushed into a minority refusing writes while its own log
grows and `commit_index` does not, then 320 operations of partitions, crashes,
restarts and elections in random order with safety asserted after every single
one. **Read the `refused` column**: Raft spends much of its time saying no, and
that is the product working.

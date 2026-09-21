"""
Log — the replicated log, and the one property everything rests on.
Complete Solution.

Raft is not "an algorithm for agreeing on a value". It is an algorithm for
making N machines hold the SAME SEQUENCE of commands, so that applying them in
order gives every machine the same state. The log is the thing being agreed
on; the state machine is a consequence.

DESIGN DECISION — agree on values, or agree on an ordered log?
  Classic Paxos agrees on one value. Agreeing on a sequence means running many
  instances, and stitching them together — deciding which instance is next,
  what happens when instance 7 is decided but 5 is not — is where Multi-Paxos
  gets its reputation.
  CHOSEN: make the LOG the primitive. One leader appends, followers copy, and
  ordering is free because a log has an order built in. Raft's entire claim is
  that this is more understandable, and this file is where you find out whether
  you agree.

THE LOG MATCHING PROPERTY, which is the whole file:

    If two logs contain an entry with the SAME INDEX and the SAME TERM, then
    the logs are IDENTICAL in all entries up to and including that index.

  That is an extraordinarily strong statement — two machines that have never
  communicated agree about their entire history because ONE entry matches — and
  it is maintained by exactly two rules:

    1. A leader never overwrites or deletes its own entries; it only appends.
       So (index, term) uniquely identifies an entry, forever.
    2. AppendEntries carries the (index, term) of the entry BEFORE the ones it
       is sending, and a follower REFUSES unless it has that exact entry. So
       agreement at index i can only be created out of agreement at i-1, and by
       induction out of agreement everywhere before it.

  Rule 2 is the consistency check, and it is three lines of code doing the work
  of an inductive proof. `matches` below is those three lines.

DESIGN DECISION — what happens to a follower that disagrees?
  CHOSEN: the leader's log is the truth, always. A follower with conflicting
  entries has them DELETED. This is safe only because of the election
  restriction in safety.py — a candidate missing committed entries cannot win —
  and those two rules are load-bearing for each other. Take either one away and
  Raft loses committed data.
"""

from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple


class Entry(NamedTuple):
    """One command, tagged with the term the leader was in when it appended.

    The term is not metadata. It is half of the identity (index, term) that the
    log matching property is built on, and it is what lets a follower tell "the
    same entry" from "a different entry that happens to sit at the same index"
    — which is exactly what happens after a leader fails mid-append.
    """
    term: int
    command: Any

    def __repr__(self) -> str:
        return f"({self.term}:{self.command})"


class Log:
    """An append-only sequence, one-indexed as the paper is.

    One-indexed, which is a small irritation in Python and the right choice
    anyway: index 0 has to mean "before the beginning" so that `prev_index = 0`
    can mean "I am sending you the very first entry", and a sentinel that is
    also a valid index is a bug generator.
    """

    def __init__(self, entries: Optional[Sequence[Entry]] = None):
        self.entries: List[Entry] = list(entries or [])
        self.commit_index = 0
        self.last_applied = 0
        self.stats = {"appends": 0, "truncations": 0, "entries_deleted": 0,
                      "rejections": 0}

    # -- reading ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:
        return f"Log({self.entries}, commit={self.commit_index})"

    @property
    def last_index(self) -> int:
        return len(self.entries)

    @property
    def last_term(self) -> int:
        return self.entries[-1].term if self.entries else 0

    def term_at(self, index: int) -> int:
        """Term of the entry at `index`. Index 0 is "before the log", term 0.

        Returning 0 for index 0 rather than raising is what makes the
        consistency check uniform: sending the first entry has prev_index 0 and
        prev_term 0, and every follower agrees about the empty prefix.
        """
        if index == 0:
            return 0
        if not 1 <= index <= len(self.entries):
            raise IndexError(f"index {index} outside 1..{len(self.entries)}")
        return self.entries[index - 1].term

    def entry_at(self, index: int) -> Entry:
        return self.entries[index - 1]

    def slice_from(self, index: int) -> List[Entry]:
        return self.entries[index - 1:]

    # -- the consistency check ----------------------------------------------

    def matches(self, index: int, term: int) -> bool:
        """Do I have an entry at `index` whose term is `term`?

        Three lines, and they carry the induction. A follower answering False
        here forces the leader to back up and try an earlier index, and the
        backing-up terminates because both logs agree about index 0.
        """
        if index == 0:
            return True                  # everyone agrees about nothing
        if index > len(self.entries):
            return False                 # I am missing entries
        return self.entries[index - 1].term == term

    # -- writing ------------------------------------------------------------

    def append(self, term: int, command: Any) -> int:
        self.entries.append(Entry(term, command))
        self.stats["appends"] += 1
        return len(self.entries)

    def append_entries(self, prev_index: int, prev_term: int,
                       entries: Sequence[Entry]) -> bool:
        """The follower side of replication. Returns False to reject.

        Three things happen here and the ORDER of them is the algorithm:

        1. REFUSE if I do not have (prev_index, prev_term). Without this the
           log matching property is simply false and everything built on it
           collapses.
        2. Where my entries conflict with the leader's, DELETE mine and
           everything after. Not "merge", not "keep the longer one" — the
           leader's log is the truth.
        3. Append whatever is new.

        Step 2 has a trap: only truncate at a genuine CONFLICT. A stale
        AppendEntries can arrive carrying entries you already have, and
        truncating on it would delete entries you have already acknowledged —
        which a later leader may already be counting as committed. That is
        silent data loss, from an unnecessary delete.
        """
        if not self.matches(prev_index, prev_term):
            self.stats["rejections"] += 1
            return False

        for offset, entry in enumerate(entries):
            index = prev_index + 1 + offset
            if index <= len(self.entries):
                if self.entries[index - 1].term != entry.term:
                    deleted = len(self.entries) - index + 1
                    self.entries = self.entries[:index - 1]
                    self.stats["truncations"] += 1
                    self.stats["entries_deleted"] += deleted
                    self.entries.append(entry)
                # else: identical entry, already present — leave it alone
            else:
                self.entries.append(entry)
        return True

    # -- committing ---------------------------------------------------------

    def advance_commit(self, index: int) -> List[Entry]:
        """Move the commit index forward and return the newly committed entries.

        Never backwards. A commit index that could move backwards would mean
        un-telling a client that its write succeeded, and there is no way to do
        that.
        """
        index = min(index, len(self.entries))
        if index <= self.commit_index:
            return []
        newly = self.entries[self.commit_index:index]
        self.commit_index = index
        return list(newly)

    def committed(self) -> List[Entry]:
        return self.entries[:self.commit_index]

    def is_at_least_as_up_to_date_as(self, other_term: int,
                                     other_index: int) -> bool:
        """Is a log with (other_term, other_index) at least as current as mine?

        The comparison is by TERM FIRST, then length. A shorter log from a
        later term beats a longer log from an earlier one, and that ordering is
        not arbitrary: entries from a later term were appended by a leader that
        a majority had already voted for, so they reflect more recent
        agreement. A longer log full of stale entries is a leader that was
        partitioned away and kept writing to itself.

        This function IS the election restriction. It is what makes truncating
        a follower's log safe.
        """
        if other_term != self.last_term:
            return other_term > self.last_term
        return other_index >= self.last_index


def diverge(base: Sequence[Entry], *branches: Sequence[Entry]) -> List[Log]:
    """Build several logs sharing a prefix — for reproducing paper figures."""
    return [Log(list(base) + list(branch)) for branch in branches]


def _demo() -> None:
    print("=" * 76)
    print("LOG — one property, maintained by two rules")
    print("=" * 76)

    print("\n1. The consistency check refuses, and the leader backs up")
    print("-" * 76)
    leader = Log([Entry(1, "a"), Entry(1, "b"), Entry(2, "c"), Entry(3, "d")])
    follower = Log([Entry(1, "a"), Entry(1, "b")])
    print(f"  leader:   {leader.entries}")
    print(f"  follower: {follower.entries}")

    next_index = leader.last_index
    while next_index > 0:
        prev = next_index - 1
        accepted = follower.append_entries(prev, leader.term_at(prev),
                                           leader.slice_from(next_index))
        print(f"    AppendEntries prev=({prev}, term "
              f"{leader.term_at(prev)}) -> "
              f"{'accepted' if accepted else 'REJECTED, back up'}")
        if accepted:
            break
        next_index -= 1
    print(f"  follower is now {follower.entries}")
    print("  The leader had no idea how far behind the follower was and did")
    print("  not need to: it walks backwards one index at a time until the")
    print("  follower agrees, and termination is guaranteed because everyone")
    print("  agrees about index 0.")

    print("\n2. Conflicting entries are DELETED, not merged")
    print("-" * 76)
    leader = Log([Entry(1, "a"), Entry(2, "x"), Entry(2, "y")])
    follower = Log([Entry(1, "a"), Entry(1, "WRONG"), Entry(1, "ALSO WRONG")])
    print(f"  leader:   {leader.entries}")
    print(f"  follower: {follower.entries}   (same indexes, different terms)")
    follower.append_entries(1, 1, leader.slice_from(2))
    print(f"  after AppendEntries: {follower.entries}")
    print(f"  {follower.stats['entries_deleted']} entries deleted")
    print("  Those two entries were appended by a leader that lost its")
    print("  majority before committing them, so no client was ever told they")
    print("  succeeded. Deleting them is correct — and it is only SAFE because")
    print("  the election restriction stops a candidate missing committed")
    print("  entries from ever becoming leader. The two rules hold each other")
    print("  up; remove either and Raft loses committed data.")

    print("\n3. The trap: never truncate on entries you already have")
    print("-" * 76)
    careful = Log([Entry(1, "a"), Entry(1, "b"), Entry(1, "c")])
    careful.commit_index = 3
    before = list(careful.entries)
    # A DELAYED AppendEntries arrives, re-sending an entry already present.
    careful.append_entries(1, 1, [Entry(1, "b")])
    print(f"  log {before} with commit_index 3")
    print(f"  a delayed AppendEntries re-sends entry 2, which is identical")
    print(f"  after: {careful.entries}, "
          f"{careful.stats['entries_deleted']} deleted")
    assert careful.entries == before
    print("  Nothing was deleted, and that is the requirement. Truncate on")
    print("  every AppendEntries rather than only on a genuine CONFLICT and a")
    print("  stale message deletes committed entries — silent data loss caused")
    print("  by an unnecessary delete, and the network delivering an old")
    print("  message twice is not a rare event.")

    print("\n4. Up-to-date means TERM first, then length")
    print("-" * 76)
    mine = Log([Entry(1, "a"), Entry(1, "b"), Entry(1, "c"), Entry(1, "d")])
    print(f"  my log: {mine.entries}  (last term {mine.last_term}, "
          f"index {mine.last_index})")
    print(f"    {'candidate log':<34}{'term':>6}{'index':>7}{'may I vote?':>14}")
    for label, term, index in (
            ("shorter, later term", 2, 2),
            ("same term, shorter", 1, 3),
            ("same term, same length", 1, 4),
            ("longer, earlier term", 0, 9)):
        allowed = mine.is_at_least_as_up_to_date_as(term, index)
        print(f"    {label:<34}{term:>6}{index:>7}"
              f"{('yes' if allowed else 'no'):>14}")
    print("  A SHORTER log from a later term wins. Entries from a later term")
    print("  were appended by a leader a majority had already voted for, so")
    print("  they reflect more recent agreement; a longer log of stale entries")
    print("  is a leader that was partitioned away and kept writing to itself.")
    print("  Compare length first instead and Raft loses committed entries.")

    print("\n5. Repair, over three hundred random divergences")
    print("-" * 76)
    import random

    rng = random.Random(7)
    trials = 300
    failures = 0
    worst_backup = 0
    for _ in range(trials):
        # Leader terms are EVEN, the stale follower's are ODD. That is not a
        # convenience — it encodes the invariant that makes any of this work:
        # at most one leader per term, so two different entries can never share
        # an (index, term). Generate junk that violates it and you get logs
        # Raft could not produce, and the repair genuinely does misbehave on
        # them. The protocol's guarantees are only about the logs the protocol
        # can create.
        leader = Log()
        term = 2
        for _ in range(rng.randint(1, 10)):
            if rng.random() < 0.3:
                term += 2
            leader.append(term, rng.randint(0, 99))

        shared = rng.randint(0, len(leader))
        follower = Log(leader.entries[:shared])
        stale_term = rng.choice([1, 3, 5])
        for _ in range(rng.randint(0, 4)):
            follower.append(stale_term, rng.randint(0, 99))

        next_index = leader.last_index + 1
        steps = 0
        while next_index > 0:
            prev = next_index - 1
            steps += 1
            if follower.append_entries(prev, leader.term_at(prev),
                                       leader.slice_from(next_index)):
                break
            next_index -= 1
        worst_backup = max(worst_backup, steps)
        if follower.entries[:len(leader)] != leader.entries:
            failures += 1

    print(f"  {trials} random divergences, each repaired by backing up one")
    print(f"  index at a time: {failures} followers left disagreeing with the")
    print(f"  leader. Worst case {worst_backup} rounds of backing up.")
    print("  Every follower ends up carrying the leader's log, and the leader")
    print("  never needed to know how far behind any of them was. The walk")
    print("  terminates because index 0 always matches, and it CONVERGES")
    print("  because one agreeing entry implies agreement about everything")
    print("  before it.")
    print("  Two things worth noticing in that loop. First, the even/odd term")
    print("  split: give the follower junk with terms the leader also used and")
    print("  repair genuinely misbehaves — but such a log could never exist,")
    print("  because one term has one leader. The guarantee is about the logs")
    print("  the protocol can PRODUCE, not about arbitrary logs.")
    print("  Second, backing up one index per round trip is Raft's known")
    print("  inefficiency: a follower a thousand entries behind costs a")
    print("  thousand round trips. Real implementations have the follower")
    print("  return the first index of its conflicting TERM, so the leader can")
    print("  skip a whole term at a time.")

    print("\n" + "=" * 76)
    print("Next: election.py decides who gets to append.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()

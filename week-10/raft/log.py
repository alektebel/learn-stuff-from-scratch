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

Learning Path:
1. term_at, matches — three lines that carry an inductive proof
2. append_entries: refuse, then truncate only on a genuine CONFLICT, then
   append. The order is the algorithm.
3. advance_commit — forward only, never backwards
4. is_at_least_as_up_to_date_as — TERM first, then length. This function IS the
   election restriction.
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
        raise NotImplementedError

    @property
    def last_term(self) -> int:
        raise NotImplementedError

    def term_at(self, index: int) -> int:
        """Term of the entry at `index`. Index 0 is "before the log", term 0.

        Returning 0 for index 0 rather than raising is what makes the
        consistency check uniform: sending the first entry has prev_index 0 and
        prev_term 0, and every follower agrees about the empty prefix.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    # -- writing ------------------------------------------------------------

    def append(self, term: int, command: Any) -> int:
        raise NotImplementedError

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
        raise NotImplementedError

    # -- committing ---------------------------------------------------------

    def advance_commit(self, index: int) -> List[Entry]:
        """Move the commit index forward and return the newly committed entries.

        Never backwards. A commit index that could move backwards would mean
        un-telling a client that its write succeeded, and there is no way to do
        that.
        """
        raise NotImplementedError

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
        raise NotImplementedError


def diverge(base: Sequence[Entry], *branches: Sequence[Entry]) -> List[Log]:
    """Build several logs sharing a prefix — for reproducing paper figures."""
    return [Log(list(base) + list(branch)) for branch in branches]


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. A leader backing up one index at a time until a follower accepts.
    2. A follower's conflicting entries being DELETED, with the count.
    3. The trap: a delayed AppendEntries carrying entries the follower already
       has must delete NOTHING. Truncate on every append rather than only on a
       conflict and a stale message deletes committed entries.
    4. A table of candidate logs and whether you may vote for each. A SHORTER
       log from a later term wins.
    5. Three hundred random divergences repaired by backing up. Generate the
       divergent entries with terms the leader never used — one term has one
       leader, so two entries can never share an (index, term), and a generator
       that violates that produces logs Raft could not create and on which the
       repair genuinely misbehaves. The guarantee is about logs the PROTOCOL
       can produce.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

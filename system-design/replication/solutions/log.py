"""The replicated log: the data structure a leader-follower cluster copies around.

Source: Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm"
(Raft), USENIX ATC 2014, section 5.4.1 (the up-to-date rule), and the MIT 6.824
labs. A log is a list of entries; the entry at position `i` carries the **term** of the
leader that created it. Replicas exchange logs, find where they agree, and overwrite
whatever diverges.

DESIGN DECISION - how do we decide which of two logs is "more up-to-date"?
    First by last term, then by length. A longer log is NOT better: another replica may
    have overwritten those entries under a newer term, so length alone can pick a stale
    replica. This is the classic failover bug that silently loses committed writes.
    Cost: a replica with many uncommitted entries can be passed over, which is correct.

DESIGN DECISION - what makes an index "committed"?
    A majority of replicas must hold the entry. One replica (even the leader) is not
    enough: if only the leader has it and the leader dies, it is gone. We return the
    highest index held by a majority, stopping at the first index that does not reach a
    majority, because logs are prefixes of each other.
    Cost: commits wait for the slowest of a majority (the sync latency cost).

DESIGN DECISION - comparing entries.
    Two entries are equal only if both term and command match. In Raft the term alone
    would do (a leader never creates two entries with the same term at the same index),
    but comparing the full entry is strictly safer and needs no invariant.
    Cost: none.
"""
from collections import namedtuple

__all__ = ["Entry", "last_term", "is_up_to_date", "choose_leader", "quorum_index"]

Entry = namedtuple("Entry", "term command")


def last_term(entries):
    return entries[-1].term if entries else 0


def is_up_to_date(candidate, other):
    """True if `candidate` is at least as up-to-date as `other` (Raft 5.4.1)."""
    candidate_term, other_term = last_term(candidate), last_term(other)
    if candidate_term != other_term:
        return candidate_term > other_term
    return len(candidate) >= len(other)


def choose_leader(logs, eligible):
    """Pick the most up-to-date replica among `eligible`; ties break by name.

    `logs` maps replica name -> list of Entry. Returns None for an empty `eligible`.
    """
    return min(eligible, key=lambda name: (-last_term(logs[name]), -len(logs[name]), name),
               default=None)


def quorum_index(logs, majority):
    """Highest index held (identically) by at least `majority` of the given logs."""
    committed = 0
    index = 0
    while True:
        index += 1
        votes = {}
        for log in logs.values():
            if len(log) >= index:
                entry = log[index - 1]
                votes[entry] = votes.get(entry, 0) + 1
        if not votes:
            break
        _, count = max(votes.items(), key=lambda pair: pair[1])
        if count < majority:
            break
        committed = index
    return committed


if __name__ == "__main__":
    old = [Entry(1, "a"), Entry(1, "b"), Entry(1, "c")]      # longer, older term
    new = [Entry(2, "x")]                                    # shorter, newer term
    print(f"last_term(old)={last_term(old)}  last_term(new)={last_term(new)}")
    print(f"is_up_to_date(new, old)={is_up_to_date(new, old)}  "
          f"is_up_to_date(old, new)={is_up_to_date(old, new)}")
    logs = {"old": old, "new": new}
    print(f"choose_leader(['old','new']) = {choose_leader(logs, ['old', 'new'])!r} "
          f"(term beats length)")
    logs3 = {"a": [Entry(1, "a"), Entry(1, "b")], "b": [Entry(1, "a")], "c": [Entry(1, "a")]}
    print(f"committed with majority=2: {quorum_index(logs3, 2)} of {len(logs3['a'])} entries "
          f"(a single replica is not a quorum)")

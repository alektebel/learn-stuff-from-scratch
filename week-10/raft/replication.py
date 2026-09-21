"""
Replication — what the leader does, and the commit rule that is not obvious.
Complete Solution.

The leader appends to its own log, sends AppendEntries to everyone, and marks
an entry committed once a majority has it. That is right, and the last clause
hides the subtlest rule in Raft.

DESIGN DECISION — what does the leader track per follower?
  CHOSEN: two indexes.
    nextIndex[f]  the leader's GUESS at where to send from. Optimistic — it
                  starts at last_index + 1 — and decremented on rejection.
    matchIndex[f] what the leader KNOWS is replicated. Only ever set from a
                  successful reply, and only ever increases.
  Keeping them separate is the point. Committing from a guess would let a
  leader commit entries a follower rejected. Real bugs in real implementations
  have come from advancing matchIndex on a request rather than on a reply.

DESIGN DECISION — when is an entry committed?
  The obvious rule is "when a majority has it". THAT RULE IS WRONG, and Figure
  8 of the paper is the counterexample. An entry from an OLD term can be
  present on a majority and still be overwritten later, because a candidate
  with a shorter but more recent log can still win an election.

  The correct rule has two parts:

    1. A majority has the entry, AND
    2. the entry is from the leader's CURRENT term.

  Older entries then become committed indirectly: once a current-term entry is
  committed, everything before it is committed too, by the log matching
  property. Section 3 builds Figure 8 and shows an entry on three of five
  servers being destroyed — and then shows the same scenario with the rule
  applied, where it survives.

  This is the part of Raft that people implement wrong, because the wrong
  version works in every test that does not include a leader change at exactly
  the wrong moment.

DESIGN DECISION — what does the leader do first, on being elected?
  CHOSEN: append a NO-OP entry in its own term. It looks like a hack and it is
  load-bearing: without an entry from the current term, the commit rule above
  can never fire, so entries from previous terms stay uncommitted indefinitely
  even though every server has them. A no-op commits them all at once.

Learning Path:
1. build_append and handle_reply — nextIndex is a guess, matchIndex is
   knowledge, and matchIndex only ever moves on a REPLY
2. advance_commit — majority AND current term. Both clauses.
3. append_noop, and why it is required rather than an optimisation
4. Build Figure 8 and watch the naive rule lose a committed entry
"""

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from log import Entry, Log


class Leader:
    """A leader's view of its followers."""

    def __init__(self, name: str, peers: Sequence[str], log: Log, term: int):
        self.name = name
        self.peers = list(peers)
        self.log = log
        self.term = term
        # Optimistic: assume everyone is up to date, and find out otherwise.
        self.next_index: Dict[str, int] = {p: log.last_index + 1 for p in peers}
        # Pessimistic: assume nothing is replicated until a reply says so.
        self.match_index: Dict[str, int] = {p: 0 for p in peers}
        self.stats = {"appends_sent": 0, "rejected": 0, "committed": 0,
                      "commit_blocked_by_term": 0}

    @property
    def cluster_size(self) -> int:
        return len(self.peers) + 1

    @property
    def majority(self) -> int:
        return self.cluster_size // 2 + 1

    def append_noop(self) -> int:
        """Append an empty entry in the current term. Not a hack — required.

        Without an entry from the current term the commit rule can never fire,
        so entries inherited from previous terms stay uncommitted forever even
        when every server has them. One no-op commits the lot.
        """
        raise NotImplementedError

    def client_request(self, command: Any) -> int:
        raise NotImplementedError

    def build_append(self, peer: str) -> Tuple[int, int, List[Entry], int]:
        """(prev_index, prev_term, entries, leader_commit) for one follower."""
        raise NotImplementedError

    def handle_reply(self, peer: str, success: bool, follower_last: int) -> None:
        """Update the two indexes from a REPLY, never from a request.

        On success, matchIndex becomes the last index we actually sent — which
        we can compute, and which is why the caller passes it in. On failure,
        back nextIndex up by one and try again.
        """
        raise NotImplementedError

    def advance_commit(self) -> List[Entry]:
        """THE COMMIT RULE. Majority replication AND current term.

        Walk down from the last index looking for one that a majority holds. If
        that entry is from an EARLIER term, refuse to commit it — it can still
        be overwritten, and Figure 8 is the proof. Once a current-term entry
        commits, everything before it commits with it, for free, by the log
        matching property.
        """
        raise NotImplementedError

    def advance_commit_naively(self) -> List[Entry]:
        """The WRONG rule — majority replication only. Here to be broken."""
        raise NotImplementedError


def replicate(leader: Leader, followers: Dict[str, Log],
              reachable: Optional[Set[str]] = None, rounds: int = 12) -> None:
    """Run AppendEntries to convergence against the reachable followers."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. Three followers at different distances behind, with nextIndex and
       matchIndex before and after replication.
    2. A commit, showing everything before the committed entry committing too.
    3. FIGURE 8. Run the same scenario under the naive rule (majority only) and
       the real one (majority AND current term). Report not just whether the
       entry survived but whether it was COMMITTED before it was destroyed —
       that difference is the whole point. Under the naive rule a client was
       told a write succeeded and a later leader deleted it.
    4. The no-op: the same cluster with and without one, showing the commit
       index stuck at 0 without it even though every server has every entry.
    5. Round trips to catch up a follower N entries behind. One per entry, and
       what real implementations do about it.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

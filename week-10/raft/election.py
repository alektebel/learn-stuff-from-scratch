"""
Election — choosing a leader, and why the timeout is random. Complete Solution.

Raft's whole structure is "elect one leader, let it be the sole writer". That
makes replication simple and moves all the difficulty into two questions: how
do you make sure there is at most one leader, and how do you make sure there is
eventually at least one?

DESIGN DECISION — how do you guarantee at most one leader per term?
  CHOSEN: a term is a logical clock, and each server casts AT MOST ONE VOTE per
  term. A candidate needs a majority. Two candidates cannot both hold a
  majority of the same set, because two majorities of the same set always
  intersect and the server in the intersection only voted once.
  That is the entire safety argument for leader election, and it is one
  sentence. Note it does not depend on timing, message ordering, or clocks —
  which is why it survives a network that does arbitrary things.

DESIGN DECISION — how do you guarantee eventually at least one?
  You cannot, in a bounded number of steps: FLP says no deterministic protocol
  decides in an asynchronous system with even one crash. Raft does not try. If
  every server times out at the same moment, every server becomes a candidate,
  every server votes for itself, nobody gets a majority, and the term is
  wasted. Nothing stops that happening again.
  CHOSEN: RANDOMISE the timeout. This does not eliminate split votes; it makes
  a repeat vanishingly unlikely, so the expected number of rounds is small.
  Raft trades a hard guarantee for a probabilistic one and says so plainly.
  Section 3 measures split-vote rate against the amount of randomness, and the
  shape of that curve is the whole argument.

DESIGN DECISION — may any server become leader?
  No, and this is the rule that makes the log repair in log.py safe. A
  candidate whose log is not at least as up to date as a voter's does not get
  that vote. Since a candidate needs a majority, and any committed entry is on
  a majority, any candidate that can win must already hold every committed
  entry. Raft calls this the ELECTION RESTRICTION, and it is why a leader
  never needs to fetch missing entries from anyone — it is why AppendEntries
  only ever flows one way.

Learning Path:
1. observe_term — the rule checked before everything else, in every handler
2. start_election, handle_vote_request, receive_vote
3. The election restriction, inside handle_vote_request
4. Measure split-vote rate against timeout jitter
"""

import random
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from log import Log

FOLLOWER, CANDIDATE, LEADER = "follower", "candidate", "leader"


class VoteRequest(NamedTuple):
    term: int
    candidate: str
    last_log_index: int
    last_log_term: int


class VoteReply(NamedTuple):
    term: int
    granted: bool
    reason: str = ""


class Server:
    """One Raft server's election-related state.

    `current_term` and `voted_for` are the two fields the paper says must be
    PERSISTED before responding to any RPC. Losing `voted_for` across a crash
    lets a server vote twice in one term, which is the one thing the safety
    argument depends on — and it is the difference between a correct
    implementation and one that is correct until a machine reboots at the wrong
    moment.
    """

    def __init__(self, name: str, peers: Sequence[str],
                 log: Optional[Log] = None,
                 rng: Optional[random.Random] = None,
                 base_timeout: int = 10, jitter: int = 10):
        self.name = name
        self.peers = list(peers)
        self.log = log or Log()
        self.rng = rng or random.Random(hash(name) % 1000)
        self.base_timeout = base_timeout
        self.jitter = jitter

        self.current_term = 0            # PERSISTED
        self.voted_for: Optional[str] = None   # PERSISTED
        self.role = FOLLOWER
        self.leader: Optional[str] = None
        self.votes: set = set()
        self.election_deadline = 0
        self.stats = {"elections_started": 0, "votes_granted": 0,
                      "votes_refused_term": 0, "votes_refused_log": 0,
                      "became_leader": 0, "stepped_down": 0}

    def __repr__(self) -> str:
        return f"<{self.name} {self.role} term={self.current_term}>"

    @property
    def cluster_size(self) -> int:
        return len(self.peers) + 1

    @property
    def majority(self) -> int:
        return self.cluster_size // 2 + 1

    # -- terms --------------------------------------------------------------

    def observe_term(self, term: int) -> bool:
        """Any message carrying a higher term makes you a follower. Any.

        This one rule is checked before anything else in every RPC handler, in
        both directions, and it is what makes stale leaders harmless. A leader
        partitioned away for an hour rejoins, hears a single message from term
        47, and steps down before it can do any damage. There is no explicit
        "am I still the leader" check anywhere in Raft; this is it.
        """
        raise NotImplementedError

    def reset_election_timer(self, now: int) -> None:
        raise NotImplementedError

    # -- becoming a candidate ----------------------------------------------

    def start_election(self, now: int) -> VoteRequest:
        raise NotImplementedError

    # -- voting -------------------------------------------------------------

    def handle_vote_request(self, request: VoteRequest, now: int) -> VoteReply:
        """Grant a vote if the term is current, I have not voted, and the
        candidate's log is at least as up to date as mine.

        All three conditions, and the third is the election restriction. Drop
        it and elections still work, right up until a candidate missing
        committed entries wins and truncates them off every follower.
        """
        raise NotImplementedError

    def receive_vote(self, voter: str, reply: VoteReply) -> bool:
        """Count a vote. Returns True if this one made me the leader."""
        raise NotImplementedError


def run_election(servers: Sequence[Server], candidate_index: int,
                 now: int = 0, reachable: Optional[set] = None
                 ) -> Tuple[bool, List[str]]:
    """One full election round. Returns (won, reasons for each refusal)."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. A candidate winning with a majority, then a SECOND candidate asking the
       same servers in the same term and getting nothing.
    2. A candidate whose log is behind being refused, and one that is current
       winning.
    3. Split-vote rate and mean rounds-to-elect against timeout jitter from 1
       to 50. Randomising does not eliminate split votes — nothing can, and
       FLP says why — it makes a REPEAT unlikely.
    4. A leader receiving one message with a higher term and stepping down.
    5. What a crash may not lose: vote in a term, then clear voted_for as a
       crash would, then vote AGAIN in the same term. Two votes in one term is
       exactly what the safety argument forbids.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

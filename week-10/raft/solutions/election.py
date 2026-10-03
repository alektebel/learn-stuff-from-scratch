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
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None        # a NEW term, so a fresh vote
            if self.role != FOLLOWER:
                self.stats["stepped_down"] += 1
            self.role = FOLLOWER
            self.leader = None
            return True
        return False

    def reset_election_timer(self, now: int) -> None:
        self.election_deadline = now + self.base_timeout + self.rng.randrange(
            max(1, self.jitter))

    # -- becoming a candidate ----------------------------------------------

    def start_election(self, now: int) -> VoteRequest:
        self.current_term += 1
        self.role = CANDIDATE
        self.voted_for = self.name       # a candidate votes for itself
        self.votes = {self.name}
        self.leader = None
        self.reset_election_timer(now)
        self.stats["elections_started"] += 1
        return VoteRequest(self.current_term, self.name,
                           self.log.last_index, self.log.last_term)

    # -- voting -------------------------------------------------------------

    def handle_vote_request(self, request: VoteRequest, now: int) -> VoteReply:
        """Grant a vote if the term is current, I have not voted, and the
        candidate's log is at least as up to date as mine.

        All three conditions, and the third is the election restriction. Drop
        it and elections still work, right up until a candidate missing
        committed entries wins and truncates them off every follower.
        """
        self.observe_term(request.term)

        if request.term < self.current_term:
            self.stats["votes_refused_term"] += 1
            return VoteReply(self.current_term, False,
                             f"stale term {request.term} < {self.current_term}")

        if self.voted_for not in (None, request.candidate):
            return VoteReply(self.current_term, False,
                             f"already voted for {self.voted_for} this term")

        if not self.log.is_at_least_as_up_to_date_as(request.last_log_term,
                                                     request.last_log_index):
            self.stats["votes_refused_log"] += 1
            return VoteReply(self.current_term, False,
                             f"candidate log ({request.last_log_term}, "
                             f"{request.last_log_index}) is behind mine "
                             f"({self.log.last_term}, {self.log.last_index})")

        self.voted_for = request.candidate
        self.reset_election_timer(now)   # do not campaign against someone valid
        self.stats["votes_granted"] += 1
        return VoteReply(self.current_term, True, "granted")

    def receive_vote(self, voter: str, reply: VoteReply) -> bool:
        """Count a vote. Returns True if this one made me the leader."""
        if self.observe_term(reply.term):
            return False
        if self.role != CANDIDATE or reply.term != self.current_term:
            return False                 # a reply from an election I have left
        if reply.granted:
            self.votes.add(voter)
        if len(self.votes) >= self.majority and self.role == CANDIDATE:
            self.role = LEADER
            self.leader = self.name
            self.stats["became_leader"] += 1
            return True
        return False


def run_election(servers: Sequence[Server], candidate_index: int,
                 now: int = 0, reachable: Optional[set] = None
                 ) -> Tuple[bool, List[str]]:
    """One full election round. Returns (won, reasons for each refusal)."""
    candidate = servers[candidate_index]
    request = candidate.start_election(now)
    reasons = []
    for index, server in enumerate(servers):
        if index == candidate_index:
            continue
        if reachable is not None and server.name not in reachable:
            reasons.append(f"{server.name}: unreachable")
            continue
        reply = server.handle_vote_request(request, now)
        if not reply.granted:
            reasons.append(f"{server.name}: {reply.reason}")
        candidate.receive_vote(server.name, reply)
    return candidate.role == LEADER, reasons


def _demo() -> None:
    from log import Entry

    print("=" * 78)
    print("ELECTION — one vote per term, and a random timeout")
    print("=" * 78)

    def fresh(count=5, jitter=10, logs=None):
        names = [f"s{i}" for i in range(count)]
        return [Server(name, [p for p in names if p != name],
                       Log(list(logs[i]) if logs else []),
                       random.Random(100 + i), jitter=jitter)
                for i, name in enumerate(names)]

    print("\n1. A majority is enough, and two majorities cannot both exist")
    print("-" * 78)
    servers = fresh(5)
    won, reasons = run_election(servers, 0)
    print(f"  s0 campaigns in term {servers[0].current_term}: "
          f"{'WON' if won else 'lost'} with {len(servers[0].votes)} of 5 votes "
          f"(needs {servers[0].majority})")
    print("  It stopped counting at the majority — the remaining replies arrive")
    print("  when it is already leader and are ignored, which is why a Raft")
    print("  cluster keeps working with a minority permanently unreachable.")

    # A SECOND candidate in the same term, hand-built so the term is not
    # incremented — which is what a real concurrent candidate looks like from
    # each voter's point of view.
    rival = VoteRequest(servers[0].current_term, "s1",
                        servers[1].log.last_index, servers[1].log.last_term)
    granted = sum(1 for server in servers[1:]
                  if server.handle_vote_request(rival, 0).granted)
    print(f"  s1 asks the same servers for votes in the SAME term: "
          f"{granted} granted, needs {servers[0].majority}")
    refusal = servers[2].handle_vote_request(rival, 0).reason
    print(f"    s2 says: {refusal}")
    print("  Two candidates cannot both hold a majority of the same five")
    print("  servers, because any two majorities intersect and the server in")
    print("  the intersection voted once. That is the whole safety argument,")
    print("  and notice what it does NOT depend on: clocks, message ordering,")
    print("  or timing of any kind.")

    print("\n2. The election restriction refuses a candidate that is behind")
    print("-" * 78)
    logs = [[Entry(1, "a"), Entry(1, "b"), Entry(2, "c")]] * 4 + [[Entry(1, "a")]]
    servers = fresh(5, logs=logs)
    won, reasons = run_election(servers, 4)          # the one that is behind
    print(f"  s4 has {servers[4].log.entries} and campaigns: "
          f"{'won' if won else 'LOST'}")
    print(f"    {reasons[0]}")
    won, _ = run_election(servers, 0)                # one that is up to date
    print(f"  s0 has {servers[0].log.entries} and campaigns: "
          f"{'WON' if won else 'lost'}")
    print("  Any committed entry is on a majority; a candidate needs a")
    print("  majority; those two sets intersect. So a candidate that can win")
    print("  already holds every committed entry — which is why a Raft leader")
    print("  never fetches anything from a follower, and why AppendEntries")
    print("  only ever flows one way.")

    print("\n3. Split votes, and what randomness buys")
    print("-" * 78)
    print(f"    {'jitter':>8}{'split at least once':>22}"
          f"{'mean rounds to elect':>24}")
    for jitter in (1, 2, 5, 10, 25, 50):
        trials_with_a_split = 0
        rounds_total = 0
        trials = 400
        for trial in range(trials):
            rng = random.Random(trial)
            names = [f"s{i}" for i in range(5)]
            servers = [Server(n, [p for p in names if p != n],
                              rng=random.Random(trial * 10 + i), jitter=jitter)
                       for i, n in enumerate(names)]
            rounds = 0
            had_split = False
            while True:
                rounds += 1
                # Everyone whose randomised timer fires first campaigns.
                deadlines = [s.base_timeout + s.rng.randrange(max(1, jitter))
                             for s in servers]
                earliest = min(deadlines)
                contenders = [i for i, d in enumerate(deadlines)
                              if d == earliest]
                if len(contenders) > 1:
                    had_split = True
                    for server in servers:
                        server.current_term += 1
                        server.voted_for = None
                    if rounds > 12:
                        break
                    continue
                run_election(servers, contenders[0])
                break
            rounds_total += rounds
            trials_with_a_split += 1 if had_split else 0
        print(f"    {jitter:>8}{trials_with_a_split / trials:>21.0%}"
              f"{rounds_total / trials:>24.2f}")
    print("  Randomising the timeout does NOT eliminate split votes — nothing")
    print("  can, and FLP says why: no deterministic protocol decides in an")
    print("  asynchronous system with one crash. What it does is make a REPEAT")
    print("  vanishingly unlikely, so the expected number of rounds stays near")
    print("  one. Raft trades a hard guarantee for a probabilistic one, and is")
    print("  unusually direct about saying so.")

    print("\n4. A higher term ends your leadership, immediately")
    print("-" * 78)
    servers = fresh(5)
    run_election(servers, 0)
    leader = servers[0]
    print(f"  {leader.name} is leader in term {leader.current_term}")
    leader.observe_term(47)
    print(f"  it receives ONE message carrying term 47 -> {leader!r}")
    print("  There is no 'am I still leader?' check anywhere in Raft. This is")
    print("  it: any message with a higher term, in either direction, makes you")
    print("  a follower before you handle it. A leader partitioned away for an")
    print("  hour rejoins and steps down on its first received message.")

    print("\n5. Persistence: what a crash may not lose")
    print("-" * 78)
    server = Server("s0", ["s1", "s2"])
    request = VoteRequest(1, "s1", 0, 0)
    print(f"  vote for s1 in term 1: "
          f"{server.handle_vote_request(request, 0).granted}")
    print(f"  vote for s2 in term 1: "
          f"{server.handle_vote_request(VoteRequest(1, 's2', 0, 0), 0).granted}"
          f"  (already voted)")
    server.voted_for = None              # simulate losing it in a crash
    print(f"  after a crash that lost voted_for, vote for s2 in term 1: "
          f"{server.handle_vote_request(VoteRequest(1, 's2', 0, 0), 0).granted}")
    print("  Two votes in one term, which is exactly what the safety argument")
    print("  forbids — and now two leaders can hold 'majorities' that overlap")
    print("  only at this server. current_term and voted_for must reach stable")
    print("  storage BEFORE the reply is sent. It is the difference between an")
    print("  implementation that is correct and one that is correct until a")
    print("  machine reboots at the wrong moment.")

    print("\n" + "=" * 78)
    print("Next: replication.py is what the leader does once it has won.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()

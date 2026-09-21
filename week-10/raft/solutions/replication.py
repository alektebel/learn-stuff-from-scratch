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
        return self.log.append(self.term, None)

    def client_request(self, command: Any) -> int:
        return self.log.append(self.term, command)

    def build_append(self, peer: str) -> Tuple[int, int, List[Entry], int]:
        """(prev_index, prev_term, entries, leader_commit) for one follower."""
        next_index = self.next_index[peer]
        prev_index = next_index - 1
        self.stats["appends_sent"] += 1
        return (prev_index, self.log.term_at(prev_index),
                self.log.slice_from(next_index) if next_index <= len(self.log)
                else [], self.log.commit_index)

    def handle_reply(self, peer: str, success: bool, follower_last: int) -> None:
        """Update the two indexes from a REPLY, never from a request.

        On success, matchIndex becomes the last index we actually sent — which
        we can compute, and which is why the caller passes it in. On failure,
        back nextIndex up by one and try again.
        """
        if success:
            self.match_index[peer] = max(self.match_index[peer], follower_last)
            self.next_index[peer] = self.match_index[peer] + 1
        else:
            self.stats["rejected"] += 1
            self.next_index[peer] = max(1, self.next_index[peer] - 1)

    def advance_commit(self) -> List[Entry]:
        """THE COMMIT RULE. Majority replication AND current term.

        Walk down from the last index looking for one that a majority holds. If
        that entry is from an EARLIER term, refuse to commit it — it can still
        be overwritten, and Figure 8 is the proof. Once a current-term entry
        commits, everything before it commits with it, for free, by the log
        matching property.
        """
        for index in range(len(self.log), self.log.commit_index, -1):
            replicas = 1 + sum(1 for peer in self.peers
                               if self.match_index[peer] >= index)
            if replicas < self.majority:
                continue
            if self.log.term_at(index) != self.term:
                # A majority has it, and it is STILL NOT SAFE to commit.
                self.stats["commit_blocked_by_term"] += 1
                continue
            newly = self.log.advance_commit(index)
            self.stats["committed"] += len(newly)
            return newly
        return []

    def advance_commit_naively(self) -> List[Entry]:
        """The WRONG rule — majority replication only. Here to be broken."""
        for index in range(len(self.log), self.log.commit_index, -1):
            replicas = 1 + sum(1 for peer in self.peers
                               if self.match_index[peer] >= index)
            if replicas >= self.majority:
                return self.log.advance_commit(index)
        return []


def replicate(leader: Leader, followers: Dict[str, Log],
              reachable: Optional[Set[str]] = None, rounds: int = 12) -> None:
    """Run AppendEntries to convergence against the reachable followers."""
    for _ in range(rounds):
        progress = False
        for peer, follower_log in followers.items():
            if reachable is not None and peer not in reachable:
                continue
            prev_index, prev_term, entries, commit = leader.build_append(peer)
            ok = follower_log.append_entries(prev_index, prev_term, entries)
            if ok:
                follower_log.advance_commit(min(commit, len(follower_log)))
                last = prev_index + len(entries)
                if leader.match_index[peer] != last:
                    progress = True
                leader.handle_reply(peer, True, last)
            else:
                leader.handle_reply(peer, False, 0)
                progress = True
        if not progress:
            break


def _demo() -> None:
    print("=" * 78)
    print("REPLICATION — and the commit rule people get wrong")
    print("=" * 78)

    print("\n1. nextIndex is a guess; matchIndex is knowledge")
    print("-" * 78)
    leader_log = Log([Entry(1, "a"), Entry(1, "b"), Entry(2, "c"), Entry(2, "d")])
    followers = {"s1": Log([Entry(1, "a"), Entry(1, "b")]),
                 "s2": Log([Entry(1, "a")]),
                 "s3": Log(list(leader_log.entries))}
    leader = Leader("s0", list(followers), leader_log, term=2)
    print(f"  leader log {leader_log.entries}")
    print(f"    {'peer':<6}{'log before':<34}{'nextIndex':>11}{'matchIndex':>12}")
    for peer, log in followers.items():
        print(f"    {peer:<6}{str(log.entries):<34}"
              f"{leader.next_index[peer]:>11}{leader.match_index[peer]:>12}")
    replicate(leader, followers)
    print(f"  after replication ({leader.stats['rejected']} rejections):")
    for peer, log in followers.items():
        print(f"    {peer:<6}{str(log.entries):<34}"
              f"{leader.next_index[peer]:>11}{leader.match_index[peer]:>12}")
    print("  nextIndex started optimistic and walked back on rejection;")
    print("  matchIndex only ever moved on a successful REPLY. Advance")
    print("  matchIndex when you SEND and the leader will commit entries a")
    print("  follower rejected — a real bug in real implementations.")

    print("\n2. Committing")
    print("-" * 78)
    leader.client_request("e")
    replicate(leader, followers)
    committed = leader.advance_commit()
    print(f"  after appending 'e' and replicating: commit_index "
          f"{leader.log.commit_index}, {len(committed)} entries newly committed")
    print(f"  committed: {leader.log.committed()}")
    print("  One current-term entry reaching a majority committed everything")
    print("  before it as well, which is the log matching property paying off.")

    print("\n3. Figure 8 — where the obvious commit rule loses data")
    print("-" * 78)
    print("  Five servers. s0 was leader in term 2 and replicated entry 2 to")
    print("  s1 before crashing. s4 then became leader in term 3 with a")
    print("  SHORTER log — allowed, because term 3 beats term 2.")

    def figure_eight(rule: str) -> Tuple[str, str]:
        logs = {
            "s0": Log([Entry(1, "a"), Entry(2, "TERM-2")]),
            "s1": Log([Entry(1, "a"), Entry(2, "TERM-2")]),
            "s2": Log([Entry(1, "a")]),
            "s3": Log([Entry(1, "a")]),
            "s4": Log([Entry(1, "a")]),
        }
        # s0 is leader again in term 4 and re-replicates the old term-2 entry.
        leader = Leader("s0", ["s1", "s2", "s3", "s4"], logs["s0"], term=4)
        followers = {k: v for k, v in logs.items() if k != "s0"}
        replicate(leader, followers, reachable={"s1", "s2"})
        before = leader.log.commit_index
        if rule == "naive":
            leader.advance_commit_naively()
        else:
            leader.advance_commit()
        committed_old = leader.log.commit_index >= 2
        note = (f"entry 2 is on {1 + sum(1 for p in ['s1','s2','s3','s4'] if leader.match_index[p] >= 2)}"
                f" of 5 servers; "
                f"{'COMMITTED' if committed_old else 'not committed'}")

        # Now s0 crashes and s4 wins term 5 with a log that never had entry 2.
        s4 = Log([Entry(1, "a")])
        s4.append(5, "TERM-5")
        new_leader = Leader("s4", ["s0", "s1", "s2", "s3"], s4, term=5)
        others = {"s0": logs["s0"], "s1": logs["s1"],
                  "s2": logs["s2"], "s3": logs["s3"]}
        replicate(new_leader, others)
        survived = any(e.command == "TERM-2" for e in logs["s1"].entries)
        if committed_old and not survived:
            verdict = "SAFETY VIOLATED: committed, then deleted"
        elif committed_old:
            verdict = "committed and survived"
        elif survived:
            verdict = "uncommitted, happened to survive"
        else:
            verdict = "never committed — no promise was broken"
        return note, verdict

    for rule in ("naive", "raft"):
        note, fate = figure_eight(rule)
        label = ("majority only (WRONG)" if rule == "naive"
                 else "majority AND current term")
        print(f"    {label}")
        print(f"      {note}")
        print(f"      -> {fate}")
    print("  With the naive rule the leader tells a client its write succeeded")
    print("  and a later leader deletes it. Raft refuses to commit an entry")
    print("  from an EARLIER term no matter how many replicas have it: it")
    print("  waits for a current-term entry, and commits the old one with it.")
    print("  Every test that does not include a leader change at exactly the")
    print("  wrong moment passes with the wrong rule. That is what makes this")
    print("  the part people implement incorrectly.")

    print("\n4. Why a new leader appends a no-op")
    print("-" * 78)
    for use_noop in (False, True):
        log = Log([Entry(1, "a"), Entry(1, "b"), Entry(1, "c")])
        leader = Leader("s0", ["s1", "s2"], log, term=5)
        followers = {"s1": Log(list(log.entries)), "s2": Log(list(log.entries))}
        if use_noop:
            leader.append_noop()
        replicate(leader, followers)
        leader.advance_commit()
        print(f"    no-op appended: {str(use_noop):<6}"
              f"commit_index {leader.log.commit_index}, "
              f"blocked {leader.stats['commit_blocked_by_term']} times")
    print("  Every server has all three entries and the leader still cannot")
    print("  commit them, because they are from term 1 and it is in term 5.")
    print("  One empty entry in the current term unblocks the whole prefix.")
    print("  It looks like a hack; it is the commit rule's direct consequence.")

    print("\n5. The cost of one slow follower")
    print("-" * 78)
    print(f"    {'entries behind':>16}{'round trips to catch up':>26}")
    for behind in (1, 10, 100, 1000):
        log = Log([Entry(1, i) for i in range(behind + 3)])
        leader = Leader("s0", ["s1"], log, term=1)
        followers = {"s1": Log(log.entries[:3])}
        replicate(leader, followers, rounds=behind + 5)
        print(f"    {behind:>16}{leader.stats['rejected'] + 1:>26}")
    print("  One index per round trip. A follower restored from a day-old")
    print("  backup costs a round trip per entry it missed, and the leader is")
    print("  doing this while also serving traffic. Real implementations fix it")
    print("  two ways: the follower returns the first index of its conflicting")
    print("  TERM so whole terms can be skipped, and a follower far enough")
    print("  behind is sent a SNAPSHOT instead of a log.")

    print("\n" + "=" * 78)
    print("Next: cluster.py runs all of this against a network that misbehaves.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()

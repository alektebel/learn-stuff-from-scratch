"""
raft.py -- Raft leader election, log replication and commitment over the
simulated network in `network.py`.

Sources
-------
* Raft paper, "In Search of an Understandable Consensus Algorithm" (Ongaro &
  Ousterhout), sections 5.1-5.4 and Figure 2. In my own words:
    - A terms is a logical clock. Every RPC carries the sender's term; a node
      that sees a higher term immediately becomes a follower and forgets its
      vote. Terms give the protocol a total order of "epochs", so the stale
      leader of an old term can never act once a new one exists.
    - A candidate wins an election with a **majority** of the votes; it grants
      its vote only if the candidate's log is at least as up to date as its own.
      The majority rule plus that check is what makes "at most one leader per
      term" and "committed entries are never lost" hold.
    - The leader replicates its log with `AppendEntries`, which carries the
      previous entry's index and term. A follower rejects it if that entry does
      not match; the leader backs up and retries. This is the *log matching*
      property: if two logs agree at one index, they agree on everything before.
    - The leader commits an entry only once it sits on a majority and belongs to
      the leader's **current term**. Committing by majority alone (a previous
      term's entry) is the bug Raft's Figure 8 is drawn to prevent.
    - Committed entries are handed to the state machine **in log order**, once,
      as `commitIndex` advances.
* van Steen & Tanenbaum, *Distributed Systems*, ch. 8: leader-based replication
  and the primary-backup commit rule; a write is durable and visible once a
  majority has acknowledged it.

DESIGN DECISION -- one file for node and cluster, or two?
  `network.py` holds the medium; this file holds the protocol and a small
  `Cluster` harness that wires N nodes to a network and drives the clock.
  Keeping the harness here means the checks can build a cluster in one line
  without a third file, and the node itself stays free of any simulation
  concerns beyond "call `net.send`".

DESIGN DECISION -- what is "persistent" across a crash?
  `current_term`, `voted_for` and the log survive a crash; that is the stable
  storage Raft requires. The volatile bits (`state`, `commit_index`,
  `last_applied`) are also kept on the object in this toy, and a restarted node
  is assumed to have recovered them. That is a simplification -- a real restart
  rebuilds `commitIndex` from the leader and replays the log into the state
  machine -- and it is listed under "where it stops" in the README. The checks
  care about election and replication safety, not about crash recovery of the
  state machine.

DESIGN DECISION -- how are committed entries delivered?
  A node keeps `applied`, an append-only list of `(index, term, command)`.
  `_apply()` runs whenever `commitIndex` advances and walks indices upward, so
  the channel is ordered by construction and an entry is applied exactly once
  per node. Alternative: a callback/queue drained by the caller. Kept as a list
  so a check can compare every node's history directly.

BUGS THIS FILE IS WRITTEN TO MAKE POSSIBLE TO CATCH
  - granting a vote to a candidate whose log is behind a committed entry;
  - committing as soon as a leader appends (without a majority);
  - applying entries that are not committed;
  - not stepping down on a higher term, or not truncating a conflicting suffix.
  Each is planted by `_build/mutations.py` and must be caught by a check.
"""

import random

from network import Network

# The three roles of a Raft node (Raft paper, Figure 2).
FOLLOWER = "follower"
CANDIDATE = "candidate"
LEADER = "leader"


class LogEntry:
    __slots__ = ("term", "command")

    def __init__(self, term, command):
        self.term = term
        self.command = command

    def __eq__(self, other):
        return isinstance(other, LogEntry) and self.term == other.term and self.command == other.command

    def __repr__(self):
        return f"LogEntry(term={self.term}, command={self.command!r})"


class RaftNode:
    """One Raft server. Drives itself with `tick()` and messages via `receive()`."""

    def __init__(self, node_id, peers, net, seed=0,
                 election_timeout=(10, 20), heartbeat_interval=3):
        # TODO: Set the stable state (current_term=0, voted_for=None, log=[]) and the volatile state (FOLLOWER, leader_id, commit_index=0, last_applied=0), plus next_index/match_index/votes_received and an empty applied list. Own a random.Random(seed). Start the election timer.
        raise NotImplementedError("RaftNode.__init__")

    # -- small queries -----------------------------------------------------

    @property
    def majority(self):
        # TODO: One more than half the peers: len(self.peers)//2 + 1.
        raise NotImplementedError("RaftNode.majority")

    @property
    def last_log_index(self):
        # TODO: len(self.log).
        raise NotImplementedError("RaftNode.last_log_index")

    @property
    def last_log_term(self):
        # TODO: The last entry's term, or 0 for an empty log.
        raise NotImplementedError("RaftNode.last_log_term")

    def is_running(self):
        # TODO: Whether tick/receive should do anything (a crashed node is not running).
        raise NotImplementedError("RaftNode.is_running")

    def _reset_election_timer(self):
        # TODO: Set the election deadline to now + rng.randint(lo, hi). The randomisation is what stops every node timing out together.
        raise NotImplementedError("RaftNode._reset_election_timer")

    def _reset_heartbeat_timer(self):
        # TODO: Set the heartbeat deadline to now + heartbeat_interval.
        raise NotImplementedError("RaftNode._reset_heartbeat_timer")

    # -- lifecycle ---------------------------------------------------------

    def stop(self):
        """Crash: stop processing. Stable storage is retained."""
        # TODO: A crash: mark the node not running. Stable storage (term, vote, log) is kept.
        raise NotImplementedError("RaftNode.stop")

    def start(self):
        """Restart after a crash: come back as a follower and wait."""
        # TODO: Come back as a follower with no known leader, clear the per-peer leader state, and reset the election timer.
        raise NotImplementedError("RaftNode.start")

    # -- the clock ---------------------------------------------------------

    def tick(self):
        # TODO: If leader: send heartbeats and reset the heartbeat timer when its deadline passes. Otherwise: if now is past the election deadline, start an election.
        raise NotImplementedError("RaftNode.tick")

    # -- message intake ----------------------------------------------------

    def receive(self, src, msg):
        # TODO: Dispatch by msg['type'] to the four handlers.
        raise NotImplementedError("RaftNode.receive")

    # -- elections ---------------------------------------------------------

    def _start_election(self):
        # TODO: Become CANDIDATE, current_term += 1, vote for yourself, reset the timer, and send RequestVote (with your last log index and term) to every peer. If you already have a majority (a one-node cluster), become leader.
        raise NotImplementedError("RaftNode._start_election")

    def _on_request_vote(self, src, msg):
        # TODO: A higher term makes you a follower and clears your vote. If the term matches and you have not voted for someone else and the candidate's log is at least as up to date (last_log_term, then last_log_index), grant the vote, remember it, and reset your timer. Reply with your term and the decision.
        raise NotImplementedError("RaftNode._on_request_vote")

    def _on_request_vote_reply(self, src, msg):
        # TODO: A higher term makes you a follower. If you are still a candidate in that term and the vote was granted, count it; on a majority become leader.
        raise NotImplementedError("RaftNode._on_request_vote_reply")

    def _become_leader(self):
        # TODO: Set state LEADER, leader_id to yourself, next_index[p]=last_log_index+1 and match_index[p]=0 for every peer, then broadcast an (empty) AppendEntries at once to assert leadership.
        raise NotImplementedError("RaftNode._become_leader")

    # -- replication -------------------------------------------------------

    def _broadcast_append(self):
        # TODO: Send an AppendEntries to every peer except yourself.
        raise NotImplementedError("RaftNode._broadcast_append")

    def _send_append(self, peer):
        # TODO: For this peer: prev = next_index-1, prev_term = that entry's term (0 if none), entries = your log from prev onward, leader_commit = commit_index. Include term and leader id.
        raise NotImplementedError("RaftNode._send_append")

    def _on_append_entries(self, src, msg):
        # TODO: Reject a lower term. A higher term makes you a follower. Reset your election timer and note the leader. If prev_log_index is past your log or its term does not match, reject with a conflict_index pointing at the first entry of the disagreeing term. Otherwise keep the matching prefix, DELETE the conflicting suffix, extend with the new entries, then set commit_index = min(leader_commit, prev_log_index + len(entries)) and apply. Reply success with match_index.
        raise NotImplementedError("RaftNode._on_append_entries")

    def _on_append_entries_reply(self, src, msg):
        # TODO: A higher term makes you a follower. Ignore replies unless you are still the leader of that term. Success: raise match_index/next_index for that peer and try to advance the commit. Failure: back next_index up (use conflict_index to skip a whole term) and resend.
        raise NotImplementedError("RaftNode._on_append_entries_reply")

    def _advance_commit(self):
        """Commit the highest N that is on a majority and from THIS term."""
        # TODO: Scan N downward from the last log index: skip entries whose term is not the current term (Figure 8), and commit the first N that is held by a majority (yourself plus the peers with match_index >= N). Then apply.
        raise NotImplementedError("RaftNode._advance_commit")

    def _apply(self):
        # TODO: While last_applied < commit_index: advance it and append (index, term, command) to self.applied. In-order and exactly once follows from walking the index up one at a time.
        raise NotImplementedError("RaftNode._apply")

    # -- client interface --------------------------------------------------

    def propose(self, command):
        """Append a client command if this node is the leader; return its index."""
        # TODO: Refuse unless you are the leader. Append an entry stamped with the current term, replicate it, and return its index.
        raise NotImplementedError("RaftNode.propose")


class Cluster:
    """N Raft nodes wired to one simulated network, plus the clock."""

    def __init__(self, n=5, seed=0, drop=0.0, delay=(1, 3), reorder=False,
                 election_timeout=(10, 20), heartbeat_interval=3):
        # TODO: Build ids n0..n(n-1), one Network (seeded), and one RaftNode per id wired to it; give each node a distinct seed so their timeouts differ.
        raise NotImplementedError("Cluster.__init__")

    def run(self, ticks=1):
        # TODO: For each tick: step the network, then tick every node in id order. Order matters for reproducibility.
        raise NotImplementedError("Cluster.run")

    def leaders(self):
        # TODO: Every running node whose state is LEADER.
        raise NotImplementedError("Cluster.leaders")

    def leader(self):
        # TODO: The single leader, or None when there is no leader or more than one.
        raise NotImplementedError("Cluster.leader")

    def crash(self, node_id):
        # TODO: Stop the node and tell the network to drop its messages.
        raise NotImplementedError("Cluster.crash")

    def restart(self, node_id):
        # TODO: Start the node and tell the network it is reachable again.
        raise NotImplementedError("Cluster.restart")

    def partition(self, groups):
        # TODO: Pass the groups to the network so cross-group messages are dropped.
        raise NotImplementedError("Cluster.partition")

    def heal(self):
        # TODO: Remove the partition.
        raise NotImplementedError("Cluster.heal")

    def propose(self, command):
        # TODO: Send the command to the current leader; None if there is no unique leader.
        raise NotImplementedError("Cluster.propose")

    # -- safety inspections -------------------------------------------------

    def applied_conflict(self):
        """Return (index, (a, node_a), (b, node_b)) if two nodes applied
        different commands at the same index, else None."""
        # TODO: For every (index, command) in every node's applied history, the same index must carry the same command everywhere. Return the first disagreement.
        raise NotImplementedError("Cluster.applied_conflict")

    def committed_conflict(self):
        """Two nodes must never have committed different entries at an index."""
        # TODO: For every index up to each node's commit_index, the (term, command) must be identical across nodes. Return the first disagreement.
        raise NotImplementedError("Cluster.committed_conflict")

    def log_matching_violation(self):
        """Property: equal (index, term) implies identical prefixes.

        We check the weaker, sufficient form: wherever two logs share a term at
        the same index, every entry up to that index must be identical.
        """
        # TODO: For every pair of logs, wherever they share a term at some index every earlier entry must be identical. Return the first violation.
        raise NotImplementedError("Cluster.log_matching_violation")


def _demo():
    """Elect a leader, replicate three commands, and print the outcome."""
    cluster = Cluster(n=5, seed=2024)
    cluster.run(40)
    leader = cluster.leader()
    print("elected leader:", leader, "term:", cluster.nodes[leader].current_term if leader else None)
    elected_term = cluster.nodes[leader].current_term
    for command in ("x=1", "y=2", "x=3"):
        cluster.propose(command)
        cluster.run(10)
    node = cluster.nodes[leader]
    print("commits:", node.commit_index, "applied:", [c for _, _, c in node.applied])
    print("terms seen:", sorted({n.current_term for n in cluster.nodes.values()}))
    print("conflicts:", cluster.applied_conflict(), cluster.committed_conflict())
    assert cluster.leader() == leader and node.commit_index == 3
    assert cluster.applied_conflict() is None
    for entry in cluster.nodes.values():
        assert [c for _, _, c in entry.applied] == ["x=1", "y=2", "x=3"]
    print(f"elected in term {elected_term}, 3/3 commands committed on all 5 nodes")


if __name__ == "__main__":
    _demo()

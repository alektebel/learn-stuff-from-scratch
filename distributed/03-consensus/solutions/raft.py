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
        self.id = node_id
        self.peers = list(peers)          # every node id, including self.id
        self.net = net
        self.rng = random.Random(seed)
        self.election_timeout = election_timeout
        self.heartbeat_interval = heartbeat_interval

        # Stable storage (Raft Figure 2).
        self.current_term = 0
        self.voted_for = None
        self.log = []                     # log[i - 1] is index i

        # Volatile state.
        self.state = FOLLOWER
        self.commit_index = 0
        self.last_applied = 0
        self.leader_id = None

        # Leader bookkeeping.
        self.next_index = {}
        self.match_index = {}
        self.votes_received = set()

        # The apply channel: (index, term, command) in index order.
        self.applied = []

        self._running = True
        self._election_deadline = None
        self._heartbeat_deadline = None
        self._reset_election_timer()

    # -- small queries -----------------------------------------------------

    @property
    def majority(self):
        return len(self.peers) // 2 + 1

    @property
    def last_log_index(self):
        return len(self.log)

    @property
    def last_log_term(self):
        return self.log[-1].term if self.log else 0

    def is_running(self):
        return self._running

    def _reset_election_timer(self):
        lo, hi = self.election_timeout
        self._election_deadline = self.net.now + self.rng.randint(lo, hi)

    def _reset_heartbeat_timer(self):
        self._heartbeat_deadline = self.net.now + self.heartbeat_interval

    # -- lifecycle ---------------------------------------------------------

    def stop(self):
        """Crash: stop processing. Stable storage is retained."""
        self._running = False

    def start(self):
        """Restart after a crash: come back as a follower and wait."""
        self._running = True
        self.state = FOLLOWER
        self.leader_id = None
        self.next_index = {}
        self.match_index = {}
        self.votes_received = set()
        self._reset_election_timer()

    # -- the clock ---------------------------------------------------------

    def tick(self):
        if not self._running:
            return
        if self.state == LEADER:
            if self._heartbeat_deadline is None or self.net.now >= self._heartbeat_deadline:
                self._broadcast_append()
                self._reset_heartbeat_timer()
        elif self.net.now >= self._election_deadline:
            self._start_election()

    # -- message intake ----------------------------------------------------

    def receive(self, src, msg):
        if not self._running:
            return
        kind = msg["type"]
        if kind == "RequestVote":
            self._on_request_vote(src, msg)
        elif kind == "RequestVoteReply":
            self._on_request_vote_reply(src, msg)
        elif kind == "AppendEntries":
            self._on_append_entries(src, msg)
        elif kind == "AppendEntriesReply":
            self._on_append_entries_reply(src, msg)

    # -- elections ---------------------------------------------------------

    def _start_election(self):
        self.state = CANDIDATE
        self.current_term += 1
        self.voted_for = self.id
        self.votes_received = {self.id}
        self.leader_id = None
        self._reset_election_timer()
        request = {
            "type": "RequestVote",
            "term": self.current_term,
            "candidate": self.id,
            "last_log_index": self.last_log_index,
            "last_log_term": self.last_log_term,
        }
        for peer in self.peers:
            if peer != self.id:
                self.net.send(self.id, peer, request)
        if len(self.votes_received) >= self.majority:
            self._become_leader()

    def _on_request_vote(self, src, msg):
        term = msg["term"]
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.state = FOLLOWER
            self.leader_id = None

        granted = False
        if term == self.current_term:
            # Up-to-date means: its last term is newer, or the same term and at
            # least as long. This single check is what stops a node that missed
            # a committed entry from ever winning an election.
            up_to_date = (
                msg["last_log_term"] > self.last_log_term
                or (msg["last_log_term"] == self.last_log_term
                    and msg["last_log_index"] >= self.last_log_index)
            )
            if (self.voted_for is None or self.voted_for == msg["candidate"]) and up_to_date:
                self.voted_for = msg["candidate"]
                granted = True
                self._reset_election_timer()
        self.net.send(self.id, msg["candidate"], {
            "type": "RequestVoteReply",
            "term": self.current_term,
            "vote_granted": granted,
        })

    def _on_request_vote_reply(self, src, msg):
        if msg["term"] > self.current_term:
            self.current_term = msg["term"]
            self.voted_for = None
            self.state = FOLLOWER
            self.leader_id = None
            return
        if self.state != CANDIDATE or msg["term"] != self.current_term:
            return
        if msg["vote_granted"]:
            self.votes_received.add(src)
            if len(self.votes_received) >= self.majority:
                self._become_leader()

    def _become_leader(self):
        self.state = LEADER
        self.leader_id = self.id
        for peer in self.peers:
            self.next_index[peer] = self.last_log_index + 1
            self.match_index[peer] = 0
        self._reset_heartbeat_timer()
        self._broadcast_append()

    # -- replication -------------------------------------------------------

    def _broadcast_append(self):
        for peer in self.peers:
            if peer != self.id:
                self._send_append(peer)

    def _send_append(self, peer):
        next_index = self.next_index.get(peer, self.last_log_index + 1)
        prev_index = next_index - 1
        if 0 < prev_index <= len(self.log):
            prev_term = self.log[prev_index - 1].term
        else:
            prev_term = 0
        entries = [
            {"term": e.term, "command": e.command}
            for e in self.log[prev_index:]
        ]
        self.net.send(self.id, peer, {
            "type": "AppendEntries",
            "term": self.current_term,
            "leader": self.id,
            "prev_log_index": prev_index,
            "prev_log_term": prev_term,
            "entries": entries,
            "leader_commit": self.commit_index,
        })

    def _on_append_entries(self, src, msg):
        term = msg["term"]
        follower_reply = {
            "type": "AppendEntriesReply",
            "term": self.current_term,
            "success": False,
            "match_index": 0,
            "conflict_index": self.last_log_index + 1,
        }
        if term < self.current_term:
            self.net.send(self.id, msg["leader"], follower_reply)
            return
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
        self.state = FOLLOWER
        self.leader_id = msg["leader"]
        self._reset_election_timer()

        prev_index = msg["prev_log_index"]
        prev_term = msg["prev_log_term"]
        # Log matching: the entry before the new ones must exist and match.
        if prev_index > len(self.log) or (prev_index > 0 and self.log[prev_index - 1].term != prev_term):
            conflict = self.last_log_index + 1
            if prev_index <= len(self.log):
                # First index whose term differs: lets the leader back up fast.
                for i in range(prev_index - 1, -1, -1):
                    if self.log[i].term != prev_term:
                        conflict = i + 2
                        break
            follower_reply["conflict_index"] = conflict
            self.net.send(self.id, msg["leader"], follower_reply)
            return

        new_entries = [LogEntry(e["term"], e["command"]) for e in msg["entries"]]
        # Keep the matching prefix, truncate any conflicting suffix, append.
        i = 0
        while i < len(new_entries) and prev_index + 1 + i <= len(self.log):
            if self.log[prev_index + i].term != new_entries[i].term:
                break
            i += 1
        del self.log[prev_index + i:]
        self.log.extend(new_entries[i:])

        if msg["leader_commit"] > self.commit_index:
            self.commit_index = min(msg["leader_commit"], prev_index + len(new_entries))
            self._apply()

        self.net.send(self.id, msg["leader"], {
            "type": "AppendEntriesReply",
            "term": self.current_term,
            "success": True,
            "match_index": prev_index + len(new_entries),
        })

    def _on_append_entries_reply(self, src, msg):
        if msg["term"] > self.current_term:
            self.current_term = msg["term"]
            self.voted_for = None
            self.state = FOLLOWER
            self.leader_id = None
            return
        if self.state != LEADER or msg["term"] != self.current_term:
            return
        if msg["success"]:
            match = msg["match_index"]
            if match > self.match_index.get(src, 0):
                self.match_index[src] = match
                self.next_index[src] = match + 1
            self._advance_commit()
        else:
            conflict = msg.get("conflict_index", self.next_index.get(src, 1) - 1)
            self.next_index[src] = max(1, min(self.next_index.get(src, 1) - 1, conflict))
            self._send_append(src)

    def _advance_commit(self):
        """Commit the highest N that is on a majority and from THIS term."""
        for n in range(len(self.log), self.commit_index, -1):
            if self.log[n - 1].term != self.current_term:
                # Figure 8: a previous-term entry may be on a majority and still
                # be overwritten later; only current-term entries are counted.
                continue
            on_majority = 1 + sum(
                1 for peer in self.peers
                if peer != self.id and self.match_index.get(peer, 0) >= n
            )
            if on_majority >= self.majority:
                self.commit_index = n
                self._apply()
                break

    def _apply(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            self.applied.append((self.last_applied, entry.term, entry.command))

    # -- client interface --------------------------------------------------

    def propose(self, command):
        """Append a client command if this node is the leader; return its index."""
        if self.state != LEADER:
            return None
        self.log.append(LogEntry(self.current_term, command))
        self._broadcast_append()
        return self.last_log_index


class Cluster:
    """N Raft nodes wired to one simulated network, plus the clock."""

    def __init__(self, n=5, seed=0, drop=0.0, delay=(1, 3), reorder=False,
                 election_timeout=(10, 20), heartbeat_interval=3):
        self.ids = [f"n{i}" for i in range(n)]
        self.net = Network(seed=seed, min_delay=delay[0], max_delay=delay[1],
                           drop=drop, reorder=reorder)
        self.nodes = {}
        for i, node_id in enumerate(self.ids):
            node = RaftNode(node_id, self.ids, self.net, seed=seed * 1000 + i,
                            election_timeout=election_timeout,
                            heartbeat_interval=heartbeat_interval)
            self.nodes[node_id] = node
            self.net.register(node_id, node)

    def run(self, ticks=1):
        for _ in range(ticks):
            self.net.step()
            for node_id in self.ids:
                self.nodes[node_id].tick()

    def leaders(self):
        return [n.id for n in self.nodes.values()
                if n.is_running() and n.state == LEADER]

    def leader(self):
        ls = self.leaders()
        return ls[0] if len(ls) == 1 else None

    def crash(self, node_id):
        self.nodes[node_id].stop()
        self.net.crash(node_id)

    def restart(self, node_id):
        self.nodes[node_id].start()
        self.net.restart(node_id)

    def partition(self, groups):
        self.net.set_partition(groups)

    def heal(self):
        self.net.heal()

    def propose(self, command):
        leader = self.leader()
        if leader is None:
            return None
        return self.nodes[leader].propose(command)

    # -- safety inspections -------------------------------------------------

    def applied_conflict(self):
        """Return (index, (a, node_a), (b, node_b)) if two nodes applied
        different commands at the same index, else None."""
        seen = {}
        for node_id in self.ids:
            for index, _term, command in self.nodes[node_id].applied:
                if index in seen and seen[index][0] != command:
                    return (index, seen[index], (command, node_id))
                seen[index] = (command, node_id)
        return None

    def committed_conflict(self):
        """Two nodes must never have committed different entries at an index."""
        seen = {}
        for node_id in self.ids:
            node = self.nodes[node_id]
            for index in range(1, node.commit_index + 1):
                entry = node.log[index - 1]
                key = (entry.term, entry.command)
                if index in seen and seen[index][0] != key:
                    return (index, seen[index], (key, node_id))
                seen[index] = (key, node_id)
        return None

    def log_matching_violation(self):
        """Property: equal (index, term) implies identical prefixes.

        We check the weaker, sufficient form: wherever two logs share a term at
        the same index, every entry up to that index must be identical.
        """
        for i in range(len(self.ids)):
            for j in range(i + 1, len(self.ids)):
                a = self.nodes[self.ids[i]].log
                b = self.nodes[self.ids[j]].log
                for k in range(min(len(a), len(b))):
                    if a[k].term == b[k].term and a[k].command != b[k].command:
                        return (self.ids[i], self.ids[j], k + 1, a[k], b[k])
        return None


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

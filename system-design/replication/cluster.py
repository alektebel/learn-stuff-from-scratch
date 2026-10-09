"""Leader-follower replication with failover and fencing.

Source: Kleppmann, "Designing Data-Intensive Applications" chapter 5 (replication,
failover, the problems with it) and Ongaro & Ousterhout, Raft (ATC 2014) for the
election and commit rules. One leader accepts writes and copies its log to followers.
Synchronous replication waits for a majority before acknowledging; asynchronous returns
as soon as the leader has written, which is fast and loses the ack if the leader dies.

DESIGN DECISION - sync or async?
    `mode="sync"` acknowledges a write after a majority of replicas store it: a
    committed write survives the loss of any minority, at the cost of one round trip to
    the slowest follower in the majority. `mode="async"` acknowledges after the leader
    appends: lower latency, and a failover can erase writes the client was already told
    succeeded. We implement both so the trade-off is measured, not asserted.
    Cost: no middle ground here (a real system commits on local disk and replicates in
    the background, trading a short loss window for latency).

DESIGN DECISION - how is a new leader chosen on failover?
    The most up-to-date reachable replica (see `log.choose_leader`), among those that can
    reach a majority. "Reachable a majority" is what prevents two leaders: a node cut off
    from the majority cannot be elected, so at most one leader per term exists.
    Cost: failover stalls while a majority is unreachable.

DESIGN DECISION - how is a diverged follower repaired?
    `_follow` finds the longest matching prefix and replaces everything after it with the
    leader's entries. Entries the follower has that conflict with the leader are dropped
    (they were uncommitted, created by an old leader). It refuses to drop an entry at or
    below `commit_index`: a leader that lacks a committed entry is a safety violation, not
    a follower to obey.
    Cost: an uncommitted tail is discarded even if it might have been durable.

DESIGN DECISION - what stops the old leader from writing after a failover?
    A monotonically increasing **epoch** (a fencing token). Every election bumps it; any
    resource that accepts writes (`FencedStore`) refuses an epoch older than the newest
    it has seen. Without it, a partitioned old leader keeps serving a client and the
    client's next read hits the new leader, which never saw the write.
    Cost: every write path must carry and check the token.
"""

from log import Entry, choose_leader, quorum_index

__all__ = ["ReplicaSet", "FencedStore", "ReplicationError", "StaleEpoch"]


class ReplicationError(Exception):
    """An operation would violate replication safety (e.g. losing committed entries)."""


class StaleEpoch(Exception):
    """A write carried a fencing token older than the resource has already seen."""


class ReplicaSet:
    def __init__(self, names, *, mode="sync"):
        if mode not in ("sync", "async"):
            raise ValueError(f"mode must be 'sync' or 'async', not {mode!r}")
        self.names = list(names)
        self.mode = mode
        self.term = 0
        self.epoch = 0
        self.leader = None
        self.logs = {name: [] for name in names}
        self.commit_index = 0
        self.down = set()
        self.blocked = set()  # frozenset({a, b}) pairs with no link between them

    # ------------------------------------------------------------------ setup
    def majority(self):
        return len(self.names) // 2 + 1

    def crash(self, name):
        self.down.add(name)
        return self

    def restart(self, name):
        self.down.discard(name)
        return self

    def partition(self, *groups):
        """Cut every link between different groups; nodes may appear in one group."""
        group_of = {name: i for i, group in enumerate(groups) for name in group}
        self.blocked = set()
        for i, a in enumerate(self.names):
            for b in self.names[i + 1:]:
                if group_of.get(a) != group_of.get(b):
                    self.blocked.add(frozenset((a, b)))
        return self

    def heal(self):
        self.blocked = set()
        return self

    def reachable(self, name):
        if name in self.down:
            return []
        return [other for other in self.names
                if other == name or (other not in self.down
                                     and frozenset((name, other)) not in self.blocked)]

    def can_lead(self, name):
        return name not in self.down and len(self.reachable(name)) >= self.majority()

    # -------------------------------------------------------------- reads/copy
    def read(self, name):
        """Commands a client reading from `name` can see: the committed prefix it holds."""
        visible = min(len(self.logs[name]), self.commit_index)
        return [entry.command for entry in self.logs[name][:visible]]

    def _follow(self, name):
        leader_log = self.logs[self.leader]
        follower_log = self.logs[name]
        prefix = 0
        while (prefix < len(follower_log) and prefix < len(leader_log)
               and follower_log[prefix] == leader_log[prefix]):
            prefix += 1
        if prefix < min(len(follower_log), self.commit_index):
            raise ReplicationError(
                f"{name} holds committed entries the leader does not; refusing to truncate")
        self.logs[name] = list(follower_log[:prefix]) + list(leader_log[prefix:])

    def _catch_up(self):
        if self.leader is None:
            return
        for name in self.reachable(self.leader):
            if name != self.leader:
                self._follow(name)

    def sync(self):
        """Copy the leader's log to every reachable follower (used by async mode)."""
        self._catch_up()
        return self.leader is not None

    def failover(self):
        """Re-elect after the current leader is gone."""
        return self.elect()

    # ------------------------------------------------------- the replication core
    def elect(self):
        # TODO: eligible = names that can_lead; leader = choose_leader(logs, eligible); if a leader was found, bump term and epoch and _catch_up(). Return the leader.
        raise NotImplementedError("ReplicaSet.elect")

    def write(self, command):
        # TODO: Reject if there is no leader or it is down. In sync mode: if fewer than a majority are reachable, return False; append Entry(term, command), _follow each reachable follower, set commit_index = quorum_index(logs, majority) and return whether the new entry committed. In async mode: append and set commit_index to the leader's log length WITHOUT replicating, then return True.
        raise NotImplementedError("ReplicaSet.write")


class FencedStore:
    """A resource that accepts writes only from the newest epoch it has seen."""

    def __init__(self, name="store"):
        self.name = name
        self.seen_epoch = 0
        self.value = None

    def write(self, epoch, value):
        # TODO: Raise StaleEpoch if `epoch` is older than self.seen_epoch; otherwise remember the new epoch, store the value, and return it.
        raise NotImplementedError("FencedStore.write")


if __name__ == "__main__":
    rs = ReplicaSet(["A", "B", "C"], mode="sync")
    rs.elect()
    print(f"elected {rs.leader} (term {rs.term}, epoch {rs.epoch})")
    rs.write("balance=100")
    for name in rs.names:
        print(f"  {name}: {rs.read(name)}  log={[e.command for e in rs.logs[name]]}")

    lag = ReplicaSet(["A", "B", "C"], mode="async")
    lag.elect()
    leader = lag.leader
    lag.write("pay=50")  # acked, not replicated
    follower = next(n for n in lag.names if n != leader)
    print(f"\nasync: leader {leader} reads {lag.read(leader)}, follower {follower} reads "
          f"{lag.read(follower)}")
    lag.crash(leader)
    new = lag.elect()
    print(f"after {leader} dies, {new} leads and reads {lag.read(new)}: "
          f"the acked write is gone (async)")

"""
quorum.py -- a single-leader log replicated with quorum reads and writes.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 5
("Replication"). DDIA presents two families and this file joins them:

* **Single-leader replication.** One node is the leader; it appends every write
  to a log and ships the log to N-1 followers. A follower applies writes in log
  order. The leader decides when a write is *committed* -- durable on enough
  replicas -- and only then acknowledges the client.

* **Quorum reads and writes (leaderless, ch. 5.5 / the Dynamo section).** With N
  replicas, a write must be written to W replicas to be acknowledged and a read
  must ask R replicas; the client keeps the answer with the highest version. The
  central rule is: **if R + W > N, every read quorum overlaps every write
  quorum**, so a read sees the last acknowledged write. If R + W <= N the
  quorums can be disjoint, and a read may return stale data.

Restated in my own words: the guarantee is an intersection count, not a
protocol trick. Count the replicas; if a read set and a write set of size R and W
must share a member, that member's value carries the write forward.

DDIA is explicit about the cost side too: relaxing to W=1 (a "sloppy quorum")
buys availability -- a partitioned coordinator still acknowledges -- and pays
with durability, because the acknowledged write sits on too few replicas to
survive. The two limit cases in this module measure exactly that, and the
opposite (a minority that must *refuse* rather than fork).

DESIGN DECISION -- leader-based commit, or pure client-side quorums?
    Pure Dynamo quorums let any coordinator talk to any replicas; a single-leader
    log funnels every write through one node. Chosen: a designated leader that
    owns the log (the "single-leader log" of the build), with the quorum rule
    used to decide when it may acknowledge, and reads answered from any R
    replicas (so a stale follower can still be read, which is the phenomenon).
    Cost: the leader is an availability bottleneck -- it does not exist to be
    partitioned away.

DESIGN DECISION -- what does a failed write leave behind?
    Keep the leader's uncommitted entry for a later retry (Raft does this), or
    roll every copy back. Chosen: roll back everywhere. The lesson is "a
    minority must not fork the log": if fewer than W replicas hold the write,
    the client is told it failed and no replica keeps a prefix the others never
    saw. Cost: a transiently-partitioned leader loses in-flight work it might
    have committed had it waited; a real system retries or uses a term/epoch.
    Raft's log-with-terms is the general answer; this module stops at the
    refusal.

DESIGN DECISION -- versions from a counter or from the log position?
    A separate logical clock (`version += 1` per write) or the log index itself.
    Chosen: the log index, `version = index`, so a write's identity is its
    position: "the write at index i". This makes the quorum question exactly
    "how many replicas reached index i?" and needs no extra clock.
    Cost: versions are dense and only meaningful within one leader's log; a
    real multi-leader system needs a Lamport/HLC timestamp instead.

DESIGN DECISION -- does a read repair the replicas it touches?
    A pure read returns the newest value and stops; a repairing read writes the
    newest value back to the stale replicas it saw. This module exposes repair
    as an explicit `catch_up()` so the stale window of check 6 is observable
    *before* it closes. Cost: repair is not automatic; the learner must call it,
    which is the point.
"""

import itertools
from typing import Any, Dict, List, Optional

from network import Network
from replica import Replica

__all__ = ["ReplicatedLog", "NotEnoughReplicas", "read_write_overlap"]


class NotEnoughReplicas(Exception):
    """Fewer than W replicas could be made to hold an acknowledged write."""


def read_write_overlap(R: int, W: int, N: int) -> bool:
    """True iff every R-replica read quorum intersects every W-replica write one.

    Two subsets of an N-element set may be disjoint only when |R| + |W| <= N.
    So `R + W > N` is exactly the condition under which a read cannot miss the
    last acknowledged write.
    """
    return R + W > N


class ReplicatedLog:
    """N replicas, one leader, quorum reads and writes over a `Network`."""

    def __init__(self, names, *, seed: int = 0, R: int = 2, W: int = 2,
                 leader: Optional[str] = None, min_delay: int = 1,
                 max_delay: int = 3) -> None:
        self.names: List[str] = list(names)
        self.N = len(self.names)
        if self.N < 1:
            raise ValueError("a cluster needs at least one replica")
        self.R = R
        self.W = W
        self.leader = leader if leader is not None else self.names[0]
        if self.leader not in self.names:
            raise ValueError(f"leader {self.leader!r} is not a replica")
        self.net = Network(seed=seed, min_delay=min_delay, max_delay=max_delay)
        self.replicas: Dict[str, Replica] = {}
        for name in self.names:
            replica = Replica(name)
            self.replicas[name] = replica
            self.net.register(name, replica)

    # -- membership and failures -------------------------------------------

    def partition(self, groups) -> None:
        """Split the cluster: only replicas in the same group can talk."""
        self.net.set_partition(groups)

    def heal(self) -> None:
        self.net.heal()

    def pause(self, name: str) -> None:
        """A slow follower: it stops receiving (and so lags) until resumed."""
        self.replicas[name].paused = True

    def resume(self, name: str) -> None:
        self.replicas[name].paused = False

    def crash(self, name: str) -> None:
        self.replicas[name].crashed = True

    def restart(self, name: str) -> None:
        self.replicas[name].crashed = False

    def _active(self, name: str) -> bool:
        r = self.replicas[name]
        return not (r.paused or r.crashed)

    # -- the quorum rule ----------------------------------------------------

    def holders(self, index: int) -> int:
        """How many replicas currently hold the entry at log position `index`."""
        return sum(1 for r in self.replicas.values() if r.get(index) is not None)

    def commit_index(self) -> int:
        """Highest position present on at least W replicas, scanning the prefix."""
        index = -1
        while self.holders(index + 1) >= self.W:
            index += 1
        return index

    # -- client operations --------------------------------------------------

    def write(self, key: str, value: Any) -> int:
        """Append through the leader and acknowledge only on a W-replica quorum.

        Returns the write's version (= its log index). Raises `NotEnoughReplicas`
        and rolls every copy back when fewer than W replicas can hold it: a
        minority must refuse, not fork the log.
        """
        self.net.flush()
        leader = self.replicas[self.leader]
        index = len(leader.log)
        entry = {"index": index, "key": key, "value": value, "version": index}
        leader.append(entry)
        for name in self.names:
            if name != self.leader and self._active(name):
                self.net.send(self.leader, name, {"kind": "append", "entry": dict(entry)})
        self.net.flush()

        if self.holders(index) >= self.W:
            return index

        for replica in self.replicas.values():
            if replica.get(index) is not None:
                replica.truncate(index)
                self.net.send(self.leader, replica.name, {"kind": "truncate", "index": index})
        self.net.flush()
        raise NotEnoughReplicas(
            f"write at index {index} reached {self.holders(index)} of {self.W} "
            f"required replicas; refused so the log does not fork")

    def read(self, key: str, from_: Optional[List[str]] = None) -> Any:
        """Query R replicas and return the value with the highest version.

        `from_` pins the read quorum, which is what the overlap checks vary; when
        omitted the first R replicas are used. Returns None if no replica holds
        the key.
        """
        self.net.flush()
        nodes = self.names[:self.R] if from_ is None else list(from_)
        best: Optional[tuple] = None
        for name in nodes:
            got = self.replicas[name].value(key)
            if got is not None and (best is None or got[0] > best[0]):
                best = got
        return None if best is None else best[1]

    def catch_up(self) -> int:
        """Replicate the leader's missing suffix to every reachable replica.

        Returns the number of entries sent. A replica behind an unreachable
        partition simply cannot advance; the loop gives up on it rather than
        spinning, which is the honest behaviour of a repair that needs the peer.
        """
        self.net.flush()
        leader = self.replicas[self.leader]
        sent = 0
        for name in self.names:
            if name == self.leader or not self._active(name):
                continue
            replica = self.replicas[name]
            while len(replica.log) < len(leader.log):
                before = len(replica.log)
                entry = dict(leader.log[len(replica.log)])
                self.net.send(self.leader, name, {"kind": "append", "entry": entry})
                sent += 1
                self.net.flush()
                if len(replica.log) == before:
                    break
        return sent

    def status(self) -> Dict[str, dict]:
        """A snapshot for inspection: per-replica log length and paused/crashed."""
        return {name: {"len": len(r.log), "paused": r.paused, "crashed": r.crashed}
                for name, r in self.replicas.items()}


def _demo() -> None:
    """Print the freshness of an overlapping vs a disjoint read quorum."""
    print("R+W>N ?  (read must see the last acknowledged write when True)")
    for R, W, N in [(2, 2, 3), (1, 3, 3), (1, 1, 3), (2, 2, 5), (1, 4, 5)]:
        print(f"  R={R} W={W} N={N}: {read_write_overlap(R, W, N)}")

    fresh = ReplicatedLog(["A", "B", "C"], seed=20261010, R=2, W=2, leader="A")
    fresh.partition([["A", "B"], ["C"]])
    v = fresh.write("x", "hello")
    print(f"R=2 W=2 N=3: write acked at version {v}; "
          f"read from [C,B] -> {fresh.read('x', from_=['C', 'B'])!r} (overlap saves us)")

    stale = ReplicatedLog(["A", "B", "C"], seed=20261010, R=1, W=1, leader="A")
    stale.partition([["A"], ["B", "C"]])
    v = stale.write("x", "hello")
    print(f"R=1 W=1 N=3: write acked at version {v}; "
          f"read from [C] -> {stale.read('x', from_=['C'])!r} (no overlap, stale)")
    stale.heal()
    stale.catch_up()
    print("        after heal + catch_up, read from [C] ->",
          repr(stale.read("x", from_=["C"])))


if __name__ == "__main__":
    _demo()

"""
Cluster — capstone. Raft against a network that misbehaves. Complete Solution.

Everything so far was a mechanism in isolation. This runs them together against
partitions, crashes and message loss, and checks the property that matters
after every single step:

    STATE MACHINE SAFETY: if any server has applied an entry at index i, then
    no other server ever applies a DIFFERENT entry at index i.

That is the guarantee Raft sells. Not "the leader is always right", not "logs
converge eventually" — those are means. This is the promise, and the checker
below asserts it after every operation rather than at the end, because a
violation that heals is still a violation.

DESIGN DECISION — what does a partition actually do to a Raft cluster?
  The minority side cannot elect anyone, so it cannot accept writes. It is
  UNAVAILABLE, and that is the correct behaviour rather than a failure. The
  majority side keeps working.
  This is the exact opposite of ../dynamo-paper/, which accepts writes on both
  sides of a partition and hands the application two conflicting versions to
  merge. Neither is better; they are answers to different questions, and
  section 4 puts the two behaviours side by side.
"""

import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from election import CANDIDATE, FOLLOWER, LEADER, Server, run_election
from log import Entry, Log
from replication import Leader, replicate


class Cluster:
    """A Raft cluster you can partition, crash and drive deterministically."""

    def __init__(self, size: int = 5, seed: int = 0):
        self.names = [f"s{i}" for i in range(size)]
        self.servers: Dict[str, Server] = {
            name: Server(name, [p for p in self.names if p != name],
                         rng=random.Random(seed * 100 + index))
            for index, name in enumerate(self.names)}
        self.leader: Optional[Leader] = None
        self.applied: Dict[str, List[Entry]] = {n: [] for n in self.names}
        self.crashed: Set[str] = set()
        self.partitions: List[Set[str]] = [set(self.names)]
        self.now = 0
        self.rng = random.Random(seed)
        self.history: List[str] = []
        self.stats = {"elections": 0, "failed_elections": 0, "writes": 0,
                      "writes_refused": 0, "safety_checks": 0}

    # -- the network --------------------------------------------------------

    def partition(self, *groups: Sequence[str]) -> None:
        self.partitions = [set(g) for g in groups]
        self.history.append(f"partition {[sorted(g) for g in groups]}")

    def heal(self) -> None:
        self.partitions = [set(self.names)]
        self.history.append("heal")

    def crash(self, name: str) -> None:
        self.crashed.add(name)
        self.history.append(f"crash {name}")

    def restart(self, name: str) -> None:
        """A restart keeps the log, current_term and voted_for.

        Those three are the persistent state, and this method is where you find
        out whether you believed that. Drop voted_for here and a server can
        vote twice in one term, which is the single assumption the whole safety
        argument rests on.
        """
        self.crashed.discard(name)
        server = self.servers[name]
        server.role = FOLLOWER
        server.leader = None
        self.history.append(f"restart {name}")

    def reachable_from(self, name: str) -> Set[str]:
        if name in self.crashed:
            return set()
        for group in self.partitions:
            if name in group:
                return {n for n in group if n not in self.crashed}
        return {name}

    # -- the protocol -------------------------------------------------------

    def elect(self, candidate: str) -> bool:
        """Run one election with only the reachable servers responding."""
        self.now += 1
        self.stats["elections"] += 1
        reachable = self.reachable_from(candidate)
        servers = [self.servers[n] for n in self.names]
        index = self.names.index(candidate)
        won, _ = run_election(servers, index, self.now, reachable)
        if won:
            server = self.servers[candidate]
            self.leader = Leader(candidate,
                                 [n for n in self.names if n != candidate],
                                 server.log, server.current_term)
            self.leader.append_noop()
            self.history.append(f"{candidate} elected in term "
                                f"{server.current_term}")
        else:
            self.stats["failed_elections"] += 1
            self.history.append(f"{candidate} failed to win an election")
        return won

    def write(self, command: Any) -> bool:
        """Append a command and try to commit it. False means unavailable."""
        if self.leader is None or self.leader.name in self.crashed:
            self.stats["writes_refused"] += 1
            return False
        reachable = self.reachable_from(self.leader.name)
        if len(reachable) < self.leader.majority:
            # The leader is in a MINORITY partition. It can append to its own
            # log — and it does — but it can never commit, so the client is
            # never told the write succeeded. The entry sits there until a
            # later leader deletes it.
            self.leader.client_request(command)
            self.stats["writes_refused"] += 1
            self.history.append(f"write {command!r} refused (minority)")
            return False

        self.leader.client_request(command)
        followers = {n: self.servers[n].log for n in self.names
                     if n != self.leader.name}
        replicate(self.leader, followers, reachable)
        committed = self.leader.advance_commit()
        replicate(self.leader, followers, reachable)   # push the commit index
        self.apply_all()
        self.stats["writes"] += 1
        self.history.append(f"write {command!r} committed"
                            if committed else f"write {command!r} pending")
        return bool(committed)

    def apply_all(self) -> None:
        for name, server in self.servers.items():
            log = server.log
            while log.last_applied < log.commit_index:
                log.last_applied += 1
                self.applied[name].append(log.entry_at(log.last_applied))

    # -- the property -------------------------------------------------------

    def check_safety(self) -> Optional[str]:
        """State machine safety, checked across every server.

        Compare what each server has APPLIED, index by index. Two servers
        applying different commands at the same index is the violation Raft
        exists to prevent, and it is checked after every operation because a
        violation that later heals is still a violation — a client was told
        something that turned out to be false.
        """
        self.stats["safety_checks"] += 1
        longest = max((len(v) for v in self.applied.values()), default=0)
        for index in range(longest):
            seen: Dict[Any, str] = {}
            for name, entries in self.applied.items():
                if index >= len(entries):
                    continue             # merely behind is not a violation
                seen.setdefault(entries[index].command, name)
            if len(seen) > 1:
                holders = ", ".join(f"{n} has {c!r}" for c, n in seen.items())
                return (f"index {index + 1}: {holders} — two servers applied "
                        f"DIFFERENT commands at the same index")
        return None

    def report(self) -> str:
        lines = [f"    {'server':<7}{'term':>6}{'role':>11}{'log':>6}"
                 f"{'commit':>8}{'applied':>9}  state"]
        for name in self.names:
            server = self.servers[name]
            role = "CRASHED" if name in self.crashed else server.role
            commands = "".join(str(e.command) for e in self.applied[name]
                               if e.command is not None)
            lines.append(f"    {name:<7}{server.current_term:>6}{role:>11}"
                         f"{len(server.log):>6}{server.log.commit_index:>8}"
                         f"{len(self.applied[name]):>9}  {commands}")
        return "\n".join(lines)


def _demo() -> None:
    print("=" * 78)
    print("CLUSTER — Raft against a network that does not cooperate")
    print("=" * 78)

    print("\n1. The happy path")
    print("-" * 78)
    cluster = Cluster(5, seed=1)
    cluster.elect("s0")
    for command in "abc":
        cluster.write(command)
    print(cluster.report())
    assert cluster.check_safety() is None
    print("  Every server has applied the same three commands in the same")
    print("  order. That is the entire product.")

    print("\n2. A partition: the minority goes unavailable, not wrong")
    print("-" * 78)
    cluster.partition(["s0", "s1"], ["s2", "s3", "s4"])
    print("  s0 (the leader) is now in a MINORITY of 2.")
    accepted = cluster.write("d")
    print(f"  write 'd' -> {'committed' if accepted else 'REFUSED'}")
    print(f"  s0's own log grew to {len(cluster.servers['s0'].log)} entries "
          f"but commit_index is still "
          f"{cluster.servers['s0'].log.commit_index}")
    won = cluster.elect("s2")
    print(f"  s2 campaigns on the majority side: "
          f"{'WON' if won else 'lost'} in term "
          f"{cluster.servers['s2'].current_term}")
    for command in "ef":
        cluster.write(command)
    print(cluster.report())
    violation = cluster.check_safety()
    assert violation is None, violation
    print("  The minority side accepted nothing and told the client so. The")
    print("  majority side elected a new leader and carried on. Raft chooses")
    print("  CONSISTENCY over availability, and 'unavailable' is the correct")
    print("  answer rather than a failure.")

    print("\n3. Healing: the stale leader's uncommitted entries are deleted")
    print("-" * 78)
    stale = list(cluster.servers["s0"].log.entries)
    cluster.heal()
    cluster.servers["s0"].observe_term(cluster.servers["s2"].current_term)
    followers = {n: cluster.servers[n].log for n in cluster.names
                 if n != "s2"}
    replicate(cluster.leader, followers)
    cluster.apply_all()
    print(f"  s0's log during the partition: {stale}")
    print(f"  s0's log after healing:        "
          f"{cluster.servers['s0'].log.entries}")
    print(cluster.report())
    violation = cluster.check_safety()
    assert violation is None, violation
    print("  The entry s0 appended while partitioned is gone. No client was")
    print("  ever told it succeeded, so deleting it breaks no promise — and")
    print("  that is exactly why the leader refused to commit it.")

    print("\n4. Raft against Dynamo, on the same partition")
    print("-" * 78)
    print(f"    {'':<22}{'Raft':<34}{'Dynamo'}")
    rows = [
        ("minority write", "refused — client told no",
         "accepted, into a sloppy quorum"),
        ("majority write", "committed", "accepted"),
        ("after healing", "minority's writes deleted",
         "both versions survive as siblings"),
        ("conflicts", "impossible by construction",
         "the application merges them"),
        ("the promise", "one order, everywhere", "eventual convergence"),
    ]
    for label, raft, dynamo in rows:
        print(f"    {label:<22}{raft:<34}{dynamo}")
    print("  Neither is better. Raft answers 'what is the agreed sequence of")
    print("  events', Dynamo answers 'stay writable no matter what'. A shopping")
    print("  cart wants the second; a bank ledger wants the first. Note that")
    print("  ../dynamo-paper/ says its gossip layer 'needs consensus, which is")
    print("  the availability cost the paper refuses' — this is the thing it")
    print("  was refusing.")

    print("\n5. Randomised chaos, with safety checked after every step")
    print("-" * 78)
    print(f"    {'run':>5}{'ops':>7}{'elections':>11}{'failed':>8}"
          f"{'committed':>11}{'refused':>9}  safety")
    total_ops = 0
    for run in range(8):
        cluster = Cluster(5, seed=run)
        cluster.elect("s0")
        rng = random.Random(run)
        violation = None
        operations = 0
        for step in range(40):
            operations += 1
            action = rng.random()
            if action < 0.55:
                cluster.write(f"{run}-{step}")
            elif action < 0.7:
                group = rng.sample(cluster.names, rng.choice([2, 3]))
                cluster.partition(group,
                                  [n for n in cluster.names if n not in group])
            elif action < 0.8:
                cluster.heal()
            elif action < 0.9:
                cluster.elect(rng.choice(cluster.names))
            else:
                victim = rng.choice(cluster.names)
                if victim in cluster.crashed:
                    cluster.restart(victim)
                else:
                    cluster.crash(victim)
            violation = cluster.check_safety()
            if violation:
                break
        total_ops += operations
        print(f"    {run:>5}{operations:>7}{cluster.stats['elections']:>11}"
              f"{cluster.stats['failed_elections']:>8}"
              f"{cluster.stats['writes']:>11}"
              f"{cluster.stats['writes_refused']:>9}  "
              f"{'VIOLATION: ' + violation if violation else 'holds'}")
    print(f"  {total_ops} operations across 8 runs — partitions, crashes,")
    print("  restarts and elections in random order — with state machine")
    print("  safety asserted after every single one.")
    print("  Note the 'refused' column. Raft spends a great deal of its time")
    print("  saying no, and that is the product working: every refusal is a")
    print("  client correctly told that its write did not happen, rather than")
    print("  a write that will quietly disappear later.")

    print("\n" + "=" * 78)
    print("The one property, once more: if any server has applied an entry at")
    print("index i, no other server ever applies a different entry at index i.")
    print("Everything else in Raft is machinery for keeping that true.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()

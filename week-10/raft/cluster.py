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

Learning Path:
1. reachable_from, partition, heal, crash, restart
2. elect and write, wired to election.py and replication.py
3. check_safety — the property, checked after EVERY operation
4. The randomised chaos loop
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
        raise NotImplementedError

    # -- the protocol -------------------------------------------------------

    def elect(self, candidate: str) -> bool:
        """Run one election with only the reachable servers responding."""
        raise NotImplementedError

    def write(self, command: Any) -> bool:
        """Append a command and try to commit it. False means unavailable."""
        raise NotImplementedError

    def apply_all(self) -> None:
        raise NotImplementedError

    # -- the property -------------------------------------------------------

    def check_safety(self) -> Optional[str]:
        """State machine safety, checked across every server.

        Compare what each server has APPLIED, index by index. Two servers
        applying different commands at the same index is the violation Raft
        exists to prevent, and it is checked after every operation because a
        violation that later heals is still a violation — a client was told
        something that turned out to be false.
        """
        raise NotImplementedError

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
    """Once the checks pass, write a demo that PRINTS these five things:

    1. The happy path: every server applying the same commands in the same
       order.
    2. A partition where the leader ends up in the MINORITY. Its own log grows
       and its commit index does not; the client is told no. The majority side
       elects someone and carries on.
    3. Healing, where the stale leader's uncommitted entries are deleted. No
       client was told they succeeded, so nothing is broken.
    4. A side-by-side table of Raft against ../dynamo-paper/ on the same
       partition. Neither is better; they answer different questions.
    5. Randomised chaos — partitions, crashes, restarts and elections in random
       order — with state machine safety asserted after every single
       operation. A violation that later heals is still a violation.
       Report the REFUSED count too: Raft spends much of its time saying no,
       and every refusal is a client correctly told its write did not happen.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

"""
Gossip Membership & Failure Detection — Complete Solution

Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007),
sections 4.8 and 4.8.2 (ring membership, failure detection, seeds).
"""

import random
from typing import Dict, List, Optional, Set, Tuple

ALIVE = "alive"
SUSPECT = "suspect"
DEAD = "dead"


class MemberState:
    """This node's belief about one peer."""

    __slots__ = ("name", "heartbeat", "last_seen", "status", "tokens")

    def __init__(self, name: str, heartbeat: int = 0, last_seen: int = 0,
                 status: str = ALIVE, tokens: Optional[List[int]] = None):
        self.name = name
        self.heartbeat = heartbeat        # monotonic counter owned by that peer
        self.last_seen = last_seen        # local round when heartbeat last rose
        self.status = status
        self.tokens = tokens or []

    def __repr__(self) -> str:
        return f"{self.name}({self.status},hb={self.heartbeat})"


class GossipNode:
    """A node running Dynamo's anti-entropy gossip protocol.

    Every node keeps a full membership table.  Once per round it bumps its own
    heartbeat and pushes its table to a random peer, which merges by taking the
    higher heartbeat per member.  Because knowledge spreads exponentially, a
    change reaches all S nodes in O(log S) rounds without any coordinator.

    Failure detection here is purely local and *not* shared: a node marks a peer
    dead only for itself, based on how long that peer's heartbeat has been flat.
    The paper is explicit that Dynamo has no global failure view — that would
    require agreement, which is exactly what it is trying to avoid.
    """

    def __init__(self, name: str, tokens: Optional[List[int]] = None,
                 suspect_after: int = 3, dead_after: int = 6,
                 rng: Optional[random.Random] = None):
        self.name = name
        self.alive = True
        self.round = 0
        self.suspect_after = suspect_after
        self.dead_after = dead_after
        self.rng = rng or random.Random(0)
        self.members: Dict[str, MemberState] = {
            name: MemberState(name, heartbeat=0, last_seen=0, tokens=tokens or [])
        }
        self.stats = {"messages_sent": 0, "messages_received": 0, "merges": 0}

    # -- membership ---------------------------------------------------------

    def seed(self, peers: List["GossipNode"]) -> None:
        """Introduce statically-configured seed nodes.

        Seeds are how Dynamo avoids a logically partitioned ring: without them,
        two nodes that only ever hear about each other can form a second,
        invisible cluster.
        """
        for peer in peers:
            if peer.name != self.name and peer.name not in self.members:
                self.members[peer.name] = MemberState(
                    peer.name, heartbeat=0, last_seen=self.round,
                    tokens=peer.members[peer.name].tokens)

    def live_members(self) -> List[str]:
        return sorted(n for n, m in self.members.items() if m.status == ALIVE)

    def view(self) -> Dict[str, str]:
        return {n: m.status for n, m in sorted(self.members.items())}

    # -- one protocol round -------------------------------------------------

    def tick(self) -> None:
        """Advance local time: bump own heartbeat, age out silent peers."""
        if not self.alive:
            return
        self.round += 1
        me = self.members[self.name]
        me.heartbeat += 1
        me.last_seen = self.round
        me.status = ALIVE

        for name, member in self.members.items():
            if name == self.name:
                continue
            silence = self.round - member.last_seen
            if silence >= self.dead_after:
                member.status = DEAD
            elif silence >= self.suspect_after:
                member.status = SUSPECT

    def gossip_to(self, peer: "GossipNode") -> bool:
        """Push our table to one peer. Returns False if the peer is unreachable."""
        if not self.alive:
            return False
        self.stats["messages_sent"] += 1
        if not peer.alive:
            return False
        peer.receive(self.digest(), from_node=self.name)
        return True

    def digest(self) -> Dict[str, Tuple[int, List[int]]]:
        """What travels on the wire: name -> (heartbeat, tokens)."""
        return {n: (m.heartbeat, m.tokens) for n, m in self.members.items()}

    def receive(self, digest: Dict[str, Tuple[int, List[int]]], from_node: str) -> None:
        """Merge a peer's table into ours, keeping the higher heartbeat.

        Heartbeats only ever increase and are only ever incremented by their
        owner, so "higher wins" is a conflict-free merge — no clock sync needed.
        """
        if not self.alive:
            return
        self.stats["messages_received"] += 1
        for name, (heartbeat, tokens) in digest.items():
            if name == self.name:
                continue
            existing = self.members.get(name)
            if existing is None:
                self.members[name] = MemberState(name, heartbeat, self.round,
                                                 ALIVE, list(tokens))
                self.stats["merges"] += 1
            elif heartbeat > existing.heartbeat:
                existing.heartbeat = heartbeat
                existing.last_seen = self.round
                existing.status = ALIVE
                existing.tokens = list(tokens)
                self.stats["merges"] += 1

    def random_peer(self, cluster: Dict[str, "GossipNode"]) -> Optional["GossipNode"]:
        candidates = [n for n in self.members if n != self.name and n in cluster]
        if not candidates:
            return None
        return cluster[self.rng.choice(candidates)]


class GossipCluster:
    def __init__(self, names: List[str], fanout: int = 1, seed: int = 7,
                 suspect_after: int = 3, dead_after: int = 6):
        self.rng = random.Random(seed)
        self.fanout = fanout
        self.nodes: Dict[str, GossipNode] = {
            name: GossipNode(name, suspect_after=suspect_after, dead_after=dead_after,
                             rng=random.Random(seed + i))
            for i, name in enumerate(names)
        }
        self.round = 0

    def seed_all(self, seeds: Optional[List[str]] = None) -> None:
        seed_nodes = [self.nodes[n] for n in (seeds or list(self.nodes)[:2])]
        for node in self.nodes.values():
            node.seed(seed_nodes)

    def step(self) -> None:
        self.round += 1
        for node in self.nodes.values():
            node.tick()
        for node in list(self.nodes.values()):
            if not node.alive:
                continue
            for _ in range(self.fanout):
                peer = node.random_peer(self.nodes)
                if peer is not None:
                    node.gossip_to(peer)

    def converged(self) -> bool:
        """True when every live node knows every live node."""
        live = {n for n, node in self.nodes.items() if node.alive}
        return all(live <= set(self.nodes[n].members) for n in live)

    def rounds_until_converged(self, limit: int = 50) -> int:
        for i in range(1, limit + 1):
            self.step()
            if self.converged():
                return i
        return -1

    def total_messages(self) -> int:
        return sum(n.stats["messages_sent"] for n in self.nodes.values())


def _demo() -> None:
    print("=== Convergence: how fast does a new node become known? ===")
    for size in (8, 32, 128):
        cluster = GossipCluster([f"node{i}" for i in range(size)], fanout=1, seed=3)
        cluster.seed_all(seeds=["node0", "node1"])
        rounds = cluster.rounds_until_converged()
        print(f"  {size:3d} nodes -> converged in {rounds:2d} rounds "
              f"({cluster.total_messages()} messages total). log2(S) = "
              f"{(size - 1).bit_length()}")

    print("\n=== A node joins an established cluster ===")
    cluster = GossipCluster([f"node{i}" for i in range(16)], fanout=1, seed=5)
    cluster.seed_all(seeds=["node0", "node1"])
    cluster.rounds_until_converged()

    newcomer = GossipNode("node99", rng=random.Random(99))
    newcomer.seed([cluster.nodes["node0"]])          # knows only a seed
    cluster.nodes["node99"] = newcomer
    print(f"node99 starts knowing: {sorted(newcomer.members)}")

    for i in range(1, 12):
        cluster.step()
        aware = sum(1 for n in cluster.nodes.values() if "node99" in n.members)
        if i <= 6 or aware == len(cluster.nodes):
            print(f"  round {i:2d}: {aware:2d}/{len(cluster.nodes)} nodes know about node99")
        if aware == len(cluster.nodes):
            break

    print("\n=== Failure detection is local, not global ===")
    cluster = GossipCluster([f"node{i}" for i in range(6)], fanout=1, seed=11,
                            suspect_after=3, dead_after=6)
    cluster.seed_all(seeds=["node0", "node1"])
    cluster.rounds_until_converged()

    cluster.nodes["node4"].alive = False
    print("node4 crashed")
    for i in range(1, 10):
        cluster.step()
        beliefs: Dict[str, int] = {}
        for node in cluster.nodes.values():
            if not node.alive:
                continue
            beliefs[node.members["node4"].status] = \
                beliefs.get(node.members["node4"].status, 0) + 1
        print(f"  round {i}: peers believe node4 is {beliefs}")
        if all(k == DEAD for k in beliefs):
            break
    print("Different nodes reach different conclusions at different times.")
    print("Dynamo never votes on this — each node just stops routing to a peer")
    print("it cannot reach, and retries later.")

    print("\n=== Why seeds matter ===")
    split = GossipCluster([f"a{i}" for i in range(4)] + [f"b{i}" for i in range(4)],
                          fanout=1, seed=17)
    for name in ("a0", "a1", "a2", "a3"):             # two islands, no shared seed
        split.nodes[name].seed([split.nodes[n] for n in ("a0", "a1")])
    for name in ("b0", "b1", "b2", "b3"):
        split.nodes[name].seed([split.nodes[n] for n in ("b0", "b1")])
    for _ in range(20):
        split.step()
    print(f"a0 knows: {sorted(split.nodes['a0'].members)}")
    print(f"b0 knows: {sorted(split.nodes['b0'].members)}")
    print("Two logical rings that never meet. A shared seed list prevents this.")


if __name__ == "__main__":
    _demo()

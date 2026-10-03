"""
Gossip Membership & Failure Detection — From Scratch
=====================================================
Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007),
       sections 4.8, 4.8.1 (ring membership) and 4.8.2 (failure detection).

Build the membership layer to understand:
- Why heartbeat counters merge without any clock synchronisation
- Why gossip converges in O(log S) rounds
- Why Dynamo deliberately has no global failure detector
- What seed nodes prevent, and how ugly it gets without them

Learning Path:
1. Implement GossipNode.tick — bump own heartbeat, age out silent peers
2. Implement digest / receive — the merge rule is "higher heartbeat wins"
3. Implement the cluster stepping loop and measure convergence
4. Crash a node and watch peers disagree about it for several rounds
5. Build two islands with disjoint seeds and see the ring split

Background:
  Every node holds a full membership table: peer -> (heartbeat, tokens). Once
  per round a node increments its OWN heartbeat and pushes its whole table to
  a random peer. The receiver merges entry by entry, keeping the higher
  heartbeat.

  That merge is conflict-free. A heartbeat only ever increases, and only its
  owner increments it, so "higher wins" needs no coordination, no timestamps,
  and no agreement on time. This is the same insight as the vector clock, in
  a simpler setting.

  Failure detection is purely local. A node marks a peer dead when that peer's
  heartbeat has been flat for too long *in its own view*, and it never gossips
  that opinion as fact. Two nodes will disagree about who is down, and Dynamo
  is fine with that: a node that thinks a peer is dead simply routes around it
  and retries later. A globally agreed membership view would require consensus,
  which is exactly the availability cost the paper refuses to pay.

  Seeds are statically configured nodes every member knows about. Without them
  two groups that only ever gossip internally form separate logical rings that
  never discover each other — and both keep serving.
"""

import random
from typing import Dict, List, Optional, Set, Tuple

ALIVE = "alive"
SUSPECT = "suspect"
DEAD = "dead"


class MemberState:
    """One node's belief about one peer."""

    __slots__ = ("name", "heartbeat", "last_seen", "status", "tokens")

    def __init__(self, name: str, heartbeat: int = 0, last_seen: int = 0,
                 status: str = ALIVE, tokens: Optional[List[int]] = None):
        self.name = name
        self.heartbeat = heartbeat      # counter owned by that peer
        self.last_seen = last_seen      # local round when the heartbeat last rose
        self.status = status
        self.tokens = tokens or []

    def __repr__(self) -> str:
        return f"{self.name}({self.status},hb={self.heartbeat})"


# ---------------------------------------------------------------------------
# Step 1-2: A gossiping node
# ---------------------------------------------------------------------------

class GossipNode:
    """A node running anti-entropy gossip over its membership table."""

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

    def seed(self, peers: List["GossipNode"]) -> None:
        """TODO: add each peer (other than self) to members with heartbeat 0."""
        raise NotImplementedError

    def live_members(self) -> List[str]:
        return sorted(n for n, m in self.members.items() if m.status == ALIVE)

    def tick(self) -> None:
        """Advance local time.

        TODO:
        1. Do nothing if this node is down.
        2. round += 1; bump own heartbeat, set own last_seen = round, ALIVE.
        3. For every other member, compute silence = round - last_seen and set
           DEAD if silence >= dead_after, SUSPECT if >= suspect_after.

        The SUSPECT state exists so a brief network hiccup does not immediately
        evict a healthy node — evicting one costs a rebalance.
        """
        raise NotImplementedError

    def digest(self) -> Dict[str, Tuple[int, List[int]]]:
        """TODO: what goes on the wire — name -> (heartbeat, tokens)."""
        raise NotImplementedError

    def receive(self, digest: Dict[str, Tuple[int, List[int]]],
                from_node: str) -> None:
        """Merge a peer's table into ours.

        TODO: for each (name, (heartbeat, tokens)) that is not ourselves:
          - unknown peer      -> insert it, ALIVE, last_seen = round
          - higher heartbeat  -> update heartbeat/tokens, last_seen = round,
                                 and mark ALIVE (this is how a node "recovers"
                                 in a peer's view)
          - otherwise         -> ignore, our information is newer

        Never accept another node's opinion about YOUR heartbeat. It is yours;
        theirs is by definition stale.
        """
        raise NotImplementedError

    def gossip_to(self, peer: "GossipNode") -> bool:
        """TODO: send digest() to peer if both are alive; return whether it
        landed. Count messages_sent even when the peer is unreachable — that is
        what a real timeout costs you."""
        raise NotImplementedError

    def random_peer(self, cluster: Dict[str, "GossipNode"]) -> Optional["GossipNode"]:
        """TODO: pick a random known peer (excluding self) via self.rng."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 3-5: The simulation
# ---------------------------------------------------------------------------

class GossipCluster:
    def __init__(self, names: List[str], fanout: int = 1, seed: int = 7,
                 suspect_after: int = 3, dead_after: int = 6):
        self.rng = random.Random(seed)
        self.fanout = fanout
        self.nodes: Dict[str, GossipNode] = {
            name: GossipNode(name, suspect_after=suspect_after,
                             dead_after=dead_after, rng=random.Random(seed + i))
            for i, name in enumerate(names)
        }
        self.round = 0

    def seed_all(self, seeds: Optional[List[str]] = None) -> None:
        """TODO: introduce the seed nodes (default: the first two) to everyone."""
        raise NotImplementedError

    def step(self) -> None:
        """One round: every live node ticks, then gossips to `fanout` peers.

        TODO: tick all nodes first, then gossip — otherwise a node can forward
        information it has not yet aged, and your convergence numbers lie.
        """
        raise NotImplementedError

    def converged(self) -> bool:
        """TODO: True when every live node's member table covers every live node."""
        raise NotImplementedError

    def rounds_until_converged(self, limit: int = 50) -> int:
        """TODO: step() until converged(), returning the round count (-1 if the
        limit is hit)."""
        raise NotImplementedError

    def total_messages(self) -> int:
        return sum(n.stats["messages_sent"] for n in self.nodes.values())


def _demo() -> None:
    """Once implemented, run these four experiments:

    1. Convergence at 8, 32 and 128 nodes. Rounds should grow roughly like
       log2(S), not like S. If it grows linearly, your merge is only accepting
       information about the direct sender.
    2. Add a node that knows only one seed. Count how many nodes know about it
       each round — the curve should roughly double each round early on.
    3. Crash a node and print what each peer believes per round. You should see
       a stretch where some say alive, some suspect, some dead. That
       disagreement is the design, not a bug.
    4. Build two groups with disjoint seed lists and step 20 rounds. Neither
       group ever learns about the other. This is why the seed list is static
       configuration rather than something discovered.
    """
    cluster = GossipCluster([f"node{i}" for i in range(32)])
    cluster.seed_all()
    print("converged in", cluster.rounds_until_converged(), "rounds")


if __name__ == "__main__":
    _demo()

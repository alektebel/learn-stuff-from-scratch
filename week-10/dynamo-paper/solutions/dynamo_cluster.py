"""
Dynamo, Assembled — Complete Solution

Wires together every mechanism from the paper into one cluster:

    partitioning.py   consistent hashing + preference lists   (section 4.2)
    vector_clock.py   versioning and reconciliation           (section 4.4)
    quorum.py         N / R / W                               (section 4.5)
    hinted_handoff.py sloppy quorum + handoff                 (section 4.6)
    merkle_sync.py    anti-entropy                            (section 4.7)
    gossip.py         membership + failure detection          (section 4.8)

The demo reproduces the paper's headline claim: the store stays writeable
through node failures, and consistency is restored afterwards by background
repair rather than by blocking the write path.
"""

import random
from typing import Any, Callable, Dict, List, Optional, Tuple

from gossip import GossipCluster
from hinted_handoff import HintedNode, SloppyCoordinator
from merkle_sync import AntiEntropy
from partitioning import ConsistentHashRing
from quorum import QuorumNotMet
from vector_clock import merge_carts


class DynamoCluster:
    """A whole Dynamo instance: ring, nodes, coordinator and background jobs."""

    def __init__(self, num_nodes: int = 6, n: int = 3, r: int = 2, w: int = 2,
                 tokens_per_node: int = 64, merkle_depth: int = 6):
        self.ring = ConsistentHashRing(tokens_per_node=tokens_per_node)
        self.nodes: Dict[str, HintedNode] = {}
        for i in range(num_nodes):
            name = f"node{i}"
            self.ring.add_node(name)
            self.nodes[name] = HintedNode(name)
        self.coordinator = SloppyCoordinator(self.ring, self.nodes, n=n, r=r, w=w)
        self.anti_entropy = AntiEntropy(depth=merkle_depth)
        self.membership = GossipCluster([f"node{i}" for i in range(num_nodes)])
        self.membership.seed_all()
        self.membership.rounds_until_converged()

    # -- client API ---------------------------------------------------------

    def put(self, key: str, value: Any, context: Optional[Dict[str, int]] = None):
        return self.coordinator.put(key, value, context=context)

    def get(self, key: str):
        return self.coordinator.get(key)

    def get_and_reconcile(self, key: str, merge_fn: Callable[[List[Any]], Any]):
        result = self.coordinator.get(key)
        if not result.versions:
            return None
        if not result.has_conflict:
            return result.value
        merged = merge_fn(result.values)
        self.coordinator.put(key, merged, context=result.context)
        return merged

    # -- operations ---------------------------------------------------------

    def kill(self, name: str) -> None:
        self.nodes[name].kill()
        self.membership.nodes[name].alive = False

    def revive(self, name: str) -> None:
        self.nodes[name].revive()
        self.membership.nodes[name].alive = True

    def run_background_jobs(self, gossip_rounds: int = 3) -> Dict[str, int]:
        """One maintenance cycle: gossip, hint delivery, then anti-entropy."""
        for _ in range(gossip_rounds):
            self.membership.step()
        delivered = self.coordinator.run_hint_delivery()
        repaired = self._anti_entropy_sweep()
        return {"hints_delivered": delivered, "keys_repaired": repaired}

    def _anti_entropy_sweep(self) -> int:
        """Sync every pair of nodes that share a preference list.

        Real Dynamo only compares the key ranges two nodes have in common, using
        one Merkle tree per range.  Here we sync full stores pairwise, which is
        the same idea at a smaller scale.
        """
        repaired = 0
        live = [name for name, node in self.nodes.items() if node.alive]
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                if not self._share_a_key_range(a, b):
                    continue
                repaired += len(self.anti_entropy.synchronize(
                    self.nodes[a].data, self.nodes[b].data))
        return repaired

    def _share_a_key_range(self, a: str, b: str) -> bool:
        keys = set(self.nodes[a].data) | set(self.nodes[b].data)
        return any({a, b} <= set(self.ring.preference_list(k, self.coordinator.n))
                   for k in keys)

    # -- inspection ---------------------------------------------------------

    def replica_divergence(self, key: str) -> Dict[str, List[Any]]:
        return {name: [v.value for v in self.nodes[name].local_get(key)]
                for name in self.ring.preference_list(key, self.coordinator.n)
                if self.nodes[name].alive}

    def durable_copies(self, key: str) -> int:
        return sum(1 for node in self.nodes.values()
                   if node.alive and node.data.get(key))

    def report(self) -> str:
        stats = self.coordinator.stats
        return (f"puts={stats['puts']} gets={stats['gets']} "
                f"sloppy={stats['sloppy_writes']} "
                f"read_repairs={stats['read_repairs']} "
                f"put_failures={stats['put_failures']} "
                f"get_failures={stats['get_failures']} "
                f"anti_entropy_keys={self.anti_entropy.stats['keys_transferred']}")


# ---------------------------------------------------------------------------
# Availability experiment
# ---------------------------------------------------------------------------

def availability_under_churn(n: int, r: int, w: int, num_nodes: int = 8,
                             operations: int = 400, failure_rate: float = 0.3,
                             sloppy: bool = True, seed: int = 42
                             ) -> Dict[str, float]:
    """Measure write/read success while a fraction of nodes is down.

    Flip `sloppy` off to see what a strict quorum would have done with exactly
    the same failures — that difference is the entire argument of section 4.6.
    """
    rng = random.Random(seed)
    cluster = DynamoCluster(num_nodes=num_nodes, n=n, r=r, w=w)
    if not sloppy:
        # Restrict the fallback list to the home replicas only.
        cluster.coordinator._extended_preference = (          # type: ignore[method-assign]
            lambda key: cluster.ring.preference_list(key, n))

    down: set = set()
    writes = write_failures = reads = read_failures = 0
    for i in range(operations):
        for name in list(down):                                # recover
            if rng.random() < 0.2:
                cluster.revive(name)
                down.discard(name)
        for name in cluster.nodes:                             # fail
            if name not in down and rng.random() < failure_rate / num_nodes:
                cluster.kill(name)
                down.add(name)

        key = f"key:{rng.randrange(50)}"
        writes += 1
        try:
            cluster.put(key, {"v": i})
        except QuorumNotMet:
            write_failures += 1
        reads += 1
        try:
            cluster.get(key)
        except QuorumNotMet:
            read_failures += 1

    return {
        "write_success": 1 - write_failures / max(writes, 1),
        "read_success": 1 - read_failures / max(reads, 1),
        "sloppy_writes": cluster.coordinator.stats["sloppy_writes"],
    }


def _demo() -> None:
    print("=" * 68)
    print("A shopping cart that survives a partial outage")
    print("=" * 68)
    cluster = DynamoCluster(num_nodes=6, n=3, r=2, w=2)
    key = "cart:user-42"
    home = cluster.ring.preference_list(key, 3)
    print(f"N=3 R=2 W=2 over 6 nodes; replicas for {key}: {home}")

    cluster.put(key, {"dynamo-paper": 1})
    first = cluster.get(key)
    print(f"\nt0  put   -> {first.value}")

    cluster.kill(home[0])
    cluster.kill(home[1])
    print(f"t1  {home[0]} and {home[1]} crash")
    try:
        cluster.get(key)
    except QuorumNotMet as exc:
        print(f"    read  -> failed: {exc}")
        print("    reads need R=2 healthy owners; writes do not stop for that")

    cluster.put(key, {"dynamo-paper": 1, "sosp-proceedings": 1}, context=first.context)
    print(f"t2  put   -> succeeded anyway "
          f"(sloppy writes: {cluster.coordinator.stats['sloppy_writes']})")
    print(f"    hints parked on: {list(cluster.coordinator.pending_hints())}")

    print("\nt3  two clients read the same version and both update it")
    shared = cluster.get(key).context
    preference = cluster.coordinator._extended_preference(key)
    live = [n for n in preference if cluster.nodes[n].alive]
    cluster.coordinator.put(key, {"dynamo-paper": 1, "sosp-proceedings": 1, "mug": 1},
                            context=shared, coordinating_node=live[0])
    cluster.coordinator.put(key, {"dynamo-paper": 1, "sosp-proceedings": 1, "poster": 1},
                            context=shared, coordinating_node=live[1])
    result = cluster.get(key)
    print(f"    read  -> {len(result.versions)} siblings: {result.values}")

    print("\nt4  nodes recover, background jobs run")
    cluster.revive(home[0])
    cluster.revive(home[1])
    jobs = cluster.run_background_jobs()
    print(f"    {jobs}")
    print(f"    replica state now: {cluster.replica_divergence(key)}")

    merged = cluster.get_and_reconcile(key, merge_carts)
    print(f"\nt5  application merges the siblings -> {merged}")
    print(f"    re-read -> {cluster.get(key).value}")
    print(f"    nothing added to the cart was lost: "
          f"{set(merged) == {'dynamo-paper', 'sosp-proceedings', 'mug', 'poster'}}")
    print(f"\n{cluster.report()}")

    print("\n" + "=" * 68)
    print("Availability: sloppy vs strict quorum under the same 30% churn")
    print("=" * 68)
    print(f"{'config':<26}{'sloppy W':>10}{'write ok':>10}{'read ok':>10}")
    for label, (n, r, w) in [("N=3 R=2 W=2 (balanced)", (3, 2, 2)),
                             ("N=3 R=3 W=1 (fast write)", (3, 3, 1)),
                             ("N=3 R=1 W=3 (fast read)", (3, 1, 3))]:
        for sloppy in (True, False):
            res = availability_under_churn(n, r, w, sloppy=sloppy)
            tag = label if sloppy else " " * len(label.split(" ")[0]) + "  strict"
            print(f"{tag:<26}{res['sloppy_writes']:>10}"
                  f"{res['write_success']:>9.1%}{res['read_success']:>10.1%}")

    print("\nR+W>N gives you overlap, but it is W that decides whether writes")
    print("survive an outage — which is why Amazon ran the always-writeable")
    print("cart service with W=1 and pushed reconciliation to read time.")


if __name__ == "__main__":
    _demo()

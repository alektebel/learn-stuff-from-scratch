"""
Progress checker for the Dynamo templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 5 6     # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Each check exercises the functions you implement in the template files. A check
that raises NotImplementedError is reported as TODO (not a failure) — that is
simply the next thing to write.

Nothing here imports solutions/. It tests YOUR code.
"""

import pathlib
import shutil
import sys
import traceback

# Always read the learner's source fresh. Python validates cached bytecode on
# (mtime, size), so an edit that keeps a file the same size within the same
# second can be masked by a stale __pycache__ — and a checker you cannot trust
# is worse than no checker.
sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"

GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Step 1-2: partitioning.py
# ---------------------------------------------------------------------------

def check_ring_basics() -> None:
    from partitioning import ConsistentHashRing

    ring = ConsistentHashRing(tokens_per_node=32)
    for i in range(4):
        ring.add_node(f"node{i}")

    assert ring.nodes == ["node0", "node1", "node2", "node3"], \
        f"nodes property returned {ring.nodes}"
    assert len(ring._positions) == 4 * 32, \
        f"expected {4 * 32} token positions, got {len(ring._positions)}"
    assert ring._positions == sorted(ring._positions), \
        "_positions must stay sorted — use bisect.insort, not append"

    owner = ring.coordinator("some-key")
    assert owner in ring.nodes, f"coordinator returned {owner!r}, not a live node"

    # The same key must always land on the same node.
    assert all(ring.coordinator("some-key") == owner for _ in range(5)), \
        "coordinator is not deterministic"

    ring.remove_node("node0")
    assert "node0" not in ring.nodes, "remove_node left the node in _nodes"
    assert len(ring._positions) == 3 * 32, "remove_node left orphaned positions"
    assert all(ring.coordinator(f"k{i}") != "node0" for i in range(50)), \
        "a removed node is still being returned as a coordinator"


def check_preference_list() -> None:
    from partitioning import ConsistentHashRing

    ring = ConsistentHashRing(tokens_per_node=32)
    for i in range(6):
        ring.add_node(f"node{i}", datacenter=f"dc{i % 3}")

    for key in [f"key:{i}" for i in range(200)]:
        pref = ring.preference_list(key, 3)
        assert len(pref) == 3, f"preference_list({key!r}, 3) returned {len(pref)} nodes"
        assert len(set(pref)) == 3, (
            f"preference_list returned a DUPLICATE node: {pref}. "
            "You are walking virtual tokens without skipping nodes already chosen — "
            "this is the bug that silently stores 1 copy where you asked for 3.")

    # The first entry of the preference list is the coordinator.
    assert ring.preference_list("key:7", 3)[0] == ring.coordinator("key:7"), \
        "preference_list[0] must equal coordinator()"

    # Asking for more replicas than there are machines must clamp, not hang.
    assert len(ring.preference_list("key:7", 99)) == 6, \
        "preference_list must clamp n to the number of physical nodes"

    dc_aware = ring.preference_list("key:7", 3, distinct_dc=True)
    dcs = [ring._nodes[n] for n in dc_aware]
    assert len(set(dcs)) == 3, (
        f"distinct_dc=True gave datacenters {dcs}; with 3 DCs available all "
        "three replicas should land in different ones")

    single = ConsistentHashRing(tokens_per_node=16)
    for i in range(4):
        single.add_node(f"n{i}", datacenter="dc0")
    assert len(single.preference_list("k", 3, distinct_dc=True)) == 3, (
        "distinct_dc must fall back gracefully when every node shares a "
        "datacenter — otherwise you loop forever or return too few replicas")


def check_balance_and_migration() -> None:
    from partitioning import ConsistentHashRing, keys_moved

    ring = ConsistentHashRing(tokens_per_node=64)
    for i in range(4):
        ring.add_node(f"node{i}")

    dist = ring.load_distribution(10_000)
    assert sum(dist.values()) == 10_000, \
        f"load_distribution should account for every key, got {sum(dist.values())}"
    imbalance = ring.imbalance(10_000)
    assert 1.0 <= imbalance < 1.6, (
        f"imbalance is {imbalance:.2f}; expected roughly 1.1-1.3 at 64 tokens/node. "
        "Far above 1.6 usually means too few virtual tokens are being created.")

    import copy
    before = copy.deepcopy(ring)
    ring.add_node("node4")
    moved, fraction = keys_moved(before, ring, 10_000)
    assert 0.10 < fraction < 0.32, (
        f"{fraction:.1%} of keys moved when adding the 5th node; consistent "
        "hashing should move roughly 1/5 = 20%. A number near 80-100% means "
        "you are hashing modulo the node count somewhere.")


def check_partitioned_ring() -> None:
    from partitioning import PartitionedRing

    ring = PartitionedRing(num_partitions=1024)
    for i in range(4):
        ring.add_node(f"node{i}")

    counts = ring.partitions_per_node()
    assert sum(counts.values()) == 1024, "every partition must be assigned"
    assert max(counts.values()) - min(counts.values()) <= 1, (
        f"partitions per node {counts} are uneven; strategy 3 gives each node "
        "exactly Q/S partitions (+/- 1)")

    pref = ring.preference_list("cart:user-42", 3)
    assert len(pref) == len(set(pref)) == 3, f"preference_list returned {pref}"

    ring.add_node("node4")
    counts = ring.partitions_per_node()
    assert len(counts) == 5 and max(counts.values()) - min(counts.values()) <= 1, \
        f"after adding a 5th node, partitions are {counts}"


# ---------------------------------------------------------------------------
# Step 3-4: vector_clock.py
# ---------------------------------------------------------------------------

def check_clock_ordering() -> None:
    from vector_clock import AFTER, BEFORE, CONCURRENT, EQUAL, VectorClock

    empty = VectorClock()
    assert empty.counter("Sx") == 0, "an absent node must read as counter 0"

    a = empty.increment("Sx")
    assert a.counter("Sx") == 1, "increment did not bump the counter"
    assert empty.counter("Sx") == 0, (
        "increment MUTATED the original clock. Clocks must be immutable — "
        "a version's clock cannot change under it.")

    b = a.increment("Sx")
    assert b.compare(a) == AFTER, f"[Sx:2] vs [Sx:1] should be AFTER, got {b.compare(a)}"
    assert a.compare(b) == BEFORE, f"[Sx:1] vs [Sx:2] should be BEFORE, got {a.compare(b)}"
    assert a.compare(a.copy()) == EQUAL, "a clock must equal its own copy"

    c = b.increment("Sy")
    d = b.increment("Sz")
    assert c.compare(d) == CONCURRENT, (
        f"[Sx:2,Sy:1] vs [Sx:2,Sz:1] should be CONCURRENT, got {c.compare(d)}. "
        "Neither descends from the other, so no node may pick a winner.")
    assert c.compare(b) == AFTER and b.compare(c) == BEFORE, \
        "a clock must descend from the clock it was incremented from"

    merged = c.merge(d)
    assert merged.descends_from(c) and merged.descends_from(d), \
        "merge must be the pointwise MAX, dominating both inputs"
    assert merged.to_context() == {"Sx": 2, "Sy": 1, "Sz": 1}, \
        f"merge produced {merged.to_context()}"

    round_trip = VectorClock.from_context(merged.to_context())
    assert round_trip.compare(merged) == EQUAL, \
        "to_context/from_context must round-trip"


def check_reconciliation() -> None:
    from vector_clock import (VectorClock, VersionedValue, coalesce,
                              merge_carts, reconcile)

    # Figure 3 from the paper.
    d1 = VersionedValue({"book": 1}, VectorClock().increment("Sx"))
    d2 = VersionedValue({"book": 1, "pen": 1}, d1.clock.increment("Sx"))
    d3 = VersionedValue({**d2.value, "mug": 1}, d2.clock.increment("Sy"))
    d4 = VersionedValue({**d2.value, "lamp": 1}, d2.clock.increment("Sz"))

    survivors = coalesce([d1, d2, d3, d4])
    assert len(survivors) == 2, (
        f"coalesce kept {len(survivors)} versions; D1 and D2 are ancestors of "
        "both D3 and D4 and must be dropped")
    assert {tuple(sorted(v.clock.to_context().items())) for v in survivors} == \
        {(("Sx", 2), ("Sy", 1)), (("Sx", 2), ("Sz", 1))}, \
        f"coalesce kept the wrong versions: {[v.clock for v in survivors]}"

    assert len(coalesce([d1])) == 1, "coalesce of a single version returns it"
    assert coalesce([]) == [], "coalesce of nothing returns nothing"
    assert len(coalesce([d3, d3])) == 1, "identical versions must collapse"

    assert merge_carts([{"a": 1}, {"b": 2}]) == {"a": 1, "b": 2}, \
        "merge_carts must union the items"
    assert merge_carts([{"a": 1}, {"a": 3}]) == {"a": 3}, \
        "merge_carts must keep the highest quantity per SKU"

    d5 = reconcile([d3, d4], merge_carts, node="Sx")
    assert d5.value == {"book": 1, "pen": 1, "mug": 1, "lamp": 1}, \
        f"reconciled cart is {d5.value}; nothing added may be lost"
    assert d5.clock.descends_from(d3.clock) and d5.clock.descends_from(d4.clock), (
        "the reconciled clock must descend from BOTH siblings — merge the "
        "clocks, then increment at the reconciling node")
    assert len(coalesce([d3, d4, d5])) == 1, \
        "after reconciliation a read must see exactly one version"


def check_truncation() -> None:
    from vector_clock import VectorClock

    clock = VectorClock()
    for i in range(14):
        clock = clock.increment(f"node{i}", now=1000.0 + i)
    assert len(clock.entries) == VectorClock.MAX_ENTRIES, (
        f"clock has {len(clock.entries)} entries; it must be capped at "
        f"{VectorClock.MAX_ENTRIES}")
    assert "node0" not in clock.entries and "node13" in clock.entries, (
        "truncation must drop the OLDEST entries by timestamp, keeping the "
        f"most recent: kept {sorted(clock.entries)}")


# ---------------------------------------------------------------------------
# Step 5-7: quorum.py
# ---------------------------------------------------------------------------

def check_storage_node() -> None:
    from quorum import NodeUnavailable, StorageNode
    from vector_clock import VectorClock, VersionedValue

    node = StorageNode("n0")
    v1 = VersionedValue("a", VectorClock().increment("n0"))
    v2 = VersionedValue("b", v1.clock.increment("n0"))
    concurrent = VersionedValue("c", VectorClock().increment("n9"))

    node.local_put("k", v1)
    assert [v.value for v in node.local_get("k")] == ["a"]

    node.local_put("k", v2)
    assert [v.value for v in node.local_get("k")] == ["b"], (
        "a newer version must SUPERSEDE an older one on local_put "
        "(coalesce the list)")

    node.local_put("k", concurrent)
    assert len(node.local_get("k")) == 2, (
        "a CONCURRENT version must be kept as a sibling, not overwrite. "
        "Overwriting here silently loses a write.")

    node.local_put("k", v2)
    assert len(node.local_get("k")) == 2, "local_put must be idempotent"

    node.kill()
    for op in (lambda: node.local_get("k"), lambda: node.local_put("k", v1)):
        try:
            op()
            raise AssertionError("a dead node must raise NodeUnavailable")
        except NodeUnavailable:
            pass


def check_quorum_ops() -> None:
    from quorum import QuorumNotMet, build_cluster

    ring, nodes, coord = build_cluster(num_nodes=5, n=3, r=2, w=2)
    assert len(nodes) == 5, "build_cluster must create num_nodes StorageNodes"

    key = "cart:user-42"
    coord.put(key, {"book": 1})
    result = coord.get(key)
    assert result.value == {"book": 1}, f"round trip returned {result.value}"
    assert result.replicas_answered == 3, \
        f"{result.replicas_answered} replicas answered, expected all 3"

    pref = ring.preference_list(key, 3)
    assert all(nodes[n].data.get(key) for n in pref), \
        "every replica in the preference list should hold the write"

    # One replica down: W=2 and R=2 are both still satisfiable.
    nodes[pref[0]].kill()
    coord.put(key, {"book": 1, "pen": 1}, context=result.context)
    assert coord.get(key).value == {"book": 1, "pen": 1}, \
        "with 2 of 3 replicas up, R=W=2 must still work"

    # Two replicas down: R=2 cannot be met.
    nodes[pref[1]].kill()
    try:
        coord.get(key)
        raise AssertionError("get must raise QuorumNotMet when fewer than R answer")
    except QuorumNotMet:
        pass


def check_siblings_and_repair() -> None:
    from vector_clock import merge_carts
    from quorum import build_cluster

    ring, nodes, coord = build_cluster(num_nodes=5, n=3, r=2, w=2)
    key = "cart:user-99"
    coord.put(key, {"book": 1})
    shared = coord.get(key).context

    pref = ring.preference_list(key, 3)
    coord.put(key, {"book": 1, "mug": 1}, context=shared, coordinating_node=pref[0])
    coord.put(key, {"book": 1, "lamp": 1}, context=shared, coordinating_node=pref[1])

    result = coord.get(key)
    assert result.has_conflict and len(result.versions) == 2, (
        f"two clients writing from the same context must produce 2 siblings, "
        f"got {len(result.versions)}")

    merged = coord.get_and_reconcile(key, merge_carts)
    assert merged == {"book": 1, "mug": 1, "lamp": 1}, f"merged to {merged}"
    assert not coord.get(key).has_conflict, \
        "after reconciliation the next read must see a single version"

    # Read repair.
    ring, nodes, coord = build_cluster(num_nodes=5, n=3, r=2, w=2)
    k2 = "profile:7"
    pref = ring.preference_list(k2, 3)
    nodes[pref[2]].kill()
    coord.put(k2, {"name": "ada"})
    nodes[pref[2]].revive()
    assert not nodes[pref[2]].data.get(k2), "setup: that replica should be stale"

    coord.get(k2)
    assert nodes[pref[2]].data.get(k2), (
        "read repair must push the merged view to replicas that were behind")
    assert coord.stats["read_repairs"] > 0, "stats['read_repairs'] was not counted"


# ---------------------------------------------------------------------------
# Step 8-9: hinted_handoff.py
# ---------------------------------------------------------------------------

def check_sloppy_quorum() -> None:
    from hinted_handoff import build_sloppy_cluster

    ring, nodes, coord = build_sloppy_cluster(num_nodes=6, n=3, r=2, w=2)
    key = "cart:user-42"
    home = ring.preference_list(key, 3)

    ordered = coord._extended_preference(key)
    assert ordered[:3] == home, "_extended_preference must start with the top-N"
    assert len(ordered) == 6, "_extended_preference must cover the whole ring"

    for name in home[:2]:
        nodes[name].kill()

    coord.put(key, {"book": 1})       # a strict W=2 write would fail here
    assert coord.stats["sloppy_writes"] > 0, (
        "with 2 of 3 owners down, W=2 can only be met by walking past them "
        "onto a fallback node and leaving a hint")

    pending = coord.pending_hints()
    assert pending, "a fallback node should be holding a hint"
    holder = next(iter(pending))
    assert holder not in home, "hints belong on nodes OUTSIDE the top-N"
    assert pending[holder][0].intended_for in home[:2], \
        "the hint must name the owner it is standing in for"

    result = coord.get(key, include_hints=True)
    assert result.values == [{"book": 1}], (
        "reading with hints included must find the value — it was never lost, "
        "only misfiled")


def check_hint_delivery() -> None:
    from hinted_handoff import build_sloppy_cluster

    ring, nodes, coord = build_sloppy_cluster(num_nodes=6, n=3, r=2, w=2)
    key = "cart:user-42"
    home = ring.preference_list(key, 3)
    for name in home[:2]:
        nodes[name].kill()
    coord.put(key, {"book": 1})

    assert coord.run_hint_delivery() == 0, (
        "hints must NOT be delivered while the intended owner is still down")

    for name in home[:2]:
        nodes[name].revive()
    delivered = coord.run_hint_delivery()
    assert delivered > 0, "hints must be handed off once the owner is reachable"
    assert not coord.pending_hints(), "delivered hints must be dropped locally"
    assert coord.run_hint_delivery() == 0, "delivery must be idempotent"

    holders = [n for n in home if nodes[n].data.get(key)]
    assert holders, "at least one owner should now hold the handed-off data"


# ---------------------------------------------------------------------------
# Step 10-11: merkle_sync.py
# ---------------------------------------------------------------------------

def check_merkle_tree() -> None:
    from merkle_sync import MerkleTree
    from vector_clock import VectorClock, VersionedValue

    def make(node: str, value: object, n: int = 1) -> VersionedValue:
        clock = VectorClock()
        for _ in range(n):
            clock = clock.increment(node)
        return VersionedValue(value, clock)

    store_a = {f"key:{i}": [make("n0", i)] for i in range(500)}
    store_b = {k: list(v) for k, v in store_a.items()}

    tree_a, tree_b = MerkleTree(depth=8), MerkleTree(depth=8)
    tree_a.build(store_a)
    tree_b.build(store_b)
    assert tree_a.root.hash == tree_b.root.hash, (
        "identical replicas must produce identical roots — your leaf hash is "
        "probably order-dependent or includes something non-deterministic")

    ranges, compared = tree_a.diff(tree_b)
    assert ranges == [], f"identical trees should report no differing ranges, got {ranges}"
    assert compared == 1, (
        f"comparing identical trees cost {compared} node comparisons; it must "
        "cost exactly 1. If the roots match you stop immediately — that is the "
        "entire point of the tree.")

    store_b["key:7"] = [make("n1", "changed", 2)]
    tree_b = MerkleTree(depth=8)
    tree_b.build(store_b)
    ranges, compared = tree_a.diff(tree_b)
    assert ranges, "a changed key must produce a differing range"
    assert compared < 60, (
        f"{compared} comparisons to find 1 difference among 500 keys; it should "
        "be a few dozen. You are descending into subtrees whose hashes match.")


def check_anti_entropy() -> None:
    from merkle_sync import AntiEntropy
    from vector_clock import VectorClock, VersionedValue, coalesce

    def make(node: str, value: object, n: int = 1) -> VersionedValue:
        clock = VectorClock()
        for _ in range(n):
            clock = clock.increment(node)
        return VersionedValue(value, clock)

    a = {f"k{i}": [make("n0", i)] for i in range(200)}
    b = {k: list(v) for k, v in a.items()}
    b["k5"] = [make("n1", "newer", 2)]     # b is ahead on k5
    del b["k9"]                            # b is missing k9 entirely

    engine = AntiEntropy(depth=8)
    moved = engine.synchronize(a, b)
    assert "k9" in moved and "k5" in moved, f"synchronize reported {sorted(moved)}"
    assert "k9" in b, "a key missing from one side must be copied to it"
    assert engine.synchronize(a, b) == set(), "synchronize must be idempotent"

    # Concurrent versions must survive as siblings, not be resolved.
    c = {"cart": [make("nX", {"a": 1})]}
    d = {"cart": [make("nY", {"b": 1})]}
    AntiEntropy(depth=6).synchronize(c, d)
    assert len(c["cart"]) == 2 and len(d["cart"]) == 2, (
        "anti-entropy must UNION concurrent versions into siblings on both "
        "sides. Picking a winner here reintroduces the lost update that vector "
        "clocks exist to prevent.")
    assert coalesce(c["cart"]) == coalesce(d["cart"]) or \
        len(coalesce(c["cart"])) == len(coalesce(d["cart"])) == 2, \
        "both replicas must end up with the same version set"


# ---------------------------------------------------------------------------
# Step 12-13: gossip.py
# ---------------------------------------------------------------------------

def check_gossip_convergence() -> None:
    from gossip import GossipCluster

    for size, limit in ((8, 20), (32, 25), (128, 30)):
        cluster = GossipCluster([f"node{i}" for i in range(size)], fanout=1, seed=3)
        cluster.seed_all(seeds=["node0", "node1"])
        rounds = cluster.rounds_until_converged(limit=limit)
        assert rounds > 0, (
            f"{size} nodes did not converge within {limit} rounds. Gossip should "
            "need O(log S). If it grows linearly, receive() is probably only "
            "accepting facts about the direct sender.")
        assert rounds <= limit, f"{size} nodes took {rounds} rounds"

    cluster = GossipCluster([f"node{i}" for i in range(16)], fanout=1, seed=5)
    cluster.seed_all()
    cluster.rounds_until_converged()
    node = cluster.nodes["node0"]
    assert len(node.members) == 16, \
        f"after convergence node0 knows {len(node.members)} of 16 members"
    assert node.members["node0"].heartbeat > 0, \
        "a node must increment its OWN heartbeat every tick"


def check_failure_detection() -> None:
    from gossip import ALIVE, DEAD, GossipCluster

    cluster = GossipCluster([f"node{i}" for i in range(6)], fanout=1, seed=11,
                            suspect_after=3, dead_after=6)
    cluster.seed_all()
    cluster.rounds_until_converged()

    live = cluster.nodes["node0"]
    assert live.members["node4"].status == ALIVE, "setup: node4 should start alive"

    cluster.nodes["node4"].alive = False
    for _ in range(15):
        cluster.step()

    beliefs = {n.members["node4"].status
               for n in cluster.nodes.values() if n.alive}
    assert DEAD in beliefs, (
        "after 15 rounds of silence at least one peer must mark node4 DEAD. "
        "Check that last_seen only advances when the heartbeat actually RISES.")

    # Two islands with disjoint seeds must never merge.
    split = GossipCluster([f"a{i}" for i in range(4)] + [f"b{i}" for i in range(4)],
                          fanout=1, seed=17)
    for name in ("a0", "a1", "a2", "a3"):
        split.nodes[name].seed([split.nodes[n] for n in ("a0", "a1")])
    for name in ("b0", "b1", "b2", "b3"):
        split.nodes[name].seed([split.nodes[n] for n in ("b0", "b1")])
    for _ in range(20):
        split.step()
    assert not any(m.startswith("b") for m in split.nodes["a0"].members), (
        "groups with disjoint seed lists must form separate logical rings — "
        "that is the failure seeds exist to prevent")


# ---------------------------------------------------------------------------
# Step 14: dynamo_cluster.py
# ---------------------------------------------------------------------------

def check_full_cluster() -> None:
    from vector_clock import merge_carts
    from dynamo_cluster import DynamoCluster, availability_under_churn

    cluster = DynamoCluster(num_nodes=6, n=3, r=2, w=2)
    key = "cart:user-42"
    home = cluster.ring.preference_list(key, 3)

    cluster.put(key, {"a": 1})
    first = cluster.get(key)
    assert first.value == {"a": 1}

    cluster.kill(home[0])
    cluster.kill(home[1])
    cluster.put(key, {"a": 1, "b": 1}, context=first.context)   # must not raise

    shared = cluster.get(key).context
    live = [n for n in cluster.coordinator._extended_preference(key)
            if cluster.nodes[n].alive]
    cluster.coordinator.put(key, {"a": 1, "b": 1, "c": 1}, context=shared,
                            coordinating_node=live[0])
    cluster.coordinator.put(key, {"a": 1, "b": 1, "d": 1}, context=shared,
                            coordinating_node=live[1])
    assert cluster.get(key).has_conflict, "expected siblings after concurrent writes"

    cluster.revive(home[0])
    cluster.revive(home[1])
    jobs = cluster.run_background_jobs()
    assert set(jobs) == {"hints_delivered", "keys_repaired"}, \
        f"run_background_jobs returned {jobs}"

    merged = cluster.get_and_reconcile(key, merge_carts)
    assert set(merged) == {"a", "b", "c", "d"}, (
        f"merged cart is {merged}; every add must survive the outage")

    sloppy = availability_under_churn(3, 2, 2, sloppy=True)
    strict = availability_under_churn(3, 2, 2, sloppy=False)
    assert sloppy["write_success"] >= strict["write_success"], (
        f"sloppy writes succeeded {sloppy['write_success']:.1%} vs strict "
        f"{strict['write_success']:.1%} — sloppy must be at least as available")
    assert sloppy["write_success"] > 0.98, \
        f"sloppy write availability was only {sloppy['write_success']:.1%}"
    assert strict["write_success"] < 0.99, (
        "strict quorum should visibly FAIL some writes under 30% churn; if it "
        "does not, the sloppy=False override is not taking effect")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("partitioning.py", "ring: add/remove/coordinator", check_ring_basics),
    ("partitioning.py", "preference lists (N distinct nodes)", check_preference_list),
    ("partitioning.py", "load balance and key migration", check_balance_and_migration),
    ("partitioning.py", "strategy 3: fixed partitions", check_partitioned_ring),
    ("vector_clock.py", "clock ordering and merge", check_clock_ordering),
    ("vector_clock.py", "reconciliation (paper Figure 3)", check_reconciliation),
    ("vector_clock.py", "clock truncation", check_truncation),
    ("quorum.py", "storage node keeps siblings", check_storage_node),
    ("quorum.py", "N/R/W put and get", check_quorum_ops),
    ("quorum.py", "siblings and read repair", check_siblings_and_repair),
    ("hinted_handoff.py", "sloppy quorum writes a hint", check_sloppy_quorum),
    ("hinted_handoff.py", "hinted handoff delivery", check_hint_delivery),
    ("merkle_sync.py", "merkle tree build and diff", check_merkle_tree),
    ("merkle_sync.py", "anti-entropy is a union", check_anti_entropy),
    ("gossip.py", "gossip convergence O(log S)", check_gossip_convergence),
    ("gossip.py", "local failure detection, seeds", check_failure_detection),
    ("dynamo_cluster.py", "capstone: cart + availability", check_full_cluster),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}Dynamo From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue

        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<20} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<20} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<20} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have implemented Dynamo.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The TODO comments in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Sloppy Quorum & Hinted Handoff — Complete Solution

Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007), section 4.6.
"""

from typing import Any, Dict, List, Optional, Tuple

from partitioning import ConsistentHashRing
from quorum import GetResult, NodeUnavailable, QuorumNotMet, StorageNode
from vector_clock import VectorClock, VersionedValue, coalesce


class Hint:
    """A replica held on behalf of a node that was unreachable."""

    __slots__ = ("key", "version", "intended_for")

    def __init__(self, key: str, version: VersionedValue, intended_for: str):
        self.key = key
        self.version = version
        self.intended_for = intended_for

    def __repr__(self) -> str:
        return f"Hint({self.key!r} for {self.intended_for}, {self.version.clock})"


class HintedNode(StorageNode):
    """A storage node that can also hold hinted replicas for its peers.

    Hinted data lives in a separate local area precisely so it is *not* served
    as if the node owned it, and so a scanner can walk it cheaply and hand it
    back once the intended node returns.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.hints: List[Hint] = []
        self.stats.update({"hints_stored": 0, "hints_delivered": 0})

    def store_hint(self, key: str, version: VersionedValue, intended_for: str) -> None:
        self._check()
        self.hints.append(Hint(key, version, intended_for))
        self.stats["hints_stored"] += 1

    def deliver_hints(self, nodes: Dict[str, "HintedNode"]) -> int:
        """Try to hand every held hint back to its intended owner.

        Delivered hints are dropped locally; undeliverable ones stay put.  This
        is the loop Dynamo runs periodically on every node.
        """
        if not self.alive:
            return 0
        delivered = 0
        remaining: List[Hint] = []
        for hint in self.hints:
            target = nodes.get(hint.intended_for)
            if target is None or not target.alive:
                remaining.append(hint)
                continue
            try:
                target.local_put(hint.key, hint.version)
                delivered += 1
            except NodeUnavailable:
                remaining.append(hint)
        self.hints = remaining
        self.stats["hints_delivered"] += delivered
        return delivered


class SloppyCoordinator:
    """Quorum coordinator that falls forward past unreachable replicas.

    A *strict* quorum only ever talks to the top-N nodes of the preference
    list.  Dynamo's *sloppy* quorum walks further down the ring until W healthy
    nodes have accepted the write, tagging the extras with a hint.  The write
    survives; the data returns home when the owner does.
    """

    def __init__(self, ring: ConsistentHashRing, nodes: Dict[str, HintedNode],
                 n: int = 3, r: int = 2, w: int = 2, read_repair: bool = True):
        self.ring = ring
        self.nodes = nodes
        self.n, self.r, self.w = n, r, w
        self.read_repair = read_repair
        self.stats = {"puts": 0, "gets": 0, "sloppy_writes": 0, "put_failures": 0,
                      "get_failures": 0, "read_repairs": 0}

    # -- helpers ------------------------------------------------------------

    def _extended_preference(self, key: str) -> List[str]:
        """Top-N plus every remaining node, in ring order — the fallback path."""
        return self.ring.preference_list(key, len(self.nodes))

    # -- write path ---------------------------------------------------------

    def put(self, key: str, value: Any, context: Optional[Dict[str, int]] = None,
            coordinating_node: Optional[str] = None) -> VectorClock:
        self.stats["puts"] += 1
        ordered = self._extended_preference(key)
        if not ordered:
            raise QuorumNotMet("empty ring")
        top_n = ordered[: self.n]

        coordinator = coordinating_node or top_n[0]
        clock = VectorClock.from_context(context or {}).increment(coordinator)
        version = VersionedValue(value, clock)

        acks = 0
        missing = []
        for node_name in top_n:                       # the home replicas first
            try:
                self.nodes[node_name].local_put(key, version)
                acks += 1
            except NodeUnavailable:
                missing.append(node_name)

        for node_name in ordered[self.n:]:            # then walk the ring
            if acks >= self.w or not missing:
                break
            fallback = self.nodes[node_name]
            if not fallback.alive:
                continue
            try:
                fallback.store_hint(key, version, intended_for=missing.pop(0))
                acks += 1
                self.stats["sloppy_writes"] += 1
            except NodeUnavailable:
                continue

        if acks < self.w:
            self.stats["put_failures"] += 1
            raise QuorumNotMet(f"put {key}: {acks} acks < W={self.w}")
        return clock

    # -- read path ----------------------------------------------------------

    def get(self, key: str, include_hints: bool = True) -> GetResult:
        """Read the home replicas; optionally consult hints still in flight.

        Dynamo reads only the top-N nodes.  `include_hints=True` shows what a
        read would see if fallback nodes also answered — useful for seeing that
        the data was never actually lost, only misfiled.
        """
        self.stats["gets"] += 1
        ordered = self._extended_preference(key)
        top_n = ordered[: self.n]

        responses: List[Tuple[str, List[VersionedValue]]] = []
        for node_name in top_n:
            try:
                responses.append((node_name, self.nodes[node_name].local_get(key)))
            except NodeUnavailable:
                continue
        home_responses = len(responses)

        hinted: List[VersionedValue] = []
        if include_hints:
            for node_name in ordered[self.n:]:
                node = self.nodes[node_name]
                if not node.alive:
                    continue
                held = [h.version for h in node.hints if h.key == key]
                if held:
                    hinted += held
                    responses.append((node_name, []))   # counts toward R, never repaired

        if len(responses) < self.r:
            self.stats["get_failures"] += 1
            raise QuorumNotMet(f"get {key}: {len(responses)} responses < R={self.r}")

        merged = coalesce([v for _, versions in responses for v in versions] + hinted)
        answered = len(responses)
        responses = responses[:home_responses]          # repair only the real owners

        if self.read_repair and merged:
            for node_name, versions in responses:
                if coalesce(versions + merged) == coalesce(versions):
                    continue
                for version in merged:
                    try:
                        self.nodes[node_name].local_put(key, version)
                    except NodeUnavailable:
                        break
                self.stats["read_repairs"] += 1

        context: Dict[str, int] = {}
        for version in merged:
            for node, counter in version.clock.to_context().items():
                context[node] = max(context.get(node, 0), counter)
        return GetResult(merged, context, answered)

    # -- background loop ----------------------------------------------------

    def run_hint_delivery(self) -> int:
        """One pass of hinted-handoff delivery across the whole cluster."""
        return sum(node.deliver_hints(self.nodes) for node in self.nodes.values())

    def pending_hints(self) -> Dict[str, List[Hint]]:
        return {name: list(node.hints) for name, node in self.nodes.items() if node.hints}


def build_sloppy_cluster(num_nodes: int = 6, tokens_per_node: int = 64,
                         n: int = 3, r: int = 2, w: int = 2
                         ) -> Tuple[ConsistentHashRing, Dict[str, HintedNode],
                                    SloppyCoordinator]:
    ring = ConsistentHashRing(tokens_per_node=tokens_per_node)
    nodes: Dict[str, HintedNode] = {}
    for i in range(num_nodes):
        name = f"node{i}"
        ring.add_node(name)
        nodes[name] = HintedNode(name)
    return ring, nodes, SloppyCoordinator(ring, nodes, n=n, r=r, w=w)


def _demo() -> None:
    ring, nodes, coord = build_sloppy_cluster(num_nodes=6, n=3, r=2, w=2)
    key = "cart:user-42"
    home = ring.preference_list(key, 3)
    print(f"N=3 R=2 W=2, home replicas for {key}: {home}")
    print(f"full ring order: {coord._extended_preference(key)}")

    print("\n=== Kill two of the three home replicas ===")
    for name in home[:2]:
        nodes[name].kill()
    print(f"down: {home[:2]}")

    print("\n--- strict quorum would fail here (W=2, only 1 home replica up) ---")
    clock = coord.put(key, {"book": 1, "pen": 1})
    print(f"sloppy put succeeded -> clock {clock}")
    print(f"sloppy writes so far: {coord.stats['sloppy_writes']}")
    for name, hints in coord.pending_hints().items():
        print(f"  {name} holds {hints}")

    print("\n=== Reading while the owners are down ===")
    try:
        result = coord.get(key, include_hints=False)
        print(f"home replicas only  -> {result.values} "
              f"({result.replicas_answered} answered)")
    except QuorumNotMet as exc:
        print(f"home replicas only  -> failed: {exc}")
    result = coord.get(key, include_hints=True)
    print(f"including hints     -> {result.values} "
          f"({result.replicas_answered} answered)")
    print("The write was never lost — it is just parked on a fallback node.")

    print("\n=== Owners come back; hints are handed off ===")
    for name in home[:2]:
        nodes[name].revive()
    delivered = coord.run_hint_delivery()
    print(f"hints delivered: {delivered}")
    print(f"hints still pending: {coord.pending_hints() or 'none'}")
    for name in home:
        print(f"  {name} local copy: {[v.value for v in nodes[name].local_get(key)]}")
    print("Note: only ONE hint was created, because W=2 was already satisfied by")
    print("one live owner plus one fallback. The third owner is still stale — only")
    print("read repair or anti-entropy will fix it.")

    print("\n=== Where sloppy quorum still loses data ===")
    ring2, nodes2, coord2 = build_sloppy_cluster(num_nodes=6, n=3, r=2, w=2)
    k2 = "order:1"
    home2 = ring2.preference_list(k2, 3)
    for name in home2:                      # all three owners unreachable
        nodes2[name].kill()
    coord2.put(k2, {"total": 99})           # W=2 met entirely by hints
    holders = list(coord2.pending_hints())
    print(f"all owners {home2} were down; hints parked on {holders}")
    for name in holders:                    # fallbacks die before handing them back
        nodes2[name].kill()
    for name in home2:
        nodes2[name].revive()
    coord2.run_hint_delivery()
    result = coord2.get(k2, include_hints=True)
    print(f"then {holders} died before delivery")
    print(f"read now returns: {result.values or 'NOTHING'}")
    print("An acknowledged write is gone. Durability still needs the Merkle-tree")
    print("anti-entropy in merkle_sync.py — and, ultimately, more replicas.")


if __name__ == "__main__":
    _demo()

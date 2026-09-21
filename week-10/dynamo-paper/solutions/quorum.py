"""
Quorum Reads & Writes (N, R, W) — Complete Solution

Paper: "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007), section 4.5.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from partitioning import ConsistentHashRing
from vector_clock import VectorClock, VersionedValue, coalesce


class NodeUnavailable(Exception):
    """Raised by a storage node that is simulating a crash or a network drop."""


class QuorumNotMet(Exception):
    """Fewer than R (or W) replicas answered in time."""


# ---------------------------------------------------------------------------
# Storage node
# ---------------------------------------------------------------------------

class StorageNode:
    """One machine's local store: key -> list of sibling versions.

    Real Dynamo puts a pluggable engine here (BDB, MySQL, an in-memory buffer).
    The only property that matters for the protocol is that a local write never
    overwrites a concurrent version — it appends a sibling.
    """

    def __init__(self, name: str):
        self.name = name
        self.alive = True
        self.data: Dict[str, List[VersionedValue]] = {}
        self.stats = {"local_puts": 0, "local_gets": 0, "rejected": 0}

    # -- failure injection --------------------------------------------------

    def kill(self) -> None:
        self.alive = False

    def revive(self) -> None:
        self.alive = True

    def _check(self) -> None:
        if not self.alive:
            self.stats["rejected"] += 1
            raise NodeUnavailable(self.name)

    # -- local operations ---------------------------------------------------

    def local_put(self, key: str, version: VersionedValue) -> None:
        self._check()
        self.stats["local_puts"] += 1
        existing = self.data.get(key, [])
        self.data[key] = coalesce(existing + [version])

    def local_get(self, key: str) -> List[VersionedValue]:
        self._check()
        self.stats["local_gets"] += 1
        return list(self.data.get(key, []))

    def keys(self) -> List[str]:
        return sorted(self.data)

    def __repr__(self) -> str:
        state = "up" if self.alive else "DOWN"
        return f"<StorageNode {self.name} {state} keys={len(self.data)}>"


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

class GetResult:
    """What a client sees from get(): possibly several siblings plus a context."""

    def __init__(self, versions: List[VersionedValue], context: Dict[str, int],
                 replicas_answered: int):
        self.versions = versions
        self.context = context
        self.replicas_answered = replicas_answered

    @property
    def value(self) -> Any:
        """Convenience for the single-version case."""
        if len(self.versions) != 1:
            raise ValueError(f"{len(self.versions)} siblings — the app must reconcile")
        return self.versions[0].value

    @property
    def values(self) -> List[Any]:
        return [v.value for v in self.versions]

    @property
    def has_conflict(self) -> bool:
        return len(self.versions) > 1

    def __repr__(self) -> str:
        return f"GetResult({self.values!r}, replicas={self.replicas_answered})"


class Coordinator:
    """Client-facing entry point. Any node can coordinate any request.

    N = replicas per key, R = replicas that must answer a read,
    W = replicas that must acknowledge a write.

      R + W > N   -> read-your-writes on the overlap (a "strict" quorum)
      W = 1       -> always-writeable, the configuration the paper favours
      R = 1, W = N-> fast reads, slow and fragile writes
    """

    def __init__(self, ring: ConsistentHashRing, nodes: Dict[str, StorageNode],
                 n: int = 3, r: int = 2, w: int = 2, read_repair: bool = True):
        if r + w <= n:
            print(f"  note: R({r}) + W({w}) <= N({n}) — reads may miss the latest write")
        self.ring = ring
        self.nodes = nodes
        self.n, self.r, self.w = n, r, w
        self.read_repair = read_repair
        self.stats = {"puts": 0, "gets": 0, "put_failures": 0, "get_failures": 0,
                      "read_repairs": 0}

    # -- write path ---------------------------------------------------------

    def put(self, key: str, value: Any, context: Optional[Dict[str, int]] = None,
            coordinating_node: Optional[str] = None) -> VectorClock:
        """Write `value`, superseding the version the client last read.

        `context` is the opaque clock returned by an earlier get().  Passing it
        back is what tells Dynamo "this update is based on that version"; omit
        it and you create a sibling instead of an update.
        """
        self.stats["puts"] += 1
        preference = self.ring.preference_list(key, self.n)
        if not preference:
            raise QuorumNotMet("empty ring")

        coordinator = coordinating_node or preference[0]
        clock = VectorClock.from_context(context or {}).increment(coordinator)
        version = VersionedValue(value, clock)

        acks = 0
        for node_name in preference:
            try:
                self.nodes[node_name].local_put(key, version)
                acks += 1
            except NodeUnavailable:
                continue
        if acks < self.w:
            self.stats["put_failures"] += 1
            raise QuorumNotMet(f"put {key}: {acks} acks < W={self.w}")
        return clock

    # -- read path ----------------------------------------------------------

    def get(self, key: str) -> GetResult:
        self.stats["gets"] += 1
        preference = self.ring.preference_list(key, self.n)
        responses: List[Tuple[str, List[VersionedValue]]] = []
        for node_name in preference:
            try:
                responses.append((node_name, self.nodes[node_name].local_get(key)))
            except NodeUnavailable:
                continue

        if len(responses) < self.r:
            self.stats["get_failures"] += 1
            raise QuorumNotMet(f"get {key}: {len(responses)} responses < R={self.r}")

        all_versions = [v for _, versions in responses for v in versions]
        merged = coalesce(all_versions)

        if self.read_repair and merged:
            self._repair(key, merged, responses)

        context: Dict[str, int] = {}
        for version in merged:
            for node, counter in version.clock.to_context().items():
                context[node] = max(context.get(node, 0), counter)
        return GetResult(merged, context, len(responses))

    def _repair(self, key: str, merged: List[VersionedValue],
                responses: List[Tuple[str, List[VersionedValue]]]) -> None:
        """Push the merged view back to any replica that was behind.

        Read repair is Dynamo's cheap anti-entropy: it only fixes keys someone
        actually reads, which is why a background Merkle sync is still needed
        for cold data.
        """
        for node_name, versions in responses:
            stale = coalesce(versions + merged) != coalesce(versions)
            if not stale:
                continue
            for version in merged:
                try:
                    self.nodes[node_name].local_put(key, version)
                except NodeUnavailable:
                    break
            self.stats["read_repairs"] += 1

    # -- convenience --------------------------------------------------------

    def get_and_reconcile(self, key: str,
                          merge_fn: Callable[[List[Any]], Any]) -> Optional[Any]:
        """Read, merge siblings with app logic, write the merge back."""
        result = self.get(key)
        if not result.versions:
            return None
        if not result.has_conflict:
            return result.value
        merged_value = merge_fn(result.values)
        self.put(key, merged_value, context=result.context)
        return merged_value


def build_cluster(num_nodes: int = 5, tokens_per_node: int = 64,
                  n: int = 3, r: int = 2, w: int = 2
                  ) -> Tuple[ConsistentHashRing, Dict[str, StorageNode], Coordinator]:
    ring = ConsistentHashRing(tokens_per_node=tokens_per_node)
    nodes: Dict[str, StorageNode] = {}
    for i in range(num_nodes):
        name = f"node{i}"
        ring.add_node(name)
        nodes[name] = StorageNode(name)
    return ring, nodes, Coordinator(ring, nodes, n=n, r=r, w=w)


def _demo() -> None:
    from vector_clock import merge_carts

    ring, nodes, coord = build_cluster(num_nodes=5, n=3, r=2, w=2)
    key = "cart:user-42"
    print(f"N=3 R=2 W=2, preference list for {key}: {ring.preference_list(key, 3)}")

    print("\n=== Normal operation ===")
    ctx = coord.put(key, {"book": 1})
    print(f"put -> clock {ctx}")
    result = coord.get(key)
    print(f"get -> {result.value}  ({result.replicas_answered}/3 replicas answered)")

    print("\n=== One replica down: still available ===")
    down = ring.preference_list(key, 3)[0]
    nodes[down].kill()
    print(f"killed {down}")
    coord.put(key, {"book": 1, "pen": 1}, context=result.context)
    result = coord.get(key)
    print(f"get -> {result.value}  ({result.replicas_answered}/3 replicas answered)")

    print("\n=== Two replicas down: R=2 cannot be met ===")
    second = ring.preference_list(key, 3)[1]
    nodes[second].kill()
    print(f"killed {second}")
    try:
        coord.get(key)
    except QuorumNotMet as exc:
        print(f"get failed: {exc}")
    print("A sloppy quorum (next file) is what keeps this write path alive.")
    nodes[down].revive()
    nodes[second].revive()

    print("\n=== Two clients update the same version -> siblings ===")
    cart = "cart:user-99"
    coord.put(cart, {"book": 1})
    shared = coord.get(cart).context          # both clients read this version
    preference = ring.preference_list(cart, 3)
    coord.put(cart, {"book": 1, "mug": 1}, context=shared, coordinating_node=preference[0])
    coord.put(cart, {"book": 1, "lamp": 1}, context=shared, coordinating_node=preference[1])
    result = coord.get(cart)
    print(f"get -> {len(result.versions)} siblings: {result.values}")
    print("Neither clock descends from the other, so no node may pick a winner.")

    merged = coord.get_and_reconcile(cart, merge_carts)
    print(f"after app-level merge: {merged}")
    print(f"re-read -> {coord.get(cart).value}")

    print("\n=== Read repair ===")
    stale_ring, stale_nodes, stale_coord = build_cluster(num_nodes=5, n=3, r=2, w=2)
    k2 = "profile:7"
    preference = stale_ring.preference_list(k2, 3)
    stale_nodes[preference[2]].kill()
    stale_coord.put(k2, {"name": "ada"})
    stale_nodes[preference[2]].revive()
    print(f"{preference[2]} missed the write: "
          f"{len(stale_nodes[preference[2]].local_get(k2))} versions locally")
    stale_coord.get(k2)
    print(f"after one read: {len(stale_nodes[preference[2]].local_get(k2))} versions locally")
    print(f"read repairs performed: {stale_coord.stats['read_repairs']}")


if __name__ == "__main__":
    _demo()

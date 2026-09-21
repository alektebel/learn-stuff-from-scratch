"""
Radix Tree Prefix Cache (RadixAttention) — Complete Solution

The scheme SGLang calls RadixAttention. Instead of a flat hash table of fixed
blocks, sequences live in a radix tree: shared prefixes are stored once, on a
shared path, and diverge exactly where the token streams diverge.
"""

from typing import Dict, List, Optional, Sequence, Tuple


class RadixNode:
    """One edge of the radix tree: a run of tokens and their KV entries."""

    __slots__ = ("key", "value", "children", "parent", "ref_count", "last_used")

    def __init__(self, key: Optional[List[int]] = None,
                 value: Optional[List[object]] = None,
                 parent: Optional["RadixNode"] = None):
        self.key: List[int] = key or []           # tokens on the edge into this node
        self.value: List[object] = value or []    # one KV entry per token
        self.children: Dict[int, "RadixNode"] = {}
        self.parent = parent
        self.ref_count = 0
        self.last_used = 0

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def __repr__(self) -> str:
        preview = self.key[:6]
        return f"<RadixNode {preview}{'...' if len(self.key) > 6 else ''} " \
               f"refs={self.ref_count}>"


def _common_prefix_len(a: Sequence[int], b: Sequence[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


class RadixCache:
    """Token-level prefix cache with LRU eviction and reference counting.

    Compared with fixed-size block hashing:

      + Matches at exact token granularity — no quantisation loss, so a shared
        prefix of 60 tokens is worth all 60 rather than being rounded down to
        the nearest block boundary.
      + Shared prefixes are stored once, physically, so eviction can reason
        about "this subtree serves N requests" instead of guessing from LRU.
      - Nodes must split on divergence, which is more bookkeeping than a hash
        lookup, and pointer-chasing costs more per lookup than one hash.
    """

    def __init__(self, capacity_tokens: int = 4096):
        self.root = RadixNode()
        self.capacity = capacity_tokens
        self.size = 0                    # cached tokens currently held
        self.clock = 0
        self.stats = {"lookups": 0, "tokens_matched": 0, "tokens_inserted": 0,
                      "tokens_evicted": 0, "splits": 0}

    # -- lookup -------------------------------------------------------------

    def match_prefix(self, tokens: Sequence[int]
                     ) -> Tuple[int, List[object], Optional[RadixNode]]:
        """Longest cached prefix. Returns (length, KV entries, last node).

        A partial match inside an edge is fine — the caller gets the first k
        entries of that edge. Splitting only becomes necessary on insert.
        """
        self.stats["lookups"] += 1
        self.clock += 1
        node = self.root
        values: List[object] = []
        index = 0

        while index < len(tokens):
            child = node.children.get(tokens[index])
            if child is None:
                break
            shared = _common_prefix_len(child.key, tokens[index:])
            child.last_used = self.clock
            values.extend(child.value[:shared])
            index += shared
            if shared < len(child.key):
                node = child                        # matched partway into the edge
                break
            node = child

        self.stats["tokens_matched"] += index
        return index, values, (node if node is not self.root else None)

    # -- insertion ----------------------------------------------------------

    def insert(self, tokens: Sequence[int], values: Sequence[object]) -> RadixNode:
        """Insert a sequence with one KV entry per token; returns the leaf node."""
        assert len(tokens) == len(values), "one KV entry per token"
        self.clock += 1
        node = self.root
        index = 0

        while index < len(tokens):
            first = tokens[index]
            child = node.children.get(first)

            if child is None:
                new_node = RadixNode(list(tokens[index:]), list(values[index:]), node)
                new_node.last_used = self.clock
                node.children[first] = new_node
                self.size += len(new_node.key)
                self.stats["tokens_inserted"] += len(new_node.key)
                self._evict_if_needed()
                return new_node

            shared = _common_prefix_len(child.key, tokens[index:])
            child.last_used = self.clock

            if shared == len(child.key):
                index += shared
                node = child
                continue

            # The new sequence diverges inside this edge: split it in two.
            self._split(node, child, shared)
            self.stats["splits"] += 1
            index += shared
            node = node.children[first]

        node.last_used = self.clock
        return node

    def _split(self, parent: RadixNode, child: RadixNode, at: int) -> None:
        """Break `child`'s edge at offset `at`, inserting an intermediate node.

        The intermediate node holds the shared head; the original child keeps
        the tail and becomes its only child, along with its children.

        The head inherits the child's reference count. A pin marks every node on
        a path, and the head is now on that path — leaving it at zero would let
        the compaction in _remove merge a pinned child into an unpinned parent
        and quietly drop the pin.
        """
        head = RadixNode(child.key[:at], child.value[:at], parent)
        head.last_used = child.last_used
        head.ref_count = child.ref_count

        child.key = child.key[at:]
        child.value = child.value[at:]
        child.parent = head
        head.children[child.key[0]] = child

        parent.children[head.key[0]] = head

    # -- eviction -----------------------------------------------------------

    def _evict_if_needed(self) -> None:
        while self.size > self.capacity:
            victim = self._lru_leaf()
            if victim is None:
                return                    # everything left is pinned
            self._remove(victim)

    def _lru_leaf(self) -> Optional[RadixNode]:
        """Least-recently-used evictable leaf.

        Only leaves are evictable, and that is the whole elegance of the tree:
        an interior node is a prefix that some longer cached sequence still
        needs, so the structure makes "do not evict a shared prefix" automatic
        rather than a heuristic.
        """
        best: Optional[RadixNode] = None
        stack = [self.root]
        while stack:
            node = stack.pop()
            stack.extend(node.children.values())
            if node is self.root or not node.is_leaf or node.ref_count > 0:
                continue
            if best is None or node.last_used < best.last_used:
                best = node
        return best

    def _remove(self, node: RadixNode) -> None:
        parent = node.parent
        if parent is None:
            return
        del parent.children[node.key[0]]
        self.size -= len(node.key)
        self.stats["tokens_evicted"] += len(node.key)

        # A parent left with exactly one child can be merged back into a single
        # edge, keeping the tree compact. Both ends must be unreferenced: the
        # merged node inherits the parent's reference count, so merging a pinned
        # child into an unpinned parent would lose the pin.
        if (parent is not self.root and len(parent.children) == 1
                and parent.ref_count == 0
                and next(iter(parent.children.values())).ref_count == 0):
            only = next(iter(parent.children.values()))
            parent.key = parent.key + only.key
            parent.value = parent.value + only.value
            parent.children = only.children
            for grandchild in parent.children.values():
                grandchild.parent = parent

    # -- pinning ------------------------------------------------------------

    def pin(self, node: Optional[RadixNode]) -> None:
        """Protect a node and all its ancestors from eviction."""
        while node is not None and node is not self.root:
            node.ref_count += 1
            node = node.parent

    def unpin(self, node: Optional[RadixNode]) -> None:
        while node is not None and node is not self.root:
            node.ref_count = max(0, node.ref_count - 1)
            node = node.parent

    # -- inspection ---------------------------------------------------------

    def num_nodes(self) -> int:
        count, stack = 0, [self.root]
        while stack:
            node = stack.pop()
            count += 1
            stack.extend(node.children.values())
        return count

    def pretty(self, node: Optional[RadixNode] = None, depth: int = 0) -> str:
        node = node or self.root
        label = "(root)" if node is self.root else \
            f"{node.key[:8]}{'...' if len(node.key) > 8 else ''} " \
            f"len={len(node.key)} refs={node.ref_count}"
        lines = ["  " * depth + label]
        for child in sorted(node.children.values(), key=lambda c: c.key[0]):
            lines.append(self.pretty(child, depth + 1))
        return "\n".join(lines)


def _kv(tokens: Sequence[int]) -> List[object]:
    """Stand-in for real KV tensors — one opaque entry per token."""
    return [f"kv({t})" for t in tokens]


def _demo() -> None:
    print("=== Shared prefixes are stored once ===")
    cache = RadixCache(capacity_tokens=4096)
    system = list(range(100, 130))                    # 30-token system prompt
    for suffix in ([1, 2, 3], [1, 2, 9], [4, 5, 6]):
        sequence = system + suffix
        cache.insert(sequence, _kv(sequence))

    print(cache.pretty())
    print(f"3 sequences of 33 tokens = 99 tokens if stored separately")
    print(f"actually stored: {cache.size} tokens in {cache.num_nodes()} nodes")

    print("\n=== Token-exact matching ===")
    matched, values, node = cache.match_prefix(system + [1, 2, 3])
    print(f"exact repeat:            {matched}/33 tokens matched")
    matched, _, _ = cache.match_prefix(system + [1, 2, 7])
    print(f"diverges at the last:    {matched}/33 tokens matched")
    matched, _, _ = cache.match_prefix(system + [1, 2, 3, 4, 5])
    print(f"extends a cached path:   {matched}/35 tokens matched")
    matched, _, _ = cache.match_prefix(list(range(500, 520)))
    print(f"nothing in common:       {matched}/20 tokens matched")
    print("No block quantisation: a 32-token shared prefix is worth 32 tokens,")
    print("not 'the nearest multiple of 16'.")

    print("\n=== Splitting on divergence ===")
    cache = RadixCache(capacity_tokens=4096)
    cache.insert([1, 2, 3, 4, 5, 6], _kv([1, 2, 3, 4, 5, 6]))
    print("after inserting [1..6]:")
    print(cache.pretty())
    cache.insert([1, 2, 3, 9, 9], _kv([1, 2, 3, 9, 9]))
    print("\nafter inserting [1,2,3,9,9] — the edge splits at the divergence:")
    print(cache.pretty())
    print(f"splits performed: {cache.stats['splits']}")

    print("\n=== Eviction protects shared prefixes automatically ===")
    cache = RadixCache(capacity_tokens=250)
    hot = list(range(100, 140))                        # 40-token shared prefix
    for i in range(3):
        sequence = hot + [900 + i]
        cache.insert(sequence, _kv(sequence))
    for i in range(8):                                 # cold unique traffic
        cache.match_prefix(hot + [900])                # a live request keeps it warm
        sequence = list(range(1000 + i * 100, 1000 + i * 100 + 30))
        cache.insert(sequence, _kv(sequence))

    matched, _, _ = cache.match_prefix(hot + [900])
    print(f"after 8 cold requests, the hot prefix still matches "
          f"{matched}/{len(hot) + 1} tokens")
    print(f"tokens evicted: {cache.stats['tokens_evicted']}, "
          f"cache size: {cache.size}/{cache.capacity}")
    print("Two things protected it. LRU kept the branch warm because requests")
    print("kept touching it — and the 40 shared tokens are an INTERIOR node, so")
    print("eviction could not reach them at all while any branch below survived.")

    print("\n=== Reference counting: a running request pins its path ===")
    cache = RadixCache(capacity_tokens=60)
    running = list(range(1, 51))
    node = cache.insert(running, _kv(running))
    cache.pin(node)
    print(f"pinned a 50-token running request; capacity is {cache.capacity}")
    for i in range(5):
        other = list(range(2000 + i * 20, 2000 + i * 20 + 20))
        cache.insert(other, _kv(other))
    matched, _, _ = cache.match_prefix(running)
    print(f"after 5 competing inserts, the pinned request still has "
          f"{matched}/50 tokens")
    print(f"cache holds {cache.size}/{cache.capacity} tokens, "
          f"{cache.stats['tokens_evicted']} evicted")
    print("Every one of those evictions was a NEWCOMER, not the pinned request.")
    print("Evicting KV a live request is decoding against would corrupt its")
    print("output, so the cache refuses — and effectively stops caching new")
    print("work instead. That pressure is a signal to admit fewer requests, not")
    print("to evict harder.")

    cache.unpin(node)
    cache.insert(list(range(7000, 7020)), _kv(range(7000, 7020)))
    print(f"after unpinning and one more insert: {cache.size}/{cache.capacity} tokens")

    print("\n=== Hit rate on a realistic mixed trace ===")
    cache = RadixCache(capacity_tokens=2048)
    system = list(range(100, 160))
    total = matched_total = 0
    for i in range(30):
        if i % 3 == 0:
            request = list(range(3000 + i * 40, 3000 + i * 40 + 50))   # unique
        else:
            request = system + list(range(700 + i, 700 + i + 8))       # shared
        matched, _, _ = cache.match_prefix(request)
        total += len(request)
        matched_total += matched
        cache.insert(request, _kv(request))
    print(f"token hit rate: {matched_total / total:.1%} "
          f"({matched_total}/{total} tokens served from cache)")
    print(f"tree: {cache.num_nodes()} nodes, {cache.size} tokens, "
          f"{cache.stats['tokens_evicted']} evicted")


if __name__ == "__main__":
    _demo()

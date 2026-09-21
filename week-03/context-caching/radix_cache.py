"""
Radix Tree Prefix Cache (RadixAttention) — From Scratch
=======================================================
The scheme SGLang calls RadixAttention. Sequences live in a radix tree: shared
prefixes are stored once, on a shared path, and diverge exactly where the token
streams diverge.

Build it to understand:
- Token-exact matching, with no block quantisation
- Why "only leaves are evictable" makes protecting shared prefixes automatic
- Node splitting, and where reference counts have to go when you split
- Why a cache that refuses to evict is sometimes behaving correctly

Learning Path:
1. Implement match_prefix — walk edges, allow a partial match inside one
2. Implement insert, including the split when a sequence diverges mid-edge
3. Implement LRU eviction over leaves only
4. Implement pin/unpin up the ancestor chain
5. Measure hit rates and compare with prefix_cache.py on the same traffic

Background:
  Each edge holds a run of tokens and their KV entries. Walking from the root
  spells out a cached sequence. Two sequences sharing a 300-token system prompt
  share one 300-token edge — stored once, matched in full.

  Versus fixed-size block hashing:
    + Exact token granularity: a 60-token shared prefix is worth 60 tokens
    + Shared prefixes are physically shared, so eviction can reason about them
    - Splitting is more bookkeeping than a hash lookup
    - Pointer chasing costs more per lookup than one hash

  The eviction rule is the elegant part. An interior node is a prefix that some
  longer cached sequence still needs, so restricting eviction to leaves means
  "never evict a shared prefix" falls out of the data structure rather than
  being a heuristic you have to tune.
"""

from typing import Dict, List, Optional, Sequence, Tuple


class RadixNode:
    """One edge of the radix tree: a run of tokens and their KV entries."""

    __slots__ = ("key", "value", "children", "parent", "ref_count", "last_used")

    def __init__(self, key: Optional[List[int]] = None,
                 value: Optional[List[object]] = None,
                 parent: Optional["RadixNode"] = None):
        self.key: List[int] = key or []          # tokens on the edge into this node
        self.value: List[object] = value or []   # one KV entry per token
        self.children: Dict[int, "RadixNode"] = {}
        self.parent = parent
        self.ref_count = 0
        self.last_used = 0

    @property
    def is_leaf(self) -> bool:
        return not self.children


def _common_prefix_len(a: Sequence[int], b: Sequence[int]) -> int:
    """TODO: how many leading elements the two sequences share."""
    raise NotImplementedError


class RadixCache:
    """Token-level prefix cache with LRU eviction and reference counting."""

    def __init__(self, capacity_tokens: int = 4096):
        self.root = RadixNode()
        self.capacity = capacity_tokens
        self.size = 0                  # cached tokens currently held
        self.clock = 0
        self.stats = {"lookups": 0, "tokens_matched": 0, "tokens_inserted": 0,
                      "tokens_evicted": 0, "splits": 0}

    # -- Step 1 -------------------------------------------------------------

    def match_prefix(self, tokens: Sequence[int]
                     ) -> Tuple[int, List[object], Optional[RadixNode]]:
        """Longest cached prefix. Returns (length, KV entries, last node).

        TODO:
        1. Start at the root with index = 0.
        2. Look up the child keyed by tokens[index]. Stop if there is none.
        3. shared = _common_prefix_len(child.key, tokens[index:])
           Collect child.value[:shared], advance index by shared, touch
           last_used.
        4. If shared < len(child.key) the match ended INSIDE this edge — stop.
           Otherwise continue from that child.

        A partial match needs no split. Splitting is an insert-time concern.
        """
        raise NotImplementedError

    # -- Step 2 -------------------------------------------------------------

    def insert(self, tokens: Sequence[int], values: Sequence[object]) -> RadixNode:
        """Insert a sequence with one KV entry per token; return the leaf.

        TODO:
        1. Walk as in match_prefix.
        2. No child for tokens[index]: attach a new node holding the whole
           remainder, add its length to self.size, evict if needed, return it.
        3. Child matches its entire key: descend and continue.
        4. Child matches partially: _split it at the divergence point, then
           continue from the newly created head node.
        """
        raise NotImplementedError

    def _split(self, parent: RadixNode, child: RadixNode, at: int) -> None:
        """Break `child`'s edge at offset `at`, inserting an intermediate node.

        TODO:
        1. head = RadixNode(child.key[:at], child.value[:at], parent)
        2. Trim child to key[at:] / value[at:], reparent it under head.
        3. head.children[child.key[0]] = child
        4. parent.children[head.key[0]] = head

        Careful with what moves and what stays. The tail keeps the original
        node's children and its reference count — it is still the same suffix.
        The head must INHERIT that reference count too: a pin marks every node
        on a path, and the head is now on that path. Leave it at zero and the
        compaction in _remove will happily merge a pinned child into an
        unpinned parent, silently dropping the pin.
        """
        raise NotImplementedError

    # -- Step 3 -------------------------------------------------------------

    def _evict_if_needed(self) -> None:
        """TODO: while size > capacity, evict the LRU leaf. Stop when no leaf
        is evictable — leaving data uncached is better than corrupting a live
        request."""
        raise NotImplementedError

    def _lru_leaf(self) -> Optional[RadixNode]:
        """TODO: walk the tree; among nodes that are leaves, not the root, and
        have ref_count == 0, return the one with the smallest last_used."""
        raise NotImplementedError

    def _remove(self, node: RadixNode) -> None:
        """TODO: unlink from the parent, subtract its length from size.

        Then a compaction step: if the parent is now down to exactly one child,
        and BOTH the parent and that child are unreferenced, merge the child
        back into the parent (concatenate key and value, adopt the
        grandchildren, fix their parent pointers). Without compaction the tree
        accumulates single-child chains and lookups get slower over time;
        without the both-unreferenced check, the merged node inherits the
        parent's count and a pin goes missing.
        """
        raise NotImplementedError

    # -- Step 4 -------------------------------------------------------------

    def pin(self, node: Optional[RadixNode]) -> None:
        """TODO: increment ref_count on the node AND every ancestor up to the
        root. Pinning only the leaf leaves the shared prefix evictable, which
        is exactly the state you were trying to prevent."""
        raise NotImplementedError

    def unpin(self, node: Optional[RadixNode]) -> None:
        raise NotImplementedError

    # -- inspection ---------------------------------------------------------

    def num_nodes(self) -> int:
        raise NotImplementedError

    def pretty(self, node: Optional[RadixNode] = None, depth: int = 0) -> str:
        """TODO: an indented dump of the tree. Worth the effort — almost every
        bug in this file is obvious the moment you can see the shape."""
        raise NotImplementedError


def _demo() -> None:
    """Once implemented, demonstrate each of these:

    1. Insert three sequences sharing a 30-token prefix. Stored size should be
       ~37 tokens, not 99. Print the tree and look at the shape.

    2. Match variations: an exact repeat (full match), a sequence diverging at
       the last token (n-1 matched), an extension of a cached path (matches the
       cached part), and something unrelated (0).

    3. Insert [1..6] then [1,2,3,9,9]. The first edge splits into [1,2,3] with
       children [4,5,6] and [9,9]. Print before and after.

    4. Eviction: a hot 40-token prefix with three branches, plus cold unique
       traffic. Keep touching the hot branch. It survives — partly through LRU,
       and partly because the shared 40 tokens are an interior node that
       eviction cannot reach at all.

    5. Pinning: pin a 50-token request in a 60-token cache, then insert five
       more sequences. All 50 pinned tokens must survive, and every eviction
       must have fallen on a NEWCOMER instead. The cache has effectively
       stopped caching new work — which is the signal to admit fewer requests,
       not to evict harder. Then unpin and confirm the data becomes evictable
       again.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

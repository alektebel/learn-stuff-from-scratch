"""
Block-Hash Prefix Caching — From Scratch
=========================================
The scheme vLLM calls "automatic prefix caching".

Build it to understand:
- Why a block's hash must cover its entire prefix, not just its own tokens
- Why one changed token invalidates everything after it
- The block-size trade-off: metadata versus match granularity
- What else besides tokens has to be in the cache key (and what happens if it
  is not)

Learning Path:
1. Implement block_hash with prefix chaining
2. Implement hash_blocks (full blocks only)
3. Implement PrefixCache.match_prefix — a CONTIGUOUS run from block 0
4. Implement insert with LRU eviction and reference counting
5. Measure hit rates across block sizes, capacities and traffic patterns

Background:
  Chunk the token sequence into fixed-size blocks. Block i's hash covers
  (hash of block i-1, block i's tokens), so the key means "this block, in this
  exact context".

  Hashing a block's own tokens alone is the classic bug. The KV values in a
  block depend on every token to its left, so ["the", "cat"] appearing in two
  different documents produces different K/V — matching them would splice one
  sequence's hidden state into another and quietly corrupt the output.

  Compared with the radix tree in radix_cache.py: hashing is O(1) per block and
  needs no tree bookkeeping, but it quantises matches to block boundaries. A
  60-token shared prefix with block size 64 yields no hit at all.
"""

import hashlib
from typing import Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Step 1-2: Hashing
# ---------------------------------------------------------------------------

def block_hash(prev_hash: Optional[str], tokens: Sequence[int],
               extra: str = "") -> str:
    """Hash of (everything before this block, this block's tokens).

    TODO: build a payload string from prev_hash (or a "ROOT" sentinel), `extra`,
    and the comma-joined tokens; return a truncated sha256 hex digest.

    `extra` carries anything else the KV values depend on: LoRA adapter id,
    image inputs, anything that changes the forward pass. Leaving it out is how
    a cache serves one tenant's hidden state to another — and it will not look
    like a cache bug when it happens, it will look like the model hallucinating.
    """
    raise NotImplementedError


def hash_blocks(tokens: Sequence[int], block_size: int,
                extra: str = "") -> List[Tuple[str, List[int]]]:
    """Split into FULL blocks and chain their hashes.

    TODO: walk the token list in steps of block_size, stopping before any
    partial trailing block, chaining each hash from the previous one.

    Why full blocks only: a partial block is still being written, and its hash
    would change as tokens arrive. Caching it would produce a key that no longer
    describes its contents.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 3-4: The cache
# ---------------------------------------------------------------------------

class CachedBlock:
    __slots__ = ("hash", "tokens", "kv", "ref_count", "last_used")

    def __init__(self, hash_: str, tokens: List[int], kv: object):
        self.hash = hash_
        self.tokens = tokens
        self.kv = kv                # stands in for the real KV tensors
        self.ref_count = 0
        self.last_used = 0


class PrefixCache:
    """A hash table of blocks with LRU eviction and reference counting."""

    def __init__(self, block_size: int = 16, capacity_blocks: int = 64):
        self.block_size = block_size
        self.capacity = capacity_blocks
        self.blocks: Dict[str, CachedBlock] = {}
        self.clock = 0
        self.stats = {"lookups": 0, "block_hits": 0, "block_misses": 0,
                      "evictions": 0, "tokens_saved": 0, "tokens_computed": 0}

    def match_prefix(self, tokens: Sequence[int],
                     extra: str = "") -> Tuple[List[CachedBlock], int]:
        """Longest CONTIGUOUS run of cached blocks from the start.

        TODO:
        1. Walk hash_blocks(tokens, block_size, extra) in order.
        2. Look each hash up. On a miss, BREAK — do not continue scanning.
        3. On a hit, touch last_used and collect the block.
        4. Return (blocks, len(blocks) * block_size).

        Step 2 is the one people get wrong. Later blocks may be present in the
        table, but their hashes were chained against a different prefix, so a
        match there would be a collision rather than a real hit.
        """
        raise NotImplementedError

    def insert(self, tokens: Sequence[int], kv_factory, extra: str = "") -> int:
        """Cache every full block of this sequence; return how many were added.

        TODO: for each (hash, block_tokens), skip if already present (but touch
        it), otherwise make room and store a new CachedBlock.
        """
        raise NotImplementedError

    def _make_room(self, needed: int) -> None:
        """Evict LRU blocks until `needed` more will fit.

        TODO: consider only blocks with ref_count == 0; evict the one with the
        smallest last_used. Raise if everything is pinned.

        Reference counting, not LRU order, is what protects a live request:
        evicting KV that a running sequence is decoding against corrupts its
        output, and LRU alone will happily do that to a long-running request.
        """
        raise NotImplementedError

    def pin(self, blocks: List[CachedBlock]) -> None:
        raise NotImplementedError

    def unpin(self, blocks: List[CachedBlock]) -> None:
        raise NotImplementedError

    def record_request(self, tokens: Sequence[int], matched_tokens: int) -> None:
        """TODO: accumulate tokens_saved and tokens_computed."""
        raise NotImplementedError

    @property
    def hit_rate(self) -> float:
        """TODO: tokens_saved / (tokens_saved + tokens_computed).

        Measure hit rate in TOKENS, not requests. A request that reuses 95% of a
        long prompt and one that reuses 5% are not the same event, and a
        per-request rate hides the difference.
        """
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self.blocks)


def simulate(requests: List[List[int]], block_size: int,
             capacity_blocks: int = 1_000_000) -> Dict[str, float]:
    """TODO: run a trace through a fresh cache — match, record, insert — and
    return the hit rate, block count and eviction count."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, produce and explain each of these:

    1. Block-size sweep over 20 requests sharing a 60-token system prompt.
       Expect roughly: size 1 -> 90%, 16 -> 72%, 32 -> 48%, 64 -> 0%.
       The last one is the lesson: a 60-token prefix never fills a 64-token
       block, so nothing is ever cached.

    2. Cache a 32-token sequence, change ONE token at position 12, and match
       again. Only the first 3 blocks (12 tokens) can be reused, even though
       blocks 4-7 are still sitting in the table.

    3. A 5-turn chat where each turn extends the previous prefix. Hit rate
       should climb past 80% by turn 5. This is the highest-value case for
       prefix caching in practice.

    4. Capacity sweep on mixed traffic (shared prefix + unique long requests).
       Watch the unique requests evict the shared prefix under plain LRU. Then
       ask: what policy would protect it? (radix_cache.py answers this.)

    5. Insert with extra="lora=A", match with extra="lora=B". Zero hits — as it
       must be. Now imagine you had left `extra` out of the hash.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

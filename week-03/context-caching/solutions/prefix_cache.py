"""
Block-Hash Prefix Caching — Complete Solution

The scheme vLLM calls "automatic prefix caching": chunk the token sequence into
fixed-size blocks, give each block a hash that covers its entire prefix, and key
the cache on that hash.
"""

import hashlib
from typing import Dict, List, Optional, Sequence, Tuple


def block_hash(prev_hash: Optional[str], tokens: Sequence[int],
               extra: str = "") -> str:
    """Hash of (everything before this block, this block's tokens).

    Chaining the previous hash is what makes the key mean "this block, in this
    exact context". Hashing the block's tokens alone would let block ["the",
    "cat"] match anywhere it appears, and its KV values depend on every token
    to its left — you would be splicing in state from a different sequence.

    `extra` carries anything else the KV values depend on: LoRA adapter id,
    image inputs, sampling parameters that alter the forward pass. Leaving it
    out is how a cache silently serves one tenant's state to another.
    """
    payload = f"{prev_hash or 'ROOT'}|{extra}|{','.join(map(str, tokens))}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def hash_blocks(tokens: Sequence[int], block_size: int,
                extra: str = "") -> List[Tuple[str, List[int]]]:
    """Split into full blocks and chain their hashes.

    Only *full* blocks are hashed. A partial trailing block is still being
    written and its hash would change as tokens arrive, so it is never cached.
    """
    result: List[Tuple[str, List[int]]] = []
    prev: Optional[str] = None
    for start in range(0, len(tokens) - block_size + 1, block_size):
        block = list(tokens[start:start + block_size])
        prev = block_hash(prev, block, extra)
        result.append((prev, block))
    return result


class CachedBlock:
    __slots__ = ("hash", "tokens", "kv", "ref_count", "last_used")

    def __init__(self, hash_: str, tokens: List[int], kv: object):
        self.hash = hash_
        self.tokens = tokens
        self.kv = kv                  # stands in for the real KV tensors
        self.ref_count = 0
        self.last_used = 0

    def __repr__(self) -> str:
        return f"<Block {self.hash[:8]} refs={self.ref_count}>"


class PrefixCache:
    """A hash table of blocks with LRU eviction and reference counting.

    Two rules that are easy to get wrong:

    1. A prefix match must be a *contiguous run from block 0*. The moment one
       block misses, everything after it misses too, even if those later blocks
       happen to be in the table — their hashes were computed against a
       different prefix, so a hit there would be a hash collision, not a match.
    2. A block in use by a live request must never be evicted. Reference
       counting, not LRU order, is what guarantees that.
    """

    def __init__(self, block_size: int = 16, capacity_blocks: int = 64):
        self.block_size = block_size
        self.capacity = capacity_blocks
        self.blocks: Dict[str, CachedBlock] = {}
        self.clock = 0
        self.stats = {"lookups": 0, "block_hits": 0, "block_misses": 0,
                      "evictions": 0, "tokens_saved": 0, "tokens_computed": 0}

    # -- lookup -------------------------------------------------------------

    def match_prefix(self, tokens: Sequence[int],
                     extra: str = "") -> Tuple[List[CachedBlock], int]:
        """Longest run of cached blocks from the start. Returns (blocks, tokens).

        The token count is what the scheduler cares about: it is how much
        prefill it gets to skip.
        """
        self.stats["lookups"] += 1
        self.clock += 1
        matched: List[CachedBlock] = []
        for hash_, _ in hash_blocks(tokens, self.block_size, extra):
            block = self.blocks.get(hash_)
            if block is None:
                self.stats["block_misses"] += 1
                break                      # a gap ends the match, always
            block.last_used = self.clock
            matched.append(block)
            self.stats["block_hits"] += 1
        return matched, len(matched) * self.block_size

    # -- insertion ----------------------------------------------------------

    def insert(self, tokens: Sequence[int], kv_factory, extra: str = "") -> int:
        """Cache every full block of this sequence. Returns blocks added."""
        self.clock += 1
        added = 0
        for index, (hash_, block_tokens) in enumerate(
                hash_blocks(tokens, self.block_size, extra)):
            if hash_ in self.blocks:
                self.blocks[hash_].last_used = self.clock
                continue
            self._make_room(1)
            block = CachedBlock(hash_, block_tokens, kv_factory(index, block_tokens))
            block.last_used = self.clock
            self.blocks[hash_] = block
            added += 1
        return added

    # -- eviction -----------------------------------------------------------

    def _make_room(self, needed: int) -> None:
        while len(self.blocks) + needed > self.capacity:
            evictable = [b for b in self.blocks.values() if b.ref_count == 0]
            if not evictable:
                raise RuntimeError("cache full and every block is pinned")
            victim = min(evictable, key=lambda b: b.last_used)
            del self.blocks[victim.hash]
            self.stats["evictions"] += 1

    def pin(self, blocks: List[CachedBlock]) -> None:
        for block in blocks:
            block.ref_count += 1

    def unpin(self, blocks: List[CachedBlock]) -> None:
        for block in blocks:
            block.ref_count = max(0, block.ref_count - 1)

    # -- accounting ---------------------------------------------------------

    def record_request(self, tokens: Sequence[int], matched_tokens: int) -> None:
        self.stats["tokens_saved"] += matched_tokens
        self.stats["tokens_computed"] += len(tokens) - matched_tokens

    @property
    def hit_rate(self) -> float:
        total = self.stats["tokens_saved"] + self.stats["tokens_computed"]
        return self.stats["tokens_saved"] / total if total else 0.0

    def __len__(self) -> int:
        return len(self.blocks)


def simulate(requests: List[List[int]], block_size: int,
             capacity_blocks: int = 1_000_000) -> Dict[str, float]:
    """Run a request trace through the cache and report the token hit rate."""
    cache = PrefixCache(block_size=block_size, capacity_blocks=capacity_blocks)
    for tokens in requests:
        matched, matched_tokens = cache.match_prefix(tokens)
        cache.record_request(tokens, matched_tokens)
        cache.insert(tokens, kv_factory=lambda i, t: None)
    return {"hit_rate": cache.hit_rate, "blocks": len(cache),
            "evictions": cache.stats["evictions"]}


def _demo() -> None:
    system = list(range(100, 160))          # 60-token shared system prompt
    print(f"shared system prompt: {len(system)} tokens")

    print("\n=== Prefix hit rate with a shared system prompt ===")
    requests = [system + [900 + i, 901 + i, 902 + i] for i in range(20)]
    print(f"{'block size':>12}{'hit rate':>12}{'blocks stored':>16}")
    for block_size in (1, 8, 16, 32, 64):
        result = simulate(requests, block_size)
        print(f"{block_size:>12}{result['hit_rate']:>11.1%}{result['blocks']:>16}")
    print("Large blocks store less metadata but quantise the match: with block")
    print("size 64 a 60-token shared prefix produces no full block at all, and")
    print("the hit rate collapses to zero.")

    print("\n=== A gap in the middle kills everything after it ===")
    cache = PrefixCache(block_size=4, capacity_blocks=64)
    base = list(range(1, 33))
    cache.insert(base, kv_factory=lambda i, t: f"kv{i}")
    variant = base[:12] + [999] + base[13:]     # one token changed at position 12
    matched, tokens = cache.match_prefix(variant)
    print(f"cached a 32-token sequence, then changed token 12")
    print(f"blocks reused: {len(matched)} ({tokens} tokens of 32)")
    print("Blocks 4-7 are still in the table, but their hashes were chained")
    print("against the OLD block 3. They can never match this sequence.")

    print("\n=== Chat: each turn extends the previous prefix ===")
    cache = PrefixCache(block_size=8, capacity_blocks=256)
    conversation: List[int] = list(range(100, 116))
    for turn in range(1, 6):
        conversation += list(range(200 + turn * 20, 200 + turn * 20 + 12))
        matched, matched_tokens = cache.match_prefix(conversation)
        cache.record_request(conversation, matched_tokens)
        cache.insert(conversation, kv_factory=lambda i, t: None)
        print(f"  turn {turn}: {len(conversation):3d} tokens, "
              f"{matched_tokens:3d} cached ({matched_tokens / len(conversation):5.1%}), "
              f"{len(conversation) - matched_tokens:3d} to prefill")
    print(f"overall token hit rate: {cache.hit_rate:.1%}")
    print("This is the single highest-value case for prefix caching: multi-turn")
    print("chat re-sends the whole history on every turn.")

    print("\n=== Capacity pressure and eviction ===")
    print(f"{'capacity':>10}{'hit rate':>12}{'evictions':>12}")
    mixed = [system + [900 + i] * 4 for i in range(10)]
    mixed += [list(range(5000 + i * 50, 5000 + i * 50 + 60)) for i in range(10)]
    mixed += [system + [910 + i] * 4 for i in range(10)]
    for capacity in (4, 16, 64, 256):
        result = simulate(mixed, block_size=8, capacity_blocks=capacity)
        print(f"{capacity:>10}{result['hit_rate']:>11.1%}{result['evictions']:>12}")
    print("The unique long requests in the middle evict the shared prefix under")
    print("LRU. A frequency- or prefix-aware policy would protect it — which is")
    print("what the radix tree in radix_cache.py makes cheap to express.")

    print("\n=== Isolation ===")
    cache = PrefixCache(block_size=4, capacity_blocks=64)
    cache.insert(base, kv_factory=lambda i, t: "tenant-a-kv", extra="lora=A")
    _, hit_a = cache.match_prefix(base, extra="lora=A")
    _, hit_b = cache.match_prefix(base, extra="lora=B")
    print(f"same tokens, adapter A: {hit_a} tokens matched")
    print(f"same tokens, adapter B: {hit_b} tokens matched")
    print("Anything that changes the forward pass must be in the hash. If it is")
    print("not, you will serve one request's hidden state to another.")


if __name__ == "__main__":
    _demo()

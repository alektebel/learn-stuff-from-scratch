"""
Progress checker for the context-caching templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

Each check exercises the functions you implement in the template files. A check
that raises NotImplementedError is reported as TODO (not a failure) — that is
simply the next thing to write.

Nothing here imports solutions/. It tests YOUR code.
"""

import math
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
# Step 1-4: kv_cache.py
# ---------------------------------------------------------------------------

def check_linalg() -> None:
    from kv_cache import add, dot, matmul, matvec, scale, softmax, transpose

    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    assert matmul(a, b) == [[19.0, 22.0], [43.0, 50.0]], \
        f"matmul is wrong: {matmul(a, b)}"
    assert transpose(a) == [[1.0, 3.0], [2.0, 4.0]], f"transpose: {transpose(a)}"
    assert matvec(a, [1.0, 1.0]) == [3.0, 7.0], f"matvec: {matvec(a, [1.0, 1.0])}"

    # Non-square, to catch a transposed-index bug that squares hide.
    assert matmul([[1.0, 2.0, 3.0]], [[1.0], [2.0], [3.0]]) == [[14.0]], \
        "matmul fails on non-square shapes"

    probs = softmax([1.0, 2.0, 3.0])
    assert abs(sum(probs) - 1.0) < 1e-12, f"softmax does not sum to 1: {sum(probs)}"
    assert probs[2] > probs[1] > probs[0], "softmax must preserve order"
    assert softmax([0.0, 0.0]) == [0.5, 0.5], "softmax of equal logits is uniform"

    big = softmax([1000.0, 1001.0, 1002.0])
    assert abs(sum(big) - 1.0) < 1e-12 and not any(math.isnan(p) for p in big), (
        "softmax overflowed on large logits — subtract the max BEFORE "
        "exponentiating")

    assert dot([1.0, 2.0], [3.0, 4.0]) == 11.0
    assert scale([1.0, 2.0], 3.0) == [3.0, 6.0]
    assert add([1.0, 2.0], [3.0, 4.0]) == [4.0, 6.0]


def check_kv_cache_object() -> None:
    from kv_cache import KVCache

    cache = KVCache()
    for i in range(5):
        cache.append([float(i)] * 4, [float(-i)] * 4)
    assert len(cache) == 5, f"len(cache) is {len(cache)}"

    cache.extend([[9.0] * 4], [[9.0] * 4])
    assert len(cache) == 6, "extend must append multiple tokens"

    clone = cache.clone()
    clone.append([0.0] * 4, [0.0] * 4)
    assert len(cache) == 6, "clone() is not deep — the original grew too"
    clone.keys[0][0] = 999.0
    assert cache.keys[0][0] != 999.0, (
        "clone() shares row objects with the original. A fork that mutates its "
        "parent's KV corrupts both requests.")

    cache.truncate(3)
    assert len(cache) == 3 and len(cache.values) == 3, \
        f"truncate(3) left {len(cache)} keys and {len(cache.values)} values"
    assert cache.keys[2][0] == 2.0, "truncate kept the wrong tokens"

    assert cache.memory_bytes(dtype_size=2) == 2 * 3 * 4 * 2, \
        f"memory_bytes returned {cache.memory_bytes(dtype_size=2)}"


def check_attention_exactness() -> None:
    from kv_cache import (KVCache, OpCounter, SelfAttention,
                          _pseudo_random_matrix)

    d_model = 16
    counter = OpCounter()
    attention = SelfAttention(d_model, seed=1, counter=counter)
    tokens = [_pseudo_random_matrix(1, d_model, 100 + i)[0] for i in range(10)]

    full = attention.forward_full(tokens)
    assert len(full) == 10 and len(full[0]) == d_model, \
        f"forward_full returned shape {len(full)}x{len(full[0])}"

    cache = KVCache()
    incremental = [attention.forward_incremental(t, cache) for t in tokens]
    assert len(cache) == 10, "forward_incremental must append to the cache"

    error = max(abs(a - b)
                for row_a, row_b in zip(full, incremental)
                for a, b in zip(row_a, row_b))
    assert error == 0.0, (
        f"cached and uncached attention differ by {error:.3e} — it must be "
        "EXACTLY 0.\n"
        "      The usual causes: forward_incremental uses x @ W where it needs "
        "W^T x\n"
        "      (the full path is row-vector convention), or K/V are appended "
        "AFTER\n"
        "      computing scores so the token cannot attend to itself.")

    # The causal mask: token 0 attends only to itself, so its output must equal
    # its own value vector regardless of what follows it.
    shorter = attention.forward_full(tokens[:3])
    assert all(abs(a - b) < 1e-12 for a, b in zip(full[0], shorter[0])), (
        "output for token 0 changed when later tokens were added — your mask "
        "is letting positions attend to the FUTURE")


def check_prefill_and_cost() -> None:
    from kv_cache import (KVCache, OpCounter, SelfAttention,
                          _pseudo_random_matrix, attention_cost)

    d_model = 16
    attention = SelfAttention(d_model, seed=1, counter=OpCounter())
    tokens = [_pseudo_random_matrix(1, d_model, 200 + i)[0] for i in range(8)]

    cache = KVCache()
    out = attention.prefill(tokens, cache)
    assert len(cache) == 8, f"prefill left {len(cache)} tokens in the cache"

    full = attention.forward_full(tokens)
    error = max(abs(a - b) for ra, rb in zip(full, out) for a, b in zip(ra, rb))
    assert error < 1e-12, f"prefill disagrees with forward_full by {error:.3e}"

    # Prefill onto a cache that already holds a reused prefix.
    warm = KVCache()
    attention.prefill(tokens[:5], warm)
    attention.prefill(tokens[5:], warm)
    assert len(warm) == 8, (
        "prefill must EXTEND an existing cache, not replace it — that is what "
        "makes prefix reuse possible")

    cheap = attention_cost(128, 128, 4096, cached=True)
    dear = attention_cost(128, 128, 4096, cached=False)
    assert dear > cheap * 20, (
        f"uncached/cached cost ratio is only {dear / cheap:.1f}x at a 128-token "
        "prompt; expect roughly 95x")
    long_ratio = (attention_cost(4096, 256, 4096, cached=False)
                  / attention_cost(4096, 256, 4096, cached=True))
    assert long_ratio > dear / cheap, \
        "the cache advantage must GROW with prefix length"


# ---------------------------------------------------------------------------
# Step 5-7: tiny_transformer.py
# ---------------------------------------------------------------------------

def check_model_blocks() -> None:
    from tiny_transformer import gelu, layer_norm

    out = layer_norm([1.0, 2.0, 3.0, 4.0])
    assert abs(sum(out)) < 1e-9, f"layer_norm output should have mean 0, got {sum(out)}"
    variance = sum(v * v for v in out) / len(out)
    assert abs(variance - 1.0) < 1e-3, \
        f"layer_norm output should have unit variance, got {variance:.4f}"
    assert layer_norm([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0] or \
        all(abs(v) < 1e-6 for v in layer_norm([5.0, 5.0, 5.0])), \
        "layer_norm must not divide by zero on constant input (use eps)"

    assert abs(gelu(0.0)) < 1e-12, f"gelu(0) should be 0, got {gelu(0.0)}"
    assert gelu(10.0) > 9.9, f"gelu(10) should be ~10, got {gelu(10.0)}"
    assert -0.2 < gelu(-10.0) <= 0.0, f"gelu(-10) should be ~0, got {gelu(-10.0)}"


def check_generation_matches() -> None:
    from kv_cache import OpCounter
    from tiny_transformer import CORPUS, CharTokenizer, TinyTransformer

    tokenizer = CharTokenizer(CORPUS)
    counter = OpCounter()
    model = TinyTransformer(len(tokenizer), d_model=16, n_layer=2, n_head=2,
                            seed=7, counter=counter)
    prompt = tokenizer.encode("the quick ")

    counter.reset()
    uncached = model.generate_no_cache(prompt, max_new_tokens=10)
    uncached_macs = counter.macs

    counter.reset()
    cached, cache = model.generate(prompt, max_new_tokens=10)
    cached_macs = counter.macs

    assert len(cached) == 10, f"generate returned {len(cached)} tokens, expected 10"
    assert cached == uncached, (
        f"cached and uncached generation DIVERGED:\n"
        f"      no cache -> {uncached}\n"
        f"      KV cache -> {cached}\n"
        "      A cache that changes the output is a bug. Common causes: the "
        "wrong\n"
        "      `position` passed to forward_token when reusing a prefix, or "
        "K/V\n"
        "      appended after computing attention scores.")
    assert cached_macs < uncached_macs / 3, (
        f"the cached path used {uncached_macs / cached_macs:.1f}x less work; "
        "expect ~10x. Are you re-running the prompt on every decode step?")
    assert len(cache) == len(prompt) + 10, \
        f"the cache holds {len(cache)} tokens, expected {len(prompt) + 10}"


def check_cache_reuse() -> None:
    from tiny_transformer import CORPUS, CharTokenizer, TinyTransformer

    tokenizer = CharTokenizer(CORPUS)
    model = TinyTransformer(len(tokenizer), d_model=16, n_layer=2, n_head=2, seed=7)

    # Truncation must reproduce an exact earlier state.
    tokens = tokenizer.encode("the quick brown")
    cache = model.new_cache()
    model.forward_sequence(tokens, cache)
    next_token = tokenizer.stoi[" "]
    logits_a = model.forward_token(next_token, len(cache), cache)

    cache.truncate(len(tokens))
    assert len(cache) == len(tokens), f"truncate left {len(cache)} tokens"
    logits_b = model.forward_token(next_token, len(cache), cache)
    error = max(abs(a - b) for a, b in zip(logits_a, logits_b))
    assert error == 0.0, (
        f"truncating and re-running gave different logits (max diff {error:.3e}). "
        "Prefix reuse is unsound until this is exactly 0 — check that truncate "
        "cuts EVERY layer and head, and the token list.")

    # clone() must isolate a fork from the shared prefix.
    shared = model.new_cache()
    model.forward_sequence(tokenizer.encode("the quick "), shared)
    before = len(shared)
    fork = shared.clone()
    model.forward_token(next_token, len(fork), fork)
    assert len(shared) == before, (
        "writing to a cloned cache also grew the original — clone() is not deep")

    # Reuse must produce the same answer as a cold run.
    prompt = tokenizer.encode("the quick brown fox ")
    cold, _ = model.generate(prompt, max_new_tokens=5)
    warm_cache = model.new_cache()
    model.forward_sequence(prompt[:10], warm_cache)
    warm, _ = model.generate(prompt, max_new_tokens=5, cache=warm_cache)
    assert cold == warm, (
        f"generating from a warm cache gave {warm} but a cold run gave {cold}. "
        "generate() must run only prompt[len(cache):], at the right positions.")


# ---------------------------------------------------------------------------
# Step 8-9: prefix_cache.py
# ---------------------------------------------------------------------------

def check_block_hashing() -> None:
    from prefix_cache import block_hash, hash_blocks

    same = block_hash(None, [1, 2, 3]) == block_hash(None, [1, 2, 3])
    assert same, "block_hash must be deterministic"
    assert block_hash(None, [1, 2, 3]) != block_hash("abc", [1, 2, 3]), (
        "the previous hash must change the result — otherwise a block matches "
        "in ANY context, and its KV values depend on the whole prefix")
    assert block_hash(None, [1, 2, 3]) != block_hash(None, [1, 2, 4]), \
        "different tokens must hash differently"
    assert block_hash(None, [1, 2, 3], extra="A") != \
        block_hash(None, [1, 2, 3], extra="B"), \
        "`extra` must be part of the hash (LoRA id, images, ...)"

    blocks = hash_blocks([1, 2, 3, 4, 5, 6, 7], block_size=3)
    assert len(blocks) == 2, (
        f"hash_blocks made {len(blocks)} blocks from 7 tokens at size 3; only "
        "FULL blocks may be hashed — the partial tail is still being written")
    assert blocks[0][1] == [1, 2, 3] and blocks[1][1] == [4, 5, 6]
    assert blocks[0][0] != blocks[1][0], "chained hashes must differ"

    prefix = hash_blocks([1, 2, 3, 4, 5, 6], block_size=3)
    assert [h for h, _ in prefix] == [h for h, _ in blocks], (
        "the same leading tokens must produce the same block hashes — this is "
        "what makes a shared prefix reusable")


def check_prefix_cache() -> None:
    from prefix_cache import PrefixCache, simulate

    cache = PrefixCache(block_size=4, capacity_blocks=64)
    base = list(range(1, 33))
    cache.insert(base, kv_factory=lambda i, t: f"kv{i}")
    assert len(cache) == 8, f"inserting 32 tokens at size 4 stored {len(cache)} blocks"

    matched, tokens = cache.match_prefix(base)
    assert tokens == 32, f"an exact repeat matched only {tokens}/32 tokens"

    variant = base[:12] + [999] + base[13:]
    _, tokens = cache.match_prefix(variant)
    assert tokens == 12, (
        f"changing token 12 left {tokens} tokens matched, expected 12. "
        "A miss must STOP the scan — later blocks are still in the table but "
        "their hashes were chained against a different prefix.")

    _, tokens = cache.match_prefix(list(range(500, 520)))
    assert tokens == 0, "an unrelated sequence must match nothing"

    _, tokens = cache.match_prefix(base, extra="lora=B")
    assert tokens == 0, (
        "data inserted without `extra` must not match a lookup with a different "
        "`extra` — this is the isolation boundary between tenants")

    # Eviction and pinning.
    small = PrefixCache(block_size=4, capacity_blocks=4)
    small.insert(list(range(1, 17)), kv_factory=lambda i, t: None)
    small.insert(list(range(100, 116)), kv_factory=lambda i, t: None)
    assert len(small) <= 4, f"cache holds {len(small)} blocks, capacity is 4"
    assert small.stats["evictions"] > 0, "stats['evictions'] was not counted"

    pinned = PrefixCache(block_size=4, capacity_blocks=4)
    pinned.insert(list(range(1, 17)), kv_factory=lambda i, t: None)
    blocks, _ = pinned.match_prefix(list(range(1, 17)))
    pinned.pin(blocks)
    try:
        pinned.insert(list(range(200, 216)), kv_factory=lambda i, t: None)
        raise AssertionError(
            "inserting into a full cache whose blocks are ALL pinned must "
            "raise, not silently evict KV a live request is using")
    except RuntimeError:
        pass

    # Block size quantises the match.
    system = list(range(100, 160))          # 60 tokens
    requests = [system + [900 + i] for i in range(10)]
    assert simulate(requests, block_size=8)["hit_rate"] > 0.5, \
        "an 8-token block size should reuse most of a 60-token shared prefix"
    assert simulate(requests, block_size=64)["hit_rate"] == 0.0, (
        "with block size 64 a 60-token prefix never fills a block, so the hit "
        "rate must be exactly 0 — that is the cost of large blocks")


# ---------------------------------------------------------------------------
# Step 10-11: radix_cache.py
# ---------------------------------------------------------------------------

def check_radix_matching() -> None:
    from radix_cache import RadixCache, _common_prefix_len

    assert _common_prefix_len([1, 2, 3], [1, 2, 9]) == 2
    assert _common_prefix_len([1, 2], [1, 2, 3]) == 2
    assert _common_prefix_len([1], [9]) == 0

    cache = RadixCache(capacity_tokens=4096)
    system = list(range(100, 130))
    for suffix in ([1, 2, 3], [1, 2, 9], [4, 5, 6]):
        seq = system + suffix
        cache.insert(seq, [f"kv{t}" for t in seq])

    assert cache.size == 37, (
        f"stored {cache.size} tokens; three 33-token sequences sharing a "
        "30-token prefix should occupy 37 (30 + 2 + 1 + 1 + 3)")

    matched, values, node = cache.match_prefix(system + [1, 2, 3])
    assert matched == 33, f"exact repeat matched {matched}/33"
    assert len(values) == 33, f"got {len(values)} KV entries for {matched} tokens"
    assert values[0] == "kv100", "KV entries must come back in token order"

    assert cache.match_prefix(system + [1, 2, 7])[0] == 32, \
        "a sequence diverging at the last token should match 32"
    assert cache.match_prefix(system + [1, 2, 3, 4, 5])[0] == 33, \
        "a sequence EXTENDING a cached path should match the cached part"
    assert cache.match_prefix(list(range(500, 520)))[0] == 0, \
        "an unrelated sequence must match nothing"

    # Splitting.
    split = RadixCache(capacity_tokens=4096)
    split.insert([1, 2, 3, 4, 5, 6], ["a"] * 6)
    split.insert([1, 2, 3, 9, 9], ["b"] * 5)
    assert split.stats["splits"] == 1, \
        f"inserting a diverging sequence should split exactly 1 node, got " \
        f"{split.stats['splits']}"
    assert split.match_prefix([1, 2, 3, 4, 5, 6])[0] == 6, \
        "splitting must not lose the original sequence"
    assert split.match_prefix([1, 2, 3, 9, 9])[0] == 5, \
        "splitting must not lose the new sequence"
    assert split.size == 8, (
        f"after the split the tree holds {split.size} tokens; it should be 8 — "
        "the shared [1,2,3] is stored ONCE (3 + 3 + 2), which is the entire "
        "point of the tree")


def check_radix_eviction() -> None:
    from radix_cache import RadixCache

    cache = RadixCache(capacity_tokens=250)
    hot = list(range(100, 140))
    for i in range(3):
        seq = hot + [900 + i]
        cache.insert(seq, [f"kv{t}" for t in seq])
    for i in range(8):
        cache.match_prefix(hot + [900])            # keep the hot branch warm
        cold = list(range(1000 + i * 100, 1000 + i * 100 + 30))
        cache.insert(cold, [f"kv{t}" for t in cold])

    assert cache.size <= cache.capacity, \
        f"cache is at {cache.size}/{cache.capacity} with nothing pinned"
    assert cache.stats["tokens_evicted"] > 0, "nothing was evicted under pressure"
    assert cache.match_prefix(hot + [900])[0] == 41, (
        "the hot prefix was evicted. Two things should have protected it: LRU "
        "recency, and the fact that the shared 40 tokens are an INTERIOR node — "
        "only leaves may be evicted.")

    # Pinning beats capacity.
    pinned = RadixCache(capacity_tokens=60)
    running = list(range(1, 51))
    node = pinned.insert(running, [f"kv{t}" for t in running])
    pinned.pin(node)
    for i in range(5):
        other = list(range(2000 + i * 20, 2000 + i * 20 + 20))
        pinned.insert(other, [f"kv{t}" for t in other])
    assert pinned.match_prefix(running)[0] == 50, (
        "a pinned request lost its KV. Evicting state a live sequence is "
        "decoding against corrupts its output — pin() must mark every ancestor, "
        "not just the leaf.")
    assert pinned.size == 50 and pinned.stats["tokens_evicted"] >= 100, (
        f"cache holds {pinned.size} tokens after {pinned.stats['tokens_evicted']} "
        "evictions. Every eviction should have fallen on a NEWCOMER: the pinned "
        "50 tokens stay, and the cache effectively stops caching new work. That "
        "pressure is a signal to admit fewer requests, not to evict harder.")

    pinned.unpin(node)
    pinned.insert(list(range(7000, 7030)), ["kv"] * 30)
    assert pinned.match_prefix(running)[0] < 50, \
        "after unpinning, that data must become evictable again"


# ---------------------------------------------------------------------------
# Step 12: paged_kv_cache.py
# ---------------------------------------------------------------------------

def check_paged_blocks() -> None:
    from paged_kv_cache import BlockManager, ContiguousAllocator, OutOfMemory

    manager = BlockManager(num_blocks=16, block_size=8)
    seq = manager.allocate(1, list(range(20)))
    assert len(seq.block_table) == 3, \
        f"20 tokens at block size 8 needs 3 blocks, got {len(seq.block_table)}"
    assert manager.num_free == 13, f"{manager.num_free} blocks free, expected 13"
    assert seq.slot(0) == (seq.block_table[0], 0), "slot(0) is block 0, offset 0"
    assert seq.slot(9) == (seq.block_table[1], 1), \
        f"slot(9) should be (block 1, offset 1), got {seq.slot(9)}"

    manager.free(1)
    assert manager.num_free == 16, "free() must return every block to the pool"

    # Growth allocates lazily.
    manager = BlockManager(num_blocks=16, block_size=8)
    manager.allocate(1, list(range(8)))          # exactly one full block
    assert manager.num_free == 15
    manager.append_token(1, 99)
    assert manager.num_free == 14, "a full last block forces a new allocation"
    for _ in range(6):
        manager.append_token(1, 0)
    assert manager.num_free == 14, (
        "appending into a partially-filled block must NOT allocate — that "
        "lazy growth is why paged attention keeps memory tight")

    try:
        BlockManager(num_blocks=2, block_size=8).allocate(1, list(range(100)))
        raise AssertionError("allocate must raise OutOfMemory when short of blocks")
    except OutOfMemory:
        pass

    contiguous = ContiguousAllocator(total_tokens=4096, max_seq_len=2048)
    admitted = sum(1 for _ in range(10) if contiguous.admit())
    assert admitted == 2, f"a contiguous allocator admits 2 here, not {admitted}"

    paged = BlockManager(num_blocks=256, block_size=16)
    lengths = [120, 340, 90, 512, 75, 200, 60, 900, 45, 130]
    for i, length in enumerate(lengths):
        paged.allocate(i, list(range(length)))
    util = paged.utilization()
    assert util["internal_waste"] < 0.10, (
        f"paged waste is {util['internal_waste']:.1%}; it should be under 10% "
        "(at most one partial block per sequence)")


def check_fork_and_cow() -> None:
    from paged_kv_cache import BlockManager

    manager = BlockManager(num_blocks=64, block_size=16)
    manager.allocate(1, list(range(200)))
    blocks_used = len(manager.sequences[1].block_table)
    before = manager.num_free

    for child in (2, 3, 4):
        manager.fork(1, child)
    assert manager.num_free == before, (
        f"forking consumed {before - manager.num_free} blocks; it must consume "
        "ZERO — a fork copies the block TABLE, not the KV data")
    assert manager.shared_block_count() == blocks_used, \
        "every block of the parent should now be shared"
    assert manager.sequences[2].tokens == manager.sequences[1].tokens, \
        "a fork inherits the parent's tokens"

    manager.append_token(2, 999)
    assert manager.stats["cow_copies"] == 1, (
        f"{manager.stats['cow_copies']} copy-on-write copies; exactly 1 block "
        "(the shared partial tail) should have been copied")
    assert manager.sequences[2].block_table[-1] != \
        manager.sequences[1].block_table[-1], \
        "after copy-on-write the fork must point at its own block"
    assert manager.sequences[2].block_table[:-1] == \
        manager.sequences[1].block_table[:-1], \
        "the shared prefix blocks must stay shared"
    assert len(manager.sequences[1].tokens) == 200, (
        "appending to the fork changed the PARENT's tokens — the copy-on-write "
        "check (ref_count > 1) is missing or running too late")

    # Reference counting on release.
    shared_block = manager.sequences[1].block_table[0]
    manager.free(2)
    manager.free(3)
    assert manager.blocks[shared_block].ref_count > 0, \
        "a block shared by several sequences must survive some of them ending"
    manager.free(1)
    manager.free(4)
    assert manager.blocks[shared_block].ref_count == 0, \
        "once every holder is gone the block must return to the free pool"


# ---------------------------------------------------------------------------
# Step 13: semantic_cache.py
# ---------------------------------------------------------------------------

def check_response_caches() -> None:
    from semantic_cache import (EVAL_PAIRS, ExactCache, SemanticCache, cosine,
                                embed, evaluate_threshold, tokenize)

    assert tokenize("Hello, World!") == ["hello", "world"], \
        f"tokenize gave {tokenize('Hello, World!')}"

    vector = embed("hello world")
    assert abs(math.sqrt(sum(v * v for v in vector)) - 1.0) < 1e-9, \
        "embed must return an L2-normalised vector"
    assert abs(cosine(vector, vector) - 1.0) < 1e-9, \
        "a vector's cosine with itself must be 1"
    assert cosine(embed("reset my password"), embed("quantum physics")) < 0.6, \
        "unrelated texts should not score highly"

    cache = ExactCache(capacity=10, ttl_seconds=60)
    assert cache.get("hi", now=1000.0) is None, "an empty cache must miss"
    cache.put("hi", "hello", now=1000.0)
    assert cache.get("hi", now=1000.0) == "hello", "exact repeat must hit"
    assert cache.get("hi", now=1030.0) == "hello", "still inside the TTL"
    assert cache.get("hi", now=1100.0) is None, "past the TTL it must expire"

    cache.put("q", "a1", model="m1", now=2000.0)
    assert cache.get("q", model="m2", now=2000.0) is None, (
        "the model must be part of the key — the same prompt gives different "
        "answers on different models")
    assert cache.get("q", model="m1", temperature=0.7, now=2000.0) is None, \
        "sampling parameters must be part of the key too"

    small = ExactCache(capacity=2, ttl_seconds=1e9)
    for i in range(5):
        small.put(f"p{i}", f"r{i}", now=3000.0 + i)
    assert len(small.entries) <= 2, f"capacity 2 but holds {len(small.entries)}"

    semantic = SemanticCache(threshold=0.99)
    semantic.put("how do I reset my password", "click reset", now=1000.0)
    hit, similarity, _ = semantic.get("how do I reset my password", now=1000.0)
    assert hit == "click reset", "an identical prompt must hit at any threshold"
    assert similarity > 0.99

    miss, _, _ = semantic.get("what is the capital of France", now=1000.0)
    assert miss is None, "an unrelated prompt must miss"

    strict = evaluate_threshold(0.99)
    loose = evaluate_threshold(0.80)
    assert loose["hits"] >= strict["hits"], \
        "a lower threshold cannot produce fewer hits"
    assert strict["wrong_answers"] > 0, (
        "even at threshold 0.99 some EVAL_PAIRS should still be answered "
        "wrongly — pairs like 'Paris to Rome' vs 'Rome to Paris' are lexically "
        "identical. If you see zero, check that a hit is being recorded when "
        "should_hit is False.")


# ---------------------------------------------------------------------------
# Step 14: cache_router.py
# ---------------------------------------------------------------------------

def check_routing() -> None:
    from cache_router import (Router, cache_aware, longest_prefix_match,
                              round_robin, run, skewed_traffic, uniform_traffic)

    requests = skewed_traffic(num_requests=200, num_tenants=16, system_len=300)
    assert len(requests) == 200, f"skewed_traffic returned {len(requests)} requests"
    prefixes = {tuple(r[:300]) for r in requests}
    assert 2 <= len(prefixes) <= 16, (
        f"{len(prefixes)} distinct system prompts among 200 requests; the "
        "traffic should reuse a small set of tenant prefixes")
    assert len(prefixes) > 1, "traffic with a single prefix cannot test routing"

    router = Router(num_workers=4, policy=round_robin(), cache_capacity=2500)
    ids = [router.dispatch(r)[0] for r in requests[:8]]
    assert ids == [0, 1, 2, 3, 0, 1, 2, 3], f"round robin dispatched {ids}"

    rr = run("rr", round_robin(), requests, cache_capacity=2500)
    lpm = run("lpm", longest_prefix_match(), requests, cache_capacity=2500)
    ca = run("ca", cache_aware(1.0), requests, cache_capacity=2500)

    for name, result in (("rr", rr), ("lpm", lpm), ("ca", ca)):
        assert 0.0 <= result["hit_rate"] <= 1.0, \
            f"{name} hit_rate is {result['hit_rate']}"
        assert result["makespan"] <= result["total_work"], \
            f"{name} makespan exceeds total work"

    assert lpm["hit_rate"] > rr["hit_rate"] + 0.10, (
        f"longest-prefix routing scored {lpm['hit_rate']:.1%} vs round robin's "
        f"{rr['hit_rate']:.1%}. On capacity-constrained skewed traffic it should "
        "win by a wide margin — round robin makes every worker thrash.")
    assert ca["hit_rate"] > rr["hit_rate"] + 0.10, \
        "cache-aware routing should also beat round robin substantially"
    affinity_only = run("w0", cache_aware(0.0), requests, cache_capacity=2500)
    assert affinity_only["imbalance"] > ca["imbalance"], (
        "with load_weight=0 every request should pile onto one worker, giving "
        "a much worse imbalance than load_weight=1")

    uniform = run("rr", round_robin(), uniform_traffic(num_requests=100))
    assert uniform["hit_rate"] == 0.0, \
        "traffic with no shared prefixes must produce a 0% hit rate"


# ---------------------------------------------------------------------------
# Step 15: serving_demo.py
# ---------------------------------------------------------------------------

def check_end_to_end() -> None:
    from kv_cache import OpCounter
    from serving_demo import CachedServer, chat_trace, restore, snapshot
    from tiny_transformer import CORPUS, CharTokenizer, TinyTransformer

    tokenizer = CharTokenizer(CORPUS)
    counter = OpCounter()
    model = TinyTransformer(len(tokenizer), d_model=16, n_layer=2, n_head=2,
                            max_seq=512, seed=7, counter=counter)

    # snapshot/restore must round-trip a cache exactly.
    tokens = tokenizer.encode("the quick brown")
    cache = model.new_cache()
    model.forward_sequence(tokens, cache)
    rebuilt = restore(snapshot(cache), tokens, model.n_layer, model.n_head)
    assert len(rebuilt) == len(cache), (
        f"restore produced {len(rebuilt)} tokens from a {len(cache)}-token "
        "snapshot — did you set cache.tokens as well as the K/V?")
    next_token = tokenizer.stoi[" "]
    a = model.forward_token(next_token, len(cache), cache)
    b = model.forward_token(next_token, len(rebuilt), rebuilt)
    assert max(abs(x - y) for x, y in zip(a, b)) == 0.0, \
        "a restored cache must be indistinguishable from the original"

    requests = chat_trace(tokenizer, num_conversations=2, turns=3)
    assert len(requests) == 6, f"chat_trace returned {len(requests)} requests"
    assert len(requests[1]) > len(requests[0]), \
        "each turn must extend the previous history"

    counter.reset()
    cold = CachedServer(model, enabled=False)
    cold_out = [cold.generate(r, max_new_tokens=4) for r in requests]
    cold_macs = counter.macs

    counter.reset()
    warm = CachedServer(model, cache_capacity=8192, enabled=True)
    warm_out = [warm.generate(r, max_new_tokens=4) for r in requests]
    warm_macs = counter.macs

    assert cold_out == warm_out, (
        "cached and uncached serving produced DIFFERENT output.\n"
        "      This is the one invariant that matters. Check: restore() setting "
        "cache.tokens,\n"
        "      the position index passed to forward_token, and the "
        "fully-cached-prompt\n"
        "      edge case (truncate by one rather than re-running the last "
        "token).")
    assert warm.hit_rate > 0.5, \
        f"token hit rate is only {warm.hit_rate:.1%} on a chat trace; expect >50%"
    assert warm_macs < cold_macs * 0.6, (
        f"caching saved only {1 - warm_macs / cold_macs:.1%} of the compute; "
        "expect well over 40% on this workload")

    tiny = CachedServer(model, cache_capacity=40, enabled=True)
    tiny_out = [tiny.generate(r, max_new_tokens=4) for r in requests]
    assert tiny_out == cold_out, (
        "output changed when the cache was too small to hold the working set. "
        "Eviction must never affect correctness — only speed.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("kv_cache.py", "linear algebra helpers", check_linalg),
    ("kv_cache.py", "KVCache append/truncate/clone", check_kv_cache_object),
    ("kv_cache.py", "cached == uncached attention", check_attention_exactness),
    ("kv_cache.py", "prefill and the cost model", check_prefill_and_cost),
    ("tiny_transformer.py", "layer_norm and gelu", check_model_blocks),
    ("tiny_transformer.py", "generation matches exactly", check_generation_matches),
    ("tiny_transformer.py", "truncate, clone, prefix reuse", check_cache_reuse),
    ("prefix_cache.py", "block hashing and chaining", check_block_hashing),
    ("prefix_cache.py", "matching, eviction, isolation", check_prefix_cache),
    ("radix_cache.py", "matching and node splitting", check_radix_matching),
    ("radix_cache.py", "eviction and pinning", check_radix_eviction),
    ("paged_kv_cache.py", "block allocation and growth", check_paged_blocks),
    ("paged_kv_cache.py", "forking and copy-on-write", check_fork_and_cow),
    ("semantic_cache.py", "exact and semantic caching", check_response_caches),
    ("cache_router.py", "cache-aware routing", check_routing),
    ("serving_demo.py", "capstone: identical output", check_end_to_end),
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

    print(f"\n{BOLD}Context Caching From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — context caching, end to end.{RESET}")
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

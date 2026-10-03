# Context Caching From Scratch — Solutions

Complete, runnable implementations of every template in the parent directory. Pure
Python 3 standard library — no numpy, no PyTorch, no GPU.

```bash
python3 kv_cache.py           # ~0.3s   attention with and without a cache
python3 tiny_transformer.py   # ~1.4s   a real model, cached and uncached
python3 prefix_cache.py       # ~0.1s   block-hash prefix caching
python3 radix_cache.py        # ~0.1s   radix tree prefix caching
python3 paged_kv_cache.py     # ~0.1s   paged blocks, forking, copy-on-write
python3 semantic_cache.py     # ~0.1s   exact vs semantic caching
python3 cache_router.py       # ~0.3s   cache-aware load balancing
python3 serving_demo.py       # ~10s    capstone: model + radix cache
```

Files import each other by name, so run them from inside this directory.

## What each file demonstrates

### `kv_cache.py`

Pure-Python matmul/softmax, causal `SelfAttention` with `forward_full` and
`forward_incremental`, a `KVCache`, and an `OpCounter` so the cost model is measured
rather than claimed.

```
max |full - incremental| = 0.00e+00
generating 24 tokens from an 8-token prompt:
  no cache: 1,781,504 MACs   122.3 ms
  KV cache:   132,096 MACs     9.8 ms      13.5x

  prompt  generate      no cache      KV cache   speedup
       8        24        23.6 G         1.6 G       15x
    4096       256    73,134.0 G       296.6 G      247x
```

Plus the memory table: Llama-3-8B at 128 KB/token, 4.3 GB for a 32k context; 70B at
320 KB/token, 10.7 GB.

### `tiny_transformer.py`

A complete character-level decoder-only transformer: multi-head causal attention,
pre-norm, GELU MLP, tied embeddings, learned positional embeddings. Deterministic
pseudo-random weights, so it runs identically everywhere with no downloads.

```
no cache -> '  aaaaaaaaaaaaaa'      7,584,000 MACs   614.6 ms
KV cache -> '  aaaaaaaaaaaaaa'        716,352 MACs    57.7 ms   10.6x
identical: True
```

The output is gibberish because the weights are random. That is not the point — the
point is that both paths produce the *same* gibberish, and that truncating a cache to
length L reproduces the state after L tokens with zero error.

### `prefix_cache.py`

Block-hash prefix caching (vLLM's automatic prefix caching), with LRU eviction, reference
counting, and an `extra` field in the hash for anything else the KV depends on.

```
block size    hit rate   blocks stored
         1      90.5%             120
        16      72.4%               3
        64       0.0%               0     <- 60-token prefix never fills a block
```

Also: changing one token at position 12 of a 32-token cached sequence reduces reuse to
12 tokens even though the later blocks are still in the table; a 5-turn chat reaches 84%
by the last turn; and matching with `extra="lora=B"` against data inserted with
`extra="lora=A"` correctly returns zero.

### `radix_cache.py`

RadixAttention: a radix tree with node splitting, LRU eviction over leaves, reference
counting up the ancestor chain, and single-child compaction after removal.

```
3 sequences of 33 tokens = 99 tokens if stored separately
actually stored: 37 tokens in 6 nodes

exact repeat:            33/33 tokens matched
diverges at the last:    32/33 tokens matched
```

The eviction section shows a hot prefix surviving eight cold requests, protected both by
LRU recency and by the structural fact that an interior node is never a leaf. The pinning
section shows the cache correctly sitting **over** capacity rather than evicting KV a
live request is decoding against.

### `paged_kv_cache.py`

A block manager with a free list, block tables, forking by reference count, and
copy-on-write — plus a `ContiguousAllocator` to compare against.

```
KV budget 4096 tokens, max_seq_len 2048, requests of 45-900 tokens:
  contiguous:  2/10 admitted, 88.8% wasted
  paged:      10/10 admitted,  2.8% wasted

forked a 200-token sequence (13 blocks) three times
  blocks consumed by the forks: 0
  copy-on-write copies after one append: 1
```

### `semantic_cache.py`

`ExactCache` (hash, TTL, LRU — can never be wrong) and `SemanticCache` (hashing-trick
embedding, cosine similarity, threshold), plus an eleven-pair evaluation set.

```
 similarity  should hit  pair
      1.000          NO  flights from Paris to Rome | flights from Rome to Paris
      1.000          NO  convert 100 USD to EUR     | convert 100 EUR to USD
      0.935          NO  what is the price with tax | what is the price without tax

 threshold   hits  correct  WRONG  precision
      0.85      9        4      5        44%
      0.95      5        3      2        60%
      0.99      5        3      2        60%
```

No threshold makes it safe. A better encoder moves the numbers; it does not remove the
failure mode, because "similar text implies interchangeable answer" is false for any
query containing a negation, a direction, a unit, or a number.

### `cache_router.py`

Four routing policies over workers that each own a `RadixCache`, on Zipf-distributed
multi-tenant traffic.

```
policy                  hit rate  total work   makespan  imbalance
round robin               61.2%      52,260     14,940      1.14x
longest prefix            90.0%      15,360      4,438      1.16x
cache-aware w=1.0         88.8%      16,860      4,430      1.05x

load_weight  hit rate  total work   makespan  imbalance
       0.00    63.3%      49,560     49,560      4.00x
       0.05    90.0%      15,360      6,365      1.66x
       1.00    88.8%      16,860      4,430      1.05x
     100.00    73.6%      36,360      9,197      1.01x
```

Total work minimises around weight 0.05; makespan around 1.0. They do not coincide.
The capacity sweep shows the whole advantage evaporating once every worker can hold the
entire working set — build this only when yours does not fit.

### `serving_demo.py`

The capstone. Real KV state from `tiny_transformer` stored in a `RadixCache`, serving a
12-request multi-turn chat trace.

```
caching off: 31,204,608 MACs in 2822 ms
caching on:   9,009,024 MACs in  861 ms   (79.2% token hit rate)

outputs bit-identical: True
compute saved:         71.1%
wall-clock speedup:    3.28x
```

The per-request table shows prompts growing from 59 to 94 tokens while the work per
request stays flat, and the capacity sweep shows the working-set cliff: 0% hit rate at
60 tokens of capacity, 79% at 150, and nothing further gained at 400.

## Implementation notes

- **`_pseudo_random_matrix` uses an inline LCG**, not `random`, so results are identical
  on every machine and every Python version.
- **Row-vector convention.** `forward_full` computes `x @ W`; the incremental path must
  therefore use `matvec(transpose(W), x)`. Getting this backwards is the most common way
  to break the exactness check.
- **Append K/V to the cache *before* computing attention scores** — a token attends to
  itself.
- **`ModelCache.clone()` is a deep copy.** Sharing a cache between two requests without
  cloning means the second appends into the first's state, and both outputs go wrong in
  ways that still look like fluent text.
- **`restore()` must set `cache.tokens`**, not just the K/V. The model derives the next
  position index from `len(cache)`, and a cache whose tokens and KV disagree produces
  confidently wrong output.
- **The fully-cached-prompt edge case** in `CachedServer.generate`: if every prompt token
  matched, there are no fresh logits to decode from. Truncate by one and recompute that
  single position — re-running the last token on top of the full cache would let it
  attend to itself twice.
- **`BlockManager.free_blocks` is named that, not `free`,** because `free()` is also a
  method. An attribute and a method with the same name means the attribute wins and the
  method becomes uncallable.
- **`skewed_traffic` uses `random.Random`, not a hand-rolled LCG.** LCG low bits have a
  short period, so `state % num_tenants` yields a perfectly cyclic tenant order that
  round-robin lines up with — making every routing policy look identical. That is a real
  trap, and it cost this file a debugging round.

"""
End-to-End Context Caching — Complete Solution

Puts the whole directory together on one workload: a real (tiny) transformer, a
radix prefix cache holding real KV state, and a multi-turn chat trace.

The claim being tested is the one that matters: caching must cut the compute
and leave the output bit-identical. Both are checked here, not asserted.
"""

import time
from typing import Dict, List, Optional, Sequence, Tuple

from kv_cache import OpCounter
from radix_cache import RadixCache
from tiny_transformer import (CORPUS, CharTokenizer, LayerCache, ModelCache,
                              TinyTransformer, _argmax)


# ---------------------------------------------------------------------------
# Moving KV state between the model and the cache
# ---------------------------------------------------------------------------

def snapshot(model_cache: ModelCache) -> List[object]:
    """One opaque entry per token, holding that token's K/V for every head.

    Per-token granularity is what lets the radix tree store a prefix once and
    hand back any prefix length. A real implementation keeps pointers to GPU
    blocks here instead of copying floats — the structure is the same, only the
    payload changes.
    """
    entries: List[object] = []
    for position in range(len(model_cache)):
        per_layer = []
        for layer in model_cache.layers:
            per_layer.append([(layer.keys[head][position], layer.values[head][position])
                              for head in range(len(layer.keys))])
        entries.append(per_layer)
    return entries


def restore(entries: Sequence[object], tokens: Sequence[int],
            n_layer: int, n_head: int) -> ModelCache:
    """Rebuild a ModelCache from cached per-token entries."""
    cache = ModelCache(n_layer, n_head)
    for entry in entries:
        for layer_index, per_layer in enumerate(entry):   # type: ignore[arg-type]
            layer = cache.layers[layer_index]
            for head, (k, v) in enumerate(per_layer):
                layer.keys[head].append(k)
                layer.values[head].append(v)
    cache.tokens = list(tokens[:len(entries)])
    return cache


# ---------------------------------------------------------------------------
# The server
# ---------------------------------------------------------------------------

class CachedServer:
    """A single-worker inference server with a radix prefix cache."""

    def __init__(self, model: TinyTransformer, cache_capacity: int = 4096,
                 enabled: bool = True):
        self.model = model
        self.cache = RadixCache(capacity_tokens=cache_capacity)
        self.enabled = enabled
        self.stats = {"requests": 0, "tokens_prefilled": 0, "tokens_reused": 0}

    def generate(self, prompt: List[int], max_new_tokens: int = 8) -> List[int]:
        self.stats["requests"] += 1

        if self.enabled:
            matched, entries, _ = self.cache.match_prefix(prompt)
        else:
            matched, entries = 0, []

        model_cache = restore(entries, prompt, self.model.n_layer, self.model.n_head)
        self.stats["tokens_reused"] += matched
        self.stats["tokens_prefilled"] += len(prompt) - matched

        logits: List[float] = []
        for position in range(matched, len(prompt)):
            logits = self.model.forward_token(prompt[position], position, model_cache)

        if matched == len(prompt):
            # Every prompt token was cached, so no forward pass produced logits.
            # Re-running the last token would be wrong (it is already in the
            # cache), so drop it and recompute that single position.
            model_cache.truncate(len(prompt) - 1)
            logits = self.model.forward_token(prompt[-1], len(prompt) - 1, model_cache)
            self.stats["tokens_reused"] -= 1
            self.stats["tokens_prefilled"] += 1

        generated: List[int] = []
        for _ in range(max_new_tokens):
            token = _argmax(logits)
            generated.append(token)
            logits = self.model.forward_token(token, len(model_cache), model_cache)

        if self.enabled:
            full = list(prompt) + generated
            self.cache.insert(full[:len(model_cache)],
                              snapshot(model_cache)[:len(full)])
        return generated

    @property
    def hit_rate(self) -> float:
        total = self.stats["tokens_reused"] + self.stats["tokens_prefilled"]
        return self.stats["tokens_reused"] / total if total else 0.0


def chat_trace(tokenizer: CharTokenizer, num_conversations: int = 3,
               turns: int = 4) -> List[List[int]]:
    """Multi-turn chat: every turn resends the whole history plus one new line.

    This is the workload prefix caching was built for. Turn 4 of a conversation
    is ~80% tokens the server has already processed twice.
    """
    system = "the quick brown fox jumps over the lazy dog. "
    user_lines = ["pack my box ", "how vexingly ", "five dozen ", "quick daft "]
    requests: List[List[int]] = []
    for conversation in range(num_conversations):
        history = system + f"{conversation} "
        for turn in range(turns):
            history += user_lines[turn % len(user_lines)]
            requests.append(tokenizer.encode(history))
    return requests


def _demo() -> None:
    tokenizer = CharTokenizer(CORPUS)
    counter = OpCounter()
    model = TinyTransformer(len(tokenizer), d_model=32, n_layer=2, n_head=4,
                            max_seq=512, seed=7, counter=counter)
    requests = chat_trace(tokenizer, num_conversations=3, turns=4)
    print(f"workload: {len(requests)} requests, "
          f"{sum(len(r) for r in requests)} prompt tokens total")
    print(f"lengths: {[len(r) for r in requests]}")

    print("\n=== Caching off ===")
    counter.reset()
    cold = CachedServer(model, enabled=False)
    start = time.perf_counter()
    cold_outputs = [cold.generate(request, max_new_tokens=6) for request in requests]
    cold_macs, cold_time = counter.macs, time.perf_counter() - start
    print(f"prefill tokens: {cold.stats['tokens_prefilled']}, "
          f"reused: {cold.stats['tokens_reused']}")
    print(f"{cold_macs:,} MACs in {cold_time * 1000:.0f} ms")

    print("\n=== Caching on (radix prefix cache) ===")
    counter.reset()
    warm = CachedServer(model, cache_capacity=8192, enabled=True)
    start = time.perf_counter()
    warm_outputs = [warm.generate(request, max_new_tokens=6) for request in requests]
    warm_macs, warm_time = counter.macs, time.perf_counter() - start
    print(f"prefill tokens: {warm.stats['tokens_prefilled']}, "
          f"reused: {warm.stats['tokens_reused']}")
    print(f"token hit rate: {warm.hit_rate:.1%}")
    print(f"{warm_macs:,} MACs in {warm_time * 1000:.0f} ms")

    print("\n=== The two things that must both be true ===")
    identical = cold_outputs == warm_outputs
    print(f"outputs bit-identical: {identical}")
    if not identical:
        for i, (a, b) in enumerate(zip(cold_outputs, warm_outputs)):
            if a != b:
                print(f"  request {i}: {tokenizer.decode(a)!r} != "
                      f"{tokenizer.decode(b)!r}")
    print(f"compute saved:         {1 - warm_macs / cold_macs:.1%}")
    print(f"wall-clock speedup:    {cold_time / warm_time:.2f}x")
    print("A cache that changes the output is not a cache, it is a bug. Make")
    print("this assertion the first test in any serving stack you build.")

    print("\n=== Per-request detail ===")
    counter.reset()
    server = CachedServer(model, cache_capacity=8192, enabled=True)
    print(f"{'req':>4}{'prompt':>8}{'cached':>8}{'prefill':>9}{'MACs':>12}")
    for i, request in enumerate(requests):
        before_reused = server.stats["tokens_reused"]
        before_macs = counter.macs
        server.generate(request, max_new_tokens=6)
        reused = server.stats["tokens_reused"] - before_reused
        print(f"{i:>4}{len(request):>8}{reused:>8}{len(request) - reused:>9}"
              f"{counter.macs - before_macs:>12,}")
    print("Requests 1-3 are turns 2-4 of the same conversation: the prompt grows")
    print("but the work per request stays roughly flat, because everything")
    print("except the new turn is already in the tree.")

    print("\n=== Cache capacity ===")
    print(f"{'capacity':>10}{'hit rate':>10}{'MACs':>14}{'evicted':>10}")
    for capacity in (60, 100, 150, 400):
        counter.reset()
        server = CachedServer(model, cache_capacity=capacity, enabled=True)
        for request in requests:
            server.generate(request, max_new_tokens=6)
        print(f"{capacity:>10}{server.hit_rate:>9.1%}{counter.macs:>14,}"
              f"{server.cache.stats['tokens_evicted']:>10}")
    print("The working set is ~150 tokens (3 conversations of ~100, sharing a")
    print("45-token system prompt). Below that the cache thrashes and the hit")
    print("rate falls off a cliff; above it, extra capacity buys nothing.")
    print("Cache sizing is a working-set question, not a 'bigger is better' one.")

    print("\n=== Where the savings come from ===")
    print("Prefill is what gets cached; decode never can be, because each")
    print("decoded token depends on the one before it. So the ceiling on any")
    print("prefix cache is the prefill share of your workload:")
    print()
    print(f"{'prompt':>8}{'generate':>10}{'prefill share':>15}{'max speedup':>13}")
    for prompt_len, gen_len in [(2000, 20), (1000, 100), (500, 500), (100, 1000)]:
        share = prompt_len / (prompt_len + gen_len)
        print(f"{prompt_len:>8}{gen_len:>10}{share:>14.0%}"
              f"{1 / (1 - share):>12.1f}x")
    print()
    print("Long prompt, short answer (RAG, classification, extraction) is where")
    print("prefix caching pays. Short prompt, long answer (creative generation)")
    print("gets almost nothing from it — go optimise decode instead.")


if __name__ == "__main__":
    _demo()

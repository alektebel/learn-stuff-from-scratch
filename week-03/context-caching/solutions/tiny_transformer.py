"""
A Tiny Transformer With Incremental Decoding — Complete Solution

A complete character-level decoder-only transformer in pure Python, small
enough to run in under a second and real enough that the KV cache has to be
correct: cached and uncached decoding must produce identical logits.

Architecture (GPT-style, pre-norm):
    embedding + learned positional embedding
    n_layer x [ LayerNorm -> multi-head causal attention -> residual
                LayerNorm -> MLP (4x, GELU)              -> residual ]
    final LayerNorm -> tied output projection
"""

import math
import time
from typing import Dict, List, Optional, Sequence, Tuple

from kv_cache import (Matrix, OpCounter, Vector, add, dot, matmul, matvec,
                      scale, softmax, transpose, zeros)


def pseudo_random(rows: int, cols: int, seed: int, gain: float = 0.4) -> Matrix:
    """Deterministic weights, no dependencies, identical on every machine."""
    matrix = zeros(rows, cols)
    state = (seed * 2654435761 + 1) & 0x7FFFFFFF
    for i in range(rows):
        for j in range(cols):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            matrix[i][j] = ((state / 0x7FFFFFFF) - 0.5) * gain
    return matrix


def layer_norm(x: Vector, eps: float = 1e-5) -> Vector:
    mean = sum(x) / len(x)
    var = sum((v - mean) ** 2 for v in x) / len(x)
    inv = 1.0 / math.sqrt(var + eps)
    return [(v - mean) * inv for v in x]


def gelu(x: float) -> float:
    return 0.5 * x * (1.0 + math.tanh(0.7978845608 * (x + 0.044715 * x ** 3)))


class LayerCache:
    """KV cache for one layer, stored per head."""

    def __init__(self, n_head: int):
        self.keys: List[Matrix] = [[] for _ in range(n_head)]
        self.values: List[Matrix] = [[] for _ in range(n_head)]

    def __len__(self) -> int:
        return len(self.keys[0])

    def truncate(self, length: int) -> None:
        for head in range(len(self.keys)):
            del self.keys[head][length:]
            del self.values[head][length:]

    def clone(self) -> "LayerCache":
        cache = LayerCache(len(self.keys))
        cache.keys = [[list(k) for k in head] for head in self.keys]
        cache.values = [[list(v) for v in head] for head in self.values]
        return cache


class ModelCache:
    """The full KV cache of a sequence: one LayerCache per layer.

    `truncate` is what makes prefix reuse possible. Because attention is causal,
    the cache entry for position i depends only on positions <= i, so cutting
    the cache at length L leaves exactly the state the model would have had
    after processing L tokens — no recomputation, no approximation.
    """

    def __init__(self, n_layer: int, n_head: int):
        self.layers = [LayerCache(n_head) for _ in range(n_layer)]
        self.tokens: List[int] = []

    def __len__(self) -> int:
        return len(self.tokens)

    def truncate(self, length: int) -> None:
        for layer in self.layers:
            layer.truncate(length)
        del self.tokens[length:]

    def clone(self) -> "ModelCache":
        cache = ModelCache(0, 0)
        cache.layers = [layer.clone() for layer in self.layers]
        cache.tokens = list(self.tokens)
        return cache


class TinyTransformer:
    """A small decoder-only transformer with random (untrained) weights.

    Untrained is fine for studying caching: the cache must reproduce the model's
    output exactly whatever the weights are. Training would only slow the demo
    down and change nothing about the mechanism.
    """

    def __init__(self, vocab_size: int, d_model: int = 32, n_layer: int = 2,
                 n_head: int = 4, max_seq: int = 256, seed: int = 7,
                 counter: Optional[OpCounter] = None):
        assert d_model % n_head == 0
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_layer = n_layer
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.max_seq = max_seq
        self.counter = counter or OpCounter()

        self.wte = pseudo_random(vocab_size, d_model, seed, gain=1.0)
        self.wpe = pseudo_random(max_seq, d_model, seed + 1, gain=0.2)
        self.blocks = []
        for layer in range(n_layer):
            base = seed + 10 * (layer + 1)
            self.blocks.append({
                "w_q": pseudo_random(d_model, d_model, base + 1),
                "w_k": pseudo_random(d_model, d_model, base + 2),
                "w_v": pseudo_random(d_model, d_model, base + 3),
                "w_o": pseudo_random(d_model, d_model, base + 4),
                "w_fc": pseudo_random(d_model, 4 * d_model, base + 5),
                "w_proj": pseudo_random(4 * d_model, d_model, base + 6),
            })

    def new_cache(self) -> ModelCache:
        return ModelCache(self.n_layer, self.n_head)

    # -- one token, using and extending the cache ---------------------------

    def forward_token(self, token: int, position: int,
                      cache: ModelCache) -> Vector:
        """Run one token and return its logits, appending to the cache."""
        x = add(self.wte[token], self.wpe[position])

        for layer_idx, block in enumerate(self.blocks):
            layer_cache = cache.layers[layer_idx]
            h = layer_norm(x)

            q = matvec(transpose(block["w_q"]), h)
            k = matvec(transpose(block["w_k"]), h)
            v = matvec(transpose(block["w_v"]), h)
            self.counter.macs += 3 * self.d_model * self.d_model

            attn_out: Vector = []
            inv_sqrt = 1.0 / math.sqrt(self.head_dim)
            for head in range(self.n_head):
                lo = head * self.head_dim
                hi = lo + self.head_dim
                layer_cache.keys[head].append(k[lo:hi])
                layer_cache.values[head].append(v[lo:hi])

                q_head = q[lo:hi]
                keys = layer_cache.keys[head]
                scores = [dot(q_head, past) * inv_sqrt for past in keys]
                weights = softmax(scores)
                acc = [0.0] * self.head_dim
                for weight, past_v in zip(weights, layer_cache.values[head]):
                    acc = add(acc, scale(past_v, weight))
                self.counter.macs += 2 * len(keys) * self.head_dim
                attn_out.extend(acc)

            x = add(x, matvec(transpose(block["w_o"]), attn_out))
            self.counter.macs += self.d_model * self.d_model

            h = layer_norm(x)
            hidden = [gelu(val) for val in matvec(transpose(block["w_fc"]), h)]
            x = add(x, matvec(transpose(block["w_proj"]), hidden))
            self.counter.macs += 8 * self.d_model * self.d_model

        x = layer_norm(x)
        logits = matvec(self.wte, x)              # tied embedding
        self.counter.macs += self.vocab_size * self.d_model
        cache.tokens.append(token)
        return logits

    # -- whole sequences ----------------------------------------------------

    def forward_sequence(self, tokens: Sequence[int],
                         cache: Optional[ModelCache] = None) -> Vector:
        """Run a whole sequence and return the last position's logits."""
        cache = cache if cache is not None else self.new_cache()
        start = len(cache)
        logits: Vector = []
        for offset, token in enumerate(tokens):
            logits = self.forward_token(token, start + offset, cache)
        return logits

    def generate(self, prompt: Sequence[int], max_new_tokens: int = 16,
                 cache: Optional[ModelCache] = None,
                 temperature: float = 0.0) -> Tuple[List[int], ModelCache]:
        """Greedy decoding on top of an existing (possibly reused) cache."""
        cache = cache if cache is not None else self.new_cache()
        tokens = list(prompt)
        logits = self.forward_sequence(prompt[len(cache):], cache)

        generated: List[int] = []
        for _ in range(max_new_tokens):
            token = _argmax(logits) if temperature == 0.0 else _sample(logits, temperature)
            generated.append(token)
            tokens.append(token)
            logits = self.forward_token(token, len(cache), cache)
        return generated, cache

    def generate_no_cache(self, prompt: Sequence[int],
                          max_new_tokens: int = 16) -> List[int]:
        """The same output, recomputing the entire sequence at every step.

        This is the baseline the KV cache replaces. It is not a different
        algorithm — it produces bit-identical results — it just repeats work
        that provably cannot have changed.
        """
        tokens = list(prompt)
        generated: List[int] = []
        for _ in range(max_new_tokens):
            logits = self.forward_sequence(tokens, self.new_cache())
            token = _argmax(logits)
            generated.append(token)
            tokens.append(token)
        return generated


def _argmax(logits: Vector) -> int:
    best, best_i = logits[0], 0
    for i, value in enumerate(logits):
        if value > best:
            best, best_i = value, i
    return best_i


def _sample(logits: Vector, temperature: float, seed: int = 0) -> int:
    probs = softmax([v / temperature for v in logits])
    state = (seed * 2654435761 + len(probs)) & 0x7FFFFFFF
    state = (state * 1103515245 + 12345) & 0x7FFFFFFF
    target = state / 0x7FFFFFFF
    cumulative = 0.0
    for i, p in enumerate(probs):
        cumulative += p
        if cumulative >= target:
            return i
    return len(probs) - 1


class CharTokenizer:
    """Character-level tokenizer — no dependencies, no vocabulary files."""

    def __init__(self, text: str):
        self.chars = sorted(set(text))
        self.stoi: Dict[str, int] = {c: i for i, c in enumerate(self.chars)}
        self.itos: Dict[int, str] = {i: c for c, i in self.stoi.items()}

    def encode(self, text: str) -> List[int]:
        return [self.stoi[c] for c in text if c in self.stoi]

    def decode(self, tokens: Sequence[int]) -> str:
        return "".join(self.itos[t] for t in tokens)

    def __len__(self) -> int:
        return len(self.chars)


CORPUS = ("the quick brown fox jumps over the lazy dog. "
          "pack my box with five dozen liquor jugs. "
          "how vexingly quick daft zebras jump! 0123456789")


def _demo() -> None:
    tokenizer = CharTokenizer(CORPUS)
    counter = OpCounter()
    model = TinyTransformer(len(tokenizer), d_model=32, n_layer=2, n_head=4,
                            seed=7, counter=counter)
    print(f"vocab={len(tokenizer)}  d_model={model.d_model}  "
          f"layers={model.n_layer}  heads={model.n_head}")

    prompt = tokenizer.encode("the quick ")
    gen = 16

    print("\n=== Correctness: cached and uncached decoding must agree exactly ===")
    counter.reset()
    start = time.perf_counter()
    uncached = model.generate_no_cache(prompt, max_new_tokens=gen)
    uncached_macs, uncached_time = counter.macs, time.perf_counter() - start

    counter.reset()
    start = time.perf_counter()
    cached, cache = model.generate(prompt, max_new_tokens=gen)
    cached_macs, cached_time = counter.macs, time.perf_counter() - start

    print(f"no cache -> {tokenizer.decode(uncached)!r}")
    print(f"KV cache -> {tokenizer.decode(cached)!r}")
    print(f"identical: {uncached == cached}")
    print("The weights are random, so the text is meaningless. That is not the")
    print("point — the point is that both paths produce the SAME meaningless")
    print("text, token for token. A cache that changes the output is a bug.")
    print(f"\n{'':10}{'MACs':>14}{'time':>10}")
    print(f"{'no cache':10}{uncached_macs:>14,}{uncached_time * 1000:>9.1f}ms")
    print(f"{'KV cache':10}{cached_macs:>14,}{cached_time * 1000:>9.1f}ms")
    print(f"{'speedup':10}{uncached_macs / cached_macs:>13.1f}x"
          f"{uncached_time / cached_time:>8.1f}x")

    print("\n=== Prefix reuse: a shared system prompt across three requests ===")
    system = tokenizer.encode("the quick brown fox jumps over the lazy dog. ")
    questions = ["how ", "pack ", "the "]

    counter.reset()
    start = time.perf_counter()
    for question in questions:
        model.generate(system + tokenizer.encode(question), max_new_tokens=8)
    cold_macs, cold_time = counter.macs, time.perf_counter() - start

    counter.reset()
    start = time.perf_counter()
    shared = model.new_cache()
    model.forward_sequence(system, shared)         # pay for the system prompt once
    for question in questions:
        warm = shared.clone()                      # fork, do not mutate the shared cache
        model.generate(system + tokenizer.encode(question), max_new_tokens=8, cache=warm)
    warm_macs, warm_time = counter.macs, time.perf_counter() - start

    print(f"{'':22}{'MACs':>14}{'time':>10}")
    print(f"{'cold (recompute)':22}{cold_macs:>14,}{cold_time * 1000:>9.1f}ms")
    print(f"{'warm (shared prefix)':22}{warm_macs:>14,}{warm_time * 1000:>9.1f}ms")
    print(f"{'saved':22}{1 - warm_macs / cold_macs:>13.0%}")
    print(f"prefix was {len(system)} of ~{len(system) + 4 + 8} tokens per request.")

    print("\n=== Truncation gives you an exact earlier state ===")
    full = model.new_cache()
    model.forward_sequence(tokenizer.encode("the quick brown"), full)
    logits_a = model.forward_token(tokenizer.stoi[" "], len(full), full)

    full.truncate(len("the quick brown"))
    logits_b = model.forward_token(tokenizer.stoi[" "], len(full), full)
    print(f"max |logits_a - logits_b| = "
          f"{max(abs(a - b) for a, b in zip(logits_a, logits_b)):.2e}")
    print("Cutting the cache at length L reproduces the state after L tokens")
    print("exactly — because attention is causal. Everything in prefix_cache.py")
    print("and radix_cache.py is built on that one property.")


if __name__ == "__main__":
    _demo()

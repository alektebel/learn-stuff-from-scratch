"""
The KV Cache — Complete Solution

Pure-Python linear algebra so nothing is hidden behind a library call.
Matrices are lists of rows; a row is a list of floats.
"""

import math
import time
from typing import List, Optional, Tuple

Matrix = List[List[float]]
Vector = List[float]


# ---------------------------------------------------------------------------
# Minimal linear algebra
# ---------------------------------------------------------------------------

def zeros(rows: int, cols: int) -> Matrix:
    return [[0.0] * cols for _ in range(rows)]


def matmul(a: Matrix, b: Matrix) -> Matrix:
    """(n, k) @ (k, m) -> (n, m). Costs n*k*m multiply-accumulates."""
    b_t = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in b_t] for row in a]


def matvec(a: Matrix, v: Vector) -> Vector:
    return [sum(x * y for x, y in zip(row, v)) for row in a]


def transpose(a: Matrix) -> Matrix:
    return [list(col) for col in zip(*a)]


def softmax(scores: Vector) -> Vector:
    """Numerically stable softmax — subtract the max before exponentiating."""
    hi = max(scores)
    exps = [math.exp(s - hi) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def dot(a: Vector, b: Vector) -> float:
    return sum(x * y for x, y in zip(a, b))


def scale(v: Vector, factor: float) -> Vector:
    return [x * factor for x in v]


def add(a: Vector, b: Vector) -> Vector:
    return [x + y for x, y in zip(a, b)]


# ---------------------------------------------------------------------------
# Attention, with an explicit operation counter
# ---------------------------------------------------------------------------

class OpCounter:
    """Counts multiply-accumulates so the cost model is visible, not asserted."""

    def __init__(self) -> None:
        self.macs = 0

    def add_matmul(self, n: int, k: int, m: int) -> None:
        self.macs += n * k * m

    def reset(self) -> None:
        self.macs = 0


class KVCache:
    """Per-layer store of the key and value vectors of every past token.

    Memory is the whole story:

        bytes = 2 (K and V) * layers * heads * head_dim * seq_len * dtype_size

    For Llama-3-8B in fp16 that is ~128 KB per token, so a 32k-token context
    costs about 4 GB of KV cache for ONE sequence. This is why every technique
    in the rest of this directory exists: KV memory, not weights, is what limits
    how many requests fit on a GPU.
    """

    def __init__(self) -> None:
        self.keys: Matrix = []
        self.values: Matrix = []

    def append(self, k: Vector, v: Vector) -> None:
        self.keys.append(k)
        self.values.append(v)

    def extend(self, keys: Matrix, values: Matrix) -> None:
        self.keys.extend(keys)
        self.values.extend(values)

    def truncate(self, length: int) -> None:
        """Drop everything past `length` — the operation prefix reuse needs."""
        del self.keys[length:]
        del self.values[length:]

    def clone(self) -> "KVCache":
        cache = KVCache()
        cache.keys = [list(k) for k in self.keys]
        cache.values = [list(v) for v in self.values]
        return cache

    def __len__(self) -> int:
        return len(self.keys)

    def memory_bytes(self, dtype_size: int = 2) -> int:
        if not self.keys:
            return 0
        return 2 * len(self.keys) * len(self.keys[0]) * dtype_size


class SelfAttention:
    """One head of causal self-attention with fixed (untrained) weights."""

    def __init__(self, d_model: int, seed: int = 0,
                 counter: Optional[OpCounter] = None):
        self.d_model = d_model
        self.counter = counter or OpCounter()
        self.w_q = _pseudo_random_matrix(d_model, d_model, seed + 1)
        self.w_k = _pseudo_random_matrix(d_model, d_model, seed + 2)
        self.w_v = _pseudo_random_matrix(d_model, d_model, seed + 3)

    # -- the naive path -----------------------------------------------------

    def forward_full(self, x: Matrix) -> Matrix:
        """Attention over the whole sequence, recomputing every K and V.

        This is what generation does if you throw the cache away each step:
        token t re-derives K and V for tokens 0..t-1 that have not changed and
        cannot change, because the mask is causal.
        """
        n = len(x)
        q = matmul(x, self.w_q)
        k = matmul(x, self.w_k)
        v = matmul(x, self.w_v)
        self.counter.add_matmul(n, self.d_model, self.d_model)
        self.counter.add_matmul(n, self.d_model, self.d_model)
        self.counter.add_matmul(n, self.d_model, self.d_model)

        scale_factor = 1.0 / math.sqrt(self.d_model)
        out: Matrix = []
        for t in range(n):
            scores = [dot(q[t], k[j]) * scale_factor for j in range(t + 1)]  # causal
            self.counter.macs += (t + 1) * self.d_model
            weights = softmax(scores)
            acc = [0.0] * self.d_model
            for j, weight in enumerate(weights):
                acc = add(acc, scale(v[j], weight))
            self.counter.macs += (t + 1) * self.d_model
            out.append(acc)
        return out

    # -- the cached path ----------------------------------------------------

    def forward_incremental(self, x_t: Vector, cache: KVCache) -> Vector:
        """One new token against a cache of everything before it.

        Only the new token's Q, K and V are computed. The past K/V are read
        straight out of the cache, which is the entire trick.
        """
        q = matvec(transpose(self.w_q), x_t)
        k = matvec(transpose(self.w_k), x_t)
        v = matvec(transpose(self.w_v), x_t)
        self.counter.macs += 3 * self.d_model * self.d_model

        cache.append(k, v)
        scale_factor = 1.0 / math.sqrt(self.d_model)
        scores = [dot(q, past_k) * scale_factor for past_k in cache.keys]
        self.counter.macs += len(cache) * self.d_model

        weights = softmax(scores)
        acc = [0.0] * self.d_model
        for weight, past_v in zip(weights, cache.values):
            acc = add(acc, scale(past_v, weight))
        self.counter.macs += len(cache) * self.d_model
        return acc

    def prefill(self, x: Matrix, cache: KVCache) -> Matrix:
        """Process a prompt in one pass, filling the cache.

        Prefill is compute-bound and parallel across positions; decode is
        memory-bound and strictly sequential. Serving stacks treat them as two
        different problems for exactly this reason.
        """
        n = len(x)
        k = matmul(x, self.w_k)
        v = matmul(x, self.w_v)
        q = matmul(x, self.w_q)
        self.counter.add_matmul(n, self.d_model, self.d_model)
        self.counter.add_matmul(n, self.d_model, self.d_model)
        self.counter.add_matmul(n, self.d_model, self.d_model)

        base = len(cache)
        cache.extend(k, v)
        scale_factor = 1.0 / math.sqrt(self.d_model)
        out: Matrix = []
        for t in range(n):
            limit = base + t + 1
            scores = [dot(q[t], cache.keys[j]) * scale_factor for j in range(limit)]
            weights = softmax(scores)
            acc = [0.0] * self.d_model
            for j, weight in enumerate(weights):
                acc = add(acc, scale(cache.values[j], weight))
            self.counter.macs += 2 * limit * self.d_model
            out.append(acc)
        return out


def _pseudo_random_matrix(rows: int, cols: int, seed: int) -> Matrix:
    """Deterministic weights without importing random — reproducible anywhere."""
    matrix = zeros(rows, cols)
    state = seed * 2654435761 + 1
    for i in range(rows):
        for j in range(cols):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            matrix[i][j] = ((state / 0x7FFFFFFF) - 0.5) * 0.4
    return matrix


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------

def attention_cost(prompt_len: int, gen_len: int, d_model: int,
                   cached: bool) -> int:
    """Analytic MAC count for generating `gen_len` tokens.

    Without a cache, step i re-runs the whole prefix: total work is O(L^2) in
    projections alone, on top of the O(L^2) attention every transformer pays.
    With a cache, projections become O(L) and only the attention scores stay
    linear per step.
    """
    total = 0
    if cached:
        total += 3 * prompt_len * d_model * d_model          # prefill projections
        for t in range(prompt_len):
            total += 2 * (t + 1) * d_model
        for i in range(gen_len):
            total += 3 * d_model * d_model                   # one token's QKV
            total += 2 * (prompt_len + i + 1) * d_model      # attend to the cache
    else:
        for i in range(gen_len):
            n = prompt_len + i
            total += 3 * n * d_model * d_model               # recompute EVERYTHING
            for t in range(n):
                total += 2 * (t + 1) * d_model
    return total


def _demo() -> None:
    d_model = 32
    print("=== Correctness: cached decoding must match full recomputation ===")
    counter = OpCounter()
    attention = SelfAttention(d_model, seed=1, counter=counter)
    tokens: Matrix = [_pseudo_random_matrix(1, d_model, 100 + i)[0] for i in range(8)]

    full = attention.forward_full(tokens)
    cache = KVCache()
    incremental = [attention.forward_incremental(t, cache) for t in tokens]

    max_error = max(abs(a - b)
                    for row_a, row_b in zip(full, incremental)
                    for a, b in zip(row_a, row_b))
    print(f"max |full - incremental| = {max_error:.2e}  (float noise only)")
    print("The cache is not an approximation. It is algebraically the same")
    print("computation with the redundant part deleted.")

    print("\n=== Measured cost of generating 24 tokens from an 8-token prompt ===")
    prompt, gen = 8, 24

    counter.reset()
    attention = SelfAttention(d_model, seed=1, counter=counter)
    sequence = [list(t) for t in tokens]
    start = time.perf_counter()
    for _ in range(gen):
        out = attention.forward_full(sequence)
        sequence.append(out[-1])
    naive_macs, naive_time = counter.macs, time.perf_counter() - start

    counter.reset()
    attention = SelfAttention(d_model, seed=1, counter=counter)
    cache = KVCache()
    start = time.perf_counter()
    out = attention.prefill(tokens, cache)
    last = out[-1]
    for _ in range(gen):
        last = attention.forward_incremental(last, cache)
    cached_macs, cached_time = counter.macs, time.perf_counter() - start

    print(f"no cache: {naive_macs:>10,} MACs   {naive_time * 1000:7.1f} ms")
    print(f"KV cache: {cached_macs:>10,} MACs   {cached_time * 1000:7.1f} ms")
    print(f"speedup:  {naive_macs / cached_macs:>10.1f}x MACs   "
          f"{naive_time / cached_time:7.1f}x wall clock")

    print("\n=== How the gap scales ===")
    print(f"{'prompt':>8}{'generate':>10}{'no cache':>16}{'KV cache':>16}{'speedup':>10}")
    for prompt_len, gen_len in [(8, 24), (128, 128), (1024, 128), (4096, 256)]:
        naive = attention_cost(prompt_len, gen_len, 4096, cached=False)
        fast = attention_cost(prompt_len, gen_len, 4096, cached=True)
        print(f"{prompt_len:>8}{gen_len:>10}{naive / 1e9:>14,.1f} G"
              f"{fast / 1e9:>14,.1f} G{naive / fast:>9.0f}x")
    print("(d_model=4096, single head. The ratio grows with the prefix — which")
    print(" is exactly why long system prompts hurt so much without caching.)")

    print("\n=== What the cache costs in memory ===")
    cache = KVCache()
    for token in tokens:
        attention.forward_incremental(token, cache)
    print(f"toy model, {len(cache)} tokens, d=32: {cache.memory_bytes():,} bytes")
    for name, layers, heads, head_dim in [("Llama-3-8B", 32, 8, 128),
                                          ("Llama-3-70B", 80, 8, 128)]:
        per_token = 2 * layers * heads * head_dim * 2
        print(f"{name}: {per_token / 1024:.0f} KB/token -> "
              f"{per_token * 32768 / 1e9:.1f} GB for a 32k context, per sequence")
    print("That number, not the weights, is what limits your batch size.")


if __name__ == "__main__":
    _demo()

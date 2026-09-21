"""
The KV Cache — From Scratch
============================
The foundation of every other file in this directory. Pure Python linear
algebra, so nothing is hidden behind a library call.

Build attention with and without a KV cache to understand:
- Why generation without a cache is quadratic in ways it does not need to be
- That the cache is an exact optimisation, not an approximation
- Why KV memory, not model weights, is what limits your batch size
- The prefill/decode split that every serving stack is organised around

Learning Path:
1. Implement the linear algebra helpers (matmul, softmax, ...)
2. Implement SelfAttention.forward_full — the naive path
3. Implement forward_incremental — one token against a cache
4. Verify the two produce IDENTICAL output. This is the whole exercise.
5. Implement attention_cost and see how the gap scales with prefix length

Background:
  Attention for token t needs the key and value vectors of tokens 0..t. Because
  the mask is causal, those vectors depend only on tokens at or before their own
  position — so once computed, they can never change.

  Generation without a cache recomputes all of them at every step. Generation
  with a cache computes each one exactly once. Same arithmetic, same results,
  a factor of tens to hundreds less work.

  The cost is memory:

      bytes = 2 (K and V) * layers * heads * head_dim * seq_len * dtype_size

  Llama-3-8B in fp16: ~128 KB per token, so a 32k context is ~4 GB for ONE
  sequence. Every other technique in this directory exists to manage that
  number.
"""

import math
import time
from typing import List, Optional, Tuple

Matrix = List[List[float]]
Vector = List[float]


# ---------------------------------------------------------------------------
# Step 1: Linear algebra
# ---------------------------------------------------------------------------

def zeros(rows: int, cols: int) -> Matrix:
    return [[0.0] * cols for _ in range(rows)]


def transpose(a: Matrix) -> Matrix:
    """TODO: swap rows and columns. `zip(*a)` does it in one expression."""
    raise NotImplementedError


def matmul(a: Matrix, b: Matrix) -> Matrix:
    """TODO: (n, k) @ (k, m) -> (n, m). Transposing b first makes the inner
    loop a dot product of two rows, which is much faster in Python."""
    raise NotImplementedError


def matvec(a: Matrix, v: Vector) -> Vector:
    """TODO: matrix times vector."""
    raise NotImplementedError


def softmax(scores: Vector) -> Vector:
    """TODO: subtract the max BEFORE exponentiating, then normalise.

    Skipping the max subtraction overflows on large logits. It costs one pass
    and it is not optional.
    """
    raise NotImplementedError


def dot(a: Vector, b: Vector) -> float:
    raise NotImplementedError


def scale(v: Vector, factor: float) -> Vector:
    raise NotImplementedError


def add(a: Vector, b: Vector) -> Vector:
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 2-4: Attention
# ---------------------------------------------------------------------------

class OpCounter:
    """Counts multiply-accumulates, so the cost model is measured not asserted."""

    def __init__(self) -> None:
        self.macs = 0

    def add_matmul(self, n: int, k: int, m: int) -> None:
        self.macs += n * k * m

    def reset(self) -> None:
        self.macs = 0


class KVCache:
    """Per-layer store of the key and value vectors of every past token."""

    def __init__(self) -> None:
        self.keys: Matrix = []
        self.values: Matrix = []

    def append(self, k: Vector, v: Vector) -> None:
        """TODO: append one token's K and V."""
        raise NotImplementedError

    def extend(self, keys: Matrix, values: Matrix) -> None:
        raise NotImplementedError

    def truncate(self, length: int) -> None:
        """Drop everything past `length`.

        TODO: `del self.keys[length:]` and the same for values.

        This one-liner is what makes prefix reuse possible: because attention is
        causal, cutting the cache at L leaves exactly the state the model would
        have had after L tokens.
        """
        raise NotImplementedError

    def clone(self) -> "KVCache":
        """TODO: a DEEP copy — two requests forking from a shared prefix must
        not write into each other's state."""
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self.keys)

    def memory_bytes(self, dtype_size: int = 2) -> int:
        """TODO: 2 * num_tokens * dim * dtype_size."""
        raise NotImplementedError


class SelfAttention:
    """One head of causal self-attention with fixed (untrained) weights."""

    def __init__(self, d_model: int, seed: int = 0,
                 counter: Optional[OpCounter] = None):
        self.d_model = d_model
        self.counter = counter or OpCounter()
        self.w_q = _pseudo_random_matrix(d_model, d_model, seed + 1)
        self.w_k = _pseudo_random_matrix(d_model, d_model, seed + 2)
        self.w_v = _pseudo_random_matrix(d_model, d_model, seed + 3)

    def forward_full(self, x: Matrix) -> Matrix:
        """Attention over the whole sequence, recomputing every K and V.

        TODO:
        1. q, k, v = x @ w_q, x @ w_k, x @ w_v (count three matmuls).
        2. For each position t:
             scores = [dot(q[t], k[j]) / sqrt(d_model) for j in range(t + 1)]
             (the `t + 1` is the causal mask — do not attend to the future)
             weights = softmax(scores)
             output[t] = sum(weights[j] * v[j])
        3. Count the MACs for the score and weighted-sum loops too.
        """
        raise NotImplementedError

    def forward_incremental(self, x_t: Vector, cache: KVCache) -> Vector:
        """One new token attending over a cache of everything before it.

        TODO:
        1. Compute q, k, v for THIS TOKEN ONLY (matvec against the transposed
           weights — the full path uses x @ W, so this must be W^T x to match).
        2. cache.append(k, v).
        3. scores over cache.keys, softmax, weighted sum over cache.values.

        The output must equal forward_full(...)[-1] exactly. Not approximately.
        """
        raise NotImplementedError

    def prefill(self, x: Matrix, cache: KVCache) -> Matrix:
        """Process a prompt in one pass, filling the cache.

        TODO: like forward_full, but write K and V into `cache` and attend over
        `cache` (which may already hold a reused prefix, so offset by len(cache)
        before extending).

        Prefill is compute-bound and parallel across positions. Decode is
        memory-bound and strictly sequential. Serving stacks schedule them
        separately for exactly this reason.
        """
        raise NotImplementedError


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
# Step 5: The cost model
# ---------------------------------------------------------------------------

def attention_cost(prompt_len: int, gen_len: int, d_model: int,
                   cached: bool) -> int:
    """Analytic MAC count for generating `gen_len` tokens.

    TODO, cached:
      3 * prompt_len * d^2 for the prefill projections
      + 2 * (t+1) * d for each prefill position
      + per generated token: 3 * d^2 projections + 2 * (prefix + i + 1) * d

    TODO, uncached:
      per generated step i, over the whole sequence of length prompt_len + i:
      3 * n * d^2 projections + the full attention loop again

    Sanity check: a 4096-token prompt generating 256 tokens at d=4096 should
    show a couple of hundred times more work uncached.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. max |forward_full - forward_incremental| == 0. If it is not zero, your
       incremental path has a transpose or a mask wrong. Fix it before moving
       on — every later file assumes exactness.
    2. Generating 24 tokens from an 8-token prompt: roughly 13x fewer MACs with
       the cache, and a matching wall-clock speedup.
    3. The scaling table: the advantage grows with prefix length, from ~15x at
       an 8-token prompt to ~250x at 4096.
    4. The memory table: Llama-3-8B at 128 KB/token, 4.3 GB for a 32k context.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

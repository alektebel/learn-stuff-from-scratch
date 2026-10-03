"""
A Tiny Transformer With Incremental Decoding — From Scratch
============================================================
Requires: kv_cache.py.

A complete character-level decoder-only transformer in pure Python — small
enough to run in a second, real enough that the KV cache has to be exactly
right for the outputs to match.

Learning Path:
1. Implement layer_norm and gelu
2. Implement TinyTransformer.forward_token — one token, using the cache
3. Implement generate() and generate_no_cache()
4. Verify the two produce IDENTICAL token sequences
5. Implement ModelCache.truncate and clone, then reuse a prefix across requests

Architecture (GPT-style, pre-norm):
    embedding + learned positional embedding
    n_layer x [ LayerNorm -> multi-head causal attention -> residual
                LayerNorm -> MLP (4x, GELU)              -> residual ]
    final LayerNorm -> tied output projection

Why untrained weights are fine:
  The cache must reproduce the model's output for ANY weights. Training would
  slow the demo down and change nothing about the mechanism. The generated text
  will be gibberish; what matters is that both code paths produce the SAME
  gibberish, token for token.
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


# ---------------------------------------------------------------------------
# Step 1: Building blocks
# ---------------------------------------------------------------------------

def layer_norm(x: Vector, eps: float = 1e-5) -> Vector:
    """TODO: subtract the mean, divide by sqrt(variance + eps).

    No learned scale/shift here — it changes nothing about caching and keeps
    the parameter count down.
    """
    raise NotImplementedError


def gelu(x: float) -> float:
    """TODO: the tanh approximation.
    0.5x * (1 + tanh(0.7978845608 * (x + 0.044715 x^3)))
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Step 2-5: The model and its cache
# ---------------------------------------------------------------------------

class LayerCache:
    """KV cache for one layer, stored per head."""

    def __init__(self, n_head: int):
        self.keys: List[Matrix] = [[] for _ in range(n_head)]
        self.values: List[Matrix] = [[] for _ in range(n_head)]

    def __len__(self) -> int:
        return len(self.keys[0])

    def truncate(self, length: int) -> None:
        """TODO: cut every head's key and value list to `length`."""
        raise NotImplementedError

    def clone(self) -> "LayerCache":
        """TODO: a DEEP copy."""
        raise NotImplementedError


class ModelCache:
    """The full KV cache of a sequence: one LayerCache per layer."""

    def __init__(self, n_layer: int, n_head: int):
        self.layers = [LayerCache(n_head) for _ in range(n_layer)]
        self.tokens: List[int] = []

    def __len__(self) -> int:
        return len(self.tokens)

    def truncate(self, length: int) -> None:
        """TODO: truncate every layer and the token list.

        Verify this against the model: run 15 tokens, save the logits for a
        16th, then truncate back to 15 and run that 16th token again. The logits
        must be bit-identical. If they are not, prefix reuse is unsound and
        everything built on it will be subtly wrong.
        """
        raise NotImplementedError

    def clone(self) -> "ModelCache":
        """TODO: a DEEP copy, so a fork cannot corrupt the shared prefix."""
        raise NotImplementedError


class TinyTransformer:
    """A small decoder-only transformer with random (untrained) weights."""

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

    def forward_token(self, token: int, position: int,
                      cache: ModelCache) -> Vector:
        """Run one token and return its logits, appending to the cache.

        TODO:
        1. x = wte[token] + wpe[position]
        2. For each block:
             h = layer_norm(x)
             q, k, v = W^T h for each of w_q, w_k, w_v
             For each head, slice [head*head_dim : (head+1)*head_dim]:
               - append the head's k and v slices to the layer cache
               - scores = dot(q_head, past_k) / sqrt(head_dim) for every
                 cached key INCLUDING the one just appended
               - weights = softmax(scores); acc = sum(weights * past_v)
               - concatenate acc onto the attention output
             x = x + w_o^T attn_out                        (residual)
             h = layer_norm(x)
             x = x + w_proj^T gelu(w_fc^T h)               (residual)
        3. x = layer_norm(x); logits = wte @ x             (tied embedding)
        4. cache.tokens.append(token)

        Two mistakes worth watching for: forgetting to append k/v BEFORE
        computing scores (the token cannot attend to itself), and using the
        wrong `position` when reusing a cached prefix — the positional
        embedding must match the token's true position in the sequence.
        """
        raise NotImplementedError

    def forward_sequence(self, tokens: Sequence[int],
                         cache: Optional[ModelCache] = None) -> Vector:
        """TODO: run each token in turn, starting at position len(cache), and
        return the last position's logits."""
        raise NotImplementedError

    def generate(self, prompt: Sequence[int], max_new_tokens: int = 16,
                 cache: Optional[ModelCache] = None,
                 temperature: float = 0.0) -> Tuple[List[int], ModelCache]:
        """Greedy decoding on top of an existing (possibly reused) cache.

        TODO:
        1. Run only the prompt tokens NOT already in the cache
           (prompt[len(cache):]) — this is the reuse.
        2. Loop: pick argmax(logits), append it, and run it to get the next
           logits.
        3. Return the generated tokens and the cache.
        """
        raise NotImplementedError

    def generate_no_cache(self, prompt: Sequence[int],
                          max_new_tokens: int = 16) -> List[int]:
        """The same output, recomputing the whole sequence at every step.

        TODO: loop max_new_tokens times, each time calling forward_sequence on
        the FULL token list with a FRESH cache.

        This is the baseline. It must produce exactly the same tokens as
        generate() — it is not a different algorithm, just a wasteful one.
        """
        raise NotImplementedError


def _argmax(logits: Vector) -> int:
    best, best_i = logits[0], 0
    for i, value in enumerate(logits):
        if value > best:
            best, best_i = value, i
    return best_i


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
    """Once implemented, verify these four things:

    1. generate() and generate_no_cache() produce the SAME tokens, and the
       cached path uses roughly 10x fewer MACs on a 16-token generation.
    2. Reusing a 45-token system prompt across three requests saves ~50% of
       the compute versus running each cold.
    3. Truncating a cache to length L and re-running token L gives bit-identical
       logits.
    4. clone() before forking. If you share a ModelCache between two requests
       without cloning, the second one appends to the first one's state and
       both outputs go wrong — try it deliberately once so you recognise the
       failure when it happens for real.
    """
    tokenizer = CharTokenizer(CORPUS)
    model = TinyTransformer(len(tokenizer), d_model=32, n_layer=2, n_head=4)
    prompt = tokenizer.encode("the quick ")
    cached, _ = model.generate(prompt, max_new_tokens=16)
    uncached = model.generate_no_cache(prompt, max_new_tokens=16)
    print("identical:", cached == uncached)


if __name__ == "__main__":
    _demo()

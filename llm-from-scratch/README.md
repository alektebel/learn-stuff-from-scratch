# LLM From Scratch

Build the parts of a language model that people wave at — the tokenizer, attention,
sampling, the KV cache, rotary positions — in pure standard-library Python, and see the
numbers each one produces.

## Scope, honestly

A frontier model is a datacenter. A model worth **understanding** is a few hundred lines
of arithmetic with the right shape. This directory implements the five mechanisms that
everything else in an LLM is assembled from, on tiny inputs, with no dependencies:

| File | The mechanism | The thing people get wrong |
|---|---|---|
| `tokenizer.py` | Byte-pair encoding | The merge order is a *rank*, not a left-to-right pass |
| `attention.py` | Scaled dot-product attention | Softmax must subtract the max or it overflows |
| `sampling.py` | Temperature, top-k, top-p | top-p keeps the token that crosses the threshold |
| `kv_cache.py` | Incremental decoding | The cached path must be bit-identical to the full one |
| `rope.py` | Rotary position embeddings | Rotation is what makes attention depend on *relative* position |

No PyTorch, no NumPy, no GPU. If a directory cannot run with `python3 file.py`, the
lesson gets buried under an install.

---

## How to use this directory

Templates are at the top level. Complete versions are in `solutions/`.

```bash
cd llm-from-scratch
python3 check.py            # what to build next
python3 check.py            # re-run after each function
```

**13 graded checks** against **your** code. A red `✗` names the likely cause:

```
  ✗  5. attention.py         softmax: stable, sums to one
      softmax([1000, 1001]) overflowed. exp(1000) is larger than a float
      can hold, so you must subtract the row max first: exp(x - max).
      The result is identical, the overflow is gone.
```

---

## The five mechanisms

### `tokenizer.py` — the merge is a rank

BPE starts from raw bytes (so every string is representable, no `[UNK]`), counts adjacent
pairs, and repeatedly merges the most frequent one into a new symbol.

**The limit case:** when two pairs tie, the choice must be deterministic, or the same
corpus trains a different tokenizer every run and nothing downstream is reproducible. And
at encode time you must apply the **lowest-rank merge first**, in rank order — not sweep
left to right. Those two rules are the whole difference between a tokenizer and a
plausible-looking one that splits text differently than it was trained.

### `attention.py` — subtract the max

Attention is `softmax(QKᵀ/√d)·V`. The only numerically interesting line is the softmax:
compute `exp(xᵢ - max(x))`, not `exp(xᵢ)`. With logits of 1000 the naive version returns
`inf/inf = nan`, and the bug only appears once your inputs get large — which is why it
survives small tests.

**The limit case:** the causal mask. Position 0 must not be able to see position 1.
Masking to `-inf` *before* the softmax (not after) is what makes each row ignore the
future and still sum to 1.

### `sampling.py` — the crossing token counts

Temperature divides the logits. top-k keeps the `k` largest. top-p (nucleus) keeps the
smallest set of tokens whose cumulative probability reaches `p` — **including the token
that crosses the threshold**, which is the one people drop by using `>` instead of `≥`.

**The limit case:** temperature 0 must be exactly greedy (argmax), not "very sharp". And
a seeded RNG must give the same sample twice, or evals are noise.

### `kv_cache.py` — exactness, then the cost model

An autoregressive model at step *t* only needs the new query against all past keys and
values. Caching them turns per-step attention from O(t·d) recompute into O(d) work plus a
cache append.

**The limit case:** the cached result must be **bit-identical** to recomputing attention
over the full sequence. A cache that is merely close is a cache that changes your model's
output, and you will chase that difference for a day. Once it is exact, the cost model
shows why prefill is quadratic and decode is linear — the reason batching and paging exist.

### `rope.py` — relative, not absolute

Rotary embeddings rotate each `(x₂ᵢ, x₂ᵢ₊₁)` pair by an angle proportional to position.
The point is a single identity: the dot product of a query at position *p* with a key at
position *p+d* depends only on *d*, never on *p*.

**The limit case:** check the norm is preserved (rotation, so it must be) and that the
relative dot product is invariant across positions. If it drifts with *p*, your frequencies
are wrong and long-context behaviour degrades in a way short tests will not show.

---

## Where this stops

Deliberately left out, so you know the boundary:

- **No training.** These are the forward-pass mechanisms. Backprop, optimizers and data
  pipelines are a different directory (`distributed-training/`, `world-models/`).
- **No real weights.** Inputs are small hand-built vectors so the arithmetic is visible.
- **No multi-head, no RMSNorm, no SwiGLU, no residual stream.** One head, one block, one
  mechanism at a time. `context-caching/` builds the full stack on top of these ideas.
- **O(n²) on purpose.** The naive attention is the readable one; `vllm-engine/` is where
  PagedAttention and continuous batching live.

When these thirteen checks pass, the next step is `context-caching/`, which wires a KV
cache into a real (tiny) transformer and makes you keep the output bit-identical while you
page, prefix-share and evict.

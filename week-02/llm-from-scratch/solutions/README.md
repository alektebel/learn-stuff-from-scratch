# LLM From Scratch — Solutions

Complete implementations of every template in the parent directory.

```bash
python3 tokenizer.py  attention.py  transformer.py
python3 train.py          # ~80s
python3 sample.py         # ~35s
```

## Implementation notes

- **`encode_word` applies the LOWEST-RANK merge present, not the leftmost.**
  Rank is the order the merges were learned in. Apply them in the order they
  happen to appear in a word and you get a different tokenisation from the one
  training produced, and the model receives sequences it has never seen. The
  merge list ships with the weights for exactly this reason.
- **`WORD` keeps the leading space attached** (` the`, not `the`), so merges
  never span a space and ` the` and `the` are different tokens. Almost every
  generation bug involving a missing or doubled space is a tokenisation bug.
- **`masked_softmax` puts `-inf` in before the exponential.** Zeroing
  probabilities afterwards and renormalising gives the same forward answer and
  a wrong gradient — the masked scores stay inside the sum softmax
  differentiates through.
- **`MultiHeadAttention` slices one projection** rather than making h small
  ones. Mathematically identical; in practice one large matmul instead of h
  small ones, which on real hardware is most of the speed.
- **`layer_norm`'s backward pass is written by hand.** Every element of a row
  affects every other through the shared mean and variance, so composing it
  from mean and variance operations would build a large graph for what is three
  dot products.
- **`embedding`'s backward is a scatter-ADD.** A token appearing five times in
  a batch contributes five gradients to the same row. Overwrite instead and only
  the last occurrence trains — meaning common tokens, the ones with the most
  signal, learn the least.
- **`Block` is pre-norm**: `x = x + attn(norm(x))`, not `x = norm(x + attn(x))`.
  In post-norm the residual path passes through a normalisation at every layer,
  breaking the gradient highway; in pre-norm the residual stream is untouched
  from input to output. That is why post-norm needs a warmup schedule.
- **`GPT.loss` predicts `ids[1:]` from `ids[:-1]`.** A 16-token window is 15
  supervised examples in one forward pass. Predict `ids[:-1]` from itself and
  the loss collapses because every answer is visible — which the checker catches
  with an upper bound on how good the loss is allowed to be.
- **`train` accumulates gradients over several sequences before stepping.**
  Exactly equivalent to a larger batch, and it works because gradients
  accumulate by default — the property that looked like a nuisance in the
  autograd engine is what makes training models too large for a real batch
  possible.
- **`softmax` divides the LOGITS by the temperature**, before the exponential.
  Dividing the probabilities afterwards and renormalising changes the ratios
  between small probabilities rather than sharpening the distribution, and it
  is a different operation with a plausible-looking output.
- **`top_p_filter` returns the nucleus SIZE** as well as the filtered
  distribution, because that size is the interesting quantity: small where the
  model is confident, large where it is not. That adaptivity is the whole
  reason nucleus sampling replaced top-k.

## What the demos measure

`tokenizer.py` — the first ten merges with their frequencies; vocabulary size
against token count against the SQUARE of token count (attention is quadratic);
compression on in-distribution, unfamiliar, and out-of-alphabet text with a
round-trip column that exposes the character-level tokeniser's one real flaw;
and the same word tokenised under a reversed merge order.

`attention.py` — mean attention entropy at four values of `d_k` with and
without the `sqrt(d_k)` scaling (0.206 bits unscaled at 256, against 3.28
scaled and 4.0 for uniform); a causal weight matrix printed in full;
per-head entropies; and score-matrix size against sequence length from 128 to
32k, beside the linear feed-forward work.

`transformer.py` — the parameter breakdown, showing the feed-forward is bigger
than the attention; gradient norm at the input with and without residuals
(352,177x at depth 12); permutation-equivariance measured at 2.22e-16 and then
broken by a positional vector; weight tying priced up to a 50,000 vocabulary;
and pre-norm against post-norm with an honest note about how small the effect is
at depths pure Python can reach.

`train.py` — a model going from perplexity 120 to 14.2; the smoothed loss
curve; the top continuations of a prompt; and **the ablation**, where removing
the causal mask takes perplexity from 26.9 to 3.2 and produces a worthless
model with a beautiful training curve.

`sample.py` — entropy across temperatures; six decoding strategies with
repetition rate, distinct ratio and actual output, where greedy scores 85%
repetition and visibly loops (`' cat ate the cat ate the cat ate t'`); nucleus
size against context entropy; the cumulative mass table; and the quadratic cost
of generating without a KV cache.

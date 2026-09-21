"""
Attention — the operation the whole architecture is named after. Complete Solution.

    Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V

Three matmuls and a softmax. Everything else in a transformer is plumbing
around that line, and each piece of the plumbing exists for a reason this file
measures.

DESIGN DECISION — why divide by sqrt(d_k)?
  Q and K have roughly unit-variance entries, so their dot product over d_k
  dimensions has variance ~d_k and typical magnitude ~sqrt(d_k). At d_k = 64
  the scores span ±8 before training has done anything; softmax of ±8 is
  essentially one-hot, and the gradient through a saturated softmax is ~0.
  CHOSEN: divide by sqrt(d_k), which puts the scores back at unit variance.
  Section 1 measures the entropy of the attention distribution with and without
  it — unscaled, the model starts out already committed to one token per query
  and cannot learn its way out.

DESIGN DECISION — why several heads instead of one wide one?
  One head produces ONE distribution over positions. A token that needs to
  attend to its subject AND its verb has to average them, and the average is
  neither.
  CHOSEN: h heads of width d_model/h. Same parameter count, same FLOPs, h
  independent distributions. This is not a capacity increase — it is a
  structural one, and it is why "more heads" and "wider model" are different
  knobs.

DESIGN DECISION — where does the causal mask go?
  BEFORE the softmax, as -inf. After it — zeroing probabilities and
  renormalising — gives the same forward answer and a WRONG gradient, because
  the masked scores are still inside the sum softmax differentiates through.
  This is the one line standing between a language model and a model that has
  read the answer, and section 4 shows what happens without it.
"""

import math
import random
from typing import List, Optional, Sequence, Tuple

from engine import (Linear, Module, Tensor, causal_mask, concat_columns,
                    masked_softmax, slice_columns)


def scaled_dot_product(q: Tensor, k: Tensor, v: Tensor,
                       mask: Optional[List[List[bool]]] = None
                       ) -> Tuple[Tensor, Tensor]:
    """One head. Returns (output, attention weights).

    Returning the weights is not debug clutter — an attention map is the most
    interpretable object in the whole architecture, and every analysis of what
    a transformer "looks at" is a picture of this matrix.
    """
    length, d_k = q.shape
    scores = (q @ k.transpose()) * (1.0 / math.sqrt(d_k))
    weights = masked_softmax(scores, mask or [[True] * length
                                              for _ in range(length)])
    return weights @ v, weights


class MultiHeadAttention(Module):
    """h heads over one projection, sliced rather than projected separately.

    The heads are a VIEW of one d_model-wide projection, not h separate small
    ones. Mathematically identical; in practice one big matmul instead of h
    small ones, which on real hardware is most of the speed.
    """

    def __init__(self, d_model: int, heads: int, rng: Optional[random.Random] = None):
        if d_model % heads:
            raise ValueError(f"d_model {d_model} is not divisible by "
                             f"{heads} heads")
        rng = rng or random.Random(0)
        self.d_model, self.heads = d_model, heads
        self.head_dim = d_model // heads
        self.to_q = Linear(d_model, d_model, activation="linear", bias=False, rng=rng)
        self.to_k = Linear(d_model, d_model, activation="linear", bias=False, rng=rng)
        self.to_v = Linear(d_model, d_model, activation="linear", bias=False, rng=rng)
        self.out = Linear(d_model, d_model, activation="linear", rng=rng)
        self.last_weights: List[Tensor] = []

    def forward(self, x: Tensor, mask: Optional[List[List[bool]]] = None
                ) -> Tensor:
        q, k, v = self.to_q(x), self.to_k(x), self.to_v(x)
        outputs = []
        self.last_weights = []
        for head in range(self.heads):
            lo, hi = head * self.head_dim, (head + 1) * self.head_dim
            head_out, weights = scaled_dot_product(
                slice_columns(q, lo, hi), slice_columns(k, lo, hi),
                slice_columns(v, lo, hi), mask)
            outputs.append(head_out)
            self.last_weights.append(weights)
        return self.out(concat_columns(outputs))


def entropy(distribution: Sequence[float]) -> float:
    """Bits. log2(n) means "spread evenly over n options", 0 means "certain".

    This is the right measurement for an attention row precisely because it is
    scale-free: it says how many positions the query is effectively looking at,
    which is the thing scaling by sqrt(d_k) is trying to control.
    """
    total = 0.0
    for p in distribution:
        if p > 1e-12:
            total -= p * math.log2(p)
    return total


def _demo() -> None:
    print("=" * 76)
    print("ATTENTION — three matmuls, a softmax, and why each detail is there")
    print("=" * 76)

    rng = random.Random(0)

    print("\n1. Why sqrt(d_k), measured as attention entropy")
    print("-" * 76)
    print(f"    {'d_k':>6}{'unscaled entropy':>20}{'scaled entropy':>18}"
          f"{'even would be':>16}")
    length = 16
    for d_k in (4, 16, 64, 256):
        q = Tensor.randn(length, d_k, rng=random.Random(1))
        k = Tensor.randn(length, d_k, rng=random.Random(2))
        full = [[True] * length for _ in range(length)]
        raw = masked_softmax(q @ k.transpose(), full)
        scaled = masked_softmax((q @ k.transpose()) * (1 / math.sqrt(d_k)), full)
        raw_e = sum(entropy(raw.data[r * length:(r + 1) * length])
                    for r in range(length)) / length
        scaled_e = sum(entropy(scaled.data[r * length:(r + 1) * length])
                       for r in range(length)) / length
        print(f"    {d_k:>6}{raw_e:>20.3f}{scaled_e:>18.3f}"
              f"{math.log2(length):>16.3f}")
    print("  At d_k = 256 the unscaled softmax has collapsed to near-certainty")
    print("  before a single gradient step — and the gradient through a")
    print("  saturated softmax is ~0, so it cannot learn its way back out.")
    print("  Dividing by sqrt(d_k) holds the entropy near the even value at")
    print("  every width, which is what lets you make d_k larger at all.")

    print("\n2. The causal mask")
    print("-" * 76)
    x = Tensor.randn(5, 8, rng=rng)
    attention = MultiHeadAttention(8, 2, rng=random.Random(3))
    attention(x, causal_mask(5))
    weights = attention.last_weights[0]
    print("  attention weights, head 0 (rows = query position):")
    for r in range(5):
        row = weights.data[r * 5:(r + 1) * 5]
        print("    " + " ".join(f"{v:5.2f}" for v in row)
              + f"    sums to {sum(row):.3f}")
    print("  Upper triangle is exactly zero and every row still sums to 1.")
    print("  The mask is applied as -inf BEFORE the exponential. Zero the")
    print("  probabilities afterwards and the forward pass looks identical")
    print("  while the gradient is wrong — the masked scores stay inside the")
    print("  sum that softmax differentiates through.")

    print("\n3. Without the mask, the model reads the answer")
    print("-" * 76)
    unmasked = attention(x, None)
    row2_masked = attention.last_weights
    attention(x, causal_mask(5))
    print(f"  position 0 with no mask attends to "
          f"{sum(1 for v in row2_masked[0].data[:5] if v > 0.01)} positions")
    print(f"  position 0 with a causal mask attends to "
          f"{sum(1 for v in attention.last_weights[0].data[:5] if v > 0.01)}")
    print("  Train without the mask and the loss drops beautifully: predicting")
    print("  token t is trivial when you can see token t. The model learns")
    print("  nothing, generation is incoherent, and the training curve gives no")
    print("  hint at all. It is the single easiest way to waste a training run.")

    print("\n4. Heads see different things")
    print("-" * 76)
    model = MultiHeadAttention(16, 4, rng=random.Random(4))
    model(Tensor.randn(6, 16, rng=random.Random(5)), causal_mask(6))
    print(f"    {'head':>6}{'entropy of the last query row':>32}"
          f"{'attends most to':>18}")
    for index, weights in enumerate(model.last_weights):
        last = weights.data[5 * 6:6 * 6]
        print(f"    {index:>6}{entropy(last):>32.3f}"
              f"{last.index(max(last)):>18}")
    print("  Untrained, so these differences are only initialisation — but the")
    print("  STRUCTURE is the point: four independent distributions over the")
    print("  same positions. One head can only produce one, so a token needing")
    print("  both its subject and its verb would have to average them, and the")
    print("  average is neither. That is why heads are not just extra width.")

    print("\n5. The cost, and why context length is the hard limit")
    print("-" * 76)
    print(f"    {'sequence':>10}{'score matrix':>15}{'vs 128':>10}"
          f"{'FFN work':>12}{'vs 128':>9}")
    for length in (128, 512, 2048, 8192, 32768):
        scores = length * length
        ffn = length
        print(f"    {length:>10}{scores:>15,}{scores / 128 ** 2:>9.0f}x"
              f"{ffn:>12,}{ffn / 128:>8.0f}x")
    print("  Attention is quadratic; everything else in the block is linear.")
    print("  From 128 to 32k tokens the feed-forward work grows 256x and the")
    print("  score matrix grows 65,536x. That single asymmetry is the whole")
    print("  reason long context is a research area rather than a config value,")
    print("  and why FlashAttention's contribution is about MEMORY rather than")
    print("  arithmetic — the N x N matrix is the thing you cannot afford to")
    print("  write down.")

    print("\n" + "=" * 76)
    print("Next: transformer.py stacks these into a model.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()

"""
sample — turning probabilities into text. Complete Solution.

The model gives you a distribution over the vocabulary. Choosing from it is a
separate decision, it is not learned, and it changes the output more than most
architectural choices do. A model that seems repetitive and a model that seems
incoherent are frequently the same model with two decoding settings.

DESIGN DECISION — take the most likely token, or sample?
  GREEDY takes the argmax every step. It is deterministic and it is the right
  answer when there IS a right answer — translation, extraction, code. Its
  failure is degeneracy: the most likely continuation of a common phrase is
  often the phrase again, and the model locks into a loop it cannot leave,
  because nothing is random enough to break out. Section 2 measures the loop.
  SAMPLING draws from the distribution. It cannot loop, and it will occasionally
  draw a token with 0.1% probability that derails the sentence.
  CHOSEN: implement both, plus the two truncations everyone actually uses, and
  measure repetition against diversity for each.

DESIGN DECISION — temperature does what, exactly?
  Divide the logits by T before the softmax. T < 1 sharpens the distribution
  (more confident, more repetitive), T > 1 flattens it (more varied, more
  mistakes), T -> 0 is greedy exactly. It is not a "creativity" dial — it is a
  monotonic rescaling of confidence, and section 1 shows what it does to the
  entropy.

DESIGN DECISION — top-k or top-p?
  Both throw away the tail before sampling, because the tail is where the
  nonsense lives — a vocabulary of 50,000 with 0.001% each still holds a
  cumulative 50% of the mass in tokens that are all wrong.
  TOP-K keeps a fixed number. Its problem is that k is wrong in both
  directions: after "the capital of France is" one token deserves all the mass
  and k=50 lets 49 wrong ones in; after "he said" a thousand are reasonable and
  k=50 throws most away.
  TOP-P (nucleus) keeps the smallest set whose probability sums to p, so it is
  narrow when the model is confident and wide when it is not. Section 3
  measures the size of that set on confident and uncertain positions.
"""

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

from engine import Tensor
from tokenizer import CORPUS, BPETokenizer
from transformer import GPT


def softmax(logits: Sequence[float], temperature: float = 1.0) -> List[float]:
    """Temperature is a division BEFORE the exponential, not a rescaling after.

    Dividing the probabilities afterwards and renormalising is a different and
    wrong operation: it changes the ratios of small probabilities to each other
    rather than sharpening the whole distribution.
    """
    if temperature <= 0:
        best = max(range(len(logits)), key=lambda i: logits[i])
        return [1.0 if i == best else 0.0 for i in range(len(logits))]
    scaled = [v / temperature for v in logits]
    biggest = max(scaled)
    exponentials = [math.exp(v - biggest) for v in scaled]
    total = sum(exponentials)
    return [v / total for v in exponentials]


def entropy(distribution: Sequence[float]) -> float:
    return -sum(p * math.log2(p) for p in distribution if p > 1e-12)


def top_k_filter(probabilities: Sequence[float], k: int) -> List[float]:
    """Keep the k most likely, renormalise the rest to zero."""
    if k <= 0 or k >= len(probabilities):
        return list(probabilities)
    threshold = sorted(probabilities, reverse=True)[k - 1]
    kept = [p if p >= threshold else 0.0 for p in probabilities]
    total = sum(kept)
    return [p / total for p in kept]


def top_p_filter(probabilities: Sequence[float], p: float
                 ) -> Tuple[List[float], int]:
    """Nucleus sampling. Returns (filtered, size of the nucleus).

    The size is returned because it is the interesting quantity: it is small
    where the model is confident and large where it is not, which is exactly
    what top-k cannot do.
    """
    order = sorted(range(len(probabilities)), key=lambda i: -probabilities[i])
    kept = [0.0] * len(probabilities)
    cumulative = 0.0
    size = 0
    for index in order:
        kept[index] = probabilities[index]
        cumulative += probabilities[index]
        size += 1
        if cumulative >= p:
            break
    total = sum(kept)
    return [v / total for v in kept], size


def choose(probabilities: Sequence[float], rng: random.Random) -> int:
    draw = rng.random()
    cumulative = 0.0
    for index, p in enumerate(probabilities):
        cumulative += p
        if draw <= cumulative:
            return index
    return len(probabilities) - 1


def generate(model: GPT, prompt_ids: Sequence[int], length: int = 40,
             temperature: float = 1.0, top_k: int = 0, top_p: float = 0.0,
             greedy: bool = False, rng: Optional[random.Random] = None
             ) -> List[int]:
    """Autoregressive generation: append, feed back, repeat.

    Note that the whole prefix is re-run every step. That is O(n^2) in the
    output length and it is precisely the waste a KV cache removes — see
    ../context-caching/, which is the same model from the serving side.
    """
    rng = rng or random.Random(0)
    ids = list(prompt_ids)
    for _ in range(length):
        window = ids[-model.block_size:]
        logits = model(window)
        _, vocab = logits.shape
        last = logits.data[(len(window) - 1) * vocab:len(window) * vocab]
        if greedy:
            ids.append(max(range(vocab), key=lambda i: last[i]))
            continue
        probabilities = softmax(last, temperature)
        if top_k:
            probabilities = top_k_filter(probabilities, top_k)
        if top_p:
            probabilities, _ = top_p_filter(probabilities, top_p)
        ids.append(choose(probabilities, rng))
    return ids


def repetition_rate(ids: Sequence[int], window: int = 4) -> float:
    """Fraction of `window`-grams that have appeared before.

    A blunt instrument and a very effective one: greedy decoding on a small
    model scores near 1.0 here, and no amount of reading the output tells you
    that as quickly as one number does.
    """
    seen = set()
    repeats = total = 0
    for i in range(len(ids) - window + 1):
        gram = tuple(ids[i:i + window])
        total += 1
        if gram in seen:
            repeats += 1
        seen.add(gram)
    return repeats / max(1, total)


def distinct_ratio(ids: Sequence[int]) -> float:
    return len(set(ids)) / max(1, len(ids))


def _demo() -> None:
    import train as training

    print("=" * 78)
    print("sample — the decisions that are not in the weights")
    print("=" * 78)

    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=120)
    tokens = tokenizer.encode(CORPUS)
    model = GPT(tokenizer.size, d_model=24, heads=2, layers=1, block_size=16,
                tie_weights=True, seed=1)
    print("\n  training a small model first (about half a minute)...")
    history = training.train(model, tokens, steps=200, lr=0.03, seed=1)
    print(f"  held-out perplexity {training.perplexity(history['held_out'][-1]):.1f} "
          f"against {tokenizer.size} for a uniform model")

    prompt = "the cat sat on the"
    prompt_ids = tokenizer.encode(prompt)

    print("\n1. Temperature is a rescaling of confidence")
    print("-" * 78)
    logits = model(prompt_ids[-8:])
    _, vocab = logits.shape
    last = logits.data[(len(prompt_ids[-8:]) - 1) * vocab:
                       len(prompt_ids[-8:]) * vocab]
    print(f"    {'T':>6}{'entropy (bits)':>17}{'top token':>13}"
          f"{'its probability':>18}")
    for temperature in (0.01, 0.5, 0.8, 1.0, 1.5, 3.0):
        p = softmax(last, temperature)
        best = max(range(vocab), key=lambda i: p[i])
        print(f"    {temperature:>6.2f}{entropy(p):>17.3f}"
              f"{tokenizer.inverse.get(best, '?')!r:>13}{p[best]:>18.1%}")
    print(f"  a uniform distribution over {vocab} tokens would be "
          f"{math.log2(vocab):.2f} bits")
    print("  T -> 0 is greedy exactly. T > 1 flattens towards uniform. It is a")
    print("  monotonic confidence dial, not a creativity setting, and the top")
    print("  token never changes — only how much mass it keeps.")

    print("\n2. Five decoding strategies on the same model")
    print("-" * 78)
    print(f"    {'strategy':<24}{'repetition':>12}{'distinct':>11}  sample")
    strategies = [
        ("greedy", dict(greedy=True)),
        ("T=0.5", dict(temperature=0.5)),
        ("T=1.0", dict(temperature=1.0)),
        ("T=1.0, top-k=8", dict(temperature=1.0, top_k=8)),
        ("T=1.0, top-p=0.9", dict(temperature=1.0, top_p=0.9)),
        ("T=2.0", dict(temperature=2.0)),
    ]
    for label, options in strategies:
        ids = generate(model, prompt_ids, length=45,
                       rng=random.Random(7), **options)
        text = tokenizer.decode(ids)[len(prompt):].replace("\n", " ")
        print(f"    {label:<24}{repetition_rate(ids):>11.0%}"
              f"{distinct_ratio(ids):>11.0%}  {text[:34]!r}")
    print("  Greedy is deterministic and loops: the most likely continuation of")
    print("  a common phrase is very often the phrase again, and nothing is")
    print("  random enough to break out. Raising the temperature fixes the loop")
    print("  and starts inventing. Top-k and top-p keep the sampling while")
    print("  removing the tail where the nonsense lives.")

    print("\n3. Why top-p rather than top-k")
    print("-" * 78)
    print(f"    {'context':<26}{'entropy':>9}{'nucleus at p=0.9':>19}"
          f"{'top-k=8 keeps':>16}")
    for context in ("the cat sat on the", "the", "a bird sat on the l"):
        ids = tokenizer.encode(context)[-8:]
        out = model(ids)
        _, v = out.shape
        row = out.data[(len(ids) - 1) * v:len(ids) * v]
        p = softmax(row, 1.0)
        _, size = top_p_filter(p, 0.9)
        print(f"    {context!r:<26}{entropy(p):>9.2f}{size:>19}{8:>16}")
    print("  The nucleus grows and shrinks with the model's confidence; k does")
    print("  not. After a context with one obvious continuation, k=8 admits")
    print("  seven wrong tokens; after an open one, it discards good ones.")
    print("  That single adaptivity is why top-p became the default.")

    print("\n4. The tail is bigger than it looks")
    print("-" * 78)
    p = softmax(last, 1.0)
    ranked = sorted(p, reverse=True)
    print(f"    {'tokens kept':>13}{'probability mass':>19}")
    for count in (1, 3, 8, 20, 50, vocab):
        print(f"    {min(count, vocab):>13}{sum(ranked[:count]):>19.1%}")
    tail = sum(1 for value in p if value < 0.001)
    print(f"  {tail} of {vocab} tokens are individually under 0.1% here, "
          f"holding")
    print(f"  {sum(v for v in p if v < 0.001):.1%} of the mass between them. "
          f"Now scale the vocabulary:")
    print("  at 50,000 tokens a tail of 49,000 at 0.001% each is half the")
    print("  distribution, every token in it is wrong, and pure sampling draws")
    print("  from it on most steps.")
    print("  Truncation is not an optimisation — it is what makes sampling")
    print("  usable at all.")

    print("\n5. Generation is quadratic, and that is the next directory")
    print("-" * 78)
    print(f"    {'tokens generated':>18}{'forward passes':>16}"
          f"{'positions processed':>21}")
    for length in (10, 50, 200, 1000):
        positions = sum(min(i + len(prompt_ids), model.block_size)
                        for i in range(length))
        print(f"    {length:>18}{length:>16}{positions:>21,}")
    print("  Every step re-runs the whole prefix, because nothing remembers the")
    print("  keys and values it computed last time. With a block size of 16")
    print("  this is bounded; with a 4,000-token context it is the difference")
    print("  between a usable model and an unusable one — and removing exactly")
    print("  this waste is what ../context-caching/ is about.")

    print("\n" + "=" * 78)
    print("You wrote the tokeniser, the attention, the model, the training")
    print("loop and the sampler. Nothing above imported a framework.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()

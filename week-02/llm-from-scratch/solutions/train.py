"""
train — fitting a language model to text. Complete Solution.

Next-token prediction, and that is the whole objective: given tokens 0..i-1,
put probability mass on token i. Everything a language model appears to know
is a side effect of getting good at that one game.

DESIGN DECISION — what is the loss, really?
  Cross-entropy on the next token, averaged over every position. A sequence of
  16 tokens is 15 supervised examples in ONE forward pass, which is why
  language models are so sample-efficient per unit of text — and why the causal
  mask has to be exactly right. One position seeing one token too far and every
  example after it is free.

DESIGN DECISION — what number do you actually watch?
  Cross-entropy in nats is hard to have intuition about. PERPLEXITY —
  exp(loss) — is "how many tokens is the model effectively choosing between".
  A perplexity of 1 is certainty; a perplexity equal to the vocabulary size is
  a model that has learned nothing. That gives you two reference points to read
  every number against, which raw loss does not.

THE ABLATION THAT MATTERS, and section 4 runs it:
  Train the same model with the causal mask removed. The loss collapses far
  below anything the masked model reaches, and the samples are incoherent.
  Predicting token t is trivial when you can see token t. Nothing in the
  training curve hints at the problem — it looks like a triumph — which makes
  it the easiest way there is to waste a training run.
"""

import math
import random
import time
from typing import Dict, List, Optional, Sequence, Tuple

from engine import Adam, Tensor, causal_mask, clip_grad_norm, cosine_schedule
from tokenizer import CORPUS, BPETokenizer, CharTokenizer
from transformer import GPT


def make_batches(ids: Sequence[int], block_size: int, count: int,
                 rng: random.Random) -> List[List[int]]:
    """Random windows into one long token stream.

    Windows, not sentences. A language model is trained on a continuous stream
    chopped anywhere, which is why it happily continues from mid-sentence and
    why the first token of every window has no context at all.
    """
    out = []
    for _ in range(count):
        start = rng.randrange(0, max(1, len(ids) - block_size - 1))
        out.append(list(ids[start:start + block_size + 1]))
    return out


def perplexity(loss: float) -> float:
    """exp(cross-entropy). 'How many tokens is it choosing between.'"""
    return math.exp(min(loss, 60.0))


def evaluate(model: GPT, batches: Sequence[Sequence[int]]) -> float:
    total = 0.0
    for batch in batches:
        total += model.loss(batch).item()
    return total / max(1, len(batches))


def train(model: GPT, tokens: Sequence[int], steps: int = 150,
          lr: float = 0.01, block_size: int = 16, warmup: int = 10,
          clip: float = 1.0, seed: int = 0, log_every: int = 0,
          masked: bool = True, accumulate: int = 4) -> Dict[str, List[float]]:
    """The loop. `masked=False` exists only so section 4 can run the ablation.

    `accumulate` is gradient accumulation: run several sequences, let their
    gradients ADD UP in `.grad`, and step once. It is exactly equivalent to a
    larger batch — because gradients accumulate by default, which is the
    property that looked like a nuisance in the autograd engine — and it is how
    every model too large to fit a real batch in memory is trained.
    """
    optimizer = Adam(model.parameters(), lr=lr)
    rng = random.Random(seed)
    holdout = make_batches(tokens, block_size, 12, random.Random(999))
    history: Dict[str, List[float]] = {"loss": [], "held_out": [], "lr": []}

    if not masked:
        _disable_mask(model)

    for step in range(steps):
        optimizer.lr = cosine_schedule(step, steps, lr, warmup=warmup,
                                       min_lr=lr * 0.05)
        optimizer.zero_grad()
        total = 0.0
        for batch in make_batches(tokens, block_size, accumulate, rng):
            loss = model.loss(batch)
            # No zero_grad in here: the gradients from every sequence in the
            # accumulation window add together, which is what makes this
            # identical to one larger batch.
            loss.backward()
            total += loss.item()
        for parameter in model.parameters():
            if parameter.grad:
                parameter.grad = [g / accumulate for g in parameter.grad]
        clip_grad_norm(model.parameters(), clip)
        optimizer.step()
        history["loss"].append(total / accumulate)
        history["lr"].append(optimizer.lr)
        if log_every and (step + 1) % log_every == 0:
            held = evaluate(model, holdout)
            history["held_out"].append(held)
            print(f"    step {step + 1:>4}  loss {loss.item():.4f}  "
                  f"held-out {held:.4f}  perplexity {perplexity(held):.1f}")
    if not history["held_out"]:
        history["held_out"].append(evaluate(model, holdout))
    return history


def _disable_mask(model: GPT) -> None:
    """Make every block attend everywhere. ONLY for the ablation in section 4.

    This is what a missing causal mask looks like, and the reason it is worth
    running deliberately once is that in a real codebase it never announces
    itself — the loss simply looks wonderful.
    """
    for block in model.blocks:
        original = block.forward

        def patched(x, mask=None, _original=original):
            return _original(x, None)

        block.forward = patched


def _smooth(values: Sequence[float], window: int = 10) -> List[float]:
    out = []
    for i in range(0, len(values), window):
        chunk = values[i:i + window]
        out.append(sum(chunk) / len(chunk))
    return out


def _demo() -> None:
    print("=" * 78)
    print("train — next-token prediction, and the ablation that looks like a win")
    print("=" * 78)

    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=120)
    tokens = tokenizer.encode(CORPUS)
    print(f"\n  corpus: {len(CORPUS):,} characters -> {len(tokens):,} tokens, "
          f"vocabulary {tokenizer.size}")
    print(f"  a uniform model would have perplexity {tokenizer.size} "
          f"(loss {math.log(tokenizer.size):.3f})")
    print("  (this file trains three small models; give it a minute)")

    print("\n1. Training")
    print("-" * 78)
    model = GPT(tokenizer.size, d_model=24, heads=2, layers=1, block_size=16,
                tie_weights=True, seed=1)
    print(f"  {model.num_parameters():,} parameters")
    start = time.perf_counter()
    history = train(model, tokens, steps=200, lr=0.03, log_every=40)
    elapsed = time.perf_counter() - start
    final = history["held_out"][-1]
    print(f"  {elapsed:.0f}s. Held-out loss {final:.4f}, "
          f"perplexity {perplexity(final):.1f} against "
          f"{tokenizer.size} for a uniform model.")
    print("  Perplexity is the number to watch: it is how many tokens the model")
    print("  is effectively choosing between. Two reference points make every")
    print("  reading meaningful — 1 is certainty, vocabulary size is ignorance.")

    print("\n2. The loss curve, smoothed")
    print("-" * 78)
    smoothed = _smooth(history["loss"], 20)
    worst = max(smoothed)
    for index, value in enumerate(smoothed):
        bar = "#" * int(40 * value / worst)
        print(f"    steps {index * 20 + 1:>4}-{(index + 1) * 20:<4} "
              f"{value:>7.4f}  {bar}")

    print("\n3. What it predicts")
    print("-" * 78)
    prompt = "the cat sat on the"
    ids = tokenizer.encode(prompt)[-8:]
    logits = model(ids)
    _, vocab = logits.shape
    last = logits.data[(len(ids) - 1) * vocab:len(ids) * vocab]
    biggest = max(last)
    exponentials = [math.exp(v - biggest) for v in last]
    total = sum(exponentials)
    ranked = sorted(range(vocab), key=lambda i: -exponentials[i])[:6]
    print(f"  after {prompt!r}, the top continuations are:")
    for token in ranked:
        print(f"    {tokenizer.inverse.get(token, '?')!r:<12}"
              f"{exponentials[token] / total:>8.1%}")
    print("  On a corpus this small the model is mostly learning which tokens")
    print("  follow which — which is exactly what next-token prediction IS.")

    print("\n4. The ablation: train without the causal mask")
    print("-" * 78)
    honest = GPT(tokenizer.size, d_model=24, heads=2, layers=1, block_size=16,
                 tie_weights=True, seed=2)
    honest_history = train(honest, tokens, steps=150, lr=0.03, seed=3)

    cheating = GPT(tokenizer.size, d_model=24, heads=2, layers=1, block_size=16,
                   tie_weights=True, seed=2)
    cheat_history = train(cheating, tokens, steps=150, lr=0.03, seed=3,
                          masked=False)

    print(f"    {'model':<28}{'final training loss':>21}{'perplexity':>13}")
    print(f"    {'with the causal mask':<28}"
          f"{sum(honest_history['loss'][-20:]) / 20:>21.4f}"
          f"{perplexity(sum(honest_history['loss'][-20:]) / 20):>13.1f}")
    print(f"    {'without it':<28}"
          f"{sum(cheat_history['loss'][-20:]) / 20:>21.4f}"
          f"{perplexity(sum(cheat_history['loss'][-20:]) / 20):>13.1f}")
    print("  The unmasked model's loss is far lower and the model is worthless:")
    print("  predicting token t is trivial when you can attend to token t.")
    print("  Nothing in that curve says anything is wrong — it looks like the")
    print("  best run you have ever had. The only way to catch it is to")
    print("  GENERATE, or to assert the mask directly in a test.")

    print("\n5. Tokeniser choice changes what a step is worth")
    print("-" * 78)
    characters = CharTokenizer(CORPUS)
    char_tokens = characters.encode(CORPUS)
    print(f"    {'tokeniser':<14}{'vocab':>7}{'tokens':>9}"
          f"{'chars per 16-token window':>28}")
    print(f"    {'characters':<14}{characters.size:>7}{len(char_tokens):>9}"
          f"{16:>28}")
    print(f"    {'BPE':<14}{tokenizer.size:>7}{len(tokens):>9}"
          f"{16 * tokenizer.compression(CORPUS):>28.0f}")
    print("  Same block size, same compute per step, and the BPE model sees")
    print("  three to four times as much TEXT in each one. Its perplexity is")
    print("  not comparable to the character model's — different vocabularies")
    print("  mean different denominators — which is why perplexity is only")
    print("  meaningful between models sharing a tokeniser. Comparing")
    print("  perplexities across tokenisers is a very common mistake.")

    print("\n" + "=" * 78)
    print("Next: sample.py turns these probabilities into text.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()

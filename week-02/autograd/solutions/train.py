"""
train — the loop, and the numbers that tell you it is working. Complete Solution.

Six lines do the work:

    zero the gradients          or they accumulate from the last step
    forward                     build the tape
    loss                        one scalar, so backward needs no seed
    backward                    walk the tape, fill every .grad
    optimizer.step()            move against the gradients
    measure on HELD-OUT data    the only number that means anything

Everything else in a training script is instrumentation, and the instrumentation
is most of what makes the difference between a run you can debug and one you
cannot.

DESIGN DECISION — what to measure, and how often?
  Training loss alone is nearly useless: it goes down for a model that is
  memorising just as smoothly as for one that is learning.
  CHOSEN: train loss AND held-out accuracy, every epoch, on the same axis. The
  gap between them IS overfitting, and section 4 makes that gap appear on
  demand by shrinking the training set.

DESIGN DECISION — full-batch, single-sample, or mini-batch?
  Full-batch gives the exact gradient and one update per pass over the data.
  Single-sample gives a very noisy gradient and many updates.
  CHOSEN: mini-batch, and the demo sweeps the size so you can see the trade
  rather than take it on faith. The noise in a small batch is not purely a
  cost — it is also what lets the optimiser leave sharp minima.

THE FIRST THING TO CHECK, ALWAYS:
  Before a single hyperparameter, overfit a tiny subset. Ten examples, no
  regularisation, as many steps as it takes. If the model cannot drive the loss
  on TEN examples to nearly zero, it will never learn the full dataset, and you
  have a bug rather than a tuning problem. Section 1 does this first for that
  reason.
"""

import math
import random
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import digits
from nn import Linear, Module, ReLU, Sequential, Tanh, train_mode
from optim import Adam, Optimizer, SGD, clip_grad_norm
from tensor import Tensor


def accuracy(model: Module, xs: List[List[float]], ys: List[int],
             batch: int = 128) -> float:
    correct = 0
    for start in range(0, len(xs), batch):
        chunk_x = xs[start:start + batch]
        chunk_y = ys[start:start + batch]
        logits = model(Tensor.from_rows(chunk_x))
        _, classes = logits.shape
        for row, target in enumerate(chunk_y):
            scores = logits.data[row * classes:(row + 1) * classes]
            if scores.index(max(scores)) == target:
                correct += 1
    return correct / len(xs)


def train(model: Module, train_x: List[List[float]], train_y: List[int],
          test_x: List[List[float]], test_y: List[int],
          optimizer: Optimizer, epochs: int = 12, batch_size: int = 32,
          clip: Optional[float] = None, seed: int = 0,
          log: bool = False) -> Dict[str, List[float]]:
    rng = random.Random(seed)
    history: Dict[str, List[float]] = {"loss": [], "train_acc": [],
                                       "test_acc": [], "grad_norm": []}
    for epoch in range(epochs):
        train_mode(model, True)
        total, count, norms = 0.0, 0, []
        for batch_x, batch_y in digits.batches(train_x, train_y, batch_size, rng):
            optimizer.zero_grad()
            logits = model(Tensor.from_rows(batch_x))
            loss = logits.softmax_cross_entropy(batch_y)
            loss.backward()
            norms.append(clip_grad_norm(optimizer.parameters,
                                        clip if clip else float("inf")))
            optimizer.step()
            total += loss.item()
            count += 1
        train_mode(model, False)
        history["loss"].append(total / max(1, count))
        history["train_acc"].append(accuracy(model, train_x, train_y))
        history["test_acc"].append(accuracy(model, test_x, test_y))
        history["grad_norm"].append(sum(norms) / max(1, len(norms)))
        if log:
            print(f"    epoch {epoch + 1:>2}  loss {history['loss'][-1]:.4f}  "
                  f"train {history['train_acc'][-1]:.1%}  "
                  f"test {history['test_acc'][-1]:.1%}")
    return history


def overfit_check(model: Module, xs: List[List[float]], ys: List[int],
                  steps: int = 200, lr: float = 0.01) -> float:
    """Drive the loss on a handful of examples to zero. Do this FIRST.

    It is a test of the plumbing, not of the model: are the gradients flowing,
    are the parameters registered, is the loss connected to the output. A model
    that cannot memorise ten examples has a bug, and no amount of learning-rate
    search will fix a bug.
    """
    optimizer = Adam(model.parameters(), lr=lr)
    batch = Tensor.from_rows(xs)
    loss = float("inf")
    for _ in range(steps):
        optimizer.zero_grad()
        out = model(batch).softmax_cross_entropy(ys)
        out.backward()
        optimizer.step()
        loss = out.item()
    return loss


def build_mlp(hidden: Sequence[int] = (48,), seed: int = 0,
              activation: str = "relu") -> Sequential:
    rng = random.Random(seed)
    layers: List[Module] = []
    fan_in = digits.PIXELS
    for width in hidden:
        layers.append(Linear(fan_in, width, activation=activation, rng=rng))
        layers.append(ReLU() if activation == "relu" else Tanh())
        fan_in = width
    layers.append(Linear(fan_in, 10, activation="linear", rng=rng))
    return Sequential(*layers)


def confusion(model: Module, xs: List[List[float]], ys: List[int]
              ) -> List[List[int]]:
    matrix = [[0] * 10 for _ in range(10)]
    logits = model(Tensor.from_rows(xs))
    _, classes = logits.shape
    for row, target in enumerate(ys):
        scores = logits.data[row * classes:(row + 1) * classes]
        matrix[target][scores.index(max(scores))] += 1
    return matrix


def _bar(value: float, width: int = 28) -> str:
    return "#" * int(round(value * width)) + "." * (width - int(round(value * width)))


def _demo() -> None:
    print("=" * 76)
    print("train — six lines of loop, and the numbers around them")
    print("=" * 76)

    # noise=0.35, not 0.12. At low noise these digits are very nearly linearly
    # separable and every model scores 100%, which makes for a demo where no
    # comparison shows anything. Pick a difficulty where the models differ.
    xs, ys = digits.make_dataset(800, noise=0.35, seed=0)
    xs = digits.normalize(xs)
    (train_x, train_y), (test_x, test_y) = digits.split(xs, ys)
    print(f"\n  {len(train_x)} train / {len(test_x)} test, "
          f"{digits.PIXELS} pixels, 10 classes")

    print("\n1. First: can it overfit ten examples?")
    print("-" * 76)
    model = build_mlp((48,), seed=1)
    final = overfit_check(model, train_x[:10], train_y[:10], steps=250)
    print(f"  loss on 10 examples after 250 steps: {final:.6f}")
    assert final < 0.02, "the plumbing is broken, not the hyperparameters"
    print("  Near zero, so gradients flow, every parameter is registered, and")
    print("  the loss is connected to the output. Do this BEFORE tuning")
    print("  anything: a model that cannot memorise ten examples has a bug, and")
    print("  no learning-rate sweep fixes a bug.")

    print("\n2. Linear model against an MLP")
    print("-" * 76)
    print(f"    {'model':<28}{'params':>9}{'train':>9}{'test':>9}{'seconds':>10}")
    results = {}
    for label, build in (
            ("linear (no hidden layer)", lambda: build_mlp((), seed=2)),
            ("MLP 64-48-10", lambda: build_mlp((48,), seed=2)),
            ("MLP 64-48-48-10", lambda: build_mlp((48, 48), seed=2))):
        model = build()
        start = time.perf_counter()
        history = train(model, train_x, train_y, test_x, test_y,
                        Adam(model.parameters(), lr=0.01), epochs=8)
        elapsed = time.perf_counter() - start
        results[label] = (model, history)
        print(f"    {label:<28}{model.num_parameters():>9,}"
              f"{history['train_acc'][-1]:>9.1%}{history['test_acc'][-1]:>9.1%}"
              f"{elapsed:>10.1f}")
    print("  The linear model is one matrix: it can only draw straight")
    print("  boundaries in pixel space. The hidden layer is what buys the")
    print("  difference, and the SECOND hidden layer buys much less — depth has")
    print("  sharply diminishing returns on a problem this small, which is")
    print("  worth having measured before assuming otherwise on a large one.")
    print("  Note also the seconds column: the MLP costs 4x the linear model")
    print("  for a few points of accuracy. That ratio is the whole argument")
    print("  behind every 'is this worth it' conversation in production.")

    model, history = results["MLP 64-48-10"]
    print("\n3. The learning curve")
    print("-" * 76)
    print(f"    {'epoch':>6}{'loss':>9}{'train':>9}{'test':>9}  test accuracy")
    for epoch in range(len(history["loss"])):
        print(f"    {epoch + 1:>6}{history['loss'][epoch]:>9.4f}"
              f"{history['train_acc'][epoch]:>9.1%}"
              f"{history['test_acc'][epoch]:>9.1%}  "
              f"{_bar(history['test_acc'][epoch])}")

    print("\n4. Overfitting, produced on demand")
    print("-" * 76)
    print(f"    {'training examples':>18}{'train acc':>12}{'test acc':>11}"
          f"{'gap':>8}")
    for size in (40, 120, 600):
        model = build_mlp((64,), seed=3)
        history = train(model, train_x[:size], train_y[:size], test_x, test_y,
                        Adam(model.parameters(), lr=0.01), epochs=20,
                        batch_size=min(32, size))
        gap = history["train_acc"][-1] - history["test_acc"][-1]
        print(f"    {size:>18}{history['train_acc'][-1]:>12.1%}"
              f"{history['test_acc'][-1]:>11.1%}{gap:>8.1%}")
    print("  With 40 examples the model reaches 100% on training data and much")
    print("  less on held-out data: it memorised. The GAP is the measurement —")
    print("  training loss alone falls just as smoothly in both cases, which is")
    print("  why a training curve on its own tells you almost nothing.")

    print("\n5. Batch size: the trade, measured")
    print("-" * 76)
    print(f"    {'batch':>7}{'updates/epoch':>15}{'test acc':>11}{'seconds':>10}")
    for batch_size in (8, 32, 128, 600):
        model = build_mlp((48,), seed=4)
        start = time.perf_counter()
        history = train(model, train_x, train_y, test_x, test_y,
                        Adam(model.parameters(), lr=0.01), epochs=6,
                        batch_size=batch_size)
        elapsed = time.perf_counter() - start
        print(f"    {batch_size:>7}{len(train_x) // batch_size:>15}"
              f"{history['test_acc'][-1]:>11.1%}{elapsed:>10.1f}")
    print("  Full batch takes ONE update per epoch, so six epochs is six")
    print("  updates and it has barely started. Small batches take many noisy")
    print("  steps and get further per pass over the data. The noise is not")
    print("  purely a cost: it is also what lets the optimiser escape sharp")
    print("  minima, which is why the largest batch that fits in memory is not")
    print("  automatically the right one.")

    print("\n6. What it actually confuses")
    print("-" * 76)
    # Deliberately on the HARDER dataset. At noise 0.12 this model is at 100%
    # and a confusion matrix of zeros teaches nothing; the interesting question
    # is which pairs it confuses when it is forced to make mistakes.
    hx, hy = digits.make_dataset(700, noise=0.45, seed=11)
    hx = digits.normalize(hx)
    (htx, hty), (hvx, hvy) = digits.split(hx, hy)
    model = build_mlp((48,), seed=6)
    train(model, htx, hty, hvx, hvy, Adam(model.parameters(), lr=0.01),
          epochs=10)
    print(f"  a model trained at noise=0.45, scoring "
          f"{accuracy(model, hvx, hvy):.1%} on held-out data:")
    matrix = confusion(model, hvx, hvy)
    print("       " + "".join(f"{d:>5}" for d in range(10)) + "   <- predicted")
    for actual in range(10):
        row = "".join(f"{matrix[actual][p]:>5}" for p in range(10))
        print(f"    {actual}  {row}")
    mistakes = sorted(((matrix[a][p], a, p) for a in range(10)
                       for p in range(10) if a != p), reverse=True)[:3]
    print("  most common confusions: " + ", ".join(
        f"{a} read as {p} ({n}x)" for n, a, p in mistakes if n))
    print("  A confusion matrix says which pairs the model finds ambiguous, and")
    print("  they are usually the pairs a person would name. An aggregate")
    print("  accuracy cannot tell you that, and 'improve accuracy' is a much")
    print("  harder instruction than 'separate 3 from 8'.")

    print("\n7. Noise: where accuracy actually comes from")
    print("-" * 76)
    print(f"    {'noise':>7}{'test accuracy':>16}")
    for noise in (0.0, 0.12, 0.35, 0.7):
        nx, ny = digits.make_dataset(500, noise=noise, seed=7)
        nx = digits.normalize(nx)
        (tx, ty), (vx, vy) = digits.split(nx, ny)
        model = build_mlp((48,), seed=5)
        history = train(model, tx, ty, vx, vy,
                        Adam(model.parameters(), lr=0.01), epochs=8)
        print(f"    {noise:>7.2f}{history['test_acc'][-1]:>16.1%}")
    print("  Report an accuracy without saying what the data looked like and")
    print("  the number means nothing. At noise 0.8 a person cannot read these")
    print("  either — go back and look at digits.py's noise ladder.")

    print("\n" + "=" * 76)
    print("Next: generative.py learns to WRITE digits rather than read them.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()

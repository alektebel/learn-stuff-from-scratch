"""
optim — what to do with a gradient. Complete Solution.

The gradient says which direction increases the loss. An optimiser decides how
far to move against it, and that decision is where most of the difference
between "trains in 200 steps" and "does not train" lives.

DESIGN DECISION — plain SGD, or something adaptive?
  SGD is `p -= lr * g` and it is one line. Its problem is that ONE learning rate
  has to suit every parameter, and in a real network the gradient scales differ
  by orders of magnitude between layers. Pick a rate that suits the largest and
  the smallest never move; suit the smallest and the largest diverge.
  CHOSEN: implement SGD, momentum, RMSProp and Adam, because the progression is
  the explanation. Each one fixes a specific failure of the last, and the demo
  puts all four on the same problem so you can see which failure each fixes.
  Adam is not "better" — it is SGD plus momentum plus a per-parameter scale,
  and it costs three extra copies of every parameter in memory.

DESIGN DECISION — is the learning rate a hyperparameter, or the hyperparameter?
  CHOSEN: the demo sweeps it across four orders of magnitude, because the shape
  of that curve is the most useful thing to have seen. Too small is slow and
  obvious. Too large does not "converge more roughly" — it DIVERGES, and the
  boundary between them is sharp rather than gradual.

DESIGN DECISION — where does weight decay go?
  Adding `wd * p` to the gradient is what "L2 regularisation" means, and for
  SGD the two are identical. For Adam they are NOT: the decay term gets divided
  by the same adaptive denominator as the gradient, so parameters with small
  gradients get decayed less — the opposite of the intent.
  CHOSEN: implement both, and let the demo show the difference. AdamW exists
  entirely because of this, and it is one line apart from Adam.
"""

import math
from typing import Dict, List, Optional, Sequence

from tensor import Tensor


class Optimizer:
    def __init__(self, parameters: Sequence[Tensor], lr: float):
        self.parameters = list(parameters)
        self.lr = lr
        self.steps = 0

    def zero_grad(self) -> None:
        for parameter in self.parameters:
            parameter.zero_grad()

    def step(self) -> None:
        raise NotImplementedError

    def _gradients(self) -> List[List[float]]:
        return [p.grad if p.grad is not None else [0.0] * len(p.data)
                for p in self.parameters]


class SGD(Optimizer):
    """p -= lr * g, optionally with momentum.

    MOMENTUM is a running average of past gradients, and the intuition that
    actually predicts its behaviour is a ravine: a long narrow valley where the
    gradient points mostly across the valley rather than along it. Plain SGD
    zig-zags between the walls; momentum cancels the oscillating component
    (it flips sign each step) and accumulates the consistent one (it does not).
    The demo builds exactly that ravine.
    """

    def __init__(self, parameters: Sequence[Tensor], lr: float = 0.01,
                 momentum: float = 0.0, weight_decay: float = 0.0,
                 nesterov: bool = False):
        super().__init__(parameters, lr)
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.nesterov = nesterov
        self.velocity: List[List[float]] = [[0.0] * len(p.data)
                                            for p in self.parameters]

    def step(self) -> None:
        self.steps += 1
        for index, (parameter, gradient) in enumerate(
                zip(self.parameters, self._gradients())):
            velocity = self.velocity[index]
            for i, g in enumerate(gradient):
                if self.weight_decay:
                    g += self.weight_decay * parameter.data[i]
                if self.momentum:
                    velocity[i] = self.momentum * velocity[i] + g
                    step = (g + self.momentum * velocity[i] if self.nesterov
                            else velocity[i])
                else:
                    step = g
                parameter.data[i] -= self.lr * step


class RMSProp(Optimizer):
    """Divide each parameter's step by the RMS of its recent gradients.

    This is the "per-parameter learning rate" idea on its own, without
    momentum. A parameter whose gradient has been consistently large gets a
    small step; one whose gradient has been tiny gets a large one. It fixes
    SGD's single-scale problem and does nothing about oscillation.
    """

    def __init__(self, parameters: Sequence[Tensor], lr: float = 0.01,
                 decay: float = 0.9, eps: float = 1e-8):
        super().__init__(parameters, lr)
        self.decay, self.eps = decay, eps
        self.squared: List[List[float]] = [[0.0] * len(p.data)
                                           for p in self.parameters]

    def step(self) -> None:
        self.steps += 1
        for index, (parameter, gradient) in enumerate(
                zip(self.parameters, self._gradients())):
            squared = self.squared[index]
            for i, g in enumerate(gradient):
                squared[i] = self.decay * squared[i] + (1 - self.decay) * g * g
                parameter.data[i] -= self.lr * g / (math.sqrt(squared[i])
                                                    + self.eps)


class Adam(Optimizer):
    """Momentum and RMSProp at once, plus the bias correction.

    THE BIAS CORRECTION is the part worth understanding rather than copying.
    Both running averages start at ZERO, so for the first several steps they
    are biased towards zero — badly, when beta2 is 0.999 and the average needs
    ~1000 steps to warm up. Dividing by (1 - beta^t) rescales them to what they
    would be if the average had already converged. Drop those two lines and the
    first hundred steps take almost no movement at all, which looks exactly
    like a learning rate that is too small.

    `decoupled=True` is AdamW. The difference is one line and it matters: with
    coupled decay the weight-decay term goes through the adaptive denominator,
    so parameters with small gradients decay LESS — the opposite of the intent.
    """

    def __init__(self, parameters: Sequence[Tensor], lr: float = 0.001,
                 beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8,
                 weight_decay: float = 0.0, decoupled: bool = False,
                 bias_correction: bool = True):
        super().__init__(parameters, lr)
        self.beta1, self.beta2, self.eps = beta1, beta2, eps
        self.weight_decay = weight_decay
        self.decoupled = decoupled
        self.bias_correction = bias_correction
        self.first: List[List[float]] = [[0.0] * len(p.data)
                                         for p in self.parameters]
        self.second: List[List[float]] = [[0.0] * len(p.data)
                                          for p in self.parameters]

    def step(self) -> None:
        self.steps += 1
        t = self.steps
        correction1 = (1 - self.beta1 ** t) if self.bias_correction else 1.0
        correction2 = (1 - self.beta2 ** t) if self.bias_correction else 1.0

        for index, (parameter, gradient) in enumerate(
                zip(self.parameters, self._gradients())):
            first, second = self.first[index], self.second[index]
            for i, g in enumerate(gradient):
                if self.weight_decay and not self.decoupled:
                    g += self.weight_decay * parameter.data[i]
                first[i] = self.beta1 * first[i] + (1 - self.beta1) * g
                second[i] = self.beta2 * second[i] + (1 - self.beta2) * g * g
                m_hat = first[i] / correction1
                v_hat = second[i] / correction2
                update = self.lr * m_hat / (math.sqrt(v_hat) + self.eps)
                if self.weight_decay and self.decoupled:
                    # AdamW: decay the WEIGHT directly, not the gradient, so it
                    # never passes through the adaptive denominator.
                    update += self.lr * self.weight_decay * parameter.data[i]
                parameter.data[i] -= update


def clip_grad_norm(parameters: Sequence[Tensor], max_norm: float) -> float:
    """Scale all gradients down if their combined norm exceeds max_norm.

    Note that it is the GLOBAL norm across every parameter, not per-tensor.
    Clipping per-tensor changes the DIRECTION of the update, which is a
    different optimiser rather than the same one taking a smaller step. The
    global version preserves the direction and shortens the step, which is what
    you actually want when one bad batch produces a gradient a thousand times
    the usual size.
    """
    total = 0.0
    for parameter in parameters:
        if parameter.grad:
            total += sum(g * g for g in parameter.grad)
    norm = math.sqrt(total)
    if norm > max_norm and norm > 0:
        scale = max_norm / norm
        for parameter in parameters:
            if parameter.grad:
                parameter.grad = [g * scale for g in parameter.grad]
    return norm


def cosine_schedule(step: int, total: int, base_lr: float,
                    warmup: int = 0, min_lr: float = 0.0) -> float:
    """Linear warmup, then a cosine decay to min_lr.

    The warmup is not decoration. Adam's second-moment estimate is meaningless
    for the first few dozen steps — it has seen almost no gradients — so a full
    learning rate applied to a noisy adaptive denominator is how large-model
    training diverges in the first minute. Warmup is the standard fix.
    """
    if warmup and step < warmup:
        return base_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    progress = min(1.0, max(0.0, progress))
    return min_lr + 0.5 * (base_lr - min_lr) * (1 + math.cos(math.pi * progress))


def _demo() -> None:
    print("=" * 76)
    print("optim — four optimisers, and the failure each one fixes")
    print("=" * 76)

    def rosenbrock_ravine(steps: int, make) -> List[float]:
        """A long narrow valley: steep across, shallow along.

        f(x, y) = 0.5*x^2 + 20*y^2. The gradient points mostly in y (across the
        valley) while progress requires moving in x (along it). This is the
        canonical hard case for a single learning rate, and it is what momentum
        was invented for.
        """
        p = Tensor([2.0, 2.0], requires_grad=True)
        optimizer = make([p])
        losses = []
        for _ in range(steps):
            optimizer.zero_grad()
            loss = (p * p * Tensor([0.5, 20.0], (2,))).sum()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        return losses

    def run(steps: int, make):
        p = Tensor([2.0, 2.0], requires_grad=True)
        optimizer = make([p])
        losses = []
        for _ in range(steps):
            optimizer.zero_grad()
            loss = (p * p * Tensor([0.5, 20.0], (2,))).sum()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        return losses, p

    print("\n1. The same ravine, four optimisers, 60 steps")
    print("-" * 76)
    print(f"    {'optimiser':<26}{'step 1':>11}{'step 20':>11}{'step 60':>11}"
          f"{'final |x|':>12}")
    setups = [
        ("SGD lr=0.02", lambda p: SGD(p, lr=0.02)),
        ("SGD + momentum 0.9", lambda p: SGD(p, lr=0.02, momentum=0.9)),
        ("RMSProp lr=0.1", lambda p: RMSProp(p, lr=0.1)),
        ("Adam lr=0.1", lambda p: Adam(p, lr=0.1)),
    ]
    for label, make in setups:
        losses, final = run(60, make)
        print(f"    {label:<26}{losses[0]:>11.3f}{losses[19]:>11.4f}"
              f"{losses[59]:>11.5f}{abs(final.data[0]):>12.4f}")
    print("  x starts at 2.0, so `final |x|` is how far along the valley each")
    print("  optimiser actually travelled. Plain SGD is limited by the STEEP")
    print("  direction: a rate large enough to make progress along the valley")
    print("  diverges across it, so x barely moves. Momentum cancels the")
    print("  oscillating component (it alternates sign each step) and")
    print("  accumulates the consistent one. The adaptive methods rescale each")
    print("  coordinate instead, solving the same problem a different way.")

    print("\n2. Learning rate is not a knob you tune gently")
    print("-" * 76)
    print(f"    {'lr':>10}{'loss after 40 steps':>24}")
    for lr in (1e-4, 1e-3, 1e-2, 3e-2, 5e-2, 1e-1):
        losses = rosenbrock_ravine(40, lambda p, lr=lr: SGD(p, lr=lr))
        final = losses[-1]
        note = "  diverged" if not math.isfinite(final) or final > 100 else ""
        print(f"    {lr:>10.0e}{final:>24.5f}{note}")
    print("  Not a gradual degradation. Below the threshold it converges, above")
    print("  it the loss goes to infinity, and the boundary is sharp. This is")
    print("  why learning-rate search is a log-scale sweep and not a nudge.")

    print("\n3. Adam's bias correction, and which way it actually cuts")
    print("-" * 76)
    print(f"    {'step':>6}{'|update| corrected':>21}{'|update| raw':>15}"
          f"{'raw / corrected':>18}")
    for step_count in (1, 2, 5, 20, 200):
        sizes = []
        for corrected in (True, False):
            p = Tensor([1.0], requires_grad=True)
            optimizer = Adam([p], lr=0.01, bias_correction=corrected)
            previous = p.data[0]
            for _ in range(step_count):
                optimizer.zero_grad()
                previous = p.data[0]
                (p * p).backward()
                optimizer.step()
            sizes.append(abs(p.data[0] - previous))
        print(f"    {step_count:>6}{sizes[0]:>21.6f}{sizes[1]:>15.6f}"
              f"{sizes[1] / sizes[0]:>18.2f}x")
    print("  Read the direction carefully, because the usual summary gets it")
    print("  backwards. Both moments start at zero. The FIRST moment is under-")
    print("  estimated by (1 - 0.9) and the SECOND by (1 - 0.999), and the")
    print("  second sits under a square root — so the raw ratio m/sqrt(v) comes")
    print("  out about 3x too LARGE on the first step, not too small.")
    print("  With correction, Adam's first step is exactly the learning rate,")
    print("  which is the property the whole method is designed around.")
    print("  Ignore the last row: by step 200 the two runs are at completely")
    print("  different points, so that ratio is about where each one ended up")
    print("  rather than about the correction. The correction only acts early —")
    print("  which is precisely when a too-large step does the damage.")

    print("\n4. Gradient clipping preserves the direction")
    print("-" * 76)
    a = Tensor([1.0, 1.0], requires_grad=True)
    b = Tensor([1.0], requires_grad=True)
    a.grad, b.grad = [30.0, 40.0], [100.0]
    before = (list(a.grad), list(b.grad))
    norm = clip_grad_norm([a, b], max_norm=1.0)
    print(f"  gradients {before[0]} and {before[1]}, global norm {norm:.2f}")
    print(f"  clipped to {[round(g, 4) for g in a.grad]} and "
          f"{[round(g, 4) for g in b.grad]}")
    new_norm = math.sqrt(sum(g * g for g in a.grad + b.grad))
    print(f"  new global norm {new_norm:.4f}, and the RATIOS are unchanged: "
          f"{a.grad[1] / a.grad[0]:.4f} vs {before[0][1] / before[0][0]:.4f}")
    print("  Clipping the GLOBAL norm shortens the step and keeps the direction.")
    print("  Clipping per tensor would change the direction, which is a")
    print("  different optimiser rather than the same one being careful.")

    print("\n5. Warmup and cosine decay")
    print("-" * 76)
    total = 100
    print(f"    {'step':>6}{'lr':>12}")
    for step in (0, 4, 9, 10, 25, 50, 75, 99):
        lr = cosine_schedule(step, total, base_lr=1e-3, warmup=10, min_lr=1e-5)
        print(f"    {step:>6}{lr:>12.6f}")
    print("  Adam's second-moment estimate is meaningless for the first few")
    print("  dozen steps — it has barely seen any gradients — so a full learning")
    print("  rate against a noisy adaptive denominator is how large-model runs")
    print("  diverge in their first minute. Warmup is the standard answer.")

    print("\n" + "=" * 76)
    print("Next: digits.py gives you something to train on.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()

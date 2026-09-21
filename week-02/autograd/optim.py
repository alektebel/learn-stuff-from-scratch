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

Learning Path:
1. SGD, then momentum on top of it
2. RMSProp — the per-parameter scale, with no momentum
3. Adam — both at once, plus the bias correction that is not optional
4. AdamW: decoupled weight decay, one line different and it matters
5. clip_grad_norm over the GLOBAL norm, and cosine_schedule with warmup
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
        raise NotImplementedError


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
        raise NotImplementedError


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
        raise NotImplementedError


def clip_grad_norm(parameters: Sequence[Tensor], max_norm: float) -> float:
    """Scale all gradients down if their combined norm exceeds max_norm.

    Note that it is the GLOBAL norm across every parameter, not per-tensor.
    Clipping per-tensor changes the DIRECTION of the update, which is a
    different optimiser rather than the same one taking a smaller step. The
    global version preserves the direction and shortens the step, which is what
    you actually want when one bad batch produces a gradient a thousand times
    the usual size.
    """
    raise NotImplementedError


def cosine_schedule(step: int, total: int, base_lr: float,
                    warmup: int = 0, min_lr: float = 0.0) -> float:
    """Linear warmup, then a cosine decay to min_lr.

    The warmup is not decoration. Adam's second-moment estimate is meaningless
    for the first few dozen steps — it has seen almost no gradients — so a full
    learning rate applied to a noisy adaptive denominator is how large-model
    training diverges in the first minute. Warmup is the standard fix.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. A ravine — f(x, y) = 0.5x^2 + 20y^2 — optimised by all four methods for
       60 steps from (2, 2). Report the loss at several steps AND the final |x|,
       which is how far along the valley each one actually travelled. Plain SGD
       is limited by the steep direction and barely moves in x.

    2. A learning-rate sweep across four orders of magnitude. It does not
       degrade gradually — below a threshold it converges, above it diverges,
       and the boundary is sharp.

    3. Adam's bias correction, measured as the SIZE OF THE UPDATE with and
       without it. Check the direction before you write the prose: the usual
       summary has it backwards. The second moment is under-estimated by
       (1 - 0.999) and sits under a square root, so the raw step comes out
       about 3x too LARGE on step one. With correction, Adam's first step is
       exactly the learning rate.

    4. Gradient clipping, showing the RATIOS between gradients unchanged.
       Clipping the global norm shortens the step; clipping per tensor changes
       the direction, which is a different optimiser.

    5. A warmup-then-cosine schedule printed at a few steps.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

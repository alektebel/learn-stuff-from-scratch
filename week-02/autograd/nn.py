"""
nn — layers, and what a "module" actually is. Complete Solution.

A layer is two things: some tensors that need gradients, and a function that
uses them. That is the whole abstraction, and everything else `nn.Module` does
is bookkeeping around those two facts.

DESIGN DECISION — why does a Module exist at all, when a function would do?
  `def linear(x, w, b): return x @ w + b` is a layer. It is also unusable in a
  network, because the optimiser needs to find `w` and `b`, the checkpointer
  needs to name them, and the training loop needs to zero them. A bare function
  hands you no way to enumerate its own state.
  CHOSEN: Module owns `parameters()`, recursively. Everything downstream —
  optimisers, `zero_grad`, saving, freezing a layer — is one traversal of that
  list. Note what this means: a tensor that is not reachable from
  `parameters()` never gets updated, and the symptom is a network that trains
  but plateaus early, with no error anywhere.

DESIGN DECISION — how are weights initialised?
  Zeros are the obvious choice and they are catastrophic: every unit in a layer
  computes the same thing, receives the same gradient, and stays identical
  forever. The layer has one effective neuron no matter how wide it is.
  CHOSEN: scaled random init — He for ReLU, Xavier for tanh — with the scale
  derived from fan-in rather than picked. The demo measures what happens at the
  wrong scale, because "initialisation matters" is unconvincing until you watch
  a 6-layer network's activations decay to 1e-8 by the output.

DESIGN DECISION — where does the nonlinearity go?
  It has to go somewhere, and the demo shows why: stack two Linear layers with
  nothing between them and you have exactly one Linear layer, because a
  composition of affine maps is an affine map. Depth without a nonlinearity is
  not depth. This is measured below rather than asserted.

Learning Path:
1. Module.parameters — recursive, and a parameter it misses is never updated
2. Linear.forward, and init_scale
3. ReLU / Tanh / Sigmoid / Sequential
4. Dropout, with the inverted scaling
5. Sequential.activations, which is the diagnostic you will use most
"""

import math
import random
from typing import Any, Callable, Iterator, List, Optional, Sequence

from tensor import Tensor


class Module:
    """Anything with parameters and a forward pass."""

    def parameters(self) -> List[Tensor]:
        """Every tensor that needs a gradient, recursively.

        A parameter this misses is a parameter the optimiser never updates.
        There is no error — the network simply trains to a worse plateau, which
        is why frameworks make registration automatic and why the manual
        version below is worth writing once.
        """
        raise NotImplementedError

    def zero_grad(self) -> None:
        for parameter in self.parameters():
            parameter.zero_grad()

    def num_parameters(self) -> int:
        return sum(len(p.data) for p in self.parameters())

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __call__(self, *args: Any, **kwargs: Any) -> Tensor:
        # *args rather than one x: attention takes a mask as well, and a
        # framework whose call signature only fits an MLP stops being a
        # framework the first time you write a second kind of layer.
        return self.forward(*args, **kwargs)


class Linear(Module):
    """y = x @ W + b, with W of shape (in, out) and b of shape (1, out).

    The bias is (1, out) and not (out,) on purpose: it makes the broadcast rule
    it relies on explicit in the shape, and the backward pass has to fold the
    batch dimension away. See `_unbroadcast` in tensor.py — that fold is the
    part people get wrong.
    """

    def __init__(self, fan_in: int, fan_out: int, activation: str = "relu",
                 bias: bool = True, rng: Optional[random.Random] = None):
        rng = rng or random.Random(0)
        scale = init_scale(fan_in, activation)
        self.weight = Tensor.randn(fan_in, fan_out, scale=scale,
                                   requires_grad=True, rng=rng)
        self.bias = Tensor.zeros(1, fan_out, requires_grad=True) if bias else None
        self.fan_in, self.fan_out = fan_in, fan_out

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"Linear({self.fan_in} -> {self.fan_out})"


def init_scale(fan_in: int, activation: str = "relu") -> float:
    """The standard deviation to draw weights from.

    He (sqrt(2/fan_in)) for ReLU, Xavier (sqrt(1/fan_in)) for tanh and linear.
    The factor of 2 in He is exactly the fact that ReLU zeroes half its inputs,
    so the variance it passes on is halved and has to be paid back.

    The reason to derive it rather than pick it: the goal is for activation
    VARIANCE to stay roughly constant as depth grows. Too small and the signal
    decays to nothing by the output layer; too large and it explodes. The demo
    measures both.
    """
    raise NotImplementedError


class ReLU(Module):
    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __repr__(self) -> str:
        return "ReLU()"


class Tanh(Module):
    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __repr__(self) -> str:
        return "Tanh()"


class Sigmoid(Module):
    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __repr__(self) -> str:
        return "Sigmoid()"


class Sequential(Module):
    def __init__(self, *layers: Module):
        self.layers = list(layers)

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def activations(self, x: Tensor) -> List[Tensor]:
        """The output of every layer. Only for inspection — and it is the
        single most useful diagnostic there is when a deep network will not
        train, because it shows you exactly which layer the signal died at."""
        raise NotImplementedError

    def __repr__(self) -> str:
        inner = ", ".join(repr(layer) for layer in self.layers)
        return f"Sequential({inner})"


class Dropout(Module):
    """Zero a fraction of activations during training, and scale the rest up.

    The scaling is the part worth understanding. If you zero 50% of activations
    and do nothing else, the layer's expected output halves — and at inference
    time, with dropout off, everything is twice as large as the next layer was
    trained to expect. "Inverted dropout" divides by the keep probability
    during TRAINING so the expected value is unchanged and inference needs no
    special case at all.
    """

    def __init__(self, probability: float = 0.5,
                 rng: Optional[random.Random] = None):
        self.probability = probability
        self.rng = rng or random.Random(0)
        self.training = True

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"Dropout({self.probability})"


def train_mode(module: Module, training: bool = True) -> None:
    """Flip every Dropout in a tree. This exists because forgetting it is the
    classic "my eval accuracy is worse than my training accuracy for no reason"
    bug — you left dropout on at inference."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. A Sequential model reporting its own parameter count.

    2. A numerical gradient check through two Linear layers and a loss.

    3. Five Linear layers with NO activation, against the single matrix you get
       by multiplying their weights together. They are the same function to
       within floating-point noise — a composition of affine maps is an affine
       map, so depth without a nonlinearity is not depth.

    4. Activation standard deviation through six layers at three init scales:
       0.1x, He, and 3x. Watch the signal reach 1e-7 at the small scale and
       450 at the large one. He keeps it flat, which is what it was derived to
       do.

    5. Dropout's training and eval means matching, because of the 1/keep
       scaling. Zero half the units without it and inference sees activations
       twice as large as the next layer expects.
    """
    raise NotImplementedError


def _std(values: Sequence[float]) -> float:
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

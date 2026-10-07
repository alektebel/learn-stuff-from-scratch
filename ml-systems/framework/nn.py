"""
Layers and modules
==================
Book: Vol I ch. 6 (NN architectures). TinyTorch modules 02 and 03.

A Module is anything with parameters and a forward(). Parameters are found by walking
the module's attributes, so a model is just objects inside objects, as in PyTorch.

DESIGN DECISION - initialisation
Weights drawn with the wrong variance make activations shrink or explode layer by
layer before training even starts. He init (variance 2 / fan_in) keeps the variance of
ReLU activations roughly constant through depth; Xavier (2 / (fan_in + fan_out)) does
the same for tanh/sigmoid. check.py measures it.
"""

from __future__ import annotations

import numpy as np

from tensor import Tensor


class Parameter(Tensor):
    def __init__(self, data):
        super().__init__(data, requires_grad=True)


class Module:
    training = True

    def forward(self, x):
        raise NotImplementedError

    def __call__(self, x):
        return self.forward(x)

    def parameters(self) -> list[Parameter]:
        """Every Parameter reachable through attributes, lists and tuples, each once."""
        # TODO: Walk vars(self) recursively: collect Parameter objects, descend into Modules, lists and tuples. Return each Parameter once (track ids).
        raise NotImplementedError("Module.parameters")

    def zero_grad(self) -> None:
        for p in self.parameters():
            p.zero_grad()

    def train(self, mode: bool = True) -> "Module":
        self.training = mode
        for v in vars(self).values():
            for m in (v if isinstance(v, (list, tuple)) else [v]):
                if isinstance(m, Module):
                    m.train(mode)
        return self

    def eval(self) -> "Module":
        return self.train(False)


class Linear(Module):
    def __init__(self, in_features: int, out_features: int, init: str = "he", rng=None):
        # TODO: Weights (in, out) drawn from N(0, std): He std = sqrt(2/in), Xavier std = sqrt(2/(in+out)). Bias zeros of shape (1, out). Store in_features and out_features.
        raise NotImplementedError("Linear.__init__")

    def forward(self, x: Tensor) -> Tensor:
        # TODO: x @ W + b. Broadcasting adds the bias to every row.
        raise NotImplementedError("Linear.forward")


class ReLU(Module):
    def forward(self, x):
        return x.relu()


class Sigmoid(Module):
    def forward(self, x):
        return x.sigmoid()


class Tanh(Module):
    def forward(self, x):
        return x.tanh()


class Sequential(Module):
    def __init__(self, *layers: Module):
        self.layers = list(layers)

    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x


def log_softmax(logits: Tensor, axis: int = -1) -> Tensor:
    """log softmax via the log-sum-exp trick: subtract the row max (a constant, so it
    carries no gradient) before exponentiating, or exp(1000) overflows to inf."""
    # TODO: Subtract the row max as a CONSTANT Tensor (no gradient through it), then z - log(sum(exp(z))) along the axis with keepdims=True.
    raise NotImplementedError("log_softmax")


def softmax(logits: Tensor, axis: int = -1) -> Tensor:
    return log_softmax(logits, axis).exp()

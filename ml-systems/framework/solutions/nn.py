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
        found, seen = [], set()

        def walk(obj):
            if isinstance(obj, Parameter):
                if id(obj) not in seen:
                    seen.add(id(obj))
                    found.append(obj)
            elif isinstance(obj, Module):
                for v in vars(obj).values():
                    walk(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    walk(v)

        walk(self)
        return found

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
        rng = rng if rng is not None else np.random.default_rng(0)
        if init == "he":
            std = np.sqrt(2.0 / in_features)
        elif init == "xavier":
            std = np.sqrt(2.0 / (in_features + out_features))
        else:
            raise ValueError(f"unknown init {init!r}")
        self.weight = Parameter(rng.normal(0.0, std, size=(in_features, out_features)))
        self.bias = Parameter(np.zeros((1, out_features)))
        self.in_features, self.out_features = in_features, out_features

    def forward(self, x: Tensor) -> Tensor:
        return x @ self.weight + self.bias


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
    shift = Tensor(logits.data.max(axis=axis, keepdims=True))
    z = logits - shift
    return z - z.exp().sum(axis=axis, keepdims=True).log()


def softmax(logits: Tensor, axis: int = -1) -> Tensor:
    return log_softmax(logits, axis).exp()

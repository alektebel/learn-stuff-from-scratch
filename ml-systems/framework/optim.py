"""
Optimizers
==========
Book: Vol I ch. 8 (Training). TinyTorch module 07.

An optimizer owns per-parameter STATE. SGD with momentum keeps one velocity buffer per
parameter; Adam keeps two (first and second moments). That state is memory: for Adam,
twice the size of the model. profile.py turns that into bytes.

Adam's moment estimates start at zero, so for the first steps they are biased towards
zero; dividing by (1 - beta^t) corrects it. Without the correction the first updates are
far too small (by a factor of about 10x at t=1 with beta1 = 0.9).

Weight decay here is L2 added to the gradient ("coupled"). AdamW decouples it: it
shrinks the weights directly instead of through Adam's adaptive scaling. The two are
NOT equivalent for Adam; they are for plain SGD.
"""

from __future__ import annotations

import numpy as np


class Optimizer:
    def __init__(self, params, lr: float):
        self.params = list(params)
        if not self.params:
            raise ValueError("optimizer got an empty parameter list")
        self.lr = lr

    def zero_grad(self) -> None:
        for p in self.params:
            p.grad = None

    def step(self) -> None:
        raise NotImplementedError

    def state_arrays(self) -> list[np.ndarray]:
        """All per-parameter state buffers (for memory accounting)."""
        return []


class SGD(Optimizer):
    def __init__(self, params, lr: float = 0.01, momentum: float = 0.0, weight_decay: float = 0.0):
        super().__init__(params, lr)
        self.momentum, self.weight_decay = momentum, weight_decay
        self.velocity = [np.zeros_like(p.data) for p in self.params] if momentum else []

    def step(self) -> None:
        # TODO: For each parameter with a grad: g = grad + weight_decay * w. With momentum: v = momentum * v + g, use v. Then w -= lr * g. Update p.data in place.
        raise NotImplementedError("SGD.step")

    def state_arrays(self):
        return list(self.velocity)


class Adam(Optimizer):
    def __init__(self, params, lr: float = 1e-3, betas=(0.9, 0.999), eps: float = 1e-8,
                 weight_decay: float = 0.0):
        super().__init__(params, lr)
        self.b1, self.b2 = betas
        self.eps, self.weight_decay = eps, weight_decay
        self.m = [np.zeros_like(p.data) for p in self.params]
        self.v = [np.zeros_like(p.data) for p in self.params]
        self.t = 0

    def step(self) -> None:
        # TODO: t += 1. m = b1*m + (1-b1)*g; v = b2*v + (1-b2)*g^2; m_hat = m/(1-b1^t); v_hat = v/(1-b2^t); w -= lr * m_hat / (sqrt(v_hat) + eps).
        raise NotImplementedError("Adam.step")

    def state_arrays(self):
        return self.m + self.v

"""
Training loop and the three milestones
======================================
Book: Vol I ch. 8 (Training). TinyTorch module 08 and milestones 1958 / 1969 / 1986.

The milestones replay history in order:
  1958  a single neuron separates linearly separable data (the perceptron)
  1969  the same model provably cannot learn XOR (Minsky & Papert)
  1986  a hidden layer trained with backprop learns XOR, and more (Rumelhart et al.)
Here the last step is a 3-class spiral, which no linear model can separate.
"""

from __future__ import annotations

import numpy as np

from data import DataLoader, TensorDataset
from losses import binary_cross_entropy_with_logits, cross_entropy
from nn import Linear, Module, ReLU, Sequential, Tanh
from optim import Adam
from tensor import Tensor


# -- synthetic datasets (no downloads) --------------------------------------------------
def make_blobs(n: int = 200, seed: int = 0):
    rng = np.random.default_rng(seed)
    a = rng.normal([-2, -2], 0.7, size=(n // 2, 2))
    b = rng.normal([2, 2], 0.7, size=(n - n // 2, 2))
    return np.vstack([a, b]), np.array([0] * (n // 2) + [1] * (n - n // 2))


def make_xor(n: int = 400, noise: float = 0.1, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1, 1, size=(n, 2))
    y = ((X[:, 0] > 0) ^ (X[:, 1] > 0)).astype(int)
    keep = (np.abs(X[:, 0]) > 0.1) & (np.abs(X[:, 1]) > 0.1)  # a margin, so 100% is reachable
    X, y = X[keep], y[keep]
    return X + rng.normal(0, noise * 0.1, size=X.shape), y


def make_spirals(n_per_class: int = 100, classes: int = 3, noise: float = 0.2, seed: int = 0):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for c in range(classes):
        r = np.linspace(0.0, 1.0, n_per_class)
        t = np.linspace(c * 4, (c + 1) * 4, n_per_class) + rng.normal(0, noise, n_per_class)
        X.append(np.c_[r * np.sin(t), r * np.cos(t)])
        y += [c] * n_per_class
    return np.vstack(X), np.array(y)


# -- training -------------------------------------------------------------------------
def fit(model: Module, X, y, loss: str = "ce", epochs: int = 100, lr: float = 0.01,
        batch_size: int = 32, seed: int = 0) -> list[float]:
    """Train with Adam; return the mean loss of each epoch."""
    # TODO: Adam over model.parameters(); a shuffled DataLoader; per batch: forward, loss (ce or bce), zero_grad, backward, step. Return the mean loss per epoch.
    raise NotImplementedError("fit")


def accuracy(model: Module, X, y) -> float:
    # TODO: Eval mode; argmax over classes, or logit > 0 when there is one output column.
    raise NotImplementedError("accuracy")


def perceptron(seed: int = 0) -> Module:
    return Sequential(Linear(2, 1, init="xavier", rng=np.random.default_rng(seed)))


def mlp(sizes: list[int], seed: int = 0, act=Tanh) -> Module:
    rng = np.random.default_rng(seed)
    layers: list[Module] = []
    for i, (a, b) in enumerate(zip(sizes, sizes[1:])):
        layers.append(Linear(a, b, init="xavier" if act is Tanh else "he", rng=rng))
        if i < len(sizes) - 2:
            layers.append(act())
    return Sequential(*layers)


if __name__ == "__main__":
    X, y = make_blobs()
    m = perceptron()
    fit(m, X, y, loss="bce", epochs=30, lr=0.05)
    print(f"1958 perceptron on separable blobs: {accuracy(m, X, y):.3f}")
    X, y = make_xor()
    m = perceptron()
    fit(m, X, y, loss="bce", epochs=60, lr=0.05)
    print(f"1969 perceptron on XOR:             {accuracy(m, X, y):.3f}  (cannot do better than ~0.75)")
    m = mlp([2, 8, 1])
    fit(m, X, y, loss="bce", epochs=150, lr=0.05)
    print(f"1986 MLP on XOR:                    {accuracy(m, X, y):.3f}")
    X, y = make_spirals()
    m = mlp([2, 64, 64, 3], act=ReLU)
    hist = fit(m, X, y, epochs=300, lr=0.01)
    print(f"     MLP on 3 spirals:              {accuracy(m, X, y):.3f}  (loss {hist[0]:.2f} -> {hist[-1]:.3f})")

"""
Loss functions
==============
Book: Vol I ch. 8 (Training). TinyTorch module 04.

Cross-entropy is computed from LOGITS, never from probabilities: softmax followed by
log loses all precision for confident wrong predictions (log of a probability that
underflowed to 0 is -inf). log_softmax keeps it finite. The gradient of mean
cross-entropy with respect to the logits is (softmax - one_hot) / N; check.py verifies it.
"""

from __future__ import annotations

import numpy as np

from nn import log_softmax
from tensor import Tensor


def mse_loss(pred: Tensor, target) -> Tensor:
    diff = pred - Tensor._wrap(target)
    return (diff * diff).mean()


def cross_entropy(logits: Tensor, labels) -> Tensor:
    """Mean negative log-likelihood of integer `labels` (shape (N,)) under `logits` (N, C)."""
    labels = np.asarray(labels, dtype=int)
    n, c = logits.shape
    if labels.shape != (n,) or labels.min() < 0 or labels.max() >= c:
        raise ValueError(f"labels must be ints in [0, {c}) with shape ({n},)")
    one_hot = np.zeros((n, c))
    one_hot[np.arange(n), labels] = 1.0
    return -(log_softmax(logits) * one_hot).sum() * (1.0 / n)


def binary_cross_entropy_with_logits(logits: Tensor, targets) -> Tensor:
    """Stable BCE on logits: mean of softplus(x) - t*x, where
    softplus(x) = log(1 + e^x) = relu(x) + log(1 + e^-|x|) never exponentiates a large
    positive number. |x| is built from differentiable ops, so d/dx = sigmoid(x) - t."""
    t = Tensor._wrap(np.asarray(targets, dtype=float).reshape(logits.shape))
    abs_x = logits.relu() + (-logits).relu()
    softplus = logits.relu() + ((-abs_x).exp() + 1.0).log()
    return (softplus - t * logits).mean()

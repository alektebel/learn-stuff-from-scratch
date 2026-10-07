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
    # TODO: Mean of the squared difference.
    raise NotImplementedError("mse_loss")


def cross_entropy(logits: Tensor, labels) -> Tensor:
    """Mean negative log-likelihood of integer `labels` (shape (N,)) under `logits` (N, C)."""
    # TODO: Validate labels. Build a one-hot (N, C) array; the loss is -sum(log_softmax(logits) * one_hot) / N. Never take log of softmax probabilities.
    raise NotImplementedError("cross_entropy")


def binary_cross_entropy_with_logits(logits: Tensor, targets) -> Tensor:
    """Stable BCE on logits: mean of softplus(x) - t*x, where
    softplus(x) = log(1 + e^x) = relu(x) + log(1 + e^-|x|) never exponentiates a large
    positive number. |x| is built from differentiable ops, so d/dx = sigmoid(x) - t."""
    # TODO: Mean of softplus(x) - t*x, with softplus(x) = relu(x) + log(1 + exp(-|x|)). Build |x| from Tensor ops (relu(x) + relu(-x)) so the gradient flows; it must equal sigmoid(x) - t.
    raise NotImplementedError("binary_cross_entropy_with_logits")

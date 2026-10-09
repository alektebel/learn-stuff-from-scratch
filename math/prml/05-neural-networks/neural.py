"""
Two-layer neural network from scratch: forward pass, backpropagation, finite-difference
gradients and Hessians, the outer-product (Gauss-Newton) Hessian approximation, and
training with weight decay and early stopping.

Pure standard library -- no numpy. The parameters are a dict of nested lists::

    W1 : H x D   input  -> hidden weights
    b1 : H       hidden biases
    Z1 = W1 x + b1,  A1 = tanh(Z1)
    W2 : K x H   hidden -> output weights
    b2 : K       output biases
    Y  = W2 A1 + b2          (a linear output layer)

The loss is squared error, ``E = 1/2 sum_n ||y_n - t_n||^2``. The hidden layer is the
only nonlinearity, so the exact Hessian is ``J^T J + sum_n sum_k r_{n,k} d^2 r_{n,k}``
and the outer-product (Gauss-Newton) approximation drops the second term, keeping
``J^T J``. Near a minimum the residuals are small and the two agree; far away they do not.

Run ``python3 neural.py`` for a demo once the functions below are implemented.
"""

import math
import random

__all__ = [
    "tanh", "tanh_prime", "sigmoid", "sigmoid_prime",
    "make_weights", "forward", "loss", "backprop",
    "numerical_gradient", "exact_hessian_fd", "outer_product_hessian",
    "flatten", "unflatten", "train", "early_stopping_split", "demo",
]

_ORDER = ("W1", "b1", "W2", "b2")


# ---------------------------------------------------------------------------
# Elementwise nonlinearities (provided)
# ---------------------------------------------------------------------------

def tanh(z: float) -> float:
    """Hyperbolic tangent."""
    return math.tanh(z)


def tanh_prime(z: float) -> float:
    """Derivative of tanh, expressed through its output: 1 - tanh(z)^2."""
    t = math.tanh(z)
    return 1.0 - t * t


def sigmoid(z: float) -> float:
    """Numerically stable logistic sigmoid."""
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def sigmoid_prime(z: float) -> float:
    """Derivative of the logistic sigmoid, expressed through its output."""
    s = sigmoid(z)
    return s * (1.0 - s)


# ---------------------------------------------------------------------------
# Parameter representation (provided): nested-list dict <-> flat vector
# ---------------------------------------------------------------------------

def make_weights(D: int, H: int, K: int = 1, rng=None) -> dict:
    """Small random init: W1 (H x D), b1 (H), W2 (K x H), b2 (K)."""
    rng = rng if rng is not None else random
    return {
        "W1": [[rng.uniform(-0.5, 0.5) for _ in range(D)] for _ in range(H)],
        "b1": [rng.uniform(-0.5, 0.5) for _ in range(H)],
        "W2": [[rng.uniform(-0.5, 0.5) for _ in range(H)] for _ in range(K)],
        "b2": [rng.uniform(-0.5, 0.5) for _ in range(K)],
    }


def flatten(weights: dict) -> list:
    """Row-major flattening in the fixed order W1, b1, W2, b2."""
    out = []
    for key in _ORDER:
        block = weights[key]
        if block and isinstance(block[0], list):
            for row in block:
                out.extend(row)
        else:
            out.extend(block)
    return out


def unflatten(vec: list, D: int, H: int, K: int) -> dict:
    """Inverse of :func:`flatten` for a net with sizes D, H, K."""
    i = 0
    W1 = [[vec[i + r * D + c] for c in range(D)] for r in range(H)]
    i += H * D
    b1 = [vec[i + r] for r in range(H)]
    i += H
    W2 = [[vec[i + r * H + c] for c in range(H)] for r in range(K)]
    i += K * H
    b2 = [vec[i + r] for r in range(K)]
    return {"W1": W1, "b1": b1, "W2": W2, "b2": b2}


def _sizes(weights: dict):
    return len(weights["W1"][0]), len(weights["b1"]), len(weights["b2"])


def _copy(weights: dict) -> dict:
    D, H, K = _sizes(weights)
    return unflatten(flatten(weights), D, H, K)


def _tvec(t, K: int) -> list:
    if isinstance(t, (list, tuple)):
        return list(t)
    return [t] if K == 1 else [t]


# ---------------------------------------------------------------------------
# Forward pass and loss  (implement these)
# ---------------------------------------------------------------------------

def forward(weights: dict, xs: list) -> dict:
    """Run every input through the net.

    Returns ``{"z1": [...], "a1": [...], "z2": [...], "y": [...]}`` where entry ``n``
    holds that sample's hidden pre-activations, hidden activations (tanh) and output.

    For each input ``x``::

        z1 = W1 x + b1
        a1 = tanh(z1)
        y  = W2 a1 + b2

    Return the outputs as lists so the loss and backprop can read them back.
    """
    raise NotImplementedError(
        "forward: for each x compute z1 = W1 x + b1, a1 = tanh(z1), y = W2 a1 + b2; "
        "return {'z1': [...], 'a1': [...], 'z2': [...], 'y': [...]}.")


def loss(weights: dict, xs: list, ts: list) -> float:
    """Squared error ``1/2 sum_n ||y_n - t_n||^2``.

    Call :func:`forward`, then accumulate half the squared difference for every output
    unit. Targets may be scalars (single output) or lists.
    """
    raise NotImplementedError(
        "loss: call forward and sum 1/2 * (y - t)^2 over every sample and output unit.")


def backprop(weights: dict, xs: list, ts: list) -> dict:
    """Analytic gradient of :func:`loss` by the chain rule.

    Returns a dict shaped like ``weights`` (``W1``, ``b1``, ``W2``, ``b2``). Do not
    build a big Jacobian: loop over samples and accumulate.

    The deltas are

        delta2 = y - t
        dW2 += delta2 a1^T,  db2 += delta2
        delta1 = (W2^T delta2) * (1 - a1^2)
        dW1 += delta1 x^T,   db1 += delta1

    The ``(1 - a1^2)`` factor is ``tanh'``; dropping it silently breaks the gradient.
    """
    raise NotImplementedError(
        "backprop: accumulate delta2 = y - t at the output, then "
        "delta1 = (W2^T delta2) * (1 - a1^2) at the hidden layer.")


# ---------------------------------------------------------------------------
# Finite differences (implement these)
# ---------------------------------------------------------------------------

def numerical_gradient(weights: dict, xs: list, ts: list, eps: float = 1e-5) -> list:
    """Central finite differences of the loss, returned as a flat vector.

    For every parameter ``i``::

        (loss(w + eps e_i) - loss(w - eps e_i)) / (2 eps)

    Use the *central* form; a one-sided difference is only O(eps) accurate and will not
    match backprop to the required precision.
    """
    raise NotImplementedError(
        "numerical_gradient: flatten w, perturb one coordinate by +eps and -eps, and "
        "use the central difference (loss(+eps) - loss(-eps)) / (2 eps).")


def exact_hessian_fd(weights: dict, xs: list, ts: list, eps: float = 1e-4) -> list:
    """The exact Hessian, as central finite differences of the analytic gradient.

    Column ``j`` is ``(grad(w + eps e_j) - grad(w - eps e_j)) / (2 eps)``, with ``grad``
    from :func:`backprop`. No second derivatives are written by hand.
    """
    raise NotImplementedError(
        "exact_hessian_fd: for each parameter j, difference the backprop gradient at "
        "+eps e_j and -eps e_j; column j = (g+ - g-) / (2 eps).")


# ---------------------------------------------------------------------------
# The outer-product (Gauss-Newton) Hessian approximation (implement these)
# ---------------------------------------------------------------------------

def _sample_jacobians(weights: dict, xs: list) -> list:
    """For each sample ``n`` a K x P Jacobian ``dy_n / dw`` (rows indexed by output).

    One clean way: treat the network as ``y = W2 tanh(W1 x + b1) + b2`` and read off
    the derivative with respect to each parameter, or run backprop once per output unit
    with a one-hot seed. ``P = H*D + H + K*H + K`` and the parameter order matches
    :func:`flatten`.
    """
    raise NotImplementedError(
        "_sample_jacobians: build dy_n/dw per sample, one row per output unit, in the "
        "flat parameter order W1, b1, W2, b2.")


def outer_product_hessian(weights: dict, xs: list, ts: list = None) -> list:
    """The Gauss-Newton approximation ``sum_n J_n^T J_n`` as a P x P matrix.

    ``J_n = d r_n / dw`` is the residual Jacobian for sample ``n`` (``ts`` does not
    appear because the target is constant). This drops the term in the exact Hessian
    that is linear in the residuals, so it is accurate only while they are small.
    """
    raise NotImplementedError(
        "outer_product_hessian: return sum_n J_n^T J_n, with J_n from "
        "_sample_jacobians. Each sample contributes the outer products of its rows.")


# ---------------------------------------------------------------------------
# Training (implement these)
# ---------------------------------------------------------------------------

def train(weights0: dict, xs: list, ts: list, lr: float = 0.5,
          maxit: int = 2000, weight_decay: float = 0.0,
          tol: float = 0.0) -> tuple:
    """Full-batch gradient descent.

    The penalised objective is ``loss + 1/2 * weight_decay * ||w||^2``, so the update is

        w <- w - lr * (grad + weight_decay * w)

    (the decay adds to the gradient; subtracting it would *grow* the weights). Return
    ``(weights, loss_history)`` with one loss per iteration, after the update.
    """
    raise NotImplementedError(
        "train: loop maxit times, w -= lr * (backprop_gradient + weight_decay * w); "
        "return (weights, loss_history).")


def early_stopping_split(weights0: dict, xs: list, ts: list, val_frac: float = 0.3,
                         lr: float = 0.5, maxit: int = 4000,
                         weight_decay: float = 0.0, seed: int = 0) -> tuple:
    """Hold out ``val_frac`` of the data, train on the rest, stop when validation rises.

    Track the training and validation losses each iteration; remember the weights with
    the lowest validation loss. Stop as soon as validation loss turns upward.

    Return ``(best_weights, train_history, val_history, best_iteration)``.
    """
    raise NotImplementedError(
        "early_stopping_split: split off a validation set, train on the rest, keep the "
        "best-validation weights, and stop when validation loss rises.")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _relative_frobenius(A, B):
    num = 0.0
    den = 0.0
    for i in range(len(A)):
        for j in range(len(A)):
            d = A[i][j] - B[i][j]
            num += d * d
            den += B[i][j] * B[i][j]
    return math.sqrt(num / den) if den > 0.0 else math.sqrt(num)


def demo():
    print("Two-layer net from scratch (tanh hidden, linear output)\n")
    rng = random.Random(3)
    xs = [[-1.0 + 2.0 * i / 11.0, 0.0] for i in range(12)]
    ts = [math.sin(3.0 * x[0]) for x in xs]

    # Generate data from a net plus tiny noise, then train to a near-minimum.
    teacher = make_weights(2, 6, 1, random.Random(11))
    xs2 = [[x[0], 0.2 * math.cos(2.0 * x[0])] for x in xs]
    ts2 = [forward(teacher, [x])["y"][0][0] + rng.gauss(0.0, 0.01) for x in xs2]

    w0 = make_weights(2, 6, 1, random.Random(1))
    w_min, hist = train(w0, xs2, ts2, lr=0.05, maxit=3000, weight_decay=0.0)
    print(f"trained {len(hist)} steps, loss {hist[0]:.4f} -> {hist[-1]:.6f}")

    exact = exact_hessian_fd(w_min, xs2, ts2, eps=1e-3)
    outer = outer_product_hessian(w_min, xs2, ts2)
    print(f"near the minimum   : outer-product vs exact Hessian rel. error "
          f"{_relative_frobenius(outer, exact):.3e}")

    far = unflatten([v + 2.5 for v in flatten(w_min)], 2, 6, 1)
    exact_far = exact_hessian_fd(far, xs2, ts2, eps=1e-3)
    outer_far = outer_product_hessian(far, xs2, ts2)
    print(f"far from the minimum: outer-product vs exact Hessian rel. error "
          f"{_relative_frobenius(outer_far, exact_far):.3e}")

    # Weight decay and early stopping on a noisy set.
    xn = [[-1.0 + 2.0 * i / 9.0, 0.0] for i in range(10)]
    tn = [math.sin(3.0 * x[0]) + rng.gauss(0.0, 0.3) for x in xn]
    base = make_weights(2, 8, 1, random.Random(5))
    w_plain, _ = train(base, xn, tn, lr=0.05, maxit=3000, weight_decay=0.0)
    w_decay, _ = train(base, xn, tn, lr=0.05, maxit=3000, weight_decay=0.01)
    nb = math.sqrt(sum(v * v for v in flatten(w_plain)))
    nd = math.sqrt(sum(v * v for v in flatten(w_decay)))
    print(f"\n||w|| without decay {nb:.3f}, with decay {nd:.3f}")

    w_es, tr_h, va_h, best = early_stopping_split(
        base, xn, tn, val_frac=0.3, lr=0.05, maxit=4000, weight_decay=0.0)
    print(f"early stopping: stopped at iteration {len(va_h)} (best {best}); "
          f"val {va_h[0]:.4f} -> {va_h[-1]:.4f}")


if __name__ == "__main__":
    demo()

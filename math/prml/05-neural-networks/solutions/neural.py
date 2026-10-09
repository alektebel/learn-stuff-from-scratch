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

Run ``python3 neural.py`` for a demo.
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
# Elementwise nonlinearities
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
# Parameter representation: a nested-list dict <-> a flat vector
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
# Forward pass and loss
# ---------------------------------------------------------------------------

def forward(weights: dict, xs: list) -> dict:
    """Run every input through the net.

    Returns ``{"z1": [...], "a1": [...], "z2": [...], "y": [...]}`` where entry ``n``
    holds that sample's hidden pre-activations, hidden activations (tanh) and output.
    """
    W1, b1, W2, b2 = weights["W1"], weights["b1"], weights["W2"], weights["b2"]
    H, D = len(W1), len(W1[0])
    K = len(W2)
    z1_all, a1_all, y_all = [], [], []
    for x in xs:
        z1 = [sum(W1[r][c] * x[c] for c in range(D)) + b1[r] for r in range(H)]
        a1 = [math.tanh(v) for v in z1]
        y = [sum(W2[k][r] * a1[r] for r in range(H)) + b2[k] for k in range(K)]
        z1_all.append(z1)
        a1_all.append(a1)
        y_all.append(y)
    return {"z1": z1_all, "a1": a1_all, "z2": y_all, "y": y_all}


def loss(weights: dict, xs: list, ts: list) -> float:
    """Squared error ``1/2 sum_n ||y_n - t_n||^2``.

    DESIGN DECISION. A linear output with squared error, not a sigmoid/softmax with
    cross-entropy. Cost: the output is not a probability and the Hessian keeps its
    residual-linear term (which the outer-product approximation drops), but the
    residual structure is exactly what checks 3 and 5 need to expose.
    """
    acts = forward(weights, xs)
    K = len(weights["b2"])
    total = 0.0
    for y, t in zip(acts["y"], ts):
        tv = _tvec(t, K)
        for k in range(K):
            d = y[k] - tv[k]
            total += 0.5 * d * d
    return total


# ---------------------------------------------------------------------------
# Backpropagation
# ---------------------------------------------------------------------------

def backprop(weights: dict, xs: list, ts: list) -> dict:
    """Analytic gradient of :func:`loss` by the chain rule.

    Returns a dict with the same shape as ``weights``. It never forms a single big
    Jacobian: it accumulates per-sample output errors and pushes them back.

    DESIGN DECISION. Accumulate the gradient in the weight shapes by hand rather than
    assembling a ``(N K) x P`` Jacobian and multiplying. Cost: the code repeats the
    chain rule per layer, but the memory is ``O(P)`` instead of ``O(N K P)`` and the
    reverse-mode structure is visible.
    """
    W2, b2 = weights["W2"], weights["b2"]
    H, D = len(weights["W1"]), len(weights["W1"][0])
    K = len(b2)
    acts = forward(weights, xs)

    dW1 = [[0.0] * D for _ in range(H)]
    db1 = [0.0] * H
    dW2 = [[0.0] * H for _ in range(K)]
    db2 = [0.0] * K

    for n in range(len(xs)):
        x = xs[n]
        t = _tvec(ts[n], K)
        a1 = acts["a1"][n]
        y = acts["y"][n]

        # Output layer: dE/dz2 = y - t.
        delta2 = [y[k] - t[k] for k in range(K)]
        for k in range(K):
            dk = delta2[k]
            row2 = dW2[k]
            for r in range(H):
                row2[r] += dk * a1[r]
            db2[k] += dk

        # Hidden layer: delta1 = (W2^T delta2) * tanh'(z1).
        delta1 = [0.0] * H
        for r in range(H):
            s = 0.0
            for k in range(K):
                s += W2[k][r] * delta2[k]
            delta1[r] = s * (1.0 - a1[r] * a1[r])
        row1 = dW1
        for r in range(H):
            d = delta1[r]
            r1 = row1[r]
            for c in range(D):
                r1[c] += d * x[c]
            db1[r] += d

    return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}


# ---------------------------------------------------------------------------
# Finite differences of the loss and of the gradient
# ---------------------------------------------------------------------------

def numerical_gradient(weights: dict, xs: list, ts: list, eps: float = 1e-5) -> list:
    """Central finite differences of the loss, returned as a flat vector."""
    D, H, K = _sizes(weights)
    vec = flatten(weights)
    grad = []
    for i in range(len(vec)):
        plus = list(vec)
        plus[i] += eps
        minus = list(vec)
        minus[i] -= eps
        g = (loss(unflatten(plus, D, H, K), xs, ts)
             - loss(unflatten(minus, D, H, K), xs, ts)) / (2.0 * eps)
        grad.append(g)
    return grad


def exact_hessian_fd(weights: dict, xs: list, ts: list, eps: float = 1e-4) -> list:
    """The exact Hessian, as central finite differences of the analytic gradient.

    Column ``j`` is ``(grad(w + eps e_j) - grad(w - eps e_j)) / (2 eps)``. This is the
    Hessian *of the loss*, computed from backprop's gradient -- no second derivatives are
    written by hand.

    DESIGN DECISION. Get the Hessian by differencing the analytic gradient instead of
    deriving second derivatives analytically. Cost: ``2 P`` gradient evaluations and an
    accuracy limited by ``eps`` (and by cancellation when the gradient is large), but the
    result is exact to the extent backprop is, and it never disagrees with the gradient
    it is built from.
    """
    D, H, K = _sizes(weights)
    vec = flatten(weights)
    P = len(vec)
    hess = [[0.0] * P for _ in range(P)]
    for j in range(P):
        plus = list(vec)
        plus[j] += eps
        minus = list(vec)
        minus[j] -= eps
        gp = flatten(backprop(unflatten(plus, D, H, K), xs, ts))
        gm = flatten(backprop(unflatten(minus, D, H, K), xs, ts))
        inv = 1.0 / (2.0 * eps)
        for i in range(P):
            hess[i][j] = (gp[i] - gm[i]) * inv
    return hess


# ---------------------------------------------------------------------------
# The outer-product (Gauss-Newton) Hessian approximation
# ---------------------------------------------------------------------------

def _sample_jacobians(weights: dict, xs: list) -> list:
    """For each sample ``n`` a K x P Jacobian ``dy_n / dw`` (rows indexed by output).

    DESIGN DECISION. Build one Jacobian row per output unit by a single forward-mode
    sweep, rather than differentiating the residual vector as a whole. Cost: ``K``
    passes of bookkeeping per sample, but it makes ``J^T J`` (the Gauss-Newton term)
    a direct outer-product accumulation and keeps the dropped residual term explicit.
    """
    W2 = weights["W2"]
    H, D = len(weights["W1"]), len(weights["W1"][0])
    K = len(W2)
    acts = forward(weights, xs)
    jac = []
    for n in range(len(xs)):
        x = xs[n]
        a1 = acts["a1"][n]
        rows = []
        for k in range(K):
            dW1 = [[0.0] * D for _ in range(H)]
            db1 = [0.0] * H
            dW2 = [[0.0] * H for _ in range(K)]
            db2 = [0.0] * K
            db2[k] = 1.0
            for r in range(H):
                dW2[k][r] = a1[r]
                delta1 = W2[k][r] * (1.0 - a1[r] * a1[r])
                db1[r] = delta1
                dW1[r] = [delta1 * x[c] for c in range(D)]
            rows.append(flatten({"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}))
        jac.append(rows)
    return jac


def outer_product_hessian(weights: dict, xs: list, ts: list = None) -> list:
    """The Gauss-Newton approximation ``sum_n J_n^T J_n`` as a P x P matrix.

    ``J_n = d r_n / dw`` is the Jacobian of the residuals for sample ``n`` (``ts`` does
    not enter because the target is constant). This ignores the term that is linear in
    the residuals, so it is only accurate while the residuals are small.

    DESIGN DECISION. Return only the Gauss-Newton term ``sum_n J_n^T J_n`` and accept
    that it is never negative definite, rather than adding a correction. Cost: far from
    a minimum the dropped ``sum_n r_n . d^2 r_n`` term dominates and the approximation
    can badly overestimate; check 5 exists precisely to show that failure.
    """
    D, H, K = _sizes(weights)
    P = H * D + H + K * H + K
    jac = _sample_jacobians(weights, xs)
    hess = [[0.0] * P for _ in range(P)]
    for rows in jac:
        for j in rows:
            for a in range(P):
                ja = j[a]
                if ja == 0.0:
                    continue
                ha = hess[a]
                for b in range(P):
                    ha[b] += ja * j[b]
    return hess


# ---------------------------------------------------------------------------
# Training: gradient descent with optional L2 weight decay
# ---------------------------------------------------------------------------

def train(weights0: dict, xs: list, ts: list, lr: float = 0.5,
          maxit: int = 2000, weight_decay: float = 0.0,
          tol: float = 0.0) -> tuple:
    """Full-batch gradient descent.

    The penalised objective is ``loss + 1/2 * weight_decay * ||w||^2``, so the descent
    direction adds ``weight_decay * w`` to the backprop gradient (never subtracts it).
    Returns ``(weights, loss_history)``.

    DESIGN DECISION. Decay the weights by adding ``weight_decay * w`` to the gradient
    (L2 in the objective), not by shrinking the weights after each step. Cost: the
    gradient is no longer just backprop's output and the penalty scale is coupled to
    ``lr``, but the update is exactly the gradient of the penalised loss, so the
    descent is still monotone; sign errors show up as growing weights.
    """
    D, H, K = _sizes(weights0)
    vec = flatten(weights0)
    history = []
    for _ in range(maxit):
        w = unflatten(vec, D, H, K)
        g = flatten(backprop(w, xs, ts))
        vec = [vec[i] - lr * (g[i] + weight_decay * vec[i]) for i in range(len(vec))]
        cur = loss(unflatten(vec, D, H, K), xs, ts)
        history.append(cur)
        if tol and cur < tol:
            break
    return unflatten(vec, D, H, K), history


def early_stopping_split(weights0: dict, xs: list, ts: list, val_frac: float = 0.3,
                         lr: float = 0.5, maxit: int = 4000,
                         weight_decay: float = 0.0, seed: int = 0) -> tuple:
    """Hold out ``val_frac`` of the data, train on the rest, stop when validation rises.

    Returns ``(best_weights, train_history, val_history, best_iteration)``. The returned
    weights are those at the best (lowest) validation loss, not the last ones seen.

    DESIGN DECISION. Keep the best-validation weights and stop on the first rise, rather
    than training to ``maxit`` and returning the last iterate. Cost: a full copy of the
    parameter vector and a strict comparison (``va > val_hist[-2]``) that a single noisy
    step can trigger; but the returned model is the one the validation set actually
    selected, which is the point of early stopping.
    """
    n = len(xs)
    order = list(range(n))
    random.Random(seed).shuffle(order)
    nval = max(1, int(round(val_frac * n)))
    val_idx = order[:nval]
    train_idx = order[nval:]
    xs_tr = [xs[i] for i in train_idx]
    ts_tr = [ts[i] for i in train_idx]
    xs_va = [xs[i] for i in val_idx]
    ts_va = [ts[i] for i in val_idx]

    D, H, K = _sizes(weights0)
    vec = flatten(weights0)
    train_hist, val_hist = [], []
    best_val = float("inf")
    best_vec = list(vec)
    best_it = 0
    for it in range(maxit):
        w = unflatten(vec, D, H, K)
        g = flatten(backprop(w, xs_tr, ts_tr))
        vec = [vec[i] - lr * (g[i] + weight_decay * vec[i]) for i in range(len(vec))]
        w = unflatten(vec, D, H, K)
        tr = loss(w, xs_tr, ts_tr)
        va = loss(w, xs_va, ts_va)
        train_hist.append(tr)
        val_hist.append(va)
        if va < best_val - 1e-12:
            best_val = va
            best_vec = list(vec)
            best_it = it
        elif it > 0 and va > val_hist[-2]:
            break
    return unflatten(best_vec, D, H, K), train_hist, val_hist, best_it


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

"""
Step 4 — The LASSO surrogate, by coordinate descent. Complete Solution.

Paper: ContextCite, section 3 ("we fit a sparse linear surrogate model").
Reference implementation uses sklearn's Lasso (alpha=0.01) inside a
StandardScaler pipeline; this reproduces it in pure Python.

Objective, matching scikit-learn's convention exactly:

    minimise   (1 / 2n) * ||y - Xw - b||^2  +  alpha * ||w||_1
"""

import math
from typing import List, Sequence, Tuple

DEFAULT_ALPHA = 0.01                 # the paper's default


def soft_threshold(value: float, threshold: float) -> float:
    """The proximal operator of the L1 penalty — where sparsity comes from.

    Shrinks toward zero by `threshold` and clamps anything smaller to exactly
    zero. A source whose evidence does not exceed the penalty gets a score of
    0, not a small number: the attribution says "no evidence", not "a little".
    """
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def standardize(X: Sequence[Sequence[float]]) -> Tuple[List[List[float]],
                                                       List[float], List[float]]:
    """Centre and scale each column. Returns (Z, means, scales).

    Standardising matters for LASSO because a single alpha penalises every
    coefficient equally — that is only fair if the columns share a scale. A
    constant column has zero variance; its scale is forced to 1 so it becomes
    all-zeros after centring and the solver assigns it a coefficient of 0.
    """
    n = len(X)
    d = len(X[0])
    means = [sum(row[j] for row in X) / n for j in range(d)]
    scales = []
    for j in range(d):
        variance = sum((row[j] - means[j]) ** 2 for row in X) / n
        scales.append(math.sqrt(variance) if variance > 1e-12 else 1.0)
    Z = [[(row[j] - means[j]) / scales[j] for j in range(d)] for row in X]
    return Z, means, scales


def lasso_coordinate_descent(Z: Sequence[Sequence[float]], y: Sequence[float],
                             alpha: float = DEFAULT_ALPHA,
                             max_iter: int = 1000,
                             tol: float = 1e-7) -> List[float]:
    """Fit LASSO on standardised, centred data (no intercept term).

    Coordinate descent cycles through coefficients, optimising each with the
    others held fixed. For column j the exact solution is

        w_j = soft_threshold(rho_j, alpha) / (||z_j||^2 / n)

    where rho_j is the correlation of column j with the current residual, with
    j's own contribution added back in. Because the columns are standardised,
    ||z_j||^2 / n == 1 and the denominator disappears.

    The residual is updated incrementally rather than recomputed, which is what
    keeps each sweep O(n*d) instead of O(n*d^2).
    """
    n, d = len(Z), len(Z[0])
    w = [0.0] * d
    residual = list(y)                       # y - Z @ w, and w starts at zero

    for _ in range(max_iter):
        max_change = 0.0
        for j in range(d):
            if w[j] != 0.0:                  # add column j back into the residual
                for i in range(n):
                    residual[i] += Z[i][j] * w[j]

            rho = sum(Z[i][j] * residual[i] for i in range(n)) / n
            norm = sum(Z[i][j] ** 2 for i in range(n)) / n
            new_w = soft_threshold(rho, alpha) / norm if norm > 1e-12 else 0.0

            if new_w != 0.0:                 # take it back out
                for i in range(n):
                    residual[i] -= Z[i][j] * new_w

            max_change = max(max_change, abs(new_w - w[j]))
            w[j] = new_w

        if max_change < tol:
            break
    return w


def fit_lasso(X: Sequence[Sequence[float]], y: Sequence[float],
              alpha: float = DEFAULT_ALPHA,
              normalize_by: float = 1.0) -> Tuple[List[float], float]:
    """Fit on raw X and return coefficients in the ORIGINAL units.

    `normalize_by` is the response length. The reference implementation divides
    the targets by the token count before fitting and multiplies the results
    back afterwards, so that one value of alpha behaves sensibly whether the
    response is five tokens or five hundred.

    Un-standardising:
        w_orig = w_std / scale
        b      = mean(y) - sum(mean_j * w_orig_j)
    """
    if not X:
        raise ValueError("no ablations to fit")
    y_scaled = [value / normalize_by for value in y]

    Z, means, scales = standardize(X)
    y_mean = sum(y_scaled) / len(y_scaled)
    y_centered = [value - y_mean for value in y_scaled]

    w_std = lasso_coordinate_descent(Z, y_centered, alpha=alpha)

    weights = [w_std[j] / scales[j] for j in range(len(w_std))]
    bias = y_mean - sum(means[j] * weights[j] for j in range(len(weights)))

    return ([w * normalize_by for w in weights], bias * normalize_by)


def predict(X: Sequence[Sequence[float]], weights: Sequence[float],
            bias: float) -> List[float]:
    return [sum(x * w for x, w in zip(row, weights)) + bias for row in X]


def r_squared(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    mean = sum(y_true) / len(y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    ss_tot = sum((t - mean) ** 2 for t in y_true)
    return 1 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0


def _demo() -> None:
    import random as _random

    print("=== Soft thresholding ===")
    for value in (0.5, 0.05, -0.5, -0.005):
        print(f"  soft_threshold({value:>6}, 0.1) = "
              f"{soft_threshold(value, 0.1):>7.3f}")
    print("Anything under the penalty becomes exactly 0 — that is the sparsity.")

    print("\n=== Recovering a known sparse signal ===")
    rng = _random.Random(0)
    true_w = [3.0, 0.0, 0.0, -2.0, 0.0, 0.0, 0.5, 0.0]
    true_b = 1.5
    X = [[float(rng.random() < 0.5) for _ in true_w] for _ in range(200)]
    y = [sum(x * w for x, w in zip(row, true_w)) + true_b + rng.gauss(0, 0.05)
         for row in X]

    weights, bias = fit_lasso(X, y, alpha=0.01)
    print(f"{'j':>3}{'true':>9}{'fitted':>10}")
    for j, (t, f) in enumerate(zip(true_w, weights)):
        flag = "  <- signal" if t != 0 else ("  (zeroed)" if f == 0.0 else "")
        print(f"{j:>3}{t:>9.2f}{f:>10.3f}{flag}")
    print(f"bias: true {true_b:.2f}, fitted {bias:.3f}")
    print(f"R^2 on the training ablations: "
          f"{r_squared(y, predict(X, weights, bias)):.4f}")

    print("\n=== alpha controls sparsity ===")
    print(f"{'alpha':>8}{'nonzero':>9}{'R^2':>9}   coefficients")
    for alpha in (0.0, 0.01, 0.1, 0.5, 2.0):
        w, b = fit_lasso(X, y, alpha=alpha)
        nonzero = sum(1 for v in w if v != 0.0)
        preview = " ".join(f"{v:5.2f}" for v in w)
        print(f"{alpha:>8}{nonzero:>9}{r_squared(y, predict(X, w, b)):>9.3f}   {preview}")
    print("Too large an alpha zeroes real sources; too small leaves noise in.")
    print("The paper uses 0.01, which keeps the handful of sources that matter.")

    print("\n=== Attribution on the real ablation data ===")
    from ablation import build_dataset, sample_masks
    from logit_probs import response_score
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    partitioner = ContextPartitioner(CONTEXT)
    response = model.generate(CONTEXT)
    masks = sample_masks(partitioner.num_sources, num_ablations=64)
    X, y = build_dataset(partitioner, model, response, masks, response_score)

    weights, bias = fit_lasso(X, y, alpha=0.01, normalize_by=len(response))
    print(f"{'source':>8}{'score':>10}")
    for index, weight in enumerate(weights):
        marker = "  <- ground truth" if index == GROUND_TRUTH_SOURCE else ""
        print(f"{index:>8}{weight:>10.2f}{marker}")
    top = max(range(len(weights)), key=lambda i: weights[i])
    print(f"\ntop-scoring source: {top} "
          f"(ground truth {GROUND_TRUTH_SOURCE}) -> "
          f"{'CORRECT' if top == GROUND_TRUTH_SOURCE else 'WRONG'}")
    print(f"surrogate R^2: {r_squared(y, predict(X, weights, bias)):.4f}")


if __name__ == "__main__":
    _demo()

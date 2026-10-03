"""
Step 4 — The LASSO surrogate, by coordinate descent
====================================================
Paper: ContextCite, section 3 ("a sparse linear surrogate model"). The
reference implementation calls sklearn's Lasso(alpha=0.01) inside a
StandardScaler pipeline; here you write it yourself, in pure Python.

Effort: the largest file in the directory, and the most rewarding. Take it in
four pieces: soft_threshold, standardize, the descent loop, then the wrapper
that undoes the standardisation.

Objective, matching scikit-learn's convention exactly:

    minimise   (1 / 2n) * ||y - Xw - b||^2  +  alpha * ||w||_1

What you build:
  soft_threshold            -> the proximal operator that creates sparsity
  standardize               -> centre and scale the columns
  lasso_coordinate_descent  -> the solver
  fit_lasso                 -> fit on raw X, return coefficients in raw units

Background:
  Why LASSO and not ordinary least squares: the L1 penalty drives most
  coefficients to EXACTLY zero. An attribution of 0 is a real statement — "no
  evidence this source mattered" — which is more useful than a small noisy
  number you then have to threshold by eye.

  Coordinate descent optimises one coefficient at a time with the rest held
  fixed. For column j the exact solution is

      w_j = soft_threshold(rho_j, alpha) / (||z_j||^2 / n)

  where rho_j is the correlation of column j with the residual, having first
  added j's own contribution back in. On standardised columns the denominator
  is exactly 1, which is a large part of why standardising is worth it.
"""

import math
from typing import List, Sequence, Tuple

DEFAULT_ALPHA = 0.01                 # the paper's default


def soft_threshold(value: float, threshold: float) -> float:
    """Shrink toward zero by `threshold`, clamping small values to exactly 0.

    TODO: three cases — above +threshold, below -threshold, and in between
    (which returns exactly 0.0, not something tiny).
    """
    raise NotImplementedError


def standardize(X: Sequence[Sequence[float]]) -> Tuple[List[List[float]],
                                                       List[float], List[float]]:
    """Centre and scale each column. Returns (Z, means, scales).

    TODO:
    1. means[j] = column mean.
    2. scales[j] = column standard deviation, but force it to 1.0 when the
       variance is ~0. A constant column would otherwise divide by zero; with
       scale 1 it becomes all-zeros after centring and the solver gives it a
       coefficient of 0, which is the right answer.
    3. Z[i][j] = (X[i][j] - means[j]) / scales[j].

    Why standardise at all: one alpha penalises every coefficient equally, and
    that is only fair if the columns are on a common scale.
    """
    raise NotImplementedError


def lasso_coordinate_descent(Z: Sequence[Sequence[float]], y: Sequence[float],
                             alpha: float = DEFAULT_ALPHA,
                             max_iter: int = 1000,
                             tol: float = 1e-7) -> List[float]:
    """Fit LASSO on standardised, centred data. No intercept term.

    TODO:
    1. w = zeros; residual = list(y). (Correct because w starts at zero, so
       y - Zw == y.)
    2. Sweep j = 0..d-1, repeatedly:
         a. If w[j] != 0, add column j back into the residual:
              residual[i] += Z[i][j] * w[j]
         b. rho  = sum(Z[i][j] * residual[i]) / n
            norm = sum(Z[i][j] ** 2) / n          (== 1 on standardised data)
            new  = soft_threshold(rho, alpha) / norm
         c. If new != 0, subtract it back out: residual[i] -= Z[i][j] * new
         d. Track the largest |new - w[j]| this sweep, then set w[j] = new.
    3. Stop when the largest change falls below tol, or after max_iter sweeps.

    Update the residual incrementally as described rather than recomputing
    y - Zw from scratch each time; that is the difference between O(n*d) and
    O(n*d^2) per sweep.
    """
    raise NotImplementedError


def fit_lasso(X: Sequence[Sequence[float]], y: Sequence[float],
              alpha: float = DEFAULT_ALPHA,
              normalize_by: float = 1.0) -> Tuple[List[float], float]:
    """Fit on raw X, returning coefficients in the ORIGINAL units.

    `normalize_by` is the response length. The reference implementation divides
    the targets by the token count before fitting and multiplies back after, so
    a single alpha behaves sensibly whether the response is 5 tokens or 500.

    TODO:
    1. y_scaled = y / normalize_by.
    2. Z, means, scales = standardize(X); centre y_scaled by its mean.
    3. w_std = lasso_coordinate_descent(Z, y_centered, alpha).
    4. Undo the standardisation:
           weights[j] = w_std[j] / scales[j]
           bias       = y_mean - sum(means[j] * weights[j])
    5. Multiply both weights and bias by normalize_by and return them.

    Step 4 is where sign and scale errors hide. Test it by fitting data you
    generated from known coefficients and checking you get them back.
    """
    raise NotImplementedError


def predict(X: Sequence[Sequence[float]], weights: Sequence[float],
            bias: float) -> List[float]:
    """TODO: X @ weights + bias."""
    raise NotImplementedError


def r_squared(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """TODO: 1 - SS_res / SS_tot, guarding SS_tot ~ 0."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify each of these in order:

    1. soft_threshold(0.5, 0.1) == 0.4 and soft_threshold(0.05, 0.1) == 0.0.
    2. Recovery: generate 200 rows of random binary X, pick a sparse true w
       such as [3, 0, 0, -2, 0, 0, 0.5, 0], add small noise, and fit. You
       should recover the three non-zero coefficients to ~0.02 and get exactly
       0.0 for the rest. If the signs are flipped, re-check step 4 of fit_lasso.
    3. Sweep alpha over 0, 0.01, 0.1, 0.5, 2.0 and count non-zero coefficients.
       At 0 nothing is zeroed (that is just OLS); at 2.0 everything is. The
       paper's 0.01 keeps exactly the three real ones.
    4. Fit the real ablation data from step 3. Source 4 should score ~40 while
       every other source lands between -3 and +2, and R^2 should exceed 0.98.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

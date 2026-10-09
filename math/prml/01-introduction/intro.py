"""Curve fitting, the bias-variance decomposition and decision theory, from scratch.

Implements chapter 1 of Bishop, *Pattern Recognition and Machine Learning*, and the
matching material in Murphy, *Probabilistic Machine Learning: An Introduction*
(`bishop:1`, `murphy1:4`). The argument is restated here, never copied:

* polynomial curve fitting by least squares, and the same with an L2 penalty (ridge);
* the bias-variance decomposition by simulating many training sets, as an identity
  ``expected test error = bias^2 + variance + noise``;
* decision theory: the minimum-risk action under a loss matrix, and how an asymmetric
  loss moves the decision boundary away from the posterior probability 0.5;
* information theory: entropy, Kullback-Leibler divergence and mutual information.

Everything is the standard library (``math``, ``random``), in double precision.

DESIGN DECISION -- normal equations with a hand-written Gaussian elimination, not a QR
factorisation? The node is about the shape of the fit and the bias-variance trade-off,
not about numerical linear algebra (that is a different node). Partial pivoting keeps a
degree-9 fit of ten points stable enough for the lesson, and the exact low-degree case is
recovered to 1e-10. **Chosen: Gaussian elimination with partial pivoting.** The cost is
that a very ill-conditioned ridge problem can still lose digits; the limit case uses
regularisation precisely to avoid that.

DESIGN DECISION -- the L2 penalty does not touch the bias term. Penalising the intercept
would make the fit depend on the origin of the target, which is not the ridge regression
of the textbook. **Chosen: add ``lam`` to every diagonal entry except the first.**

DESIGN DECISION -- the expected test error is simulated with fresh test noise, not read
off the decomposition. If the checker computed the expected error as ``bias^2 + variance
+ noise`` it would prove nothing; the identity is only meaningful when the two sides are
measured independently. **Chosen: average ``(h(x*) - t*)^2`` over sets and fresh test
noise, then compare with the sum.**

    python3 intro.py     # prints the measurements this file promises
"""

import math
import random

# The function the bias-variance simulation learns: the textbook example.
TRUE_F = lambda x: math.sin(2.0 * math.pi * x)  # noqa: E731


# ---------------------------------------------------------------------------
# Linear algebra and polynomial fitting
# ---------------------------------------------------------------------------

def poly_features(x, degree):
    """The feature vector ``[1, x, x^2, ..., x^degree]``."""
    # TODO: The feature vector [1, x, x**2, ..., x**degree].
    raise NotImplementedError("poly_features")


def solve_linear(A, b):
    """Solve ``A x = b`` by Gaussian elimination with partial pivoting.

    Raises ``ValueError`` for a singular system. Returns the solution as a list.
    """
    # TODO: Gaussian elimination with PARTIAL PIVOTING: at each column swap in the row with the largest |entry|, eliminate below it, then back-substitute. Raise ValueError when the pivot is ~0 (singular).
    raise NotImplementedError("solve_linear")


def poly_fit(xs, ts, degree, lam=0.0):
    """Least-squares polynomial weights, with an L2 penalty ``lam`` (ridge).

    Minimises ``sum_i (w . phi(x_i) - t_i)^2 + lam * sum_{k>=1} w_k^2``; the bias
    ``w_0`` is not penalised.
    """
    # TODO: Normal equations: A[i][j] = sum_x phi_i(x) phi_j(x), b[i] = sum_x phi_i(x) t. Add lam to every diagonal entry EXCEPT i == 0 (the bias is not penalised), then solve_linear(A, b).
    raise NotImplementedError("poly_fit")


def poly_predict(weights, x):
    """Evaluate the fitted polynomial ``sum_k weights[k] x^k``."""
    # TODO: sum_k weights[k] * x**k.
    raise NotImplementedError("poly_predict")


def squared_error(weights, xs, ts):
    """Mean squared error of ``weights`` on ``(xs, ts)``."""
    # TODO: The mean of (poly_predict(weights, x) - t)**2 over the points.
    raise NotImplementedError("squared_error")


# ---------------------------------------------------------------------------
# The bias-variance decomposition by simulation
# ---------------------------------------------------------------------------

def bias_variance(degree, n_train, sigma, seed, n_sets=300, n_test=25):
    """Simulate many training sets and return ``(bias^2, variance, noise, error)``.

    The target is ``t = sin(2 pi x) + N(0, sigma)``. Each training set is fit with a
    degree-``degree`` polynomial; predictions are averaged at ``n_test`` fixed test
    inputs. ``error`` is the average squared test error measured with *fresh* test
    noise, so the identity ``error == bias^2 + variance + noise`` is a real check.
    """
    # TODO: Simulate n_sets training sets of sin(2 pi x) + N(0, sigma); average the predictions at fixed test inputs. bias^2 = mean over test of (mean_pred - f)^2; variance = mean over test of the per-set squared deviation from mean_pred; noise = sigma^2; the returned error is the average (pred - (f + FRESH test noise))^2, so the identity error == bias^2 + variance + noise is a real measurement.
    raise NotImplementedError("bias_variance")


# ---------------------------------------------------------------------------
# Decision theory
# ---------------------------------------------------------------------------

def min_risk_decision(p, loss):
    """The action (0 or 1) of least expected loss.

    ``p`` is ``P(class = 1)``. ``loss[a][c]`` is the loss of taking action ``a`` when
    the true class is ``c``. The expected loss of action ``a`` is
    ``loss[a][0] (1 - p) + loss[a][1] p``; ties go to action 0.
    """
    # TODO: The action a minimising loss[a][0]*(1-p) + loss[a][1]*p (ties to action 0). Do NOT fall back to a fixed 0.5 threshold: an asymmetric loss moves the boundary.
    raise NotImplementedError("min_risk_decision")


# ---------------------------------------------------------------------------
# Information theory
# ---------------------------------------------------------------------------

def entropy(p):
    """Shannon entropy in nats of a discrete distribution ``p``, with 0 log 0 = 0."""
    # TODO: -sum(pi * log(pi) for pi > 0) in nats; skip zero-probability terms.
    raise NotImplementedError("entropy")


def kl_divergence(p, q):
    """``KL(p || q) = sum_i p_i log(p_i / q_i)``, with 0 log 0 = 0.

    Not symmetric; non-negative, and zero exactly when p and q agree on p's support.
    """
    # TODO: sum(pi * log(pi / qi) for pi > 0). Not symmetric; non-negative and zero only for equal distributions. Do not flip the ratio.
    raise NotImplementedError("kl_divergence")


def mutual_information(joint):
    """Mutual information ``I(X; Y)`` of a 2-D joint pmf ``joint[x][y]``, in nats."""
    # TODO: From a 2-D joint: px, py are the marginals; return sum over p_ij > 0 of p_ij * log(p_ij / (px_i * py_j)). Zero when independent, positive otherwise.
    raise NotImplementedError("mutual_information")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    """Print one measurement per construction this module promises."""
    print("Curve fitting, bias-variance and decision theory — measurements")

    xs = [i / 19.0 for i in range(20)]
    ts = [1.0 - 2.0 * x + 0.5 * x * x for x in xs]
    w = poly_fit(xs, ts, 2)
    print(f"  exact quadratic fit: weights {[round(v, 6) for v in w]}  (expected [1, -2, 0.5])")

    rng = random.Random(2)
    x9 = [i / 9.0 for i in range(10)]
    t9 = [TRUE_F(x) + rng.gauss(0.0, 0.3) for x in x9]
    xt = [0.005 + 0.99 * i / 399.0 for i in range(400)]
    tt = [TRUE_F(x) for x in xt]
    w9 = poly_fit(x9, t9, 9)
    wr = poly_fit(x9, t9, 9, lam=1e-5)
    print(f"  degree-9 on 10 noisy points: train {squared_error(w9, x9, t9):.2e}"
          f"  test {squared_error(w9, xt, tt):.2e}")
    print(f"  the same with ridge 1e-5: test {squared_error(wr, xt, tt):.2e}")

    b, v, n, e = bias_variance(degree=1, n_train=20, sigma=0.2, seed=1)
    print(f"  bias-variance (degree 1): bias^2 {b:.4f} + variance {v:.4f}"
          f" + noise {n:.4f} = {b + v + n:.4f}  vs simulated error {e:.4f}")

    sym = [[0.0, 1.0], [1.0, 0.0]]
    asym = [[0.0, 10.0], [1.0, 0.0]]
    print(f"  symmetric loss:   decision at p=0.4 -> {min_risk_decision(0.4, sym)}"
          f", p=0.6 -> {min_risk_decision(0.6, sym)}")
    print(f"  asymmetric loss:  decision at p=0.4 -> {min_risk_decision(0.4, asym)}"
          f", p=0.6 -> {min_risk_decision(0.6, asym)}")

    print(f"  entropy([0.5, 0.5]) = {entropy([0.5, 0.5]):.6f}  (ln 2 = {math.log(2):.6f})")
    print(f"  KL([0.7,0.3] || [0.5,0.5]) = {kl_divergence([0.7, 0.3], [0.5, 0.5]):.6f}")
    print(f"  MI(correlated 2x2) = {mutual_information([[0.5, 0.0], [0.0, 0.5]]):.6f}"
          f"  MI(independent) = {mutual_information([[0.25, 0.25], [0.25, 0.25]]):.6f}")


if __name__ == "__main__":
    demo()

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
    return [x ** k for k in range(degree + 1)]


def solve_linear(A, b):
    """Solve ``A x = b`` by Gaussian elimination with partial pivoting.

    Raises ``ValueError`` for a singular system. Returns the solution as a list.
    """
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            raise ValueError("singular system")
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            factor = M[r][col] / M[col][col]
            for k in range(col, n + 1):
                M[r][k] -= factor * M[col][k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


def poly_fit(xs, ts, degree, lam=0.0):
    """Least-squares polynomial weights, with an L2 penalty ``lam`` (ridge).

    Minimises ``sum_i (w . phi(x_i) - t_i)^2 + lam * sum_{k>=1} w_k^2``; the bias
    ``w_0`` is not penalised.
    """
    n = degree + 1
    A = [[0.0] * n for _ in range(n)]
    b = [0.0] * n
    for x, t in zip(xs, ts):
        phi = poly_features(x, degree)
        for i in range(n):
            b[i] += phi[i] * t
            for j in range(n):
                A[i][j] += phi[i] * phi[j]
    for i in range(n):
        if i > 0:
            A[i][i] += lam
    return solve_linear(A, b)


def poly_predict(weights, x):
    """Evaluate the fitted polynomial ``sum_k weights[k] x^k``."""
    return sum(w * (x ** k) for k, w in enumerate(weights))


def squared_error(weights, xs, ts):
    """Mean squared error of ``weights`` on ``(xs, ts)``."""
    return sum((poly_predict(weights, x) - t) ** 2 for x, t in zip(xs, ts)) / len(xs)


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
    rng = random.Random(seed)
    test_x = [0.03 + 0.94 * i / (n_test - 1) for i in range(n_test)]
    preds = []
    for _ in range(n_sets):
        x = []
        while len(x) < n_train:
            v = rng.random()
            if all(abs(v - u) > 1e-9 for u in x):
                x.append(v)
        t = [TRUE_F(v) + rng.gauss(0.0, sigma) for v in x]
        w = poly_fit(x, t, degree)
        preds.append([poly_predict(w, v) for v in test_x])

    mean = [sum(preds[s][i] for s in range(n_sets)) / n_sets for i in range(n_test)]
    bias_sq = sum((mean[i] - TRUE_F(test_x[i])) ** 2 for i in range(n_test)) / n_test
    variance = sum(
        sum((preds[s][i] - mean[i]) ** 2 for s in range(n_sets)) / n_sets
        for i in range(n_test)
    ) / n_test
    noise = sigma * sigma
    total = 0.0
    count = 0
    for s in range(n_sets):
        for i in range(n_test):
            target = TRUE_F(test_x[i]) + rng.gauss(0.0, sigma)
            total += (preds[s][i] - target) ** 2
            count += 1
    return bias_sq, variance, noise, total / count


# ---------------------------------------------------------------------------
# Decision theory
# ---------------------------------------------------------------------------

def min_risk_decision(p, loss):
    """The action (0 or 1) of least expected loss.

    ``p`` is ``P(class = 1)``. ``loss[a][c]`` is the loss of taking action ``a`` when
    the true class is ``c``. The expected loss of action ``a`` is
    ``loss[a][0] (1 - p) + loss[a][1] p``; ties go to action 0.
    """
    expected = [loss[a][0] * (1.0 - p) + loss[a][1] * p for a in range(2)]
    return 0 if expected[0] <= expected[1] else 1


# ---------------------------------------------------------------------------
# Information theory
# ---------------------------------------------------------------------------

def entropy(p):
    """Shannon entropy in nats of a discrete distribution ``p``, with 0 log 0 = 0."""
    return -sum(pi * math.log(pi) for pi in p if pi > 0.0)


def kl_divergence(p, q):
    """``KL(p || q) = sum_i p_i log(p_i / q_i)``, with 0 log 0 = 0.

    Not symmetric; non-negative, and zero exactly when p and q agree on p's support.
    """
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0.0)


def mutual_information(joint):
    """Mutual information ``I(X; Y)`` of a 2-D joint pmf ``joint[x][y]``, in nats."""
    rows = len(joint)
    cols = len(joint[0])
    px = [sum(joint[i][j] for j in range(cols)) for i in range(rows)]
    py = [sum(joint[i][j] for i in range(rows)) for j in range(cols)]
    total = 0.0
    for i in range(rows):
        for j in range(cols):
            p_ij = joint[i][j]
            if p_ij > 0.0:
                total += p_ij * math.log(p_ij / (px[i] * py[j]))
    return total


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

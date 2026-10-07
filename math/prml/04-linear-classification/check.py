"""
Progress checker for the PRML-linear-classification templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own linear algebra (`_solve`, `_inverse`), its own Fisher
closed form (`_fisher_reference`, an inverse-scatter direction) and its own Newton
solver for logistic regression (`_logistic_newton`), so the numeric comparisons are
against an independent implementation, not against a restatement of yours. The accept
criteria -- IRLS beats gradient descent by a wide margin at the same tolerance, and the
Laplace mean is exactly the MAP -- plus the two limit cases are measured on fixed
hand-built data.
"""

import math
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# The checker's own references (never the learner's)
# ---------------------------------------------------------------------------

def _design(Xs):
    """Bias column prepended: row ``i`` is ``[1.0, x_i...]``."""
    return [[1.0] + [float(v) for v in row] for row in Xs]


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _solve(A, b):
    """Solve ``A x = b`` by Gaussian elimination with partial pivoting."""
    n = len(A)
    m = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            factor = m[r][col] / m[col][col]
            if factor != 0.0:
                for k in range(col, n + 1):
                    m[r][k] -= factor * m[col][k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def _inverse(A):
    """Invert ``A`` by Gauss-Jordan elimination with partial pivoting."""
    n = len(A)
    m = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        for k in range(2 * n):
            m[col][k] /= scale
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                factor = m[r][col]
                for k in range(2 * n):
                    m[r][k] -= factor * m[col][k]
    return [row[n:] for row in m]


def _sigmoid(z):
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _probs(Xs, w):
    return [_sigmoid(_dot(w, row)) for row in _design(Xs)]


def _fisher_reference(Xs, ts):
    """The closed form ``S_W^{-1} (m_1 - m_0)``, the checker's way."""
    d = len(Xs[0])
    n1 = sum(1 for t in ts if t >= 0.5)
    n0 = len(ts) - n1
    m1 = [sum(x[j] for x, t in zip(Xs, ts) if t >= 0.5) / n1 for j in range(d)]
    m0 = [sum(x[j] for x, t in zip(Xs, ts) if t < 0.5) / n0 for j in range(d)]
    scatter = [[0.0] * d for _ in range(d)]
    for x, t in zip(Xs, ts):
        mean = m1 if t >= 0.5 else m0
        diff = [x[j] - mean[j] for j in range(d)]
        for i in range(d):
            for j in range(d):
                scatter[i][j] += diff[i] * diff[j]
    inv = _inverse(scatter)
    delta = [m1[j] - m0[j] for j in range(d)]
    return [sum(inv[i][j] * delta[j] for j in range(d)) for i in range(d)]


def _logistic_newton(Xs, ts, ridge, tol=1e-13, maxit=200):
    """Independent Newton-Raphson fit of the penalised logistic model."""
    B = _design(Xs)
    d = len(B[0])
    w = [0.0] * d
    for _ in range(maxit):
        p = [_sigmoid(_dot(w, row)) for row in B]
        g = [0.0] * d
        H = [[0.0] * d for _ in range(d)]
        for row, t, pi in zip(B, ts, p):
            s = pi * (1.0 - pi)
            e = t - pi
            for i in range(d):
                g[i] -= e * row[i]
                for j in range(d):
                    H[i][j] += s * row[i] * row[j]
        for i in range(d):
            g[i] += ridge * w[i]
            H[i][i] += ridge
        if math.sqrt(sum(v * v for v in g)) < tol:
            break
        step = _solve(H, [-g[i] for i in range(d)])
        w = [w[i] + step[i] for i in range(d)]
    return w


def _logistic_hessian(Xs, w, ridge):
    B = _design(Xs)
    d = len(B[0])
    H = [[0.0] * d for _ in range(d)]
    for row, pi in zip(B, _probs(Xs, w)):
        s = pi * (1.0 - pi)
        for i in range(d):
            for j in range(d):
                H[i][j] += s * row[i] * row[j]
    for i in range(d):
        H[i][i] += ridge
    return H


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _close(a, b, tol):
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# Fixed data (deterministic, no random draws)
# ---------------------------------------------------------------------------

# Linearly separable but anisotropic 2-D data: the within-class scatter is not a
# multiple of the identity, so Fisher's rule is not the plain difference of means.
SEPARABLE_XS = [
    [-1.4, -0.2], [-1.1, -0.5], [-0.9, 0.1], [-1.2, 0.4], [-0.8, -0.3],
    [0.8, 0.1], [1.0, -0.4], [1.3, 0.2], [0.9, 0.6], [1.2, -0.1],
]
SEPARABLE_TS = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]

# A small 2-D set that is NOT linearly separable (the skew keeps the logistic MLE
# finite and away from the symmetric origin), used for the logistic checks.
LOGISTIC_XS = [
    [-1.0, 0.0], [-0.3, 0.2], [0.4, -0.1], [0.8, 0.3],
    [-0.6, 0.1], [0.0, 0.3], [0.5, 0.4], [1.0, 0.0],
]
LOGISTIC_TS = [0, 0, 0, 0, 1, 1, 1, 1]

# Linearly separable 1-D data for the divergence limit case.
DIVERGE_XS = [[-1.0], [-0.7], [-0.4], [0.4], [0.7], [1.0]]
DIVERGE_TS = [0, 0, 0, 1, 1, 1]

# Overlapping 1-D data (finite logistic MLE) plus one far outlier labelled 0.
OUTLIER_CLEAN_XS = [[-1.0], [-0.8], [-0.4], [0.1], [-0.2], [0.6], [0.8], [1.0]]
OUTLIER_TS = [0, 0, 0, 0, 1, 1, 1, 1]


def _predict(w, x, cut=0.5):
    return 1 if _dot(w, [1.0] + [float(v) for v in x]) > cut else 0


# ---------------------------------------------------------------------------
# Step 1: least squares, Fisher and the perceptron on separable data
# ---------------------------------------------------------------------------

def check_linear_classifiers() -> None:
    from classification import least_squares_classifier, fisher_lda, perceptron

    w_ls = least_squares_classifier(SEPARABLE_XS, SEPARABLE_TS)
    assert len(w_ls) == 3, \
        f"with an intercept the weight vector has 2 + 1 = 3 entries, got {len(w_ls)}"
    pred = [_predict(w_ls, x) for x in SEPARABLE_XS]
    assert pred == list(SEPARABLE_TS), (
        "the least-squares discriminant must classify this separable training set "
        f"perfectly; got {pred} for targets {SEPARABLE_TS}")

    direction, threshold = fisher_lda(SEPARABLE_XS, SEPARABLE_TS)
    assert len(direction) == 2, \
        f"Fisher's direction lives in the 2-D feature space, got {len(direction)} entries"
    labels = [1 if _dot(direction, x) > threshold else 0 for x in SEPARABLE_XS]
    assert labels == list(SEPARABLE_TS), (
        "the Fisher threshold must sit at the midpoint of the projected class means; "
        f"got labels {labels} for targets {SEPARABLE_TS}")

    want = _fisher_reference(SEPARABLE_XS, SEPARABLE_TS)
    assert all(_close(direction[j], want[j], 1e-8) for j in range(2)), (
        "Fisher's direction must be S_W^{-1} (m_1 - m_0), the inverse WITHIN-class "
        "scatter times the difference of means -- the plain difference of means is "
        f"wrong (unless S_W is the identity): got {direction}, want {want}")

    w_perc, iters = perceptron(SEPARABLE_XS, SEPARABLE_TS, maxit=100)
    assert len(w_perc) == 3, \
        f"the perceptron weights must include the bias, got {len(w_perc)} entries"
    plabels = [1 if _dot(w_perc, [1.0] + list(x)) > 0.0 else 0 for x in SEPARABLE_XS]
    assert plabels == list(SEPARABLE_TS), (
        "on linearly separable data the perceptron must reach a separating weight "
        f"vector; got labels {plabels} for targets {SEPARABLE_TS}")
    assert iters < 100, (
        "the perceptron converges in finitely many passes on separable data, so it must "
        f"stop before maxit (the perceptron convergence theorem); used {iters} passes")


# ---------------------------------------------------------------------------
# Step 2: logistic IRLS matches an independent Newton reference
# ---------------------------------------------------------------------------

def check_logistic_reference() -> None:
    from classification import logistic_irls

    w, iters = logistic_irls(LOGISTIC_XS, LOGISTIC_TS, maxit=200, tol=1e-11)
    reference = _logistic_newton(LOGISTIC_XS, LOGISTIC_TS, 0.0, tol=1e-13)

    got = _probs(LOGISTIC_XS, w)
    want = _probs(LOGISTIC_XS, reference)
    assert all(_close(g, e, 1e-7) for g, e in zip(got, want)), (
        "the IRLS predicted probabilities must match an independent Newton fit of the "
        "logistic likelihood; check the Newton update (Phi^T R Phi) w = Phi^T R z and "
        f"the stable sigmoid: got {got}, want {want}")

    grad = _logistic_newton(LOGISTIC_XS, LOGISTIC_TS, 0.0)  # warm the reference path
    assert _norm([w[j] - reference[j] for j in range(len(w))]) < 1e-7, (
        f"the IRLS weights must equal the Newton MLE, got {w} vs {reference}")
    assert grad is not None

    # At the optimum the gradient of the negative log-likelihood vanishes.
    d = len(w)
    g = [0.0] * d
    for row, t, pi in zip(_design(LOGISTIC_XS), LOGISTIC_TS, got):
        e = t - pi
        for i in range(d):
            g[i] -= e * row[i]
    assert _norm(g) < 1e-7, (
        f"the IRLS solution must be a stationary point; ||Phi^T (t - p)|| = {_norm(g):.2e}")


# ---------------------------------------------------------------------------
# Step 3 (ACCEPT): IRLS needs far fewer iterations than gradient descent
# ---------------------------------------------------------------------------

def check_irls_beats_gradient_descent() -> None:
    from classification import logistic_irls, logistic_gradient_descent

    tol = 1e-9
    w_irls, n_irls = logistic_irls(LOGISTIC_XS, LOGISTIC_TS, maxit=200, tol=tol)
    w_gd, n_gd = logistic_gradient_descent(
        LOGISTIC_XS, LOGISTIC_TS, lr=0.5, maxit=200000, tol=tol)

    assert _norm([a - b for a, b in zip(w_irls, w_gd)]) < 1e-3, (
        "the two optimisers must land on the same optimum before their iteration "
        f"counts can be compared: IRLS {w_irls}, gradient descent {w_gd}")

    assert n_irls <= 12, (
        "IRLS is Newton's method: on this 8-point problem it must take only a handful "
        f"of steps, got {n_irls}. Check the weight matrix R = diag(p(1-p)); dropping it "
        "turns Newton into a much slower fixed-metric iteration")

    assert n_gd > 20 * n_irls, (
        "the ACCEPT: IRLS must reach the tolerance in FAR fewer iterations than "
        f"gradient descent; got IRLS {n_irls}, gradient descent {n_gd}")


# ---------------------------------------------------------------------------
# Step 4 (ACCEPT): the Laplace mean is the MAP estimate
# ---------------------------------------------------------------------------

def check_laplace_mean_is_map() -> None:
    from classification import laplace_logistic

    prior_var = 4.0
    ridge = 1.0 / prior_var
    mean, cov = laplace_logistic(LOGISTIC_XS, LOGISTIC_TS, prior_var)
    reference = _logistic_newton(LOGISTIC_XS, LOGISTIC_TS, ridge, tol=1e-14)

    assert all(_close(mean[j], reference[j], 1e-9) for j in range(len(mean))), (
        "the ACCEPT: the Laplace approximation is centred on the MAP weights (the mode "
        "of the posterior), so its mean must equal the penalised MLE w_MAP -- not zero "
        f"and not the prior mean: got {mean}, want {reference}")

    want_cov = _inverse(_logistic_hessian(LOGISTIC_XS, mean, ridge))
    assert len(cov) == len(want_cov) and all(
        _close(cov[i][j], want_cov[i][j], 1e-8)
        for i in range(len(cov)) for j in range(len(cov))
    ), "the Laplace covariance must be the inverse Hessian at the MAP: (Phi^T R Phi + ridge I)^{-1}"
    for i in range(len(cov)):
        assert cov[i][i] > 0.0, \
            f"the Laplace covariance must be positive definite, variance {i} = {cov[i][i]}"
        for j in range(len(cov)):
            assert _close(cov[i][j], cov[j][i], 1e-12), \
                "the Laplace covariance must be symmetric"


# ---------------------------------------------------------------------------
# Step 5 (LIMIT CASES)
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    from classification import (
        least_squares_classifier, logistic_irls)

    # (a) Linearly separable data: the unregularised logistic weights diverge.
    def norm_at(cap):
        # No ridge argument: the unregularised run must fall back to the default prior-free
        # fit, which is exactly the path that DIVERGES on separable data.
        w, _ = logistic_irls(DIVERGE_XS, DIVERGE_TS, maxit=cap, tol=0.0)
        return _norm(w)

    def norm_with_prior(cap):
        w, _ = logistic_irls(DIVERGE_XS, DIVERGE_TS, maxit=cap, tol=0.0, ridge=1.0)
        return _norm(w)

    no_prior = [norm_at(cap) for cap in (4, 8, 12)]
    assert no_prior[0] < no_prior[1] < no_prior[2], (
        "on linearly separable data the unregularised logistic likelihood keeps rising "
        "as the weights grow along the separating direction, so ||w|| must keep growing "
        f"with more Newton steps; got {no_prior} at 4/8/12 steps")
    assert no_prior[2] > 2.0 * no_prior[0], (
        "the growth must be substantial, not a numerical wobble: "
        f"||w|| went {no_prior[0]:.3f} -> {no_prior[2]:.3f}")

    with_prior = [norm_with_prior(cap) for cap in (4, 8, 12)]
    assert _norm([with_prior[0] - with_prior[2]]) < 1e-6, (
        "an L2 prior must pin the weights to a finite MAP: with ridge = 1 the norm must "
        f"settle, not grow; got {with_prior} at 4/8/12 steps")
    assert with_prior[2] < 5.0 < no_prior[2], (
        "the prior must keep ||w|| finite and well below the unregularised run: "
        f"regularised {with_prior[2]:.3f}, unregularised {no_prior[2]:.3f}")

    # (b) An outlier wrecks the least-squares boundary but barely moves logistic's.
    def boundary(w):
        return -w[0] / w[1]

    ls_clean = boundary(least_squares_classifier(OUTLIER_CLEAN_XS, OUTLIER_TS))
    ls_out = boundary(least_squares_classifier(
        OUTLIER_CLEAN_XS + [[8.0]], OUTLIER_TS + [0]))
    log_clean = boundary(logistic_irls(
        OUTLIER_CLEAN_XS, OUTLIER_TS, maxit=300, tol=1e-12)[0])
    log_out = boundary(logistic_irls(
        OUTLIER_CLEAN_XS + [[8.0]], OUTLIER_TS + [0], maxit=300, tol=1e-12)[0])

    ls_shift = abs(ls_out - ls_clean)
    log_shift = abs(log_out - log_clean)
    assert ls_shift > 10.0, (
        "a far outlier labelled against the local trend must drag the least-squares "
        f"boundary a long way (it weighs the point by its distance): shift = {ls_shift:.4f}")
    assert ls_shift > 5.0 * log_shift, (
        "the ACCEPT: logistic regression saturates, so the same outlier must move its "
        f"boundary far less than least squares': LS {ls_shift:.4f} vs logistic {log_shift:.4f}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("classification.py", "least squares, Fisher and the perceptron separate the data", check_linear_classifiers),
    ("classification.py", "logistic IRLS matches an independent Newton fit", check_logistic_reference),
    ("classification.py", "ACCEPT: IRLS beats gradient descent on iteration count", check_irls_beats_gradient_descent),
    ("classification.py", "ACCEPT: the Laplace mean equals the MAP estimate", check_laplace_mean_is_map),
    ("classification.py", "LIMIT: separable divergence and the outlier asymmetry", check_limit_cases),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}PRML Linear Classification From Scratch — progress check{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<18} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<18} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<18} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built linear classification from scratch.{RESET}")
        print(f"  {GREY}Run solutions/classification.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

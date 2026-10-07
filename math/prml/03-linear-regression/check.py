"""
Progress checker for the PRML-linear-regression templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own linear algebra (`_solve`, `_inverse`, `_log_det`), its own
Gram matrix and its own log-evidence (`_log_evidence`), so the numeric comparisons are
against an independent implementation, not against a restatement of yours. The accept
criterion -- the predictive variance grows away from the training data, and the evidence
recovers the true noise precision -- is measured on fixed synthetic data.
"""

import math
import pathlib
import random
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

def _poly(degree):
    """A polynomial basis ``[1, x, ..., x^degree]`` as a list of callables."""
    return [lambda x, k=k: x ** k for k in range(degree + 1)]


def _design(xs, basis):
    """The design matrix, the checker's way."""
    return [[f(x) for f in basis] for x in xs]


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
    """Invert ``A`` by Gauss-Jordan elimination."""
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


def _log_det(A):
    """``ln |det A|`` by elimination with partial pivoting."""
    n = len(A)
    m = [list(row) for row in A]
    total = 0.0
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            return -math.inf
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
        value = m[col][col]
        total += math.log(abs(value))
        for r in range(col + 1, n):
            factor = m[r][col] / value
            if factor != 0.0:
                for k in range(col, n):
                    m[r][k] -= factor * m[col][k]
    return total


def _gram(Phi):
    """``Phi^T Phi``."""
    cols = len(Phi[0])
    A = [[0.0] * cols for _ in range(cols)]
    for row in Phi:
        for i in range(cols):
            for j in range(cols):
                A[i][j] += row[i] * row[j]
    return A


def _rhs(Phi, ts):
    """``Phi^T t``."""
    cols = len(Phi[0])
    b = [0.0] * cols
    for row, t in zip(Phi, ts):
        for i in range(cols):
            b[i] += row[i] * t
    return b


def _precision(Phi, alpha, beta):
    """``S_N^{-1} = alpha I + beta Phi^T Phi``."""
    A = [[beta * value for value in row] for row in _gram(Phi)]
    for i in range(len(A)):
        A[i][i] += alpha
    return A


def _ridge(Phi, ts, alpha):
    """The checker's ridge weights."""
    A = _gram(Phi)
    for i in range(len(A)):
        A[i][i] += alpha
    return _solve(A, _rhs(Phi, ts))


def _log_evidence(Phi, ts, alpha, beta):
    """The checker's log marginal likelihood (Bishop 3.77)."""
    n = len(Phi)
    cols = len(Phi[0])
    precision = _precision(Phi, alpha, beta)
    mean = _solve(precision, [beta * value for value in _rhs(Phi, ts)])
    residual = sum(
        (t - sum(row[i] * mean[i] for i in range(cols))) ** 2
        for row, t in zip(Phi, ts)
    )
    energy = 0.5 * beta * residual + 0.5 * alpha * sum(w * w for w in mean)
    return (0.5 * cols * math.log(alpha) + 0.5 * n * math.log(beta) - energy
            - 0.5 * n * math.log(2.0 * math.pi) - 0.5 * _log_det(precision))


def _norm(w):
    return math.sqrt(sum(v * v for v in w))


def _close(a, b, tol):
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# Step 1: MLE and ridge on a synthetic polynomial
# ---------------------------------------------------------------------------

def check_mle_and_ridge() -> None:
    from regression import design_matrix, mle_weights, ridge_weights

    basis = _poly(2)
    xs = [-1.0 + 2.0 * i / 19.0 for i in range(20)]
    ts = [1.0 - 2.0 * x + 0.5 * x * x for x in xs]

    Phi = design_matrix(xs, basis)
    assert len(Phi) == 20 and len(Phi[0]) == 3, \
        f"the design matrix must be N x M = 20 x 3, got {len(Phi)} x {len(Phi[0])}"
    assert _close(Phi[0][0], 1.0, 1e-12) and _close(Phi[0][1], xs[0], 1e-12) \
        and _close(Phi[0][2], xs[0] ** 2, 1e-12), \
        f"row 0 must be [1, x, x^2], got {Phi[0]}"

    w = mle_weights(Phi, ts)
    assert w is not None, \
        "with 20 points and 3 basis functions the normal equations are not singular"
    want = [1.0, -2.0, 0.5]
    assert all(_close(w[k], want[k], 1e-7) for k in range(3)), \
        f"MLE must recover the exact quadratic [1, -2, 0.5], got {w}"

    rng = random.Random(1)
    noisy = [t + rng.gauss(0.0, 0.3) for t in ts]
    w_mle = mle_weights(Phi, noisy)
    w_ridge = ridge_weights(Phi, noisy, 1.0)
    assert _norm(w_ridge) < _norm(w_mle), (
        "ridge must shrink the weights relative to MLE (the penalty adds alpha I to "
        f"Phi^T Phi, it does not subtract): ||MLE|| {_norm(w_mle):.4f}, "
        f"||ridge|| {_norm(w_ridge):.4f}")

    reference = _ridge(Phi, noisy, 1.0)
    assert all(_close(w_ridge[k], reference[k], 1e-8) for k in range(3)), \
        f"ridge weights must solve (alpha I + Phi^T Phi) w = Phi^T t; got {w_ridge}, want {reference}"

    w_strong = ridge_weights(Phi, noisy, 10.0)
    assert _norm(w_strong) < _norm(w_ridge), \
        "a larger penalty must shrink the weights further"


# ---------------------------------------------------------------------------
# Step 2: the posterior mean is a ridge solution (a consistency check)
# ---------------------------------------------------------------------------

def check_posterior_consistency() -> None:
    from regression import bayesian_posterior, mle_weights

    basis = _poly(3)
    xs = [-1.0 + 2.0 * i / 14.0 for i in range(15)]
    rng = random.Random(7)
    ts = [math.sin(2.0 * x) + rng.gauss(0.0, 0.2) for x in xs]
    Phi = _design(xs, basis)

    alpha, beta = 0.5, 20.0
    mean, cov = bayesian_posterior(Phi, ts, alpha, beta)

    # m_N = (alpha I + beta Phi^T Phi)^{-1} beta Phi^T t == ridge with lambda = alpha/beta.
    reference = _ridge(Phi, ts, alpha / beta)
    assert all(_close(mean[k], reference[k], 1e-7) for k in range(len(mean))), (
        "the Bayesian posterior mean must equal the ridge solution with lambda = "
        f"alpha / beta: got {mean}, want {reference}. Check that S_N^{-1} carries the "
        "factor beta on Phi^T Phi.")

    ref_cov = _inverse(_precision(Phi, alpha, beta))
    assert len(cov) == len(ref_cov) and all(
        _close(cov[i][j], ref_cov[i][j], 1e-8)
        for i in range(len(cov)) for j in range(len(cov))
    ), "the posterior covariance must be S_N = (alpha I + beta Phi^T Phi)^{-1}"

    # beta -> infinity sends the posterior mean to the maximum-likelihood solution.
    mean_inf, _ = bayesian_posterior(Phi, ts, alpha, 1e9)
    w_mle = mle_weights(Phi, ts)
    assert w_mle is not None
    assert all(_close(mean_inf[k], w_mle[k], 1e-4) for k in range(len(mean_inf))), (
        "as the noise precision beta grows the posterior mean must approach the MLE, "
        f"got {mean_inf} vs {w_mle}")


# ---------------------------------------------------------------------------
# Step 3 (ACCEPT): the predictive variance grows away from the training data
# ---------------------------------------------------------------------------

def check_predictive_variance_grows() -> None:
    from regression import bayesian_posterior, design_matrix, predictive_distribution

    basis = _poly(5)
    xs = [-0.6 + 1.2 * i / 10.0 for i in range(11)]  # training region [-0.6, 0.6]
    ts = [1.0 - 2.0 * x + 0.5 * x * x for x in xs]
    Phi = design_matrix(xs, basis)
    alpha, beta = 1.0, 25.0
    mean, cov = bayesian_posterior(Phi, ts, alpha, beta)

    # Inside the training region the variance sits near the noise floor 1 / beta.
    inside = design_matrix([0.0], basis)
    _, var_inside = predictive_distribution(inside, mean, cov, beta)
    assert var_inside[0] > 0.5 / beta, (
        "the predictive variance inside the data must include the observation noise "
        f"1/beta = {1.0 / beta:.4f}: got only {var_inside[0]:.4f}. The 1/beta term is "
        "the floor every prediction carries.")

    # Moving away from the data, the variance must increase monotonically.
    outward = [0.7, 1.0, 1.4, 1.9, 2.5, 3.2]
    _, variances = predictive_distribution(design_matrix(outward, basis), mean, cov, beta)
    assert all(math.isfinite(v) for v in variances), \
        f"the predictive variances must be finite, got {variances}"
    for i in range(len(variances) - 1):
        assert variances[i] < variances[i + 1], (
            "the predictive variance must grow as the test point moves away from the "
            f"training region: at |x| = {outward[i]} it is {variances[i]:.5f}, at "
            f"|x| = {outward[i + 1]} it is {variances[i + 1]:.5f}")
    assert variances[-1] > 10.0 * var_inside[0], (
        "far outside the data the predictive variance must be much larger than the "
        f"noise floor: {variances[-1]:.4f} vs {var_inside[0]:.4f}")


# ---------------------------------------------------------------------------
# Step 4: the evidence approximation recovers the true noise precision
# ---------------------------------------------------------------------------

def check_evidence() -> None:
    from regression import log_evidence, maximise_evidence

    basis = _poly(5)
    xs = [-1.0 + 2.0 * i / 29.0 for i in range(30)]
    rng = random.Random(5)
    ts = [1.0 - 2.0 * x + 0.5 * x * x + rng.gauss(0.0, 0.2) for x in xs]
    Phi = _design(xs, basis)

    for alpha, beta in ((0.5, 10.0), (1.0, 25.0), (2.0, 50.0)):
        got = log_evidence(Phi, ts, alpha, beta)
        want = _log_evidence(Phi, ts, alpha, beta)
        assert _close(got, want, 1e-7), (
            f"log_evidence(alpha={alpha}, beta={beta}) must include the M/2 ln alpha, "
            "N/2 ln beta, -E(m_N) and the +1/2 ln|S_N| Occam term: "
            f"got {got:.6f}, want {want:.6f}")

    alphas = [10.0 ** e for e in (-3, -2, -1, 0, 1, 2)]
    betas = [10.0 ** e for e in (0, 0.5, 1, 1.5, 2, 2.5, 3)]
    selected = maximise_evidence(Phi, ts, alphas, betas)
    assert selected is not None, "maximise_evidence must return the best (alpha, beta)"
    best_alpha, best_beta = selected

    # The data were generated with noise sigma = 0.2, i.e. beta = 1/0.04 = 25.
    assert 0.5 * 25.0 <= best_beta <= 2.0 * 25.0, (
        "evidence maximisation must recover the true noise precision 1/sigma^2 = 25 "
        f"to within a factor of 2, got beta = {best_beta:g} (alpha = {best_alpha:g})")

    # The Occam term keeps the selection off the smallest penalty (infinite flexibility).
    assert best_alpha > min(alphas), (
        "the +1/2 ln|S_N| Occam term must stop the evidence from choosing the most "
        f"flexible model (smallest alpha); got alpha = {best_alpha:g}")


# ---------------------------------------------------------------------------
# Step 5 (LIMIT CASE): more basis functions than data points
# ---------------------------------------------------------------------------

def check_limit_case() -> None:
    from regression import bayesian_posterior, design_matrix, mle_weights

    xs = [-1.0 + 2.0 * i / 4.0 for i in range(5)]
    ts = [1.0 - 2.0 * x + 0.5 * x * x for x in xs]
    Phi = design_matrix(xs, _poly(7))  # 5 data points, 8 basis functions

    result = mle_weights(Phi, ts)
    assert result is None, (
        "with fewer data points than basis functions the normal equations are "
        f"singular and the MLE is not unique; mle_weights must return None, got {result}")

    mean, cov = bayesian_posterior(Phi, ts, 1.0, 25.0)
    assert len(mean) == 8 and all(math.isfinite(w) for w in mean), (
        f"the Bayesian posterior mean must still be finite and well defined, got {mean}")
    assert len(cov) == 8 and all(math.isfinite(v) for row in cov for v in row), \
        "the Bayesian posterior covariance must be finite"
    for i in range(8):
        assert cov[i][i] > 0.0, \
            f"the posterior covariance must be positive definite, variance {i} = {cov[i][i]}"
        for j in range(8):
            assert _close(cov[i][j], cov[j][i], 1e-9), \
                "the posterior covariance must be symmetric"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("regression.py", "MLE and ridge recover a synthetic polynomial", check_mle_and_ridge),
    ("regression.py", "posterior mean equals the ridge solution", check_posterior_consistency),
    ("regression.py", "predictive variance grows away from the data", check_predictive_variance_grows),
    ("regression.py", "evidence recovers the true noise precision", check_evidence),
    ("regression.py", "limit case: more basis functions than points", check_limit_case),
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
    print(f"\n{BOLD}PRML Linear Regression From Scratch — progress check{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built linear regression from scratch.{RESET}")
        print(f"  {GREY}Run solutions/regression.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

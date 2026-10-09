"""
Progress checker for the PRML kernels and Gaussian processes templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own RBF/linear/polynomial kernel values, its own Gram matrix,
its own Gaussian elimination, its own log-determinant and its own log-evidence, so the
numeric comparisons are against an independent implementation, not a restatement of
yours. The accept criterion -- the GP posterior mean interpolates noise-free training
data, and the marginal-likelihood gradient matches finite differences -- is measured on
fixed synthetic data.
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

def _rbf_ref(length_scale, variance):
    """The reference RBF kernel: ``variance * exp(-d^2 / (2 l^2))``."""
    def kernel(x, y):
        d = x - y
        return variance * math.exp(-d * d / (2.0 * length_scale * length_scale))
    return kernel


def _linear_ref(variance=1.0, offset=0.0):
    return lambda x, y: variance * (x * y + offset)


def _poly_ref(degree, scale=1.0, offset=1.0, variance=1.0):
    return lambda x, y: variance * (scale * x * y + offset) ** degree


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


def _gram_ref(kernel, xs):
    """The checker's Gram matrix, built entry by entry."""
    n = len(xs)
    return [[kernel(xs[i], xs[j]) for j in range(n)] for i in range(n)]


def _obs_cov(xs, kernel, noise):
    """``K(X, X) + noise I``, the checker's way."""
    n = len(xs)
    return [[kernel(xs[i], xs[j]) + (noise if i == j else 0.0) for j in range(n)]
            for i in range(n)]


def _gp_log_evidence(xs, ys, kernel, noise):
    """The checker's log marginal likelihood of a zero-mean GP."""
    n = len(xs)
    C = _obs_cov(xs, kernel, noise)
    alpha = _solve(C, ys)
    return (-0.5 * sum(ys[i] * alpha[i] for i in range(n))
            - 0.5 * _log_det(C) - 0.5 * n * math.log(2.0 * math.pi))


def _gp_mean_ref(xs, ys, xs_test, kernel, noise):
    """The checker's posterior mean ``K_* (K + noise I)^{-1} y``."""
    n = len(xs)
    alpha = _solve(_obs_cov(xs, kernel, noise), ys)
    means = []
    for x in xs_test:
        means.append(sum(kernel(x, xs[i]) * alpha[i] for i in range(n)))
    return means


def _min_eig(A):
    """Smallest eigenvalue of a symmetric matrix, by Jacobi rotations."""
    n = len(A)
    a = [list(row) for row in A]
    for _ in range(200):
        p = q = 0
        off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > off:
                    off = abs(a[i][j])
                    p, q = i, j
        if off < 1e-14:
            break
        theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
        t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
        c = 1.0 / math.sqrt(t * t + 1.0)
        s = t * c
        for k in range(n):
            akp, akq = a[k][p], a[k][q]
            a[k][p] = c * akp - s * akq
            a[k][q] = s * akp + c * akq
        for k in range(n):
            apk, aqk = a[p][k], a[q][k]
            a[p][k] = c * apk - s * aqk
            a[q][k] = s * apk + c * aqk
    return min(a[i][i] for i in range(n))


def _close(a, b, tol):
    return abs(a - b) <= tol


def _symmetric(K):
    n = len(K)
    return all(_close(K[i][j], K[j][i], 1e-12) for i in range(n) for j in range(n))


# ---------------------------------------------------------------------------
# Step 1: kernels are symmetric, valid, and closed under sum and product
# ---------------------------------------------------------------------------

def check_kernels_and_constructions() -> None:
    from kernels import (gram_matrix, is_psd, linear_kernel, polynomial_kernel,
                         rbf_kernel)

    xs = [-1.5, -0.7, -0.1, 0.3, 0.9, 1.6]
    cases = [
        ("linear", linear_kernel(1.3, 0.2), _linear_ref(1.3, 0.2)),
        ("polynomial", polynomial_kernel(3, scale=0.7, offset=1.1, variance=0.9),
         _poly_ref(3, 0.7, 1.1, 0.9)),
        ("rbf", rbf_kernel(0.6, 2.0), _rbf_ref(0.6, 2.0)),
    ]

    for name, kernel, reference in cases:
        for x in xs:
            for y in xs:
                assert _close(kernel(x, y), reference(x, y), 1e-12), (
                    f"the {name} kernel value k({x}, {y}) must be "
                    f"{reference(x, y)!r}, got {kernel(x, y)!r}. Check the definition "
                    "(for the RBF the exponent uses the SQUARED distance).")
        K = gram_matrix(kernel, xs)
        ref_K = _gram_ref(reference, xs)
        assert _symmetric(K), f"the {name} Gram matrix must be symmetric"
        for i in range(len(xs)):
            for j in range(len(xs)):
                assert _close(K[i][j], ref_K[i][j], 1e-12), (
                    f"gram_matrix({name}) entry [{i}][{j}]: got {K[i][j]!r}, "
                    f"want {ref_K[i][j]!r}")
        assert is_psd(K), (
            f"the {name} Gram matrix must be positive semi-definite")

    k_lin = linear_kernel(1.3, 0.2)
    k_rbf = rbf_kernel(0.6, 2.0)
    K1 = gram_matrix(k_lin, xs)
    K2 = gram_matrix(k_rbf, xs)
    n = len(xs)

    k_sum = lambda x, y: k_lin(x, y) + k_rbf(x, y)  # noqa: E731
    k_prod = lambda x, y: k_lin(x, y) * k_rbf(x, y)  # noqa: E731
    K_sum = gram_matrix(k_sum, xs)
    K_prod = gram_matrix(k_prod, xs)
    for i in range(n):
        for j in range(n):
            assert _close(K_sum[i][j], K1[i][j] + K2[i][j], 1e-12), \
                "the Gram matrix of a sum of kernels must be the sum of Gram matrices"
            assert _close(K_prod[i][j], K1[i][j] * K2[i][j], 1e-12), \
                "the Gram matrix of a product of kernels must be the Schur product"
    assert is_psd(K_sum), "a sum of PSD kernels must have a PSD Gram matrix"
    assert is_psd(K_prod), "a product of PSD kernels must have a PSD Gram matrix"


# ---------------------------------------------------------------------------
# Step 2: GP regression on noise-free data interpolates the training points
# ---------------------------------------------------------------------------

def check_gp_interpolation() -> None:
    from kernels import cholesky, gram_matrix, gp_posterior, rbf_kernel

    xs = [-1.7, -1.0, -0.2, 0.6, 1.4, 2.1]
    ys = [math.sin(1.3 * x) + 0.3 * x for x in xs]
    length_scale, variance = 0.7, 1.5
    kernel = rbf_kernel(length_scale, variance)
    reference = _rbf_ref(length_scale, variance)
    n = len(xs)

    # Cholesky: lower triangular and reconstructs the matrix.
    K = gram_matrix(kernel, xs)
    L = cholesky(K)
    for i in range(n):
        for j in range(i + 1, n):
            assert _close(L[i][j], 0.0, 1e-14), (
                "cholesky must return the LOWER-triangular factor L with L L^T = K; "
                f"entry [{i}][{j}] = {L[i][j]!r} is above the diagonal. Do not return "
                "the upper factor U of K = U^T U without transposing.")
    for i in range(n):
        for j in range(n):
            got = sum(L[i][k] * L[j][k] for k in range(n))
            assert _close(got, K[i][j], 1e-9), (
                f"cholesky must satisfy L L^T = K: [{i}][{j}] got {got!r}, "
                f"want {K[i][j]!r}")

    # Noise-free: the posterior mean interpolates the training targets.
    mean, _ = gp_posterior(xs, ys, xs, kernel, 0.0)
    for i in range(n):
        assert _close(mean[i], ys[i], 1e-9), (
            "on noise-free data the GP posterior mean must reproduce the training "
            f"targets exactly: at x = {xs[i]} got {mean[i]!r}, want {ys[i]!r}")

    # Nonzero noise: the mean must equal the checker's independent conditioned mean,
    # which uses C = K + noise I. This is where a dropped noise term shows up.
    noise = 0.1
    mean_n, _ = gp_posterior(xs, ys, xs, kernel, noise)
    ref_n = _gp_mean_ref(xs, ys, xs, reference, noise)
    for i in range(n):
        assert _close(mean_n[i], ref_n[i], 1e-7), (
            f"with noise = {noise} the posterior mean is K_* (K + noise I)^-1 y; at "
            f"x = {xs[i]} got {mean_n[i]!r}, want {ref_n[i]!r}. The observation-noise "
            "term belongs on the diagonal of the training covariance.")


# ---------------------------------------------------------------------------
# Step 3: the posterior variance is small near the data and grows away from it
# ---------------------------------------------------------------------------

def check_posterior_variance() -> None:
    from kernels import gp_posterior, rbf_kernel

    kernel = rbf_kernel(0.6, 1.0)
    xs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    ys = [math.cos(1.5 * x) for x in xs]
    noise = 1e-8

    _, near = gp_posterior(xs, ys, xs, kernel, noise)
    assert max(near) < 1e-4, (
        "the posterior variance at a training input must collapse towards zero "
        f"(the observation noise {noise}): got {max(near):.3e}")

    outward = [1.2, 1.6, 2.1, 2.7, 3.4]
    _, far = gp_posterior(xs, ys, outward, kernel, noise)
    assert all(math.isfinite(v) for v in far), \
        f"the posterior variances must be finite, got {far}"
    for i in range(len(far) - 1):
        assert far[i] < far[i + 1], (
            "the posterior variance must grow as the test input moves away from the "
            f"training region: at x = {outward[i]} it is {far[i]:.6f}, at "
            f"x = {outward[i + 1]} it is {far[i + 1]:.6f}")
    assert far[0] > 10.0 * max(near), (
        "just outside the data the variance must already exceed the near-data "
        f"variance by a wide margin: {far[0]:.6f} vs {max(near):.3e}")
    assert far[-1] > 0.5, (
        "far from the data the variance must approach the prior variance k(x, x) = 1: "
        f"got only {far[-1]:.6f}")


# ---------------------------------------------------------------------------
# Step 4 (ACCEPT): the marginal-likelihood gradient matches finite differences
# ---------------------------------------------------------------------------

def check_marginal_likelihood_gradient() -> None:
    from kernels import (gp_log_marginal_likelihood, log_marginal_gradient_fd,
                         rbf_kernel)

    xs = [-2.0, -1.4, -0.6, 0.1, 0.8, 1.5, 2.3]
    ys = [math.sin(x) + 0.2 * x for x in xs]
    noise = 0.05
    h = 1e-5

    for params in ([0.6, 1.0], [1.4, 2.0]):
        length_scale, variance = params
        kernel = rbf_kernel(length_scale, variance)

        got = gp_log_marginal_likelihood(xs, ys, kernel, noise)
        want = _gp_log_evidence(xs, ys, _rbf_ref(length_scale, variance), noise)
        assert _close(got, want, 1e-7), (
            "gp_log_marginal_likelihood must be -1/2 y^T C^-1 y - 1/2 ln|C| "
            f"- n/2 ln(2 pi) for C = K + noise I: got {got:.8f}, want {want:.8f}")

        factory = lambda p: rbf_kernel(p[0], p[1])  # noqa: E731
        grad = log_marginal_gradient_fd(xs, ys, factory, params, noise, h)
        ref = []
        for i in range(len(params)):
            up = list(params)
            up[i] += h
            down = list(params)
            down[i] -= h
            f_up = _gp_log_evidence(xs, ys, _rbf_ref(up[0], up[1]), noise)
            f_down = _gp_log_evidence(xs, ys, _rbf_ref(down[0], down[1]), noise)
            ref.append((f_up - f_down) / (2.0 * h))
        for i, name in enumerate(("length_scale", "variance")):
            assert _close(grad[i], ref[i], 1e-4), (
                f"the finite-difference evidence gradient w.r.t. {name} at "
                f"params = {params} must be {ref[i]:.6f}; got {grad[i]:.6f}. "
                "Central differences use log p(params + h e_i) - log p(params - h e_i) "
                "over 2h.")


# ---------------------------------------------------------------------------
# Step 5 (LIMIT CASES): invalid kernels and numerically singular Gram matrices
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    from kernels import cholesky, gram_matrix, is_psd, rbf_kernel

    # (a) An invalid kernel: the "quadratic form" k(x, y) = -x y is negative
    # semi-definite, so its Gram matrix has a negative eigenvalue.
    invalid = lambda x, y: -x * y  # noqa: E731
    xs = [-1.0, 0.5, 2.0]
    K_bad = gram_matrix(invalid, xs)
    assert _min_eig(K_bad) < -1e-8, (
        "the check's own eigenvalue routine must see a negative eigenvalue in the "
        f"Gram matrix of k(x, y) = -x y; got {_min_eig(K_bad):.3e}")
    assert not is_psd(K_bad), (
        "is_psd must reject a Gram matrix with a negative eigenvalue; k(x, y) = -x y "
        f"is not a valid kernel (smallest eigenvalue {_min_eig(K_bad):.3e})")

    # (b) A Gram matrix that is PSD in theory but singular in practice: a duplicated
    # input makes two rows and columns identical.
    duplicated = [0.0, 0.0, 1.0, 2.0]
    K_dup = gram_matrix(rbf_kernel(1.0, 1.0), duplicated)
    assert is_psd(K_dup), (
        "a duplicated input gives an exactly rank-deficient Gram matrix: PSD with a "
        f"zero eigenvalue, so is_psd must accept it (smallest eigenvalue "
        f"{_min_eig(K_dup):.3e})")
    raised = False
    try:
        cholesky(K_dup)
    except ValueError:
        raised = True
    assert raised, (
        "with two identical rows the Gram matrix is singular and has no exact "
        "Cholesky factor: cholesky must refuse (raise ValueError) WITHOUT jitter. "
        "Silently returning a factor hides the rank deficiency.")

    jitter = 1e-8
    L = cholesky(K_dup, jitter)
    n = len(duplicated)
    for i in range(n):
        for j in range(n):
            got = sum(L[i][k] * L[j][k] for k in range(n))
            want = K_dup[i][j] + (jitter if i == j else 0.0)
            assert _close(got, want, 1e-9), (
                f"with jitter = {jitter} the factor must satisfy L L^T = K + jitter I: "
                f"[{i}][{j}] got {got!r}, want {want!r}. The jitter is added to the "
                "diagonal.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("kernels.py", "kernels are symmetric, valid, and closed under sum/product", check_kernels_and_constructions),
    ("kernels.py", "GP regression interpolates noise-free training data", check_gp_interpolation),
    ("kernels.py", "posterior variance grows away from the data", check_posterior_variance),
    ("kernels.py", "marginal-likelihood gradient matches finite differences", check_marginal_likelihood_gradient),
    ("kernels.py", "limit cases: invalid kernel and singular Gram matrix", check_limit_cases),
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
    print(f"\n{BOLD}PRML Kernels and Gaussian Processes From Scratch — progress check{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built kernels and GPs from scratch.{RESET}")
        print(f"  {GREY}Run solutions/kernels.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

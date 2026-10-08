"""
Progress checker for the PRML latent-continuous-variables templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write.  Nothing here imports solutions/.  It tests YOUR code.

The checker carries its own statistics, its own Jacobi eigen-solver and its own PPCA
reference, so the numeric comparisons are against an independent implementation.  The
accept criterion -- PPCA fitted by EM converges to the closed-form maximum-likelihood
solution -- is measured on fixed synthetic data.
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

def _mean(X):
    n, d = len(X), len(X[0])
    return [sum(X[i][j] for i in range(n)) / n for j in range(d)]


def _center(X):
    mu = _mean(X)
    return [[X[i][j] - mu[j] for j in range(len(X[i]))] for i in range(len(X))]


def _cov(X):
    """The checker's maximum-likelihood covariance ``Xc^T Xc / N``."""
    n, d = len(X), len(X[0])
    xc = _center(X)
    return [[sum(xc[k][i] * xc[k][j] for k in range(n)) / n for j in range(d)]
            for i in range(d)]


def _jacobi(A, sweeps=100):
    n = len(A)
    a = [row[:] for row in A]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(sweeps):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        if off < 1e-14:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                tau = s / (1.0 + c)
                h = t * a[p][q]
                a[p][p] -= h
                a[q][q] += h
                a[p][q] = a[q][p] = 0.0
                for i in range(p):
                    aip, aiq = a[i][p], a[i][q]
                    a[i][p] = aip - s * (aiq + tau * aip)
                    a[i][q] = aiq + s * (aip - tau * aiq)
                for i in range(p + 1, q):
                    aip, aiq = a[p][i], a[i][q]
                    a[p][i] = aip - s * (aiq + tau * aip)
                    a[i][q] = aiq + s * (aip - tau * aiq)
                for i in range(q + 1, n):
                    aip, aiq = a[p][i], a[q][i]
                    a[p][i] = aip - s * (aiq + tau * aip)
                    a[q][i] = aiq + s * (aip - tau * aiq)
                for i in range(n):
                    vip, viq = v[i][p], v[i][q]
                    v[i][p] = vip - s * (viq + tau * vip)
                    v[i][q] = viq + s * (vip - tau * viq)
    vals = [a[i][i] for i in range(n)]
    vecs = [[v[i][j] for i in range(n)] for j in range(n)]
    return vals, vecs


def _eig_sorted(A):
    vals, vecs = _jacobi(A)
    order = sorted(range(len(vals)), key=lambda i: -vals[i])
    return [vals[i] for i in order], [vecs[i] for i in order]


def _projector(W):
    d, k = len(W), len(W[0])
    WTW = [[sum(W[i][a] * W[i][b] for i in range(d)) for b in range(k)] for a in range(k)]
    # Inverse of a small symmetric positive definite matrix.
    m = [list(WTW[i]) + [1.0 if i == j else 0.0 for j in range(k)] for i in range(k)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        for j in range(2 * k):
            m[col][j] /= scale
        for r in range(k):
            if r != col and m[r][col]:
                factor = m[r][col]
                for j in range(2 * k):
                    m[r][j] -= factor * m[col][j]
    inv = [row[k:] for row in m]
    return [[sum(W[i][a] * inv[a][b] * W[j][b] for a in range(k) for b in range(k))
             for j in range(d)] for i in range(d)]


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _norm(v):
    return math.sqrt(sum(a * a for a in v))


def _frob(A, B):
    return math.sqrt(sum((A[i][j] - B[i][j]) ** 2 for i in range(len(A)) for j in range(len(A[0]))))


def _close(a, b, tol):
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# Step 1: the eigendecomposition and SVD routes agree; components are orthonormal
# ---------------------------------------------------------------------------

def check_pca_routes_agree() -> None:
    from latent import pca_eig, pca_svd

    rng = random.Random(11)
    X = [[rng.gauss(0.0, 1.0) for _ in range(4)] for _ in range(7)]

    c_eig, v_eig, p_eig, r_eig = pca_eig(X, 3)
    c_svd, v_svd, p_svd, r_svd = pca_svd(X, 3)

    assert len(c_eig) == 3 and len(c_eig[0]) == 4, \
        f"pca_eig must return 3 components of length 4, got {len(c_eig)} x {len(c_eig[0])}"
    assert len(p_eig) == 7 and len(p_eig[0]) == 3, \
        f"the projection must be N x k = 7 x 3, got {len(p_eig)} x {len(p_eig[0])}"
    assert len(r_eig) == 7 and len(r_eig[0]) == 4, \
        f"the reconstruction must be N x D = 7 x 4, got {len(r_eig)} x {len(r_eig[0])}"

    for i in range(3):
        assert _close(_norm(c_eig[i]), 1.0, 1e-8), \
            f"principal component {i} must be a unit vector, got norm {_norm(c_eig[i])}"
        for j in range(i + 1, 3):
            assert abs(_dot(c_eig[i], c_eig[j])) < 1e-8, (
                "principal components must be mutually orthogonal: "
                f"dot(c[{i}], c[{j}]) = {_dot(c_eig[i], c_eig[j])}")

    for i in range(3):
        assert _close(v_eig[i], v_svd[i], 1e-7), (
            "the eigendecomposition and SVD routes must produce the same eigenvalues: "
            f"eig {v_eig[i]} vs svd {v_svd[i]}. Check the 1/N scaling on the SVD route.")
        assert _close(_norm(c_svd[i]), 1.0, 1e-8), \
            f"the SVD components must be unit vectors, component {i} norm {_norm(c_svd[i])}"

    assert _frob(r_eig, r_svd) < 1e-7, (
        "the reconstruction from the eigendecomposition and SVD routes must agree; "
        f"Frobenius difference {_frob(r_eig, r_svd):.3e}")


# ---------------------------------------------------------------------------
# Step 2 (ACCEPT): reconstruction error equals the sum of the discarded eigenvalues
# ---------------------------------------------------------------------------

def check_reconstruction_error() -> None:
    from latent import pca_eig

    rng = random.Random(4)
    X = [[rng.gauss(0.0, 1.0) for _ in range(5)] for _ in range(9)]
    n, d, k = len(X), len(X[0]), 2

    components, eigenvalues, projection, reconstruction = pca_eig(X, k)
    assert len(projection) == n and len(projection[0]) == k, \
        f"the projection must be {n} x {k}, got {len(projection)} x {len(projection[0])}"

    # PCA scores are centred: each projection column has mean zero.
    for c in range(k):
        col_mean = sum(projection[i][c] for i in range(n)) / n
        assert abs(col_mean) < 1e-8, (
            "the scores must be mean-centred: if pca_eig forgets to mean-centre the "
            f"data, the projection column {c} has mean {col_mean:.3e} instead of 0")

    # Mean squared reconstruction error, using the learner's own reconstruction.
    err = sum((X[i][j] - reconstruction[i][j]) ** 2
              for i in range(n) for j in range(d)) / n

    full = _eig_sorted(_cov(X))[0]
    discarded = sum(full[k:])
    assert _close(err, discarded, 1e-9), (
        "the mean squared reconstruction error must equal the sum of the discarded "
        f"eigenvalues: error {err:.12f}, discarded {discarded:.12f}. With the 1/N "
        "covariance the identity is exact; check the centring and the number of "
        "components used.")
    assert discarded > 0.0, "the test data must leave a nonzero discarded spectrum"


# ---------------------------------------------------------------------------
# Step 3: principal directions are eigenvectors; explained variance is monotone
# ---------------------------------------------------------------------------

def check_eigen_directions() -> None:
    from latent import pca_eig

    rng = random.Random(23)
    X = [[rng.gauss(0.0, 1.0) for _ in range(6)] for _ in range(11)]
    d, k = len(X[0]), 4
    C = _cov(X)

    components, eigenvalues, _, _ = pca_eig(X, k)
    for c in range(k):
        v = components[c]
        Cv = [sum(C[i][j] * v[j] for j in range(d)) for i in range(d)]
        rayleigh = _dot(v, Cv)
        residual = _norm([Cv[i] - rayleigh * v[i] for i in range(d)])
        assert residual < 1e-8, (
            f"component {c} must be an eigenvector of the covariance (residual {residual:.3e}); "
            "it is not, so the eigen-solver or the centring is wrong")
        assert _close(rayleigh, eigenvalues[c], 1e-7), (
            f"eigenvalue {c} must equal the Rayleigh quotient v^T C v: "
            f"got {eigenvalues[c]}, want {rayleigh}")

    for c in range(k - 1):
        assert eigenvalues[c] >= eigenvalues[c + 1] - 1e-12, (
            "the explained variance must be non-increasing: "
            f"lambda[{c}] = {eigenvalues[c]} < lambda[{c + 1}] = {eigenvalues[c + 1]}")


# ---------------------------------------------------------------------------
# Step 4 (ACCEPT): PPCA by EM converges to the closed-form solution
# ---------------------------------------------------------------------------

def check_ppca_converges() -> None:
    from latent import ppca_closed_form, ppca_em

    rng = random.Random(7)
    n, d, k = 90, 5, 2
    Z = [[rng.gauss(0.0, 1.0) for _ in range(k)] for _ in range(n)]
    A = [[rng.gauss(0.0, 1.0) for _ in range(k)] for _ in range(d)]
    X = [[sum(Z[i][a] * A[j][a] for a in range(k)) + rng.gauss(0.0, 0.1)
          for j in range(d)] for i in range(n)]

    full, vecs = _eig_sorted(_cov(X))
    ref_sigma2 = sum(full[k:]) / (d - k)
    ref_projector = [[sum(vecs[c][i] * vecs[c][j] for c in range(k))
                      for j in range(d)] for i in range(d)]

    W, sigma2 = ppca_closed_form(X, k)
    assert len(W) == d and len(W[0]) == k, \
        f"W must be D x k = {d} x {k}, got {len(W)} x {len(W[0])}"
    assert _close(sigma2, ref_sigma2, 1e-8), (
        "ppca_closed_form must set sigma^2 to the average of the discarded eigenvalues: "
        f"got {sigma2:.8f}, want {ref_sigma2:.8f}. The noise term is a floor, not an "
        "eigenvalue of the retained subspace.")
    assert _frob(_projector(W), ref_projector) < 1e-6, (
        "the closed-form W must span the top-k principal subspace; "
        f"projector difference {_frob(_projector(W), ref_projector):.3e}")

    W_em, sigma2_em, lls = ppca_em(X, k, iterations=1500)
    assert len(lls) >= 2, "ppca_em must report a log-likelihood trajectory"
    for t in range(len(lls) - 1):
        assert lls[t + 1] >= lls[t] - 1e-6, (
            f"EM must not decrease the log-likelihood: step {t} {lls[t]:.6f} -> "
            f"{lls[t + 1]:.6f}")
    assert lls[-1] > lls[0] + 1e-6, "EM must improve the log-likelihood from the initial point"

    assert _close(sigma2_em, ref_sigma2, 1e-4), (
        "PPCA by EM must converge to the closed-form noise variance: "
        f"EM sigma^2 {sigma2_em:.8f} vs closed form {ref_sigma2:.8f}. If sigma^2 is "
        "never updated it stays at its initialization and cannot match.")
    assert _frob(_projector(W_em), ref_projector) < 1e-2, (
        "PPCA by EM must converge to the top-k principal subspace (up to rotation): "
        f"projector difference {_frob(_projector(W_em), ref_projector):.3e}")


# ---------------------------------------------------------------------------
# Step 5: kernel PCA — feature-space centring and the score spectrum
# ---------------------------------------------------------------------------

def _rbf_kernel(xs, gamma):
    n = len(xs)
    return [[math.exp(-gamma * sum((xs[i][t] - xs[j][t]) ** 2
                                   for t in range(len(xs[i]))))
             for j in range(n)] for i in range(n)]


def check_kernel_pca() -> None:
    from latent import kernel_pca

    # Four 1-D points: 0, 1 in one cluster and 3, 6 spread out. A linear method
    # sees a single dimension; kernel PCA must extract more from the RBF kernel.
    xs = [[0.0], [1.0], [3.0], [6.0]]
    n = len(xs)
    k = 2
    K = _rbf_kernel(xs, 0.5)

    vals, proj = kernel_pca(K, k)

    assert len(vals) == k, f"kernel_pca must return k={k} eigenvalues, got {len(vals)}"
    assert len(proj) == n and len(proj[0]) == k, (
        f"the projection must be N x k = {n} x {k}, got {len(proj)} x {len(proj[0])}")
    for j in range(k):
        assert vals[j] >= -1e-9, f"kernel eigenvalues must be non-negative, got {vals[j]}"
        if j + 1 < k:
            assert vals[j] >= vals[j + 1] - 1e-9, (
                f"kernel eigenvalues must be in descending order, got {vals}")

    # The checker's own centring of the same kernel and its own eigen-solver.
    # The returned spectrum must match the centred kernel, not the raw K.
    row = [sum(K[i]) / n for i in range(n)]
    total = sum(row) / n
    Kc = [[K[i][j] - row[i] - row[j] + total for j in range(n)] for i in range(n)]
    ref_vals, _ = _eig_sorted(Kc)
    for j in range(k):
        assert _close(vals[j], ref_vals[j], 1e-9), (
            "kernel PCA must eigendecompose the feature-space-centred kernel, not the "
            f"raw K: eigenvalue {j} = {vals[j]:.6f} but the centred kernel gives "
            f"{ref_vals[j]:.6f}. If you forgot to centre K, the top eigenvalue is the "
            "uninformative constant direction.")

    # The scores are sqrt(lambda_j) * v_j with v_j orthonormal, so the N x k score
    # matrix must have Gram matrix diag(lambda).
    for a in range(k):
        for b in range(a, k):
            ip = sum(proj[i][a] * proj[i][b] for i in range(n))
            want = vals[a] if a == b else 0.0
            assert _close(ip, want, 1e-9), (
                "the score columns must be sqrt(lambda_j) v_j with orthonormal v_j, so "
                f"col({a}).col({b}) = {ip:.6f}, expected {want:.6f}")

    # The Gram test alone is satisfied by *any* orthonormal basis of the right
    # norms, so pin the actual eigenvectors: each score column p must satisfy
    # Kc p = lambda p on the checker's own centred kernel.
    for a in range(k):
        p = [proj[i][a] for i in range(n)]
        Kp = [sum(Kc[i][j] * p[j] for j in range(n)) for i in range(n)]
        resid = math.sqrt(sum((Kp[i] - vals[a] * p[i]) ** 2 for i in range(n)))
        assert resid < 1e-8, (
            "the score columns must be eigenvectors of the centred kernel: "
            f"||Kc p - lambda p|| = {resid:.3e} for component {a}. The Gram test alone "
            "does not catch a transposed eigenvector indexing; the columns must be "
            "sqrt(lambda_j) v_j for the centred kernel's own eigenvectors.")


# ---------------------------------------------------------------------------
# Step 6 (LIMIT CASE): D > N, PCA via the N x N Gram matrix
# ---------------------------------------------------------------------------

def check_gram_limit() -> None:
    from latent import pca_eig, pca_gram

    rng = random.Random(31)
    n, d = 5, 8  # more dimensions than samples
    X = [[rng.gauss(0.0, 1.0) for _ in range(d)] for _ in range(n)]
    k = n - 1  # the rank of the centred data is at most N - 1

    _, g_vals, _, g_rec = pca_gram(X, k)
    _, e_vals, _, e_rec = pca_eig(X, k)

    assert len(g_vals) == k, f"pca_gram must return {k} eigenvalues, got {len(g_vals)}"
    for i in range(k):
        assert g_vals[i] > 1e-9, (
            "the Gram route must return the nonzero eigenvalues of Xc Xc^T; "
            f"eigenvalue {i} = {g_vals[i]:.3e} is (numerically) zero")
        assert _close(g_vals[i], n * e_vals[i], 1e-7), (
            "the Gram eigenvalues must equal N times the covariance eigenvalues: "
            f"Gram {g_vals[i]:.8f} vs N * cov {n * e_vals[i]:.8f}. Using the D x D "
            "Xc^T Xc matrix instead of the N x N Gram matrix loses the N factor.")
    assert _frob(g_rec, e_rec) < 1e-7, (
        "the Gram route must reconstruct the data exactly like the covariance route; "
        f"difference {_frob(g_rec, e_rec):.3e}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("latent.py", "PCA by eigendecomposition and SVD agree", check_pca_routes_agree),
    ("latent.py", "reconstruction error equals discarded eigenvalues", check_reconstruction_error),
    ("latent.py", "principal directions are eigenvectors; variance monotone", check_eigen_directions),
    ("latent.py", "PPCA by EM converges to the closed form", check_ppca_converges),
    ("latent.py", "kernel PCA centres the kernel and returns the score spectrum", check_kernel_pca),
    ("latent.py", "limit case: D > N via the Gram matrix", check_gram_limit),
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
    print(f"\n{BOLD}PRML Latent Continuous Variables From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — latent variable models built from scratch.{RESET}")
        print(f"  {GREY}Run solutions/latent.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

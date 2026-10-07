"""
Progress checker for the analytic-geometry templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

All reference values are computed here, in closed form or by an independent formula, so
the checker never asks your own code what the right answer is.
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
# Small independent helpers (this file's own arithmetic, not the learner's)
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _subtract(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _maxabs(A):
    return max(abs(v) for row in A for v in row)


def _det2(M):
    return M[0][0] * M[1][1] - M[0][1] * M[1][0]


def _det3(M):
    return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
            - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))


def _orthogonality_error(Q):
    k = len(Q)
    worst = 0.0
    for a in range(k):
        for b in range(k):
            worst = max(worst, abs(_dot(Q[a], Q[b]) - (1.0 if a == b else 0.0)))
    return worst


def _random_vectors(rng, m, k, spread=4.0):
    return [[rng.uniform(-spread, spread) for _ in range(m)] for _ in range(k)]


# ---------------------------------------------------------------------------
# Step 1: what counts as an inner product (limit case: non-SPD is rejected)
# ---------------------------------------------------------------------------

def check_spd_validation() -> None:
    from geometry import NotPositiveDefinite, inner, is_spd

    assert is_spd([[2.0, 1.0], [1.0, 2.0]]), "this matrix is symmetric positive definite"
    assert is_spd([[3.0, 0.0], [0.0, 0.5]]), "a positive diagonal is positive definite"
    assert not is_spd([[1.0, 0.0], [0.0, -1.0]]), "an indefinite matrix has no Cholesky factor"
    assert not is_spd([[1.0, 1.0], [1.0, 1.0]]), "a singular matrix is not positive definite"
    assert not is_spd([[1.0, 2.0], [3.0, 4.0]]), "a non-symmetric matrix defines no inner product"
    assert not is_spd([[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]), "a non-square matrix defines no inner product"

    for A in ([[1.0, 0.0], [0.0, -1.0]], [[1.0, 1.0], [1.0, 1.0]], [[1.0, 2.0], [3.0, 4.0]]):
        try:
            inner(A, [1.0, 0.0], [1.0, 0.0])
            raise AssertionError(
                f"inner() accepted {A} as an inner product; a non-SPD matrix must raise "
                "NotPositiveDefinite (positive definiteness is what makes a length non-negative)")
        except NotPositiveDefinite:
            pass


# ---------------------------------------------------------------------------
# Step 2: the induced inner product, norm and angle
# ---------------------------------------------------------------------------

def check_inner_norm_angle() -> None:
    from geometry import angle, inner, norm

    A = [[2.0, 1.0], [1.0, 2.0]]
    u, v, w = [1.0, 1.0], [1.0, 0.0], [0.0, 1.0]

    assert abs(inner(A, u, v) - inner(A, v, u)) < 1e-12, "an inner product is symmetric"
    assert abs(inner(A, [1.0, 1.0], [1.0, 0.0])
               - (inner(A, [1.0, 0.0], [1.0, 0.0]) + inner(A, [0.0, 1.0], [1.0, 0.0]))) < 1e-12, \
        "an inner product is linear in its first argument"
    assert inner(A, [1.0, 0.0], [1.0, 0.0]) == 2.0, "uᵀ A u for u=e₁ and A=[[2,1],[1,2]] is the (0,0) entry"
    assert abs(norm(A, [0.0, 0.0])) < 1e-15 and norm(A, [1.0, 0.0]) > 0.0, "a norm is 0 only at 0"

    # With A=[[2,1],[1,2]], the angle between e₁ and e₂ is arccos(1/2) = 60°.
    deg = math.degrees(angle(A, [1.0, 0.0], [0.0, 1.0]))
    assert abs(deg - 60.0) < 1e-9, (
        f"angle_A(e₁,e₂) = {deg}°, expected 60°: the angle must use the inner product, not "
        "the ordinary dot product (which would give 90°)")
    assert abs(angle(A, [1.0, 1.0], [2.0, 2.0])) < 1e-9, "a vector makes angle 0 with itself"

    # Cauchy-Schwarz, on random pairs.
    rng = random.Random(3)
    for _ in range(200):
        a = [rng.uniform(-3, 3) for _ in range(2)]
        b = [rng.uniform(-3, 3) for _ in range(2)]
        assert abs(inner(A, a, b)) <= norm(A, a) * norm(A, b) + 1e-9, "Cauchy-Schwarz fails"


# ---------------------------------------------------------------------------
# Step 3: the projection matrix is idempotent (accept criterion)
# ---------------------------------------------------------------------------

def check_projection_idempotent() -> None:
    from geometry import projection_matrix

    B = [[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]]
    P = projection_matrix(B)
    assert len(P) == 3 and len(P[0]) == 3, "the projection matrix of vectors in R³ must be 3×3"
    P2 = _matmul(P, P)
    assert _maxabs(_subtract(P2, P)) < 1e-10, (
        "P² ≠ P: projecting twice must change nothing (a projection is idempotent)")


# ---------------------------------------------------------------------------
# Step 4: the projection is symmetric and its residual is orthogonal (accept criterion)
# ---------------------------------------------------------------------------

def check_projection_symmetric_residual() -> None:
    from geometry import project, projection_matrix

    B = [[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]]
    P = projection_matrix(B)
    assert _maxabs(_subtract(P, _transpose(P))) < 1e-10, (
        "P is not symmetric: the orthogonal (as opposed to oblique) projection is symmetric")

    rng = random.Random(5)
    for _ in range(50):
        x = [rng.uniform(-5, 5) for _ in range(3)]
        p = project(B, x)
        r = [x[i] - p[i] for i in range(3)]
        assert all(abs(_dot(b, r)) < 1e-8 for b in B), (
            f"Bᵀ(x − Px) = {[_dot(b, r) for b in B]}, expected 0: the residual must be "
            "orthogonal to the subspace")
        assert max(abs(v) for v in project(B, r)) < 1e-8, (
            "P·(x − Px) must be 0: the residual is already orthogonal to the subspace")


# ---------------------------------------------------------------------------
# Step 5: projection onto an affine subspace
# ---------------------------------------------------------------------------

def check_affine_projection() -> None:
    from geometry import affine_project, project

    B = [[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]]
    x0 = [1.0, 0.0, 0.0]          # off the plane: b₀×b₁ = (1,−1,−1), and x0·n = 1 ≠ 0
    x = [-1.0, 3.0, 2.0]
    p = affine_project(B, x0, x)

    # p − x0 must lie in span(B): it is unchanged by the projection onto span(B).
    d = [p[i] - x0[i] for i in range(3)]
    assert all(abs(project(B, d)[i] - d[i]) < 1e-8 for i in range(3)), (
        "p − x0 is not in span(B): the offset was ignored or the wrong direction was projected")
    # x − p must be orthogonal to span(B).
    r = [x[i] - p[i] for i in range(3)]
    assert all(abs(_dot(b, r)) < 1e-8 for b in B), (
        "x − p is not orthogonal to span(B): an affine projection is orthogonal to the subspace")


# ---------------------------------------------------------------------------
# Step 6: Gram-Schmidt gives an orthonormal basis (accept criterion)
# ---------------------------------------------------------------------------

def check_gram_schmidt_orthonormal() -> None:
    from geometry import gram_schmidt

    rng = random.Random(7)
    for _ in range(40):
        k, m = rng.randint(1, 4), rng.randint(4, 6)
        V = _random_vectors(rng, m, k)
        for modified in (False, True):
            Q = gram_schmidt(V, modified=modified)
            assert len(Q) == k, (
                f"Gram-Schmidt returned {len(Q)} vectors for {k} independent inputs")
            err = _orthogonality_error(Q)
            assert err < 1e-10, (
                f"max|QᵀQ − I| = {err:.2e} (modified={modified}): the output is not orthonormal")


# ---------------------------------------------------------------------------
# Step 7: Gram-Schmidt preserves the span
# ---------------------------------------------------------------------------

def check_gram_schmidt_span() -> None:
    from geometry import gram_schmidt

    rng = random.Random(9)
    for _ in range(40):
        k, m = rng.randint(1, 4), rng.randint(4, 6)
        V = _random_vectors(rng, m, k)
        Q = gram_schmidt(V)
        for v in V:
            coeffs = [_dot(q, v) for q in Q]
            recon = [sum(coeffs[t] * Q[t][i] for t in range(len(Q))) for i in range(m)]
            assert max(abs(recon[i] - v[i]) for i in range(m)) < 1e-9, (
                "an input vector is not in span(Q): Gram-Schmidt changed the subspace")


# ---------------------------------------------------------------------------
# Step 8: 2-D rotation matrices preserve norms and have determinant +1
# ---------------------------------------------------------------------------

def check_rotation_2d() -> None:
    from geometry import rotation_2d

    for theta in (0.0, 0.3, math.pi / 2, 2.7, -1.1, 6.0):
        R = rotation_2d(theta)
        assert _maxabs(_subtract(_matmul(R, _transpose(R)), [[1.0, 0.0], [0.0, 1.0]])) < 1e-12, \
            "R Rᵀ ≠ I: a rotation is orthogonal"
        assert abs(_det2(R) - 1.0) < 1e-12, (
            f"det R = {_det2(R)}, expected +1: a rotation does not reflect")
        v = [1.7, -0.4]
        Rv = _matvec(R, v)
        assert abs(math.hypot(*Rv) - math.hypot(*v)) < 1e-12, "a rotation preserves lengths"

    # R(π/2) sends e₁ to e₂.
    R = rotation_2d(math.pi / 2)
    assert abs(R[0][0]) < 1e-12 and abs(R[1][0] - 1.0) < 1e-12, "R(π/2)·e₁ should be e₂"
    # R(a) R(b) = R(a + b).
    for a, b in ((0.4, 1.3), (-2.0, 0.7)):
        AB = _matmul(rotation_2d(a), rotation_2d(b))
        AB2 = rotation_2d(a + b)
        assert _maxabs(_subtract(AB, AB2)) < 1e-12, "rotations compose by adding angles"


# ---------------------------------------------------------------------------
# Step 9: 3-D rotation matrices (Rodrigues) are proper rotations
# ---------------------------------------------------------------------------

def check_rotation_3d() -> None:
    from geometry import rotation_3d

    for axis, theta in (([1.0, 2.0, 3.0], 1.1), ([0.0, 0.0, 1.0], 0.9),
                        ([1.0, 0.0, 0.0], -2.3), ([2.0, -1.0, 0.5], 3.0)):
        R = rotation_3d(axis, theta)
        n = math.sqrt(_dot(axis, axis))
        k = [a / n for a in axis]
        assert _maxabs(_subtract(_matmul(R, _transpose(R)),
                                 [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])) < 1e-12, \
            "R Rᵀ ≠ I: a 3-D rotation is orthogonal"
        assert abs(_det3(R) - 1.0) < 1e-12, (
            f"det R = {_det3(R)}, expected +1: it must be a rotation, not a reflection")
        v = [1.0, -2.0, 0.5]
        Rv = _matvec(R, v)
        assert abs(math.sqrt(_dot(Rv, Rv)) - math.sqrt(_dot(v, v))) < 1e-12, \
            "a rotation preserves lengths"
        assert max(abs(_matvec(R, k)[i] - k[i]) for i in range(3)) < 1e-12, \
            "the axis must be fixed: R·axis = axis"

    # About z, the xy block must match the 2-D rotation.
    theta = 0.7
    R = rotation_3d([0.0, 0.0, 5.0], theta)      # non-unit axis: it must be normalised
    c, s = math.cos(theta), math.sin(theta)
    assert abs(R[0][0] - c) < 1e-12 and abs(R[0][1] + s) < 1e-12, \
        "a z-axis rotation must rotate the xy-plane like the 2-D rotation"
    assert max(abs(R[i][2] - (1.0 if i == 2 else 0.0)) for i in range(3)) < 1e-12, \
        "a z-axis rotation must leave z unchanged"

    try:
        rotation_3d([0.0, 0.0, 0.0], 1.0)
        raise AssertionError("a zero axis was accepted; rotation about it is undefined")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Step 10: classical vs modified Gram-Schmidt on nearly dependent vectors (limit case)
# ---------------------------------------------------------------------------

def check_gram_schmidt_conditioning() -> None:
    from geometry import gram_schmidt

    # The Läuchli matrix: three columns almost equal, condition ~ 1/eps.
    eps = 1e-8
    lauchli = [[1.0, 1.0, 1.0], [eps, 0.0, 0.0], [0.0, eps, 0.0], [0.0, 0.0, eps]]
    cols = [[lauchli[i][j] for i in range(4)] for j in range(3)]

    classical = gram_schmidt(cols, modified=False)
    modified = gram_schmidt(cols, modified=True)
    c_err = _orthogonality_error(classical)
    m_err = _orthogonality_error(modified)

    assert c_err > 1e-3, (
        f"classical Gram-Schmidt lost orthogonality as expected (max|QᵀQ−I| = {c_err:.2e}), "
        "but the loss is below 1e-3: is this really classical?")
    assert m_err < 1e-6, (
        f"modified Gram-Schmidt should keep orthogonality (got max|QᵀQ−I| = {m_err:.2e}); "
        "using the original vector in each inner product loses it")
    assert c_err > 1e4 * m_err, (
        f"the whole point is the gap: classical {c_err:.2e} vs modified {m_err:.2e}. "
        "The modified version must use the partially reduced vector.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("geometry.py", "what counts as an inner product (SPD)", check_spd_validation),
    ("geometry.py", "inner product, induced norm and angle", check_inner_norm_angle),
    ("geometry.py", "projection matrix is idempotent", check_projection_idempotent),
    ("geometry.py", "projection symmetric, residual orthogonal", check_projection_symmetric_residual),
    ("geometry.py", "projection onto an affine subspace", check_affine_projection),
    ("geometry.py", "Gram-Schmidt is orthonormal", check_gram_schmidt_orthonormal),
    ("geometry.py", "Gram-Schmidt preserves the span", check_gram_schmidt_span),
    ("geometry.py", "2-D rotations: orthogonal, det +1, lengths kept", check_rotation_2d),
    ("geometry.py", "3-D rotations (Rodrigues): proper rotations", check_rotation_3d),
    ("geometry.py", "classical vs modified Gram-Schmidt (conditioning)", check_gram_schmidt_conditioning),
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
    print(f"\n{BOLD}Analytic Geometry From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built analytic geometry from scratch.{RESET}")
        print(f"  {GREY}Run solutions/geometry.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

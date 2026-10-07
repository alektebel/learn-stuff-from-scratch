"""Convex sets and convex functions from scratch: two numerical tests (Jensen
on random points, positive-semidefiniteness of the Hessian) and the operations
that preserve convexity.

Implements chapters 2 and 3 of Boyd & Vandenberghe, *Convex Optimization*:
convex sets, convex functions and the composition rules that keep a function
convex. The argument is restated here, never copied.

Two tests with different jobs. Jensen's inequality is the definition, and a
positive gap (f at a convex combination above the convex combination of the
values) is a witness of non-convexity *or* concavity; it is global but random.
The Hessian is local and exact for smooth functions, and it is the certificate
at the point the chords cannot nail down. A function is called convex only when
both agree.

The node's limit case is a function that is quasiconvex but not convex
(``sqrt(abs(x))``): its sublevel sets are intervals, so the naive grid test of
the sublevel sets is fooled, while Jensen and the Hessian are not.

    python3 convexity.py      # prints the measurements this file promises
"""

import math
import random

# The convex-combination weights swept for Jensen's inequality.
LAMBDAS = [i / 10.0 for i in range(1, 10)]

# name -> (f, box). ``box`` is [(lo, hi), ...], one interval per coordinate: the
# region the tests sample. Restricted to x > 0 for the geometric mean, which is
# only defined there.
CATALOGUE = {
    "x^2": (lambda x: x[0] ** 2, [(-2.0, 2.0)]),
    "abs(x)": (lambda x: abs(x[0]), [(-2.0, 2.0)]),
    "x^4": (lambda x: x[0] ** 4, [(-2.0, 2.0)]),
    "exp(x)": (lambda x: math.exp(x[0]), [(-2.0, 2.0)]),
    "log-sum-exp": (lambda x: math.log(math.exp(x[0]) + math.exp(x[1])),
                    [(-2.0, 2.0), (-2.0, 2.0)]),
    "geometric-mean": (lambda x: math.sqrt(x[0] * x[1]), [(0.5, 3.0), (0.5, 3.0)]),
    "-x^2": (lambda x: -(x[0] ** 2), [(-2.0, 2.0)]),
    "x*y": (lambda x: x[0] * x[1], [(-2.0, 2.0), (-2.0, 2.0)]),
    "sqrt(abs(x))": (lambda x: math.sqrt(abs(x[0])), [(-2.0, 2.0)]),
}

# The truth the tests have to reproduce. ``geometric-mean`` is False (it is
# concave) and ``sqrt(abs(x))`` is False (quasiconvex, not convex).
EXPECTED_CONVEX = {
    "x^2": True, "abs(x)": True, "x^4": True, "exp(x)": True,
    "log-sum-exp": True, "geometric-mean": False, "-x^2": False,
    "x*y": False, "sqrt(abs(x))": False,
}


def _sample(box, rng):
    """A uniform point in ``box``."""
    return [rng.uniform(lo, hi) for lo, hi in box]


def _box_center(box):
    return [(lo + hi) / 2.0 for lo, hi in box]


# ---------------------------------------------------------------------------
# The two tests
# ---------------------------------------------------------------------------

def hessian(f, x, h=1e-4):
    """The Hessian of ``f`` at ``x`` by central differences.

    DESIGN DECISION: central differences (not forward) and a step h = 1e-4.
    Forward differences with the same h are exact for quadratics too, but they
    carry an O(h) bias for everything else; central differences are O(h^2) and
    cost one extra evaluation per entry. Missing a semidefinite matrix (zero
    curvature, as at x = 0 for x^4) is the failure that matters, and the central
    form keeps the noise well under the PSD tolerance.
    """
    n = len(x)
    fx = f(list(x))
    H = [[0.0] * n for _ in range(n)]
    for i in range(n):
        hi = list(x)
        hi[i] += h
        lo = list(x)
        lo[i] -= h
        H[i][i] = (f(hi) - 2.0 * fx + f(lo)) / (h * h)
    for i in range(n):
        for j in range(i + 1, n):
            pp = list(x); pp[i] += h; pp[j] += h
            pm = list(x); pm[i] += h; pm[j] -= h
            mp = list(x); mp[i] -= h; mp[j] += h
            mm = list(x); mm[i] -= h; mm[j] -= h
            value = (f(pp) - f(pm) - f(mp) + f(mm)) / (4.0 * h * h)
            H[i][j] = H[j][i] = value
    return H


def jacobi_eigenvalues(A, tol=1e-12, max_sweeps=100):
    """Eigenvalues of a symmetric matrix by the cyclic Jacobi method.

    DESIGN DECISION: a full eigendecomposition, not a Cholesky factorisation.
    Cholesky is cheaper and answers "is A positive definite?", but a convex
    function may have a *semidefinite* Hessian (x^4 at 0 gives the zero matrix),
    and Cholesky rejects that. Jacobi returns the eigenvalues themselves, so the
    tolerance can be stated on them ("every eigenvalue >= -tol").
    """
    n = len(A)
    a = [row[:] for row in A]
    for _ in range(max_sweeps):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                b = [row[:] for row in a]
                for k in range(n):
                    b[p][k] = c * a[p][k] - s * a[q][k]
                    b[q][k] = s * a[p][k] + c * a[q][k]
                for i in range(n):
                    a[i][p] = c * b[i][p] - s * b[i][q]
                    a[i][q] = s * b[i][p] + c * b[i][q]
    return sorted(a[i][i] for i in range(n))


def is_psd(A, tol=1e-8):
    """True when every eigenvalue of the symmetric matrix ``A`` is >= -tol.

    The tolerance is negative: a zero eigenvalue is allowed (semidefinite),
    which is what a flat direction of a convex function gives.
    """
    return all(lam >= -tol for lam in jacobi_eigenvalues(A))


def jensen_gap(f, box, n, rng):
    """The largest violation of Jensen's inequality over ``n`` random chords.

    For a convex function f(lam x + (1-lam) y) <= lam f(x) + (1-lam) f(y), so the
    gap is <= 0; a gap > 0 is a witness of non-convexity (or concavity).
    DESIGN DECISION: sweep the whole weight grid, not just the midpoint. This is
    free robustness, not a necessity for any one example: a general non-convex
    function's largest violation over a chord can sit at any weight, so the sweep
    is the definition applied faithfully. (For -x^2 the maximum happens to be at
    the midpoint, so the midpoint alone would also catch that particular case.)
    The maximum is returned, never the minimum, so a single witness is enough.
    """
    d = len(box)
    best = 0.0
    for _ in range(n):
        x = _sample(box, rng)
        y = _sample(box, rng)
        fx = f(x)
        fy = f(y)
        for lam in LAMBDAS:
            mid = [lam * x[k] + (1.0 - lam) * y[k] for k in range(d)]
            gap = f(mid) - (lam * fx + (1.0 - lam) * fy)
            if gap > best:
                best = gap
    return best


# ---------------------------------------------------------------------------
# Operations that preserve convexity
# ---------------------------------------------------------------------------

def nonneg_sum(fs, weights):
    """A nonnegative weighted sum of functions: sum_i weights[i] * fs[i](x).

    Convex when every weight is >= 0. A negative weight destroys it (it makes
    the corresponding term concave).
    """
    return lambda x: sum(w * f(x) for f, w in zip(fs, weights))


def pointwise_max(fs):
    """The pointwise maximum max_i fs[i](x): convex when every fs[i] is."""
    return lambda x: max(f(x) for f in fs)


def affine_compose(f, A, b):
    """Composition with an affine map: f(A x + b).

    Convex when f is convex: an affine map preserves convexity for any A and b.
    """
    def g(x):
        y = [sum(A[i][j] * x[j] for j in range(len(x))) + b[i] for i in range(len(A))]
        return f(y)
    return g


# ---------------------------------------------------------------------------
# A naive test, kept to show what it misses
# ---------------------------------------------------------------------------

def sublevel_grid_test(f, lo, hi, levels, n=201):
    """A naive test of whether every sublevel set {x : f(x) <= level} looks convex.

    On a 1-D grid a set is convex exactly when the points where f <= level form
    a single interval. This is the test the limit case is built to fool: a
    quasiconvex function has convex sublevel sets but need not be convex, so a
    function like sqrt(abs(x)) passes here and fails the real tests.
    """
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    vals = [f([t]) for t in xs]
    for level in levels:
        inside = [v <= level for v in vals]
        runs = 0
        prev = False
        for flag in inside:
            if flag and not prev:
                runs += 1
            prev = flag
        if runs > 1:
            return False
    return True


# ---------------------------------------------------------------------------
# The classifier the node's acceptance criterion is about
# ---------------------------------------------------------------------------

def classify(f, box, rng, n=400, tol=1e-6):
    """True when the two tests agree that ``f`` is convex on ``box``.

    Convex only if Jensen finds no violation AND the Hessian at the box centre
    is positive semidefinite. DESIGN DECISION: one Hessian certificate, at the
    centre, not a cheap sampling of the box. The centre is the point where a
    symmetric non-convexity (sqrt(abs(x)) has its cusp there) is otherwise
    hardest to see, and Jensen already covers the rest of the box; sampling the
    Hessian instead would let the classifier lean on the random chords and stop
    being a second, independent opinion.
    """
    if jensen_gap(f, box, n, rng) > tol:
        return False
    if not is_psd(hessian(f, _box_center(box)), tol):
        return False
    return True


def demo():
    """Print the classification and the limit case."""
    width = max(len(name) for name in CATALOGUE)
    print("Classification (Jensen + PSD Hessian at the centre):")
    right = 0
    for name, (f, box) in CATALOGUE.items():
        got = classify(f, box, random.Random(2024))
        want = EXPECTED_CONVEX[name]
        right += got == want
        mark = "ok " if got == want else "BAD"
        gap = jensen_gap(f, box, 400, random.Random(2024))
        print(f"  {mark} {name:<{width}}  convex={str(got):<5} expected={str(want):<5} jensen gap={gap:+.3e}")
    print(f"  {right}/{len(CATALOGUE)} correct")

    print("\nThe naive sublevel test is fooled:")
    levels = [0.25, 0.5, 0.75, 1.0]
    fooled = sublevel_grid_test(lambda x: math.sqrt(abs(x[0])), -4.0, 4.0, levels)
    print(f"  sqrt(abs(x)) sublevel sets look convex: {fooled}  (quasiconvex, not convex)")
    print(f"  classify(sqrt(abs(x))) = {classify(lambda x: math.sqrt(abs(x[0])), [(-2.0, 2.0)], random.Random(0))}")
    caught = sublevel_grid_test(lambda x: -(x[0] ** 2), -4.0, 4.0, [-4.0, -2.0, -1.0, -0.5])
    print(f"  -x^2 sublevel sets look convex: {caught}")


if __name__ == "__main__":
    demo()

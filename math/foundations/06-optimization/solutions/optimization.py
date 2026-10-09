"""Continuous optimization from scratch: gradient descent, momentum, Lagrange multipliers.

Implements *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 7
("Continuous Optimization"). The chapter's themes, restated here rather than copied:

  * The gradient is the steepest-ascent direction, so −∇f is the steepest-descent
    direction; but the *step size* decides whether iterating x ← x − t∇f converges.
    For a quadratic with Hessian eigenvalues in [λ_min, λ_max] the fixed step must obey
    0 < t < 2/λ_max. With the best fixed step the error contracts by exactly
    (κ − 1)/(κ + 1), κ = λ_max/λ_min, so the iteration count grows like κ.
  * A backtracking line search removes the need to know λ_max: it picks a step that
    satisfies the Armijo sufficient-decrease condition.
  * Momentum (the heavy ball) carries the previous velocity and damps the zig-zag of
    plain descent along an ill-conditioned valley.
  * An equality-constrained quadratic has a closed-form optimum from the KKT system;
    it is characterised by stationarity ∇f + Cᵀλ = 0 together with primal feasibility
    Cx = d.

Everything is standard-library Python: no numpy. Matrices are lists of lists of floats;
`_solve` (Gaussian elimination) and `jacobi_eigenvalues` (symmetric Jacobi) are provided
as arithmetic, not as the lesson.

DESIGN DECISION — objective convention: ½xᵀAx − bᵀx, not xᵀAx − bᵀx.
The half cancels in the gradient, leaving ∇f = Ax − b, and at the optimum Ax = b, so
A must be positive definite for a unique minimum. **Chosen: the ½ convention**, because
the Hessian of f is exactly A, not 2A, and A's eigenvalues are the L that bounds the
step size. Cost: every demo writes an explicit ½.

DESIGN DECISION — fixed step, or a line search?
A fixed step is one multiply per iteration but needs λ_max (and converges only for
0 < t < 2/λ_max); a backtracking line search costs one function evaluation per trial but
adapts to any curvature. **Chosen: both, as separate functions**, because the fixed step
is what makes the 2/L divergence boundary visible, and the line search is what makes the
non-convex-looking start x0 = (1, 1) recoverable. Cost: the line search needs f as well as
∇f, and more evaluations per step.

DESIGN DECISION — backtracking criterion: plain decrease, or Armijo?
Accepting any step that lowers f is easy to fool: a step can lower f while being almost
orthogonal to the descent direction and stall. **Chosen: Armijo sufficient decrease**,
f(x + αd) ≤ f(x) + c·α·∇f(x)ᵀd with c = 1e-4. It ties the decrease to the directional
derivative, so a too-long step is rejected even when it happens to lower f. Cost: one extra
dot product per trial, and the returned step is not the exact 1-D minimiser.

DESIGN DECISION — momentum: heavy ball, and which β?
v ← βv + ∇f(x); x ← x − t·v. Nesterov's look-ahead variant is used more in deep learning,
but the heavy ball is the one whose per-mode error recurrence,
e_{k+1} = (1 + β − tλ)e_k − βe_{k−1}, is a plain second-order linear recurrence, so it can
be checked against a closed-form reference. **Chosen: heavy ball, β = 0.9** in the demos.
Cost: the effective stability limit widens to t < 2(1+β)/λ_max, so the plain 2/L boundary
does not apply to it.

DESIGN DECISION — Lagrange multipliers: closed form or a linear solve?
Eliminating x from Qx + b + Cᵀλ = 0 gives λ = (CQ⁻¹Cᵀ)⁻¹(CQ⁻¹(−b) − d), which needs two
inverses and is unstable when CQ⁻¹Cᵀ is ill-conditioned. **Chosen: assemble the (n+m)×(n+m)
KKT matrix [[Q, Cᵀ], [C, 0]] and solve it with the same Gaussian elimination used
elsewhere.** It is the textbook system, it needs no matrix inverse, and the sign convention
(the constraint enters the Lagrangian as +λᵀ(Cx − d)) is stated once. Cost: the KKT matrix
is indefinite, so partial pivoting is required.

DESIGN DECISION — why return the iteration history?
The condition-number, divergence and zig-zag claims are statements about a *trajectory*,
not about the final point. **Chosen: every descent routine returns (x, iterations, history)**
with history[0] = x0. Cost: O(n·iterations) memory, which is why the checks cap max_iter.

    python3 optimization.py     # prints the measurements this file promises
"""

import math

_EPS = 1e-12


# ---------------------------------------------------------------------------
# Small matrix helpers (the arithmetic, not the lesson)
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _norm(u):
    return math.sqrt(_dot(u, u))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _solve(M, v):
    """Solve M z = v by Gaussian elimination with partial pivoting."""
    n = len(M)
    A = [list(M[i]) + [v[i]] for i in range(n)]
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(A[i][col]))
        if abs(A[p][col]) <= _EPS:
            raise ValueError("singular linear system")
        A[col], A[p] = A[p], A[col]
        pv = A[col][col]
        A[col] = [z / pv for z in A[col]]
        for i in range(n):
            if i != col:
                fac = A[i][col]
                if fac:
                    A[i] = [A[i][j] - fac * A[col][j] for j in range(n + 1)]
    return [A[i][n] for i in range(n)]


def jacobi_eigenvalues(A, tol=1e-12, max_sweeps=100):
    """Eigenvalues of a real symmetric A, ascending, by the Jacobi rotation method.

    Only used to read off λ_min and λ_max (the step-size bound and the condition number).
    """
    n = len(A)
    M = [[float(A[i][j]) for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        p = q = 0
        off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(M[i][j]) > off:
                    off = abs(M[i][j])
                    p, q = i, j
        if off < tol:
            break
        theta = 0.5 * math.atan2(2.0 * M[p][q], M[q][q] - M[p][p])
        c = math.cos(theta)
        s = math.sin(theta)
        for k in range(n):
            mkp, mkq = M[k][p], M[k][q]
            M[k][p] = c * mkp - s * mkq
            M[k][q] = s * mkp + c * mkq
        for k in range(n):
            mpk, mqk = M[p][k], M[q][k]
            M[p][k] = c * mpk - s * mqk
            M[q][k] = s * mpk + c * mqk
    return sorted(M[i][i] for i in range(n))


def condition_number(A):
    """λ_max / λ_min of a symmetric positive-definite A (via jacobi_eigenvalues)."""
    eigs = jacobi_eigenvalues(A)
    return eigs[-1] / eigs[0]


# ---------------------------------------------------------------------------
# The quadratic objective
# ---------------------------------------------------------------------------

def quadratic_value(A, b, x, c=0.0):
    """f(x) = ½ xᵀ A x − bᵀ x + c for a symmetric A."""
    return 0.5 * _dot(x, _matvec(A, x)) - _dot(b, x) + c


def quadratic(A, b, c=0.0):
    """Return the pair (f, ∇f) for f(x) = ½ xᵀ A x − bᵀ x + c with A symmetric."""
    f = lambda x: quadratic_value(A, b, x, c)
    grad = lambda x: quadratic_gradient(A, b, x)
    return f, grad


def quadratic_gradient(A, b, x):
    """Gradient of f(x) = ½ xᵀ A x − bᵀ x + c: A x − b.

    A is symmetric, so the Hessian of f is exactly A (not A + Aᵀ), giving the step-size
    bound t < 2/λ_max(A) directly in terms of A's eigenvalues.
    """
    n = len(x)
    return [sum(A[i][j] * x[j] for j in range(n)) - b[i] for i in range(n)]


# ---------------------------------------------------------------------------
# Fixed-step gradient descent and its stability ceiling
# ---------------------------------------------------------------------------

def max_stable_step(L):
    """Largest fixed step for which descent on a quadratic with λ_max = L converges.

    The per-mode multiplier is 1 − tλ, so convergence needs |1 − tλ| < 1 for every
    eigenvalue, i.e. 0 < t < 2/λ. The binding eigenvalue is the largest, L, so the
    supremum is 2/L.
    """
    return 2.0 / L


def gradient_descent(f, grad_f, x0, step, tol=1e-9, max_iter=10000):
    """Fixed-step gradient descent: x ← x − step·∇f(x), stopping at ‖∇f‖ ≤ tol.

    Returns (x, iterations, history); history[0] = x0 and len(history) = iterations + 1.
    """
    x = list(x0)
    n = len(x)
    history = [list(x)]
    for _ in range(max_iter):
        g = grad_f(x)
        if _norm(g) <= tol:
            break
        x = [x[i] - step * g[i] for i in range(n)]
        history.append(list(x))
        if not all(math.isfinite(v) for v in x):
            break
    return x, len(history) - 1, history


# ---------------------------------------------------------------------------
# Backtracking line search and the descent that uses it
# ---------------------------------------------------------------------------

def backtracking_line_search(f, grad_f, x, direction, alpha0=1.0, rho=0.5, c=1e-4):
    """Armijo backtracking: largest α = alpha0·rhoᵏ with

        f(x + α·direction) ≤ f(x) + c·α·∇f(x)ᵀdirection.

    `direction` must be a descent direction (∇f(x)ᵀdirection < 0); otherwise no step can
    satisfy the inequality and the search would never terminate.
    """
    g = grad_f(x)
    gd = _dot(g, direction)
    if gd >= 0.0:
        raise ValueError("direction is not a descent direction")
    alpha = alpha0
    while f([x[i] + alpha * direction[i] for i in range(len(x))]) > f(x) + c * alpha * gd:
        alpha *= rho
        if alpha < 1e-300:
            break
    return alpha


def gradient_descent_backtracking(f, grad_f, x0, alpha0=1.0, tol=1e-9,
                                  max_iter=1000, rho=0.5, c=1e-4):
    """Gradient descent whose step is chosen by Armijo backtracking on −∇f(x).

    Returns (x, iterations, history) with history[0] = x0; every accepted step decreases
    f (by the Armijo condition with c > 0).
    """
    x = list(x0)
    n = len(x)
    history = [list(x)]
    for _ in range(max_iter):
        g = grad_f(x)
        if _norm(g) <= tol:
            break
        direction = [-v for v in g]
        alpha = backtracking_line_search(f, grad_f, x, direction, alpha0, rho, c)
        x = [x[i] + alpha * direction[i] for i in range(n)]
        history.append(list(x))
        if not all(math.isfinite(v) for v in x):
            break
    return x, len(history) - 1, history


# ---------------------------------------------------------------------------
# Momentum (heavy ball)
# ---------------------------------------------------------------------------

def momentum(f, grad_f, x0, step, beta, tol=1e-9, max_iter=10000):
    """Heavy-ball momentum: v ← βv + ∇f(x); x ← x − step·v.

    The previous velocity term βv is the whole method: with β = 0 it collapses to plain
    gradient descent. Returns (x, iterations, history) with history[0] = x0.
    """
    x = list(x0)
    n = len(x)
    v = [0.0] * n
    history = [list(x)]
    for _ in range(max_iter):
        g = grad_f(x)
        if _norm(g) <= tol:
            break
        v = [beta * v[i] + g[i] for i in range(n)]
        x = [x[i] - step * v[i] for i in range(n)]
        history.append(list(x))
        if not all(math.isfinite(w) for w in x):
            break
    return x, len(history) - 1, history


# ---------------------------------------------------------------------------
# Equality-constrained quadratic: Lagrange multipliers
# ---------------------------------------------------------------------------

def lagrange_quadratic(Q, b, C, d):
    """Minimise ½xᵀQx + bᵀx subject to Cx = d, via the KKT linear system.

    Q is n×n (symmetric positive definite), C is m×n (full row rank). With the Lagrangian
    L = ½xᵀQx + bᵀx + λᵀ(Cx − d), the first-order conditions are

        Q x + b + Cᵀλ = 0     (stationarity)
        C x = d               (primal feasibility)

    i.e. the block system [[Q, Cᵀ], [C, 0]] [x; λ] = [−b; d]. Returns (x, λ).
    """
    n = len(Q)
    m = len(C)
    K = [[0.0] * (n + m) for _ in range(n + m)]
    for i in range(n):
        for j in range(n):
            K[i][j] = Q[i][j]
        for k in range(m):
            K[i][n + k] = C[k][i]
    for k in range(m):
        for j in range(n):
            K[n + k][j] = C[k][j]
    rhs = [-b[i] for i in range(n)] + [d[k] for k in range(m)]
    z = _solve(K, rhs)
    return z[:n], z[n:]


def kkt_residuals(Q, b, C, d, x, lam):
    """Return (stationarity, primal) residuals of the KKT conditions at (x, λ):

        stationarity = ‖Qx + b + Cᵀλ‖,  primal = ‖Cx − d‖.

    Both must vanish at the constrained optimum; a routine that reports only one of them
    cannot tell a feasible non-stationary point from an optimum.
    """
    n = len(x)
    m = len(lam)
    residual = [sum(Q[i][j] * x[j] for j in range(n)) + b[i]
                + sum(C[k][i] * lam[k] for k in range(m)) for i in range(n)]
    stationarity = _norm(residual)
    primal = _norm([sum(C[k][j] * x[j] for j in range(n)) - d[k] for k in range(m)])
    return stationarity, primal


if __name__ == "__main__":
    # --- condition number vs iteration count on a diagonal quadratic -----------------
    print("Optimization from scratch — measurements")
    print("  kappa   predicted   measured   (fixed step 2/(1+kappa), tol 1e-8)")
    for kappa in (10, 100, 1000):
        L = float(kappa)
        A = [[1.0, 0.0], [0.0, L]]
        f, g = quadratic(A, [0.0, 0.0])
        x0 = [0.0, 1.0]                      # aligned with λ_max
        t = 2.0 / (1.0 + L)                  # the optimal fixed step 2/(λ_min+λ_max)
        r = (kappa - 1.0) / (kappa + 1.0)
        g0 = _norm(g(x0))
        predicted = math.ceil(math.log(1e-8 / g0) / math.log(r))
        x, it, _ = gradient_descent(f, g, x0, t, tol=1e-8, max_iter=200000)
        print(f"  {kappa:>5}   {predicted:>9}   {it:>8}")

    # --- 2/L boundary -----------------------------------------------------------------
    L = 100.0
    A = [[1.0, 0.0], [0.0, L]]
    f, g = quadratic(A, [0.0, 0.0])
    t_c = max_stable_step(L)
    lo, it_lo, _ = gradient_descent(f, g, [1.0, 1.0], t_c * 0.99, tol=1e-8, max_iter=5000)
    hi, it_hi, _ = gradient_descent(f, g, [1.0, 1.0], t_c * 1.01, tol=1e-8, max_iter=5000)
    print(f"\n  2/L = {t_c:.5f}:  0.99x -> |grad| = {_norm(g(lo)):.2e} ({it_lo} it)"
          f"   1.01x -> |grad| = {_norm(g(hi)):.2e} ({it_hi} it)")

    # --- zig-zag vs momentum ----------------------------------------------------------
    L = 1000.0
    A = [[1.0, 0.0], [0.0, L]]
    f, g = quadratic(A, [0.0, 0.0])
    x0 = [1.0, 1.0]
    t = 2.0 / (1.0 + L)                      # optimal fixed step, shared by both methods
    xg, it_gd, hg = gradient_descent(f, g, x0, t, tol=1e-6, max_iter=50000)
    xm, it_mom, hm = momentum(f, g, x0, t, 0.9, tol=1e-6, max_iter=50000)

    def path(h):
        return sum(_norm([h[k + 1][i] - h[k][i] for i in range(2)])
                   for k in range(len(h) - 1))

    def reversals(h):
        return sum(1 for k in range(1, len(h) - 1)
                   if (h[k + 1][1] - h[k][1]) * (h[k][1] - h[k - 1][1]) < 0)

    print(f"\n  ill-conditioned valley (kappa=1000):")
    print(f"    plain GD   iterations {it_gd:>6}   path {path(hg):>8.1f}   "
          f"sign reversals {reversals(hg):>6}")
    print(f"    momentum   iterations {it_mom:>6}   path {path(hm):>8.1f}   "
          f"sign reversals {reversals(hm):>6}")

    # --- constrained optimum and KKT --------------------------------------------------
    Q = [[2.0, 0.5], [0.5, 1.0]]
    b = [-1.0, 2.0]
    C = [[1.0, 1.0]]
    d = [1.0]
    x, lam = lagrange_quadratic(Q, b, C, d)
    st, pr = kkt_residuals(Q, b, C, d, x, lam)
    print(f"\n  constrained min: x = ({x[0]:.4f}, {x[1]:.4f}), lambda = {lam[0]:.4f}")
    print(f"    KKT stationarity = {st:.2e}   primal feasibility = {pr:.2e}")

    # --- spectral helper on a rotated (non-diagonal) SPD matrix -----------------------
    R = [[2.0, 1.0], [1.0, 2.0]]            # eigenvalues 1 and 3
    print(f"\n  rotated SPD matrix: eigenvalues {jacobi_eigenvalues(R)}, "
          f"condition number {condition_number(R):.3f}")

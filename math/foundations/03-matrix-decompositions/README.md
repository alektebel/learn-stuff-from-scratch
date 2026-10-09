# Matrix Decompositions From Scratch

Cholesky, power iteration with deflation, and the SVD from the eigendecomposition of
`AᵀA`, in pure Python (standard library only), built one mechanism at a time.

Third node of the [skill tree](../../../skill-tree/README.md), in the `foundations`
track: *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 4. It
follows [02-analytic-geometry](../02-analytic-geometry/), whose SPD test by Cholesky is
the same predicate this module factors with.

The idea the chapter turns on: **the decompositions worth having have orthonormal or
triangular factors, and the price of getting them is conditioning.** Forming `AᵀA` is
the standard route to an SVD and the standard way to square the condition number; the
last check measures exactly that damage instead of hiding it.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Cholesky | `A = LLᵀ`, one pass, first non-positive pivot raises | `decompositions.py` | 1-2 |
| Power iteration | dominant eigenpair of a symmetric matrix | `decompositions.py` | 3-4 |
| Deflation | `M ← M − λvvᵀ` for the next eigenpair | `decompositions.py` | 5 |
| SVD | `A = UΣVᵀ` from the eigenpairs of `AᵀA` | `decompositions.py` | 6 |
| Rank-k approximation | keep the top `k` terms; Eckart-Young error `= σ_{k+1}` | `decompositions.py` | 7 |
| Conditioning | `κ(AᵀA) = κ(A)²` and the precision it costs | `decompositions.py` | 8 |

## How to use this directory

`decompositions.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
a working version for when you are stuck, or to compare afterwards.

```bash
cd math/foundations/03-matrix-decompositions
python3 check.py        # what to build next; stops at the first gap
python3 check.py 5      # one step
python3 check.py 5 7    # a range
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`. Every
reference value is computed in `check.py` itself: an exact `Fraction` Cholesky for an
integer matrix, a self-contained power iteration for the spectral norm, and a 60-digit
`decimal` Jacobi eigensolver for the conditioning check.

### The NumPy comparison was replaced

The original node spec accepted *"SVD via `AᵀA` squaring the condition number: show the
precision loss against `numpy.linalg.svd`."* This repository has **no numpy, no pip and no
network** (see the root [CLAUDE.md](../../../CLAUDE.md)), so that comparison cannot run
here. It is replaced by an **independent high-precision oracle written in this repo**: the
checker converts every float of `AᵀA` exactly to `decimal.Decimal` and runs a 60-digit
Jacobi eigendecomposition (`_decimal_eigenvalues`). The precision loss is the gap between
your float `AᵀA` path and that oracle — a stricter test than NumPy, because it answers the
same question without any third-party code.

## The checker was itself tested

Six classic bugs were planted in copies of the solutions, and each one has to be caught by
its check:

| Planted bug | Caught by |
|---|---|
| Cholesky skips the positive-pivot test (reaches `sqrt` of a negative) | step 2 |
| power iteration ignores the equal-magnitude non-convergence | step 4 |
| deflation loop runs `k+1` times | step 5 |
| rank-k approximation keeps `k+1` terms | step 7 |
| SVD reports the eigenvalue, not its square root | step 6 |
| the small eigenvalue is clamped away, hiding the `AᵀA` loss | step 8 |

## Design decisions, named

Each function's docstring names the alternatives and the cost. In short:

- **Cholesky tests and factors in one pass.** "Has a Cholesky factor" and "is SPD" are the
  same predicate, so there is no separate SPD pre-test that can disagree at the tolerance
  boundary — and no path that reaches `math.sqrt` with a negative number.
- **Power iteration accepts on the residual `‖Av − λv‖`, not on a small change in `λ`.**
  With eigenvalues `+1` and `−1` the Rayleigh quotient is constant while the vector
  alternates; a step-size test would call that converged. The cost is one extra
  matrix-vector product.
- **Deflation subtracts `λvvᵀ` from the working matrix**, not "re-orthogonalise the start
  vector". It is the textbook construction and makes each next eigenpair a property of the
  matrix in hand; the cost is an `O(n²)` subtraction per pair, fine for small `k`.
- **The SVD eigendecomposes `AᵀA` (n×n), not `AAᵀ`.** The right singular vectors — the ones
  the low-rank approximation keeps — come out directly. The cost is the squared condition
  number, which is the point of step 8.
- **`low_rank_approx` takes a rank `k`, not an error tolerance.** It makes `k` exactly the
  number of terms, so the Eckart-Young identity can be stated with the single value
  `σ_{k+1}`.

## Questions to answer before reading the solutions

1. Cholesky needs the pivot `s > 0`. What does a zero pivot mean about `A`, and why is a
   positive semidefinite matrix (e.g. `[[1,1],[1,1]]`) still rejected — correctly?
2. Power iteration converges at rate `|λ₂/λ₁|` per step. For `λ₁ = 1` and `λ₂ = 0.99`, how
   many iterations to reach residual `1e-7`? Why does the equal-magnitude case never get
   there, no matter how many steps you take?
3. Deflation replaces `λ` by `0` in the spectrum. Which eigenvalue must therefore be the
   *largest remaining* one for the next power iteration to find it, and what happens if two
   eigenvalues have the same magnitude but opposite sign?
4. Eckart-Young says the best rank-k error is `σ_{k+1}`. Why does keeping the `k` largest
   singular values minimise the spectral norm, and which singular values would a *Frobenius*
   norm choose? (They are the same here; say why in general.)
5. Forming `AᵀA` squares the condition number. Given `κ(A) = 10⁷` and `ε ≈ 2.2·10⁻¹⁶`,
   predict the relative error of the small singular value before running step 8, then compare
   with the printed `1.5e-03`.

## Limits

- **Floating point, not exact arithmetic.** The reconstruction checks use `1e-10` and the
  conditioning loss is a *relative* property, so it is asserted as a ratio/gap, not an
  absolute threshold. The one exact computation is the integer Cholesky factor, checked
  over `Fraction`.
- **Power iteration and deflation, not QR iteration.** Only the top `k` eigenpairs are
  available, and deflation loses accuracy for small eigenvalues; a full, backward-stable
  spectrum would use QR iteration with shifts (`linalg-02-eigenvalues`).
- **The SVD is the "thin" one built from `AᵀA`.** It is deliberately the numerically worse
  route, kept because that is the route the chapter and this node's limit case are about.
  A production SVD uses bidiagonalisation and does not square the condition number.
- **Symmetric / SPD inputs.** Power iteration and deflation here assume a real symmetric
  matrix; complex or non-symmetric matrices need different machinery (Schur form).
- **Small, dense matrices.** The helpers are `O(n³)` with no blocking or sparsity; the
  point is the mechanism, not throughput.

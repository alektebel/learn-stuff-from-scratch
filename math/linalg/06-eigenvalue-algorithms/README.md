# Eigenvalue Algorithms From Scratch

Householder reduction to Hessenberg and tridiagonal form, Rayleigh quotient iteration,
and the unshifted and shifted QR algorithms — in pure Python (standard library only).
Node `linalg-06-eigenvalue-algorithms` of the [skill tree](../../../skill-tree/README.md),
in the `linalg` track. Sources, restated rather than copied: **Trefethen & Bau, *Numerical
Linear Algebra*, lectures 25-29** (`trefethen:25`–`trefethen:29`) — the reduction to
Hessenberg form (25), symmetric tridiagonalization (26), Rayleigh quotient iteration (27),
and the unshifted and shifted QR algorithms (28-29). Its prerequisite is
`linalg-02-eigenvalues`, whose Householder QR and Wilkinson shift are the helpers left
implemented here.

The idea the module turns on: **reduce first, then iterate, and shift when the spectrum
has equal magnitudes.** QR costs O(n²) per sweep on a Hessenberg matrix instead of O(n³)
on a full one; and the *unshifted* QR iteration converges only linearly and stalls outright
when two eigenvalues have equal magnitude, which the Wilkinson shift repairs.

## Environment adaptation (named, not silent)

The node's acceptance line asks that eigenvalues match `numpy.linalg.eigvalsh` on random
symmetric matrices to `1e-10`. **numpy is not installed in this repository and cannot
be.** The oracle is therefore replaced by two independent references that need no
third-party package:

- a **cyclic Jacobi symmetric eigensolver carried inside `check.py` itself**, run at a
  tolerance of `1e-15`; it is an algorithm independent of QR, so agreement is evidence;
- a handful of symmetric matrices whose **spectra are known exactly** (rational) and are
  written down in the checks.

The `1e-10` agreement requirement is kept unchanged. Only the source of the reference
changed: numpy's LAPACK path was swapped for a self-contained Jacobi path, and this is
stated here rather than hidden.

## What you build

| Concept | Mechanism | Checks |
|---|---|---|
| Hessenberg reduction | Householder similarity `H = Qᵀ A Q`, `H` upper Hessenberg | 1 |
| Tridiagonal reduction | the same similarity for symmetric `A`, `T = Qᵀ A Q` | 2 |
| QR algorithm | Hessenberg, then deflation; `"none"` and `"wilkinson"` shifts | 3, 5 |
| Rayleigh quotient iteration | `(A − ρI) w = v`, ρ the current quotient | 4 |
| Cubic convergence (accept) | `log e_{k+1} / log e_k → 3` from the error sequence | 4 |
| Equal-magnitude limit case | unshifted QR stalls; the Wilkinson shift converges | 5 |

## How to use this directory

`eigenalg.py` is a **template**: each graded function keeps its signature and docstring, has
a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds a working
version for when you are stuck, or to compare afterwards. The prerequisite helpers
(`_qr_factor`, `_solve`, `_wilkinson_shift`, `jacobi_reference`, …) are left implemented.

```bash
cd math/linalg/06-eigenvalue-algorithms
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`. The
numerical oracle is the checker's own Jacobi solver and exact known spectra; the error
tolerances are stated at each assertion.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Reduce to Hessenberg before iterating.** One-off O(n³) reduction makes every later QR
  sweep O(n²). Iterating on the full matrix is correct but does `n` times the work.
- **Householder reflectors, not elementary elimination.** A reflector is orthogonal to
  working precision, so `QᵀQ = I` and `Q H Qᵀ = A` are testable at `1e-12`; a
  non-orthogonal similarity would preserve the spectrum only in exact arithmetic.
- **A dedicated symmetric tridiagonalization.** For symmetric input an upper Hessenberg
  form is automatically tridiagonal; writing it separately lets the checker demand
  symmetry and the tridiagonal pattern, not merely Hessenberg.
- **Relative deflation and a counted budget.** The subdiagonal is declared zero when it
  falls below `tol` times the local diagonal scale; the iteration stops at `maxit` and
  *reports* the count, so the unshifted stall is measured rather than hidden behind an
  exception.
- **Wilkinson shift, not none and not the Rayleigh shift.** Unshifted QR is linear and
  stalls on equal magnitudes; the Rayleigh shift is quadratic but fragile; the Wilkinson
  shift (the trailing 2×2 eigenvalue nearest its corner) is the robust accelerated
  choice.
- **Rayleigh quotient iteration solves the shifted system directly.** The
  near-singularity of `A − ρI` is the mechanism that produces cubic convergence, so it is
  accepted, with only a tiny scale-aware nudge when a pivot vanishes.

## The checker was itself tested

Five classic bugs were planted in copies of the solutions, and each is caught by its
check (`_build/mutations.py`):

| Planted bug | Caught by |
|---|---|
| hessenberg applies the reflector on one side only | step 1 |
| tridiagonalize skips the last reflector | step 2 |
| QR algorithm reads the diagonal instead of iterating | step 3 |
| Rayleigh quotient iteration uses a fixed step | step 4 |
| unshifted QR silently uses the Wilkinson shift | step 5 |

Run it yourself:
`python3 .claude/skills/graded-module/scripts/mutate.py math/linalg/06-eigenvalue-algorithms math/linalg/06-eigenvalue-algorithms/_build/mutations.py`
— every line must read `CAUGHT`.

## The two limit cases

- **Equal-magnitude eigenvalues (step 5).** On
  `blkdiag([[0,1],[1,0]], [[0,2],[2,0]])`, whose spectrum is `{1, −1, 2, −2}`, the
  unshifted QR iteration is a fixed point on each 2×2 block: the subdiagonal never decays,
  so it runs the whole 200-sweep budget and returns garbage. The Wilkinson shift separates
  each pair and converges in 2 sweeps. This is exactly the failure Trefethen & Bau
  lecture 28 warns about, and the shift is the fix.
- **Cubic convergence (step 4).** Rayleigh quotient iteration's eigenvalue error obeys
  `e_{k+1} ≈ C e_k³`, so `log e_{k+1} / log e_k` approaches 3. The checker measures this
  exponent from the returned error sequence; a method with a *fixed* shift is shifted
  inverse iteration, linearly convergent, and its exponent stays near 1.

## Questions to answer before reading the solutions

1. Why is a Householder reflector applied on **both** sides a similarity, and what
   quantity does a one-sided application preserve instead?
2. QR on a full matrix costs O(n³) per sweep; on Hessenberg form it costs O(n²). Where
   does the saving come from, and why does the reduction not lose accuracy?
3. The unshifted QR iteration stalls when eigenvalues have equal magnitude. Why does the
   Wilkinson shift — a single number per step — remove the tie?
4. Rayleigh quotient iteration converges cubically. What in `(A − ρI) w = v` supplies the
   exponent, and why does a fixed shift give only linear convergence?
5. Eigenvalues are well-conditioned for symmetric matrices, but eigenvectors of a
   defective matrix are not. Which of these algorithms would expose that, and how?

## Limits

- The QR iteration here targets **small dense real** matrices. It handles repeated real
  eigenvalues and equal-magnitude pairs (with the shift) but does not implement implicit
  double-shift for complex eigenvalues; a genuinely complex spectrum is out of scope.
- The convergence claim is **local**: Rayleigh quotient iteration needs a start vector
  with a nonzero component along the wanted eigenvector, and can fail when the initial
  quotient lands exactly halfway between two eigenvalues.
- The reference is a **dense Jacobi** solver, so the `1e-10` agreement is measured on
  matrices small enough to solve both ways; it is not a large-scale benchmark.
- No SVD, no pseudospectra, and no generalised eigenproblem `A v = λ B v`. Those belong to
  later nodes.

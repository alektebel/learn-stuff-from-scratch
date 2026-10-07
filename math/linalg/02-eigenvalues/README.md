# Eigenvalues From Scratch

Eigenvalues, eigenvectors, diagonalisability and the two roads to the spectrum — an exact
`fractions.Fraction` road and a numerical QR road — in pure Python (standard library
only). Node `linalg-02-eigenvalues` of the [skill tree](../../../skill-tree/README.md), in
the `linalg` track. Sources, restated rather than copied: **Sheldon Axler, *Linear Algebra
Done Right*, chapter 5** (`axler:5`) — eigenvalues, eigenvectors, and the independence of
eigenvectors belonging to distinct eigenvalues. Its prerequisite is
`linalg-01-vector-spaces`, whose exact RREF and null space (`_rref`, `_null_space_basis`)
are the helpers left implemented here.

The idea the module turns on: **a matrix is diagonalisable iff it has n independent
eigenvectors — that is, the geometric multiplicities of its eigenvalues sum to n.** The
trap is that two shorter counts look right and are not: the number of *distinct*
eigenvalues undercounts (the identity has one and is diagonalisable), and the *algebraic*
multiplicities always sum to n (a Jordan block has n counting multiplicity and is not).

## What you build

| Concept | Mechanism | Checks |
|---|---|---|
| Characteristic polynomial | Faddeev-LeVerrier recurrence, exact | 1 |
| Horner evaluation / rational roots | rational root theorem + synthetic division | 2 |
| Eigenvalues and eigenspaces | roots of the polynomial; null space of `A − λI` | 3 |
| Diagonalisability | sum of eigenspace dimensions `== n` (the accept criterion) | 4 |
| Diagonalisation | `A = P D P⁻¹`, or `None` if defective | 5 |
| Householder QR | reflectors `H = I − 2vvᵀ`, so `Q ᵀ Q = I` | 6 |
| QR eigensolver | Hessenberg → Wilkinson-shifted QR, closed-form 2×2 | 7 |
| Wilkinson's polynomial | `∏(x − k)`, exact, and its companion matrix | 8 |
| Limit case | Newton+deflation loses accuracy, QR stays stable | 9 |

## How to use this directory

`eigenvalues.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
a working version for when you are stuck, or to compare afterwards. The prerequisite
helpers (`_rref`, `_null_space_basis`, `_integer_divisors`, `_clear_denominators`,
`_synthetic_divide`, `_poly_eval_complex`, `hessenberg`, …) are left implemented.

```bash
cd math/linalg/02-eigenvalues
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py 4 6    # a range
python3 check.py --all  # everything
```

`check.py` runs 9 checks against **your** code and never imports `solutions/`. Every exact
reference value is computed in the checker itself; in particular the characteristic
polynomial is recomputed by cofactor expansion of `det(xI − A)`, a method independent of
the Faddeev-LeVerrier recurrence the template asks for, so a wrong sign cannot hide. The
numerical checks state their tolerance at the assertion.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Exact `Fraction`s for the qualitative questions, floats only for the numerical
  ones.** Roots, eigenspaces, diagonalisability and diagonalisation are exact equalities;
  the numerical eigensolver and its conditioning lesson are the one place equality would
  be wrong. A matrix with a non-rational spectrum therefore has no exact
  diagonalisability report and raises `ValueError`; `qr_eigenvalues` still answers.
- **Faddeev-LeVerrier, not cofactor expansion or interpolation**, for the characteristic
  polynomial: O(n⁴) exact operations against O(n!) for the definitional expansion.
- **Diagonalisability counts geometry.** Not distinct eigenvalues, not algebraic
  multiplicities. Only the sum of eigenspace dimensions separates the identity from the
  Jordan block.
- **`diagonalize` refuses.** When the eigenvectors fall short it returns `None` rather
  than filling in a missing column, which would produce a non-invertible `P` and a fake
  factorisation.
- **Householder QR, not Gram-Schmidt.** Reflectors stay orthogonal to working precision,
  which is what the `QᵀQ = I` check measures.
- **Hessenberg reduction plus the Wilkinson shift, plus a closed-form 2×2**, rather than
  the plain unshifted iteration, so a complex-conjugate pair is produced correctly.
- **The Wilkinson limit case measures both routes.** The root finder is the textbook
  naive Newton-with-forward-deflation; the experiment reports each route's largest error
  and the checker decides which one is stable.

## The checker was itself tested

Ten classic bugs were planted in copies of the solutions, and each one has to be caught by
its check (`_build/mutations.py`):

| Planted bug | Caught by |
|---|---|
| characteristic polynomial coefficient sign flipped | step 1 |
| diagonalisability counts distinct eigenvalues | step 4 |
| Jordan block reported diagonalisable | step 4 |
| Wilkinson errors report the polynomial route as stable | step 9 |
| eigenspace uses `A + λI` | step 3 |
| rational roots drop the negative candidates | step 2 |
| QR skips the last reflector | step 6 |
| eigensolver reads the diagonal instead of iterating | step 7 |
| diagonalize does not check independence | step 5 |
| Wilkinson product stops one factor early | step 8 |

Run it yourself:
`python3 .claude/skills/graded-module/scripts/mutate.py math/linalg/02-eigenvalues math/linalg/02-eigenvalues/_build/mutations.py`
— every line must read `CAUGHT`. Two checks needed care: step 4 must contain a matrix
with a repeated eigenvalue that is *still* diagonalisable (the identity), otherwise
counting distinct eigenvalues and counting eigenvectors agree on every test and the
mutation slips through; and step 9 must report both errors from the same experiment, so
swapping them is a detectable lie rather than a matter of opinion.

## Questions to answer before reading the solutions

1. The identity has one distinct eigenvalue and is diagonalisable; a Jordan block has one
   distinct eigenvalue and is not. Write the two eigenspaces and say which quantity
   differs — distinct eigenvalues, algebraic multiplicities, or geometric multiplicities.
2. `characteristic_polynomial` returns `[1, a₁, …, aₙ]` for `xⁿ + a₁xⁿ⁻¹ + … + aₙ`. What
   are `a₁` and `aₙ` in terms of the matrix, and why does every coefficient being an exact
   rational matter for the accept test?
3. A diagonalisable matrix is built as `A = S D S⁻¹`. Why do its eigenvalues not depend
   on `S`, and why is `A` diagonalisable by construction?
4. `qr_decompose` uses Householder reflectors. Why is `Q` orthogonal by construction,
   whereas classical Gram-Schmidt only drifts away from orthogonality, and what does the
   checker measure to see the difference?
5. On Wilkinson's polynomial `W₂₀`, the polynomial route has a much larger root error
   than QR does on the companion matrix. What is ill-conditioned — the roots as functions
   of the coefficients, or the matrix eigenvalues as functions of the entries — and why
   does not forming the coefficients help?

## Limits

- The exact road needs a **rational spectrum**. A rational matrix with an irrational or
  complex eigenvalue raises `ValueError` in `is_diagonalizable`/`diagonalize`; only
  `qr_eigenvalues` reports it. A mixed spectrum (rational roots plus an irreducible
  quadratic factor) is likewise out of scope.
- The numerical road assumes a **small dense** matrix. `qr_eigenvalues` is the classic
  shifted-QR iteration with a closed-form 2×2; it is not tuned for large matrices, but it
  handles repeated real eigenvalues, complex-conjugate pairs, and the companion matrix of
  `W₂₀`.
- The Wilkinson experiment uses the **naive** root finder on purpose. A carefully
  implemented simultaneous iteration (Durand-Kerner, Jenkins-Traub) would narrow the gap;
  the lesson is that *forming the coefficients and finding their roots* is the fragile
  road, and on `W₂₀` the gap is large.
- No SVD, no pseudospectra, no condition-number theory beyond the measured Wilkinson
  gap, and no generalised eigenproblem `A v = λ B v`. Those belong to later nodes.

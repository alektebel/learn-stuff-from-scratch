# Linear Algebra From Scratch

Gaussian elimination and everything it unlocks — row echelon form, rank, the null
space, `Ax = b`, the inverse and the determinant — in pure Python (standard library
only), built one mechanism at a time.

It is the first node of the [skill tree](../../../skill-tree/README.md), the
`foundations` track: the material of *Mathematics for Machine Learning* (Deisenroth,
Faisal & Ong), chapter 2. Everything later in the tree that solves a linear system,
takes a gradient or factors a matrix stands on this.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Elimination | forward elimination, partial pivoting, row echelon form | `elimination.py` | 1 |
| Rank | pivots of the reduced matrix | `elimination.py` | 2 |
| Solve `Ax = b` | Gauss-Jordan on the augmented matrix | `elimination.py` | 3-4 |
| Null space | basis from the free columns of the reduced matrix | `elimination.py` | 5 |
| General solution | particular + homogeneous | `elimination.py` | 6 |
| Inverse | Gauss-Jordan on `[A \| I]` | `elimination.py` | 7-8 |
| Determinant | product of pivots, sign from the row swaps | `elimination.py` | 9 |
| Stability | why the pivot must be the largest in the column | `elimination.py` | 10 |

## How to use this directory

`elimination.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/`
holds a working version for when you are stuck, or to compare afterwards.

```bash
cd math/foundations/01-linear-algebra
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 10 checks against **your** code and never imports `solutions/`. The
reference answers come from numpy when it is installed and from an exact rational oracle
(`fractions.Fraction`, in `check.py`) when it is not, so the module runs with no
dependencies and the oracle never shares the learner's rounding.

**The checker was itself tested.** Six classic bugs were planted in copies of the
solutions, and each one has to be caught by its check:

| Planted bug | Caught by |
|---|---|
| dividing by the diagonal instead of pivoting | step 10 |
| building the null space from the pivot columns | step 5 |
| ignoring the row-swap sign in the determinant | step 9 |
| returning a vector for an inconsistent system | step 4 |
| inverting a singular matrix instead of raising | step 8 |
| dropping the homogeneous part of the general solution | step 6 |

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Partial pivoting, not the diagonal** (`_forward`, `_reduce_aug`). One extra pass per
  column buys unconditional stability; the naive version is wrong in the first digit on
  the small-pivot system in step 10.
- **Reduced row echelon, not just echelon** (`_reduce_aug`). Back-substitution would solve
  the system, but the null-space basis and the particular solution fall out of the
  reduced form directly.
- **Named exceptions, not sentinels** (`solve`, `inverse`). `InconsistentSystem`,
  `NotUnique` and `SingularMatrix` let the caller (and a test) know *which* assumption
  failed, instead of guessing from a `None`.
- **A tolerance scaled to the matrix** (`_scale`). Rank and singularity are decided
  against `eps * max|entry|`, so the answer does not change with the units of the matrix.

## Questions to answer before reading the solutions

1. **Why does partial pivoting fix the small-pivot system, and what exactly does it cost?**
   Step 10 shows the failure; explaining *why* the largest entry is the safe choice is the
   point.
2. A zero pivot is really a rank deficiency, not a small number. Where in your code is
   that distinction made, and what goes wrong if you compare against `0.0` instead?
3. `general_solution` returns *one* particular solution. If `rank < n`, infinitely many
   are valid. Which free variables did you choose to zero, and does the choice matter?
4. The determinant is a product of pivots times a sign. Why is that the same number for
   every valid elimination order, even though the pivots themselves change?
5. `inverse` and `solve` both call the same reduction. Name a matrix where one succeeds
   and the other fails, and say why.

## Limits

- Floating point, not exact arithmetic. Everything is a `float`, so results are accurate
  to about `1e-12` on well-conditioned input; the checker's oracle is exact, the learner's
  code is not.
- No least-squares path. An inconsistent system raises instead of returning a
  pseudo-inverse solution; that arrives with `linalg-04-qr-least-squares`.
- Dense matrices only. A sparse or banded matrix would reuse all of this but should never
  be stored as a list of lists.
- Complexity is `O(n^3)`; there is no blocking or cache-aware variant. That is the subject
  of `linalg-05-conditioning-stability` and `linalg-06-eigenvalue-algorithms`.

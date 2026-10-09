# Vector Spaces From Scratch

Rank, null spaces, ranges, change of basis and the fundamental theorem of linear maps, in
pure Python (standard library only), with `fractions.Fraction` so every acceptance test is
an exact equality rather than a floating-point threshold.

Node `linalg-01-vector-spaces` of the [skill tree](../../../skill-tree/README.md), in the
`linalg` track. Sources, restated rather than copied: **Sheldon Axler, *Linear Algebra Done
Right*, chapters 1-3** (`axler:1`, `axler:2`, `axler:3`) — vector spaces and bases
(ch. 1-2), and linear maps, null spaces, ranges and the fundamental theorem (ch. 3). It
follows `foundations-01-linear-algebra`, whose Gaussian elimination (`_rref`, `_inverse`)
is the one helper left implemented here.

The idea the module turns on: **a matrix is a linear map only after you choose two bases,
and the same linear map has a different matrix in every pair of bases.** The running
example is P_n, the polynomials of degree at most n. Once the monomial basis
`1, x, ..., x^n` is fixed, a polynomial *is* a coordinate vector of n+1 rationals, and
differentiation *is* an (n+1)×(n+1) matrix.

## What you build

| Concept | Mechanism | Checks |
|---|---|---|
| Rank | pivot count of the exact RREF | 1 |
| Null space | a basis read off the free columns | 2 |
| Range (column space) | the pivot columns of the *original* matrix | 3 |
| Change of basis | `M = S⁻¹ A S`, inverse first, on the left | 4 |
| Matrix in two bases | `M = C⁻¹ A B`; columns are images in the codomain basis | 5 |
| Differentiation on P_n | `d/dx xᵏ = k·xᵏ⁻¹` as a square matrix | 6 |
| Fundamental theorem | `dim V = dim null T + dim range T` on 100 random maps | 7 |
| Nilpotency (limit case) | `Dⁿ ≠ 0` but `Dⁿ⁺¹ = 0`; index `n+1` | 8 |

## How to use this directory

`vector_spaces.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
a working version for when you are stuck, or to compare afterwards. The exact-arithmetic
helpers (`_matmul`, `_rref`, `_inverse`, `apply`, ...) are left implemented: they are the
prerequisite node, not this one.

```bash
cd math/linalg/01-vector-spaces
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py 4 6    # a range
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`. Every
reference value is computed in `check.py` itself, with its own exact rational arithmetic,
so the checker never asks your code what the right answer is.

## The checker was itself tested

Seven classic bugs were planted in copies of the solutions, and each one has to be caught
by its check (`_build/mutations.py`):

| Planted bug | Caught by |
|---|---|
| change of basis applied as `S A S⁻¹` instead of `S⁻¹ A S` | step 4 |
| change of basis that cancels to `A S S⁻¹ = A` | step 4 |
| differentiation off by one: uses the output power `k−1` as the factor | step 6 |
| rank-nullity reports the number of rows as `dim range` | step 7 |
| nilpotency searched only up to power `n`, missing `Dⁿ⁺¹ = 0` | step 8 |
| null-space free variable given the wrong sign | step 2 |
| range basis taken from the reduced frame instead of the original columns | step 3 |

Run it yourself: `python3 .claude/skills/graded-module/scripts/mutate.py math/linalg/01-vector-spaces math/linalg/01-vector-spaces/_build/mutations.py`
— every line must read `CAUGHT`.

Two of these needed care. The change-of-basis check could pass a wrong order if the random
`A` and `S` commute, so the check asserts that at least one test case has
`S⁻¹ A S ≠ S A S⁻¹`: the test must *be able* to tell the two orders apart. And the
nilpotency check calls `nilpotency_index(D, n+1)` (not `n+2`): searching up to `n+2` would
also find the answer when the code stops one power early, and the mutation would slip
through.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Exact `Fraction` arithmetic, not floats.** Every accept criterion here is an
  equality (`S⁻¹ A S == M`, `rank == n − nullity`, `Dⁿ⁺¹ == 0`); with floats they become
  thresholds a planted bug can hide under. The cost is speed, and no conditioning lesson.
- **A linear map is its matrix in the standard bases, and each basis is passed as the
  columns of a matrix.** Change of basis is then the single product `C⁻¹ A B`. A callable
  map would bury that product inside every test.
- **Gaussian elimination is provided, not graded.** `foundations-01` already built it;
  re-grading it would bury the new lesson (bases, rank-nullity, change of basis).
- **Differentiation is padded to a square map `P_n → P_n`.** The honest `P_n → P_{n−1}`
  derivative is not square, so `Dⁿ⁺¹ = 0` would not be a statement about matrix powers.
  The cost is one convention: the high-degree image is simply zero.
- **Nilpotency is detected by repeated multiplication, not by a characteristic
  polynomial.** It mirrors the definition `Dⁿ⁺¹ = 0` directly and needs no triangular form.

## Questions to answer before reading the solutions

1. The change-of-basis formula `C⁻¹ A B` has the inverse on the **left**. If you multiply
   in the other order you get `S A S⁻¹`, which is also "a change of basis" for a *different*
   convention. What are the two conventions, and for which one is `S` (rather than
   `S⁻¹`) the matrix whose columns are the new basis vectors?
2. `column_space_basis` returns pivot columns of the *original* matrix, not of the RREF.
   Both span an `r`-dimensional space. Give a 2×2 rank-1 example where the RREF pivot
   column is not in the column space at all, and say why row operations are allowed to
   move the columns while preserving their dependencies.
3. `dim V = dim null T + dim range T` is an equality of three numbers. For a random
   `3×5` matrix, which term is which? Why must `dim range ≤ 3` and `dim null ≥ 2`?
4. Differentiation on P_n has `Dⁿ ≠ 0` and `Dⁿ⁺¹ = 0`. What is the single nonzero entry of
   `Dⁿ`, and where does it send `xⁿ`? Why is the nilpotency index always exactly `n+1`
   (the dimension)?
5. Is a nilpotent matrix ever invertible? Use `Dⁿ⁺¹ = 0` with `n+1 ≥ 1` to answer, and say
   what that implies about the diagonal of any triangular form of `D`.

## Limits

- Exact rational arithmetic only: entries must be rational (integers and `Fraction`s).
  Irrational or floating-point data would need a numerical rank with a tolerance, which is
  `linalg-04-qr-least-squares`.
- Dense matrices. `_rref` is the naive O(n³) elimination, fine for the lesson, not for
  large sparse maps.
- The differentiation example is limited to the monomial basis and to `P_n` padded square.
  Change of basis onto other polynomial bases (Legendre, Bernstein) is possible with
  `matrix_of_map` but not built here, and `D` in a non-monomial basis is a separate
  exercise (the matrix stops being strictly triangular).
- No eigenvalues, no characteristic polynomial, no triangular/Jordan form; the nilpotency
  limit case is decided by powers, not by a normal form. That is `linalg-02-eigenvalues`.

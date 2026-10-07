# Inner product spaces and the spectral theorem

The spectral theorem and its consequences, from scratch. Implements chapters 6 and 7 of
Sheldon Axler, *Linear Algebra Done Right* (the argument is restated here, never copied).

**Status: not built.** `spectral.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`spectral.py`, six graded functions; the small dense arithmetic helpers and the catalogue
of test matrices are given.

| Function | What it does |
|---|---|
| `jacobi_eigh(A)` | eigenvalues (ascending) and an orthonormal eigenbasis `Q`, so `A = Q diag(evals) Q^T` |
| `orthonormal_eigenbasis(A, tol)` | the same, but re-orthonormalising each eigenspace (matters when an eigenvalue repeats) |
| `is_orthogonal(Q, tol)` | are the columns orthonormal (`Q^T Q = I`) |
| `positive_sqrt(A, tol)` | the symmetric PSD square root of a PSD matrix; raise `ValueError` for a negative eigenvalue |
| `polar_decomposition(A, tol)` | `A = Q P` with `Q` orthogonal and `P` symmetric PSD |
| `svd(A)` | `A = U diag(S) V^T` from the spectral theorem applied to `A^T A` |

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`spectral.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | `jacobi_eigh` on a 2x2 and a 3x3 symmetric matrix: ascending eigenvalues, `Q` orthonormal, `A = Q diag(evals) Q^T` |
| 2 | `orthonormal_eigenbasis` returns an orthonormal basis to 1e-10, and `is_orthogonal` accepts the identity and rejects a matrix whose columns are not orthonormal |
| 3 | the limit case: a rotated `diag(2,1,1)` whose eigenvalue `1` has multiplicity 2, checked by the eigenvalue multiset and `Q^T Q = I`, **never** against a fixed basis |
| 4 | `positive_sqrt`: symmetric, squares back to `A`, PSD, and a negative eigenvalue raises `ValueError` |
| 5 | `polar_decomposition`: `Q` orthogonal, `P` symmetric PSD, `A = Q P`, on a symmetric and a non-symmetric matrix |
| 6 | `svd`: singular values descending, `U` and `V` orthonormal, reconstruction `A = U diag(S) V^T`, and the rank-deficient case where a zero singular value is completed |

## Design decisions

- **Cyclic Jacobi, not shifted QR, for symmetric matrices.** The rotation engine keeps the
  accumulated `Q` orthonormal by construction, which is exactly the accept criterion
  (`Q^T Q = I` to 1e-10). A QR path would need its own symmetric shift and deflation.
- **Never fix an eigenbasis.** At a repeated eigenvalue the eigenspace is a subspace, not a
  list of vectors; the checker validates the invariant (`Q^T Q = I`, `A = Q diag Q^T`, the
  eigenvalue multiset) instead of comparing to an answer key.
- **The SVD from `A^T A`.** The spectral theorem gives `V` and the squared singular values;
  the left vectors are `A v / s`, and a zero singular value is completed to an orthonormal
  basis rather than divided by zero.
- **`positive_sqrt` clamps round-off, rejects a real negative.** An eigenvalue at `-1e-16`
  is round-off and becomes zero; an eigenvalue at `-1e-2` is a property of the matrix and
  raises.

## Limit case

A symmetric matrix with a repeated eigenvalue has a non-unique eigenbasis. The step-3
matrix is `R diag(2,1,1) R^T` for a rotation `R` that mixes the distinct eigenvalue `2`
with one of the repeated `1`s, so it is genuinely off-diagonal and a fixed expected basis
would be wrong; the check only demands an orthonormal basis of each eigenspace. (Rotating
`diag(1,1,2)` instead would be a no-op: the rotation would act inside the eigenspace of
the repeated eigenvalue.) The rank-deficient SVD is the same idea for `U`: it is only
unique up to the orthogonal group acting on the zero-singular-value subspace.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/linalg/03-spectral-theorem math/linalg/03-spectral-theorem/_build/mutations.py`).

| Bug | Step |
|---|---|
| `jacobi_eigh` accumulates the rotation into `Q` with the wrong sign | 1 |
| `is_orthogonal` never rejects a non-orthonormal matrix | 2 |
| `positive_sqrt` never rejects a negative eigenvalue | 4 |
| `polar_decomposition` uses `Q = U` instead of `Q = U V^T` | 5 |
| `svd` returns the singular values in ascending order | 6 |
| `svd` does not complete the basis for a zero singular value | 6 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why is the eigenbasis of a matrix with a repeated eigenvalue not unique, and why would a
   checker that compares to a fixed basis be wrong even for a correct solution?
2. `jacobi_eigh` applies each rotation to `A` and to `Q`. Which of the two makes `Q`
   orthonormal, and which drives the off-diagonal entries to zero?
3. In the SVD, why is `A^T A` the right matrix to hand to the spectral theorem? What does
   its null space give you?
4. `polar_decomposition` uses `Q = U V^T` and `P = V diag(S) V^T`. Why is `Q = U` wrong
   even though `U` is orthogonal?
5. A rank-deficient `A` has a zero singular value. Why can the left singular vector not be
   `A v / 0`, and what does the checker verify instead of that vector?

## Limits

- The SVD is built from `A^T A`, which squares the condition number: a singular value at
  `1e-9` is computed as the square root of an eigenvalue at `1e-18` and loses relative
  precision. A bidiagonal SVD would avoid this and is out of scope.
- `svd` here expects a tall or square `A` (`m >= n`); the wide case is not graded.
- The grouping tolerance in `orthonormal_eigenbasis` is a floating-point call: two genuinely
  distinct eigenvalues closer than `tol` would be treated as one. At `tol = 1e-10` this is
  far below the separation any matrix in this module needs.

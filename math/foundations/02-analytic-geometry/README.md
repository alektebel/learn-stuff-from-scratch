# Analytic Geometry From Scratch

Inner products, orthogonal projections, Gram-Schmidt and rotations, in pure Python
(standard library only), built one mechanism at a time.

Second node of the [skill tree](../../../skill-tree/README.md), in the `foundations`
track: *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 3. It
follows [01-linear-algebra](../01-linear-algebra/), whose Gaussian elimination is the one
helper this module reuses (`_solve`, left implemented for that reason).

The idea the chapter turns on: **geometry is whatever the inner product says it is.**
Give the same vectors a different symmetric positive definite matrix `A`, and distances,
angles and projections all change together.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Inner product | `⟨u,v⟩_A = uᵀAv`, admitted only for SPD `A` | `geometry.py` | 1-2 |
| Norm and angle | induced by `A`; `arccos` of the normalised inner product | `geometry.py` | 2 |
| Projection matrix | `P = B(BᵀB)⁻¹Bᵀ`, idempotent and symmetric | `geometry.py` | 3-4 |
| Affine projection | `x0 + P(x − x0)` onto `x0 + span(B)` | `geometry.py` | 5 |
| Gram-Schmidt | classical and modified orthonormalisation | `geometry.py` | 6-7 |
| Rotations | 2-D and 3-D (Rodrigues): orthogonal, determinant +1 | `geometry.py` | 8-9 |
| Conditioning | why modified Gram-Schmidt beats classical on close vectors | `geometry.py` | 10 |

## How to use this directory

`geometry.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
a working version for when you are stuck, or to compare afterwards.

```bash
cd math/foundations/02-analytic-geometry
python3 check.py        # what to build next; stops at the first gap
python3 check.py 5      # one step
python3 check.py 5 7    # a range
python3 check.py --all  # everything
```

`check.py` runs 10 checks against **your** code and never imports `solutions/`. Every
reference value is computed in `check.py` itself, in closed form or by an independent
formula, so the checker never asks your code what the right answer is.

**The checker was itself tested.** Eight classic bugs were planted in copies of the
solutions, and each one has to be caught by its check:

| Planted bug | Caught by |
|---|---|
| the inner product ignores `A` (ordinary dot product) | step 2 |
| a non-SPD matrix accepted as an inner product | step 1 |
| projection without the `(BᵀB)⁻¹` factor (`B Bᵀ`) | step 3 |
| affine projection that ignores the offset `x0` | step 5 |
| Gram-Schmidt that does not normalise | step 6 |
| "modified" Gram-Schmidt that is really classical | step 10 |
| 2-D rotation with the wrong sign (determinant −1) | step 8 |
| 3-D Rodrigues without the `sin` term (not a rotation) | step 9 |

One of them initially slipped through: step 5 used a test point `x0` that happened to lie
*in* the subspace, so ignoring the offset changed nothing. The check now takes `x0` off
the plane (`x0 · (b₀ × b₁) ≠ 0`).

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Everything takes the SPD matrix `A`** (no separate Euclidean path). The ordinary dot
  product is the case `A = I`; a second code path would hide that and double the surface.
- **Projection via `B(BᵀB)⁻¹Bᵀ`, not via an orthonormal basis.** It needs only `_solve`
  and makes the dependence on `BᵀB` explicit; `Q Qᵀ` would quietly require Gram-Schmidt
  to be correct first.
- **Both classical and modified Gram-Schmidt**, selected by a flag. They are the same
  function on well-conditioned input and measurably different on nearly dependent vectors.
- **SPD test by Cholesky**, not by leading principal minors: same criterion (Sylvester),
  one pass, and the positive diagonal is exactly the "lengths are `≥ 0`" condition.

## Questions to answer before reading the solutions

1. `angle` needs `A` to be positive definite, but the formula `arccos(⟨u,v⟩/(‖u‖‖v‖))`
   still produces a number for an indefinite `A`. What *geometrically* goes wrong? (Find a
   pair of vectors whose "angle" is not real / not in `[0, π]`.)
2. `P = B(BᵀB)⁻¹Bᵀ` needs `BᵀB` invertible. What does that say about the columns of `B`,
   and what should happen if they are dependent? Where in your code is that decided?
3. On the Läuchli matrix, classical Gram-Schmidt loses orthogonality (`≈0.5`) while
   modified keeps it (`≈1e-8`). Both compute the *same* mathematical projection. Where
   exactly does classical lose the digits, and why does the residual norm `≈ eps` make the
   relative error huge?
4. A rotation is an orthogonal matrix with determinant `+1`. Why is `det = −1` a
   reflection, and what does `det = +1` alone *not* guarantee (think of the axis in 3-D)?
5. Affine projection is "project the difference, add the offset back". What goes wrong if
   you project `x` first and then subtract the projected `x0`? (Try it on the step-5 case.)

## Limits

- Floating point, not exact arithmetic. Orthonormality is asserted to `1e-10`; the
  classical/modified gap is a *conditioning* property, so it is asserted as a ratio, not
  an absolute threshold.
- Dense vectors and matrices. A large sparse basis would use a QR factorisation instead of
  the normal equations (which square the condition number); that is
  `linalg-04-qr-least-squares`.
- `_solve` raises `ValueError` on a singular system; the module does not attempt a
  least-squares projection onto a dependent basis.
- No quaternions and no arbitrary-dimension rotations (only the 2-D and 3-D cases the
  chapter builds). The general `SO(n)` construction is out of scope.

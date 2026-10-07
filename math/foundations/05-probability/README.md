# Probability and Distributions From Scratch

Multivariate Gaussians and the change-of-variables formula, in pure Python (standard
library only), built one mechanism at a time.

Fifth node of the [skill tree](../../../skill-tree/README.md), in the `foundations`
track: *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 6
("Probability and Distributions"). It follows
[04-vector-calculus](../04-vector-calculus/); the only arithmetic support it reuses is a
triangular solve (the Cholesky of [03-matrix-decompositions](../03-matrix-decompositions/)),
left implemented in the template.

The idea the chapter turns on: **the Gaussian is the distribution whose algebra is
linear.** A linear map of a Gaussian is Gaussian, a product of Gaussians is Gaussian, and
its marginals and conditionals are Gaussian. The density is the one place where this
linearity becomes a numerical trap: the textbook formula needs `Σ⁻¹` and `det Σ`, and
both are exactly the quantities that fail on a nearly singular covariance.

## What you build

| Concept | Mechanism | Checks |
|---|---|---|
| Cholesky factor | `Σ = L Lᵀ`; one pass decides SPD and factors | 1 |
| Log density | `−½(n log 2π + 2Σ log Lᵢᵢ + ‖L⁻¹(x−μ)‖²)` | 2 |
| Normalisation | the density integrates to 1 (quadrature) | 3 |
| Limit: near-singular `Σ` | `det Σ` underflows; the Cholesky pivots do not | 4 |
| Sampling | `x = μ + L z`, `z ~ N(0, I)` | 5 |
| Linear map | `Y = AX + b` ⟹ `(Aμ + b, AΣAᵀ)` | 6 |
| Product | precision form `(Σ₁⁻¹+Σ₂⁻¹)⁻¹` | 7 |
| Marginal | the matching blocks of `μ` and `Σ` | 8 |
| Conditional | Schur complement; matches regression on samples | 9 |
| Change of variables | `p_Y(y) = p_X(g⁻¹(y))·|(g⁻¹)′(y)|` | 10 |

## How to use this directory

`gaussians.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
a working version for when you are stuck, or to compare afterwards.

```bash
cd math/foundations/05-probability
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py 4 6    # a range
python3 check.py --all  # everything
```

`check.py` runs 10 checks against **your** code and never imports `solutions/`. Every
reference value is computed in `check.py` itself, independently: exact rational
(`Fraction`) arithmetic for the density oracle, the checker's own Gaussian elimination
for the regression and Schur references, and numerical quadrature for the integrals. The
checker never asks your code what the right answer is.

## The checker was itself tested

Nine classic bugs were planted in copies of the solutions, and each one has to be caught
by its check:

| Planted bug | Caught by |
|---|---|
| Cholesky accepts a non-SPD matrix | step 1 |
| density without its normalising constant | step 3 |
| log density through `Σ⁻¹` and `det Σ` (underflows) | step 4 |
| sampling ignores the covariance | step 5 |
| linear map covariance loses the transpose (`AΣ`, not `AΣAᵀ`) | step 6 |
| product adds covariances instead of precisions | step 7 |
| marginal returns the whole covariance | step 8 |
| conditional covariance omits the Schur-complement subtraction | step 9 |
| change of variables drops the Jacobian | step 10 |

The first version of step 4 used a 2×2 Toeplitz covariance `[[1, 1−δ],[1−δ,1]]`. That
matrix cannot separate the two methods: `det` is tiny but still a normal float, and the
Cholesky pivot `L₂₂ = √(1−(1−δ)²)` is rounded the same way as `det`, so the naive
inverse+det mutation survived. The check now uses a block covariance whose determinant
(`≈ 2e-328`) underflows to `0.0`, where `log det` through the pivots is the only route
that stays finite.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Cholesky, not inverse+determinant**, for the log density. Forming `Σ⁻¹` and `det Σ`
  costs `O(n³)` and loses the small eigenvalues; one factorisation and a forward solve
  keeps them, and `log det Σ = 2 Σ log Lᵢᵢ` never builds the product.
- **The caller passes a `random.Random`** to the sampler; the standard library supplies
  `rng.gauss`, so the lesson is the map `x = μ + Lz`, not a hand-rolled scalar normal,
  and the Monte-Carlo checks are reproducible.
- **Index lists, not a fixed 2-block API**, for marginals and conditionals. The Schur
  complement is the same operation on any subset of coordinates.
- **The product in precision form.** Precisions add, so `P = Σ₁⁻¹ + Σ₂⁻¹`; the covariance
  form would need three inversions and hide that the operation is linear.

## Questions to answer before reading the solutions

1. `Σ⁻¹` and the Cholesky factor both cost `O(n³)`. Why does the log density still prefer
   the factor, even when you already have the inverse? (What does a product of `n`
   eigenvalues do to a small one?)
2. The product formula `(Σ₁⁻¹ + Σ₂⁻¹)⁻¹` looks like it should be *larger* than either
   factor. Show it is smaller in the Loewner order, and say what that means when both
   Gaussians describe the same measurement.
3. Conditioning subtracts `Σ_ab Σ_bb⁻¹ Σ_ba` from `Σ_aa`. Why can the result never have a
   larger variance than the marginal, and what does that imply about
   `Σ_ab Σ_bb⁻¹ Σ_ba`?
4. In the change-of-variables formula, why is the absolute value of the Jacobian needed,
   and what goes wrong for a *non-monotone* `g` when the formula is applied piecewise?
5. Sampling uses `x = μ + Lz` with `L` lower-triangular. What changes if you use the
   upper factor `Lᵀ` instead? (Is `Lᵀz` distributed as `Lz` when `z` is standard normal?)

## Limits

- Floating point, not exact arithmetic. Monte-Carlo tolerances are computed from the CLT
  (`6` standard errors) with a fixed seed, not guessed.
- Dense, small covariance matrices; the explicit `O(n³)` factorisation is fine up to a few
  hundred dimensions. Large sparse covariances would use a sparse factorisation.
- One-dimensional change of variables for a monotone map. The multivariate version adds a
  Jacobian determinant and is the route to normalising flows
  (`prml`-track material); here the 1-D case is enough to show that dropping the Jacobian
  stops the result being a density.

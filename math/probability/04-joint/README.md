# Joint Distributions From Scratch

Joint, marginal and conditional pmfs; covariance and correlation; the
multinomial and the bivariate normal, in pure Python (standard library only).
There is no `numpy`: the bivariate normal density is a closed-form 2x2 quadratic
form, its sampler is a hand-written 2x2 Cholesky factor, and every reference
value the checker needs is recomputed from the definition.

Node `probability-04-joint` of the [skill tree](../../../skill-tree/README.md),
in the `probability` track, after `probability-03-continuous`. Source: Blitzstein
& Hwang, *Introduction to Probability* (2nd ed.), **chapter 7** (joint
distributions; covariance and correlation; the multinomial and bivariate normal).
The ideas are restated here, not copied.

The idea the node turns on: **a joint distribution carries more than its two
marginals, and correlation captures only the linear part of the dependence.**
The acceptance criterion is statistical -- sample covariance matrices must
converge to the analytic covariance -- and the limit case is where the natural
reading of that criterion fails: `X` symmetric and `Y = X^2` are perfectly
dependent yet have covariance exactly zero.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Joint, marginal, conditional | sum one axis; normalise a row by its marginal | `joint.py` | 1 |
| Covariance and correlation | `(1/n) Σ(x-x̄)(y-ȳ)`; divide by `sd x · sd y` | `joint.py` | 2 |
| Multinomial | `n!/∏cᵢ! · ∏pᵢ^{cᵢ}`; cumulative-walk sampler | `joint.py` | 3 |
| Bivariate normal | quadratic form with the cross term; Cholesky `L Lᵀ = Σ` | `joint.py` | 4 |
| Sample covariance | unbiased `1/(n-1)` estimator, 2x2 matrix | `joint.py` | 4 |
| Uncorrelated ≠ independent (limit case) | `Cov(X, X²) = 0`, conditional degenerate | `joint.py` | 5 |

## How to use this directory

`joint.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. The
Box-Muller helper `_standard_normal_pair` and `demo()` stay implemented.
`solutions/` holds a working version for when you are stuck, or to compare
afterwards.

```bash
cd math/probability/04-joint
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`.
Its reference values are independent: marginals and conditionals by summing the
joint directly, covariance and correlation from the definition, the multinomial
pmf from its own factorial ratio, the bivariate normal density from its own
quadratic form, and the sample covariance from the `1/(n-1)` definition. The
node's acceptance rule is enforced both at large `n` (convergence within 0.05 of
the analytic matrix) and exactly at small `n` (a hand sample whose `1/(n-1)`
value differs from the `1/n` one by a factor `3/2`).

## Mutation table

The checker was itself tested: four classic bugs were planted in copies of the
solution -- and one in the checker -- and each must be caught by the step named.
Run `python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| correlation uses the unnormalised covariance | step 2 |
| conditional uses the wrong denominator (not `P(X = x)`) | step 1 |
| bivariate normal drops the correlation cross term | step 4 |
| sample covariance uses `1/n` instead of `1/(n-1)` | step 4 |
| the limit-case check infers independence from zero covariance | step 5 |

Step 4 catches the dropped cross term in the direction that matters: a density
without `-2 cxy dx dy` is still normal and still integrates to 1, so the
integration test alone would miss it -- the grid's cross moment `E[XY] - μx μy`
does not. The last row mutates `check.py`: the assertion that decides dependence
from the conditional rather than from the covariance must fire when the checker
is weakened.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In
short:

- **`axis` names the coordinate to KEEP, and the return type follows the input.**
  numpy's `sum(axis=k)` removes axis `k`; a marginal is the distribution of one
  coordinate, so this keeps what it names. A dict of `(x, y)` pairs comes back
  as a dict; a matrix comes back as a list, so a joint over non-numeric labels
  works without an index. Cost: two code paths.
- **Population covariance `(1/n)` and sample covariance `1/(n-1)` are separate
  functions.** The joint-distribution covariance is an expectation over equally
  weighted outcomes, so it uses `1/n`; an i.i.d. sample estimate is unbiased at
  `1/(n-1)`. Cost: two names; payoff: each call site states its denominator.
- **Correlation divides by `sd x · sd y`, never returns the covariance.** The
  correlation is unit-free, so a perfect line reads exactly `+1`/`-1`; the raw
  covariance only looks like a correlation on standardised data. Zero variance
  is rejected, not reported as 0.
- **The multinomial coefficient is built in exact integers, then scaled.** The
  factorial ratio `n!/∏cᵢ!` overflows nothing and stays exact, so a single
  count vector sums to exactly 1; `lgamma` in logs would round it. Cost:
  big-integer arithmetic for large `n`.
- **The multinomial sampler walks the cumulative pmf.** It reuses only the
  uniform stream and is O(k) per draw; the conditionally-binomial construction
  is exact too but needs a binomial sampler. Cost: O(trials · k) per vector.
- **The bivariate normal uses a closed-form 2x2 quadratic form and Cholesky.**
  The cross term `-2 cxy dx dy` is what couples the coordinates and is what the
  cross-moment check probes; the triangular factor makes `y = μy + l21 z1 + l22 z2`
  and the convergence to `L Lᵀ = Σ` visible. Cost: dimension is baked in at 2,
  exactly the node's scope.
- **Dependence is read from the conditional, not the covariance.** The limit case
  makes this concrete: `Y = X²` is a deterministic function of a symmetric `X`,
  so `P(Y | X = x)` is a point mass while `marginal(Y)` spreads `1/2`–`1/2`, even
  though `Cov(X, Y) = 0`. Cost: none; it is the point of the node.

## Questions to answer before reading the solutions

1. `marginal(joint, axis)` keeps the axis it is given. Why is summing the *other*
   axis the definition of the marginal, and what does `axis` mean in numpy's
   `sum(axis=k)` by contrast?
2. `conditional` divides a joint row by `P(X = x)`. Show that dividing by 1 makes
   the row sum to `P(X = x)`, and dividing by `len(row)` makes its entries average
   to 1. Which check catches each?
3. Covariance is `(1/n) Σ(x-x̄)(y-ȳ)` and sample covariance is `1/(n-1)`. At
   `n = 3` the second is `3/2` times the first. Why is the `1/(n-1)` estimator
   unbiased, and why would a large-`n` convergence test alone not notice the slip?
4. The bivariate density without its `-2 cxy dx dy` term is still a valid normal
   density and still integrates to 1. Compute its covariance matrix and explain
   why the grid's cross moment is the test that separates it from the correct one.
5. `X` symmetric on `{-2,-1,1,2}` and `Y = X²`. Compute `E[XY]`, `Cov(X, Y)` and
   the correlation by hand. Is `Y` independent of `X`? What single quantity
   distinguishes dependence from zero correlation, and which function computes it?
6. In the Cholesky factor `L = [[√vx, 0], [cxy/√vx, √(vy - cxy²/vx)]]`, the lower
   entry is `cxy/√vx`. Why does setting it to 0 give an uncorrelated sample with
   the right marginal variances, and how does the acceptance test detect it?

## Limits

- Dimension 2 only. The ziggurat/Box-Muller path is scalar; the density and the
  Cholesky are the closed 2x2 formulas, not a general linear algebra library.
- Only the multinomial and the bivariate normal among joint distributions. The
  Dirichlet, the multivariate normal of dimension > 2, and copulas are later
  nodes.
- `covariance` and `correlation` take equally weighted paired data, not a joint
  pmf with weights; a discrete joint is expanded into its outcome list for them.
- The bivariate-normal integration grid is midpoint rule on `[-8,8] x [-10,10]`
  with 200 steps per side; the tolerances (1e-3 on the mass, 0.01 on the cross
  moment) are set by that truncation, not by the formulas.
- The sample-covariance convergence test is seeded and compares within 0.05 at
  `n = 200000`; the small-`n` exact case is what pins the `1/(n-1)` denominator.

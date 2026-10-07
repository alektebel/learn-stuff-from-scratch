# Limits and Inequalities From Scratch

Change of variables and convolutions; the Markov, Chebyshev and Chernoff bounds
against exact tails; and the law of large numbers and the central limit theorem
by simulation, in pure Python (standard library only). There is no `numpy`: the
transformed densities are closed forms, the convolutions are exact with
`fractions.Fraction`, and every reference value the checker needs is recomputed
from the definition.

Node `probability-05-limits-inequalities` of the
[skill tree](../../../skill-tree/README.md), in the `probability` track, after
`probability-04-joint`. Sources: Blitzstein & Hwang, *Introduction to
Probability* (2nd ed.), **chapter 8** (change of variables, convolution) and
**chapter 10** (inequalities and limit theorems). The ideas are restated here,
never copied.

The idea the node turns on: **a bound is only a bound if it sits above the tail
it estimates, and the central limit theorem converges at a rate you can watch.**
The acceptance rule is pointwise -- every bound at or above the exact tail,
with Chernoff strictly tighter than Markov -- and the CLT error is measured as
the Kolmogorov-Smirnov distance to the standard normal, which falls like
`1/sqrt(n)` (the Berry-Esseen order). The limit case is where the whole
enterprise fails: for the **Cauchy distribution** the mean is undefined and the
sample mean does not converge at all, so no `1/sqrt(n)` shrinkage appears.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Change of variables | `f_Y(y) = f_X(g⁻¹(y)) / |g'(g⁻¹(y))|` | `limits.py` | 1 |
| Convolution | `r[k] = Σᵢ p[i] q[k−i]`, exact with `Fraction` | `limits.py` | 2 |
| Markov / Chebyshev / Chernoff | `E[X]/t`; `Var/t²`; `inf_{s>0} e^{−st} M(s)` on a grid | `limits.py` | 3 |
| Exact tails | binomial sum with `Fraction`; exponential `e^{−rate·t}` | `limits.py` | 3 |
| Law of large numbers | running sample means settle on `E[X]` | `limits.py` | 4 |
| Central limit theorem | KS distance to `N(0,1)`, decaying like `1/√n` | `limits.py` | 4 |
| Cauchy (limit case) | sample mean does **not** concentrate | `limits.py` | 5 |

## How to use this directory

`limits.py` is a **template**: each graded function keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. The
standard-normal CDF helper, the IQR helper, the demo-only sampling helper, and
`demo()` stay implemented. `solutions/` holds a working version for when you are
stuck, or to compare afterwards.

```bash
cd math/probability/05-limits-inequalities
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`.
Its reference values are independent: the transformed density from its analytic
closed form, the dice convolution from the hand count `(k−1)/36` as exact
`Fraction`s, the binomial tail from its own factorial ratio, and the Cauchy and
exponential spreads from the checker's own sampler. Step 3 tests the bounds in
the direction that matters -- `bound ≥ exact tail` point by point, and
`Chernoff < Markov` -- and step 4 pins the Berry-Esseen order by checking that
the KS error at `4n` is about half the error at `n`. Step 5 is the limit case:
the Cauchy sample-mean spread does not shrink, while an exponential control's
does.

## Mutation table

The checker was itself tested: five classic bugs were planted in copies of the
solution -- two in the checker -- and each must be caught by the step named. Run
`python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| change of variables drops the `1/|g'|` Jacobian factor | step 1 |
| convolution returns the elementwise product of the pmfs | step 2 |
| Markov bound replaced by the exact tail (not a bound above it) | step 3 |
| CLT standardisation divides by the variance, not the standard deviation | step 4 |
| the Cauchy limit-case check assumes the mean converges | step 5 |

Step 3 catches the omitted Markov bound through the strict `Chernoff < Markov`
comparison: once Markov is the exact tail, Chernoff -- itself at or above that
tail -- cannot be strictly below it. The last row mutates `check.py`: the guard
that decides non-convergence from the measured spread must fire when the checker
is weakened to assume convergence.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In
short:

- **Change of variables takes `g⁻¹` and `g'` as callables.** Symbolic inversion
  and differentiation would need a computer-algebra layer; the closed form the
  node asks for stays visible, and the caller is responsible for monotonicity.
  Cost: the caller supplies the two pieces.
- **Convolution uses sequences indexed by value from 0.** List index arithmetic
  is plain, and `p[i] q[j]` is exact for `Fraction` inputs; a dict would handle
  negative or gapped support the node does not need. Cost: a shifted index for
  the dice case.
- **All three bounds cap at 1.** A probability bound above 1 is valid but
  useless; the cap keeps the comparison with Chernoff meaningful. Cost: for `t`
  below the mean the bound is flat at 1, so the node always tests `t` above it.
- **Chernoff minimises on a geometric grid, distribution-free.** Solving
  `M'/M = t` has no closed form for a general mgf; a grid ratio of 1.05 over
  `(1e−6, 50)` is always an upper bound (it is a tilted probability), and an
  `OverflowError` at large `s` is skipped. Cost: the grid minimum can exceed the
  true infimum by a small factor.
- **The binomial tail is exact with `Fraction`.** The acceptance rule compares
  bounds to the *exact* tail; a float tail could be rounded down and make a
  bound appear to beat the truth in the far tail. Cost: big-integer rationals.
- **`lln_sample_means` averages running means over replications.** One path is
  too noisy to show or check convergence; averaging divides its variance by the
  number of replications so the curve settles tightly on `E[X]`. Cost:
  `n · trials` draws and no single realisation.
- **`clt_error` estimates `mu` and `sigma` from the pooled draws and divides by
  `sigma/√n`.** A bare callable cannot name its own parameters, so the plug-in
  estimate is the only route; dividing by the standard deviation (not the
  variance) is what makes the distance a CLT distance. Cost: a `1/√trials`
  empirical floor, which is why `trials` is large and the check compares the
  ratio between `n` and `4n`.
- **`cauchy_sample_means` uses the inverse CDF `tan(π(u−½))`.** One `tan` on the
  shared uniform stream, and the heavy tails are explicit; the ratio-of-normals
  construction would need the Box-Muller pair. Cost: `rng.random()` near 0 or 1
  yields a very large magnitude -- which is the heavy tail the limit case needs.

## Questions to answer before reading the solutions

1. For `Y = g(X)` with `g` strictly decreasing, the density carries `|g'|`. Write
   `f_Y` for `X ~ Exp(1)`, `Y = 1/X`, and explain what sign a missing absolute
   value produces and why that is impossible.
2. The convolution of two pmfs is `r[k] = Σᵢ p[i] q[k−i]`. Why is the elementwise
   product `p[k] q[k]` a different object, and what does each represent
   probabilistically?
3. Markov gives `E[X]/t`, Chebyshev `Var/t²`, Chernoff `inf_s e^{−st} M(s)`.
   For `X ~ Binomial(100, 3/10)` and `k = 45`, compute all three by hand (use
   `s* = log(k(1−p)/((n−k)p))` for Chernoff) and compare with the exact tail.
   Why must each be at least the tail?
4. The standard error of a sample mean is `sigma / sqrt(n)`, not `sigma² / √n`.
   If you divide by the variance, what happens to the standardised sample mean's
   scale, and which check catches it?
5. The mean of `n` i.i.d. standard Cauchy draws is again standard Cauchy. Using
   its characteristic function `e^{−|t|}`, prove that, and explain why the IQR of
   the sample mean therefore does not fall with `n`.
6. `clt_error` estimates `mu` and `sigma` from the pooled draws. Why does that
   leave the Berry-Esseen decay intact, and what is the order of the residual
   error introduced by the estimation?

## Limits

- The bounds are demonstrated on the binomial and the exponential only; the
  Chernoff grid is generic but not adaptive, and its minimum can exceed the true
  infimum by a small factor.
- `convolution` handles integer support starting at 0 with no gaps; negative or
  sparse support would need dicts.
- `clt_error` compares an empirical CDF to `Phi`, so it carries a `1/√trials`
  floor; the `1/√n` order is checked as a ratio between `n` and `4n`, not as an
  absolute constant.
- The Cauchy limit case is checked by a robust spread (IQR), not by a
  convergence test for an undefined mean; a finite-variance exponential control
  is run alongside to show the metric can detect concentration.
- Only these named inequalities and limit theorems. The large-deviation
  principle, the multivariate CLT and Stein's method are later nodes.

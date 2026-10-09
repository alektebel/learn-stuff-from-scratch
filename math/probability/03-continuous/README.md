# Continuous Random Variables From Scratch

The Uniform, Normal and Exponential distributions, inverse-CDF sampling
(universality of the uniform), memorylessness, and the Kolmogorov-Smirnov
goodness-of-fit test, in pure Python (standard library only). There is no
`numpy`: the normal quantile is a bisection on `math.erf`, and every reference
value the checker needs is recomputed from `math.erf` and `math.exp`.

Node `probability-03-continuous` of the [skill tree](../../../skill-tree/README.md),
in the `probability` track, after `probability-02-random-variables` and
`foundations-04-vector-calculus`. Source: Blitzstein & Hwang, *Introduction to
Probability* (2nd ed.), **chapter 5** (continuous random variables and their
distributions). The ideas are restated here, not copied.

The idea the node turns on: **a continuous distribution is its CDF, and the
inverse CDF turns one Uniform stream into any distribution.** The acceptance
criterion is statistical -- inverse-CDF samples must pass a KS test against the
target -- and the limit case is where that breaks: for an unbounded tail, float
precision near `u = 1` truncates the support.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Uniform, Exponential quantiles | invert `F`; `F⁻¹(u) = -ln(1-u)/rate` | `continuous.py` | 1 |
| Normal quantile | bisection on `Φ(x) = ½(1+erf(x/√2))` | `continuous.py` | 2 |
| Inverse-CDF sampling | `X = ppf(U)`, `U = rng.random()` | `continuous.py` | 3 |
| KS statistic | two-sided `D`, both ECDF limits | `continuous.py` | 4 |
| KS p-value | `Q(d√n)`, full alternating series | `continuous.py` | 5 |
| Memorylessness | gap 0 for Exponential, nonzero when shifted | `continuous.py` | 6 |
| Tail truncation (limit case) | `u < 1` caps the quantile, tail mass lost | `continuous.py` | 7 |

## How to use this directory

`continuous.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. The
survival-function helpers and `demo()` stay implemented. `solutions/` holds a
working version for when you are stuck, or to compare afterwards.

```bash
cd math/probability/03-continuous
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 7 checks against **your** code and never imports `solutions/`.
Its reference values are independent: `Φ` from `math.erf`, the exponential
survival from `math.exp`, the KS statistic by counting the empirical CDF just
left of and just right of every order statistic, and the p-value from its own
alternating series. The node's acceptance rule is enforced in both directions:
the correct sampler must pass, and a mis-scaled sampler must fail the same test.

## Mutation table

The checker was itself tested: six classic bugs were planted in copies of the
solution and each must be caught by the step named. Run
`python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| Exponential `ppf` uses `-ln(u)` instead of `-ln(1-u)` | step 1 |
| Normal `ppf` returns the CDF `Φ(x)`, not its inverse | step 2 |
| KS statistic uses `i/n` on both sides (drops the `(i-1)/n` left limit) | step 4 |
| KS p-value truncated to its first term (exceeds 1) | step 5 |
| memorylessness asserted on a shifted variable | step 6 |
| tail truncation hides the missing (infinite) quantile | step 7 |

Steps 3 and 4 each check the statistic from a different side: step 3 runs the
real KS test on real samples, step 4 compares `D` to a brute-force supremum of
`|F_n - F|` on a deliberately left-limit-dominated sample. Step 5 pins both the
value of `Q` and the fact that a p-value cannot exceed 1.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In
short:

- **Normal quantile by bisection on `math.erf`, not a rational approximation.**
  A wrong constant in an approximation is indistinguishable from a wrong method;
  bisection makes each step an honest evaluation of `Φ` and is accurate to
  ~1e-11. Cost: ~40 `erf` calls per quantile.
- **One inverse-CDF sampler, not per-distribution algorithms.** `X = ppf(U)`
  reuses the stream, preserves order statistics, and states the node's
  universality of the uniform. Cost: it needs a closed-form quantile, hence the
  bisection for the Normal.
- **The KS statistic keeps both ECDF limits,** `max(i/n - F, F - (i-1)/n)`.
  Using `i/n` on both sides forgets the left limit and shrinks `D`. Cost: one
  extra term; the payoff is that a mis-specified CDF cannot hide below a step.
- **The whole alternating series for the p-value, not its first term.**
  `2e^{-2λ²}` exceeds 1 for `λ <~ 0.6`, where `Q` is near 1. Cost: a few hundred
  `exp` calls.
- **Report the missing tail quantile as `+inf`.** `rng.random() < 1` caps the
  quantile at `u = 1 - 2⁻⁵³`; the piece of the support above it has mass `2⁻⁵³`
  but infinite quantile extent. Cost: the honest answer is not a single number.

## Questions to answer before reading the solutions

1. The identity `X = F⁻¹(U)` with `U ~ Uniform(0, 1)` is called universality of
   the uniform. Why does it need `F` to be continuous (or at least to have an
   inverse), and what goes wrong at the jumps of a discrete CDF?
2. `uniform_ppf` is the identity. So for the KS test, is the statistic invariant
   under a strictly increasing transformation of the data? Check with the
   uniform and exponential demos, which use the same `D` formula.
3. In `D = max(i/n - F(xᵢ), F(xᵢ) - (i-1)/n)`, the second term uses `(i-1)/n`.
   Construct a sample where it, and not the first, is the maximum, and say what
   a checker that used `i/n` on both sides would report.
4. The p-value series is alternating with terms of *decreasing* magnitude. Why
   does the first term alone exceed 1 for small `d√n`, and what does the true
   `Q` do there? Where does the large-argument approximation start being safe?
5. `Exponential(rate)` is memoryless: `P(X>s+t|X>s) = P(X>t)`. If you shift it to
   `X = shift + Exponential(rate)`, is the *excess* `X - s` still memoryless, and
   why does `P(X>s+t|X>s) - P(X>t)` nevertheless stop being zero?
6. The tail above the largest reachable quantile has mass `2⁻⁵³ ~ 1e-16`. Why is
   calling that "negligible" wrong for an unbounded tail even though the mass is
   tiny?

## Limits

- Only the three named distributions. The Gamma, Beta and chi-squared quantiles,
  which are built from these, are later nodes.
- The KS p-value is the **asymptotic** `Q(d√n)`, not the exact finite-`n` law
  (which depends on `n` and is a step function). At `n = 50000` the difference is
  far below the tolerances used here.
- The checker's brute-force `KS` reference probes just left and right of each
  order statistic with an `epsilon`, so it agrees with the formula only to
  ~1e-6; the tolerances say so.
- Memorylessness is demonstrated on the Exponential (gap 0) and a shifted
  exponential (gap nonzero). The "shifted variable" counterexample is the
  identity `P(X>s+t|X>s) = P(X>t)`, which a shift breaks; the excess of a shifted
  exponential is still itself memoryless.
- No change of variables or joint distributions -- this node is the univariate
  continuous CDF and its inverse. Joint distributions are `probability-04`.

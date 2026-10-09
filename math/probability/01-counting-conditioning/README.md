# Counting & Conditioning From Scratch

Counting, conditional probability, the law of total probability and Bayes' rule, in pure
Python (standard library only), each probability computed twice — exactly with
`fractions.Fraction`, and independently by seeded Monte-Carlo simulation.

Node `probability-01-counting-conditioning` of the [skill tree](../../../skill-tree/README.md),
in the `probability` track. Sources: Blitzstein & Hwang, *Introduction to Probability*
(2nd ed.), **chapter 1** (counting, the multiplication principle, binomial coefficients)
and **chapter 2** (conditional probability, the law of total probability, Bayes' rule).
The ideas are restated here, not copied.

The idea the node turns on: **a probability is a favourable count divided by a sample
space, under a stated conditioning.** Every planted bug below breaks one of those three
things — the count, the division, or the conditioning — and the simulation catches it
because the simulation builds the sample space the honest way.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Multiplication principle | `P(n, k) = n(n−1)···(n−k+1)` | `probability.py` | 1 |
| Subsets | `C(n, k) = P(n, k)/k!`, exact integers | `probability.py` | 2 |
| Counting + sample space | `P(two pair) = C(13,2)C(4,2)²·44 / C(52,5)` | `probability.py` | 3 |
| Unions without double counting | inclusion-exclusion for "at least one ace" | `probability.py` | 4 |
| Law of total probability | `P(E) = Σ P(Hᵢ)P(E\|Hᵢ)` | `probability.py` | 5 |
| Bayes' rule | posterior over the full evidence denominator | `probability.py` | 6 |
| Base rate | a 95%-sensitive test on a 1% disease | `probability.py` | 7 |
| Conditioning on a reveal | Monty Hall, knowing and unknowing host | `probability.py` | 8–9 |
| Simulation | seeded `random.Random`, one per call | `probability.py` | 3,4,7,8,9 |

## How to use this directory

`probability.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
a working version for when you are stuck, or to compare afterwards.

```bash
cd math/probability/01-counting-conditioning
python3 check.py        # what to build next; stops at the first gap
python3 check.py 5      # one step
python3 check.py 5 7    # a range
python3 check.py --all  # everything
```

`check.py` runs 9 checks against **your** code and never imports `solutions/`. Every
reference probability is computed in `check.py` itself from `math.comb` and `Fraction`, so
the checker never asks your code what the right answer is.

The acceptance rule from the node is enforced literally: at `TRIALS = 100_000`, each exact
Fraction must sit within **four standard errors** of its simulation,
`|exact − sim| ≤ 4·sqrt(p(1−p)/N)`. The simulations are seeded, so a failure is
reproducible rather than flaky.

## Mutation table

The checker was itself tested: seven classic bugs were planted in copies of the solution
and each must be caught by the step named. Run
`python3 ../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| `P(n, k)` multiplies one factor too few | step 1 |
| two pair returns the count, not the probability | step 3 |
| at-least-one-ace keeps only the first inclusion-exclusion term (hands with two aces counted twice) | step 4 |
| law of total probability drops the last case | step 5 |
| Bayes denominator drops the false-positive term | step 6 |
| unknowing Monty Hall host treated as knowing (2/3 instead of 1/2) | step 9 |
| unknowing Monty Hall simulation never discards rounds where the host reveals the car | step 9 |

The two Monty Hall bugs are deliberately different views of the same mistake: one corrupts
the closed form, the other corrupts the experiment. A check that only tested the formula
would miss a simulation that quietly ignores the conditioning.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Exact `Fraction`, not floats.** A wrong sample space and rounding must not look alike;
  floats would destroy exactly the signal the module teaches. Cost: inputs must be exact
  Fractions, and arithmetic is slower.
- **Counting built from scratch, not `math.comb`.** Chapter 1 *is* the multiplication
  principle. `check.py` still uses `math.comb` as its oracle — the point of not using it in
  the solution.
- **One `random.Random(seed)` per simulation.** A module-level generator would make results
  depend on call order; explicit seeds make every measurement reproducible. Cost: the caller
  must pass a seed.
- **Simulations return `Fraction(wins, trials)`.** Converting to float only inside the
  four-standard-error test keeps the acceptance rule explicit and avoids rounding at the
  wrong moment.
- **The unknowing host is modelled as random and the game conditioned on a goat reveal.**
  Treating him as omniscient would give 2/3 in both variants and hide the lesson; the
  1/2-vs-2/3 contrast is the node's limit case.

## Questions to answer before reading the solutions

1. The two-pair count is `C(13,2)·C(4,2)²·44`. Why the factor `44` and not `C(11,1)·4` or
   `C(14,1)·4`? What goes wrong with each wrong kicker?
2. `C(4,1)·C(51,4)` over-counts. Exactly how many times is a hand with `j` aces counted,
   and why does inclusion-exclusion with `C(4,j)·C(52−j, 5−j)` fix it? Show that the
   result equals `1 − C(48,5)/C(52,5)`.
3. With prevalence 1%, sensitivity 95%, specificity 90%, the posterior is about 8.8%, not
   95%. Which term in the denominator did your intuition forget? By how much must
   specificity rise for the posterior to pass 50%?
4. In Monty Hall the knowing host gives switching 2/3 but the unknowing host gives 1/2.
   What exactly does the knowing host condition on that the unknowing host does not, and
   why does conditioning on "a goat was revealed" *not* transfer the same information?
5. The simulation's standard error is `sqrt(p(1−p)/N)`. For the diagnostic posterior,
   `p ≈ 0.088`, so the SE is smaller than for a coin flip. Does that make the test easier or
   harder to pass, and does the four-SE bound stay meaningful when `p` is near 0 or 1?

## Limits

- Exact answers are combinatorial, so they need a countable, finite sample space. Continuous
  distributions (where a probability is an integral) are `probability-02`.
- The base-rate case has one test and one disease. Combining several conditionally
  independent tests (the odds form of Bayes, naive Bayes) is left out.
- The Monty Hall simulation discards rounds where the unknowing host reveals the car; at very
  low trial counts this makes the surviving sample smaller, and the checker says so rather
  than pretending the estimate is exact.
- `Fraction(x)` on a float produces the exact binary fraction, not the decimal you typed;
  the module documents that exactness requires `Fraction(1, 100)`, not `Fraction(0.01)`.
- No confidence intervals beyond the four-SE acceptance rule and no variance reduction —
  that is `probability-03` (limit theorems and simulation).

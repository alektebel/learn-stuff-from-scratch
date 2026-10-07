# Solutions — Limits and Inequalities From Scratch

`limits.py` is the complete implementation. Run its demo:

```bash
python3 limits.py
```

Expected output (fixed seeds, so it is reproducible; the CLT block draws
`60000 * (25 + 100 + 400)` observations, so it takes a few seconds):

```
Limits and inequalities from scratch
  change of variables: X ~ Exp(1), Y = X^2
    y =  0.25   f_Y = 0.60653066   analytic = 0.60653066
    y =  1.00   f_Y = 0.18393972   analytic = 0.18393972
    y =  4.00   f_Y = 0.03383382   analytic = 0.03383382
  convolution of two dice: P(sum = k)
    k =  2   P = 0.027778   (1/36)
    k =  4   P = 0.083333   (1/12)
    k =  7   P = 0.166667   (1/6)
    k = 10   P = 0.083333   (1/12)
    k = 12   P = 0.027778   (1/36)
  bounds at Binomial(100, 3/10)
    k = 40   exact = 2.099e-02   Markov = 0.7500   Chebyshev = 0.2100   Chernoff = 1.0463e-01
    k = 45   exact = 1.086e-03   Markov = 0.6667   Chebyshev = 0.0933   Chernoff = 6.8645e-03
    k = 50   exact = 2.206e-05   Markov = 0.6000   Chebyshev = 0.0525   Chernoff = 1.6386e-04
  exact_tail_exponential(2, 3) = 0.002479   (e^-6 = 0.002479)
  law of large numbers: running mean of U(0, 1) -> 0.5
    m =    1   running mean = 0.50837
    m =    5   running mean = 0.50179
    m =   20   running mean = 0.49935
    m =  100   running mean = 0.50028
    m =  400   running mean = 0.50066
  central limit theorem: KS distance of the standardised mean to N(0, 1)
    n =   25   error = 0.02694
    n =  100   error = 0.01448   x1.86
    n =  400   error = 0.00610   x2.37
  limit case: spread of the sample mean, n -> 4n
    Cauchy IQR   n=4  = 1.9852   n=16 = 2.0131   (does not shrink)
    Exp(1) IQR   n=4  = 0.6466   n=16 = 0.3340   (shrinks by ~2)
```

The two blocks that carry the node's acceptance criteria:

- The bounds block: at every `k`, the exact tail is below Markov, Chebyshev and
  Chernoff, and Chernoff is the tightest of the three.
- The CLT block: the KS distance to `N(0, 1)` roughly halves each time `n` is
  multiplied by 4, the Berry-Esseen `1/sqrt(n)` order.
- The last block is the limit case: the Cauchy sample-mean IQR barely moves from
  `n = 4` to `n = 16`, while an exponential control's IQR falls by about half.

## Run the checker against these solutions

From a temporary directory holding a copy of `limits.py` and `check.py`:

```bash
python3 check.py --all
```

All five steps report `PASS` (takes a few seconds; step 4 draws on the order of
`2.5e7` observations). To exercise the planted bugs, run
`python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`
from inside the module directory; all five mutations are CAUGHT.

## What is deliberately left out

The standard-normal CDF helper `_standard_normal_cdf`, the IQR helper `_iqr`,
the demo-only helper `_sample_means` and `demo()` are scaffolding, not graded
deliverables; `make_templates.py` leaves them intact. See `../README.md` for the
design decisions, the questions the module asks before you read this file, and
the limits.

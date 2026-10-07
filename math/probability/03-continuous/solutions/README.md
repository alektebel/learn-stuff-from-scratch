# Continuous Random Variables From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no
dependencies. Run it from the module directory:

```bash
python3 solutions/continuous.py
```

Expected output (the Monte-Carlo numbers are seed-fixed; the exact values never
change):

```
Continuous random variables from scratch
  uniform_ppf(0.3)                = 0.300000
  exponential_ppf(0.5, rate=1.3)  = 0.533190  (F = 0.500000)
  normal_ppf(0.975)               = 1.959964  (Phi = 0.975000)
  inverse-CDF sample, n = 50000, against the target CDF (KS test)
    uniform      D = 0.00293   p = 0.7857
    exponential  D = 0.00381   p = 0.4633
    normal       D = 0.00533   p = 0.1162
  memorylessness gap Exp(1.3), s=2.0, t=3.0   = +6.939e-18
  same gap, shifted by 0.75 (not memoryless) = -3.342e-02
  tail truncation Exp(1), u -> 1: largest reachable x = 36.736801
    missing mass = 1.110e-16, missing quantile = inf
```

Three lines carry the module:

- **`normal_ppf(0.975) = 1.959964`.** The quantile is the number whose CDF is
  0.975, not 0.975 itself. Returning `Phi(x)` instead of its inverse is the
  planted bug: the CDF of 0.975 is 0.975, and the checker's round trip through
  `math.erf` catches it.
- **the KS p-values.** At `n = 50000` each inverse-CDF sample has a small `D`
  and a p-value well above 0.01, so the sample is consistent with its target
  CDF. The checker also builds a sampler with three times the rate and requires
  the same test to reject it: passing alone is not evidence.
- **`missing quantile = inf`.** The sampler draws `u < 1`, so it can never reach
  the exponential's `u = 1` quantile `+inf`; the point it can reach is
  `-log1p(-(1 - 2**-53))/rate ~ 36.7`, and the tail above it (mass `2**-53`) is
  truncated. `memorylessness gap ... = +6.9e-18` is zero up to rounding; the
  shifted variable gives `-3.3e-02`, which is not zero.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/probability/03-continuous
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 7/7 passing
```

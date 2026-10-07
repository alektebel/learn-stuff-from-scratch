# solutions

The reference implementation of `math/optimization/02-duality`. This directory is for
the learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 duality.py       # the demo
```

Expected output (`python3 duality.py`):

```text
QP  minimise (1/2) x^T Q x s.t. x1 + x2 >= 1
  primal optimum 0.500000 at [0.5, 0.5], lambda* = [1.0]
  dual   optimum 0.500000   gap = +0.000e+00

LP  minimise -x1 - x2 s.t. x1 <= 1, x2 <= 1, x1 + x2 <= 1.5
  primal optimum -1.500000
  dual   optimum -1.500000   gap = +0.000e+00

KKT residuals at the QP optimum:
  primal_feasibility       0.000e+00
  dual_feasibility         0.000e+00
  stationarity             0.000e+00
  complementary_slackness  0.000e+00
  max_residual             0.000e+00

Limit case (no Slater point: the feasible set is a single point):
  minimise e^{-x} s.t. x^2 / y <= 0, y > 0
  primal optimum 1.000000   dual optimum 0.000000     gap = +1.000e+00
  strong duality holds: False
```

To grade the reference, put `check.py` and the reference `duality.py` in one directory
and run there:

```bash
mkdir /tmp/opt-check && cp check.py solutions/duality.py /tmp/opt-check/
cd /tmp/opt-check && python3 check.py --all
```

`check.py` never imports this directory. It hard-codes the known primal optima of the
teaching problems and evaluates the limit-case dual on its own grid
(`_limit_dual`), so a passing run means the *learned* code agrees with arithmetic
done independently of it.

## Design decisions

- **Closed-form coordinate ascent, not gradient ascent, for the QP dual.** Each
  coordinate of `g(lam) = -1/2 lam^T H lam - d^T lam + const` is maximised exactly by
  `-((d + H lam)_{-i}) / H_ii` clipped at 0. A projected gradient method would need a
  step below `1/||H||` to stay stable; the coordinate step needs no step size at all.
- **Basis enumeration, not the simplex method, for the LP dual.** With two variables the
  dual has one degree of freedom and the optimum is a basic solution; enumerating every
  pair of constraints and keeping the feasible `y >= 0` is exact and has no pivoting
  rules to get wrong.
- **A sign that can be checked.** `weak_duality_gap` returns `primal - dual`, which weak
  duality forces to be `>= 0`; the limit case makes that number strictly positive, so a
  flipped sign is visible.
- **Strong duality is a hypothesis, not a theorem to assume.** `strong_duality_holds`
  compares the two values within a tolerance, so it returns `False` exactly where
  Slater's condition fails.

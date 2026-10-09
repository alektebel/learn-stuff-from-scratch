# solutions

The reference implementation of `math/optimization/03-unconstrained`. This directory is
for the learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 minimise.py       # the demo
```

Expected output (`python3 minimise.py`):

```text
Convex quadratic
  optimum from solve: [0.090909, 0.636364]
  gradient descent:  18 iterations -> [0.090909, 0.636364]
  Newton:            1 iterations -> [0.090909, 0.636364], final decrement 8.96e-32
Non-quadratic e^x - x (optimum (0, 0))
  gradient descent:  7 iterations
  Newton:            5 iterations, last log-ratio ~2.13
Limit case sqrt(1 + x^2), start x = 2
  undamped Newton ran away to x = 6.578e+07
  damped   Newton converged to  x = 2.641e-06
```

To grade the reference, put `check.py` and the reference `minimise.py` in one directory
and run there:

```bash
mkdir /tmp/opt-check && cp check.py solutions/minimise.py /tmp/opt-check/
cd /tmp/opt-check && python3 check.py --all
```

`check.py` never imports this directory. It solves the teaching quadratics itself
(`_gauss`) and knows the analytic optimum of every other problem, so a passing run means
the *learned* code agrees with arithmetic done independently of it.

## Design decisions

- **One backtracking routine, shared by both methods.** Gradient descent takes `d = -g`;
  damped Newton takes `d = -H^{-1} g`. The step-size logic is identical, so the two
  methods differ only in the direction, which is what makes the iteration-count comparison
  meaningful.
- **The decrement does double duty.** Solving `H y = g` yields the direction `-y` and the
  stopping scalar `g^T y` at once; there is no second gradient-norm test to tune.
- **The ridge is attempted lazily.** `_solve_regularized` tries the exact solve first and
  only adds `lam*I` when it raises, so well-conditioned problems get the exact step and
  singular ones stay finite.
- **`line_search` is a first-class argument.** It lets the limit case call the raw Newton
  step directly, instead of hiding divergence behind a damped default.

# Solutions

A complete, pure-standard-library implementation of
`math/probability/06-conditional-expectation`. Run it as a script to see the
measurements the node promises:

```bash
cd math/probability/06-conditional-expectation/solutions
python3 cond.py
```

## Expected demo output

```
Adam's law on the hand joint
  E[Y] from the joint          = 1/4
  sum_x P(X = x) E[Y | X = x]  = 1/4
Eve's law on the hand joint
  Var(Y) from the joint        = 3/16
  E[Var(Y | X)]                = 1/6
  Var(E[Y | X])                = 1/48
  within + between             = 3/16
E[Y | X] as the best predictor (mean squared error)
  E[Y | X]          = 1/6
  best constant     = 2/9
  a linear fit      = 13/48
  quadratic fit     = 1/6
Hierarchical model, law of total variance
  total Var(Y)      = 12/5
  E[Var(Y | X)]     = 28/25   (the naive within-only spread)
  Var(E[Y | X])     = 32/25
  total > within    = True
Simulation of the same hierarchy (200000 draws)
  sample Var(Y)     = 2.3935
  closed-form total = 2.4000
```

The last two lines are seeded (`random.Random(20241006)`); the sample variance
lands near `2.4` and clearly above the within-group `28/25 = 1.12`, which is the
point of the limit case.

## How the acceptance rule is met

`E[Y | X]` scores `1/6`, the best constant `2/9`, a particular linear fit
`13/48`, and the interpolating quadratic `1/6`. So the optimal predictor is
strictly better than every constant on this dependent joint and no worse than any
other tested function of `X` -- the quadratic ties it because with three
conditioning values a parabola can reproduce the three conditional means exactly.

## Running the checker against this solution

`check.py` sits one level up and never imports this directory. Copy these
solutions next to it in a scratch directory:

```bash
tmp=$(mktemp -d)
cp cond.py ../check.py "$tmp"/
( cd "$tmp" && python3 check.py --all )
```

All five steps pass. To see what a learner sees, run `python3 ../check.py --all`
in the module directory (the template there reports every step as TODO).

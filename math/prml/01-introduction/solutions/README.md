# solutions

The reference implementation of `math/prml/01-introduction`. This directory is for the
learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 intro.py       # the demo
```

Expected output (`python3 intro.py`):

```text
Curve fitting, bias-variance and decision theory — measurements
  exact quadratic fit: weights [1.0, -2.0, 0.5]  (expected [1, -2, 0.5])
  degree-9 on 10 noisy points: train 5.11e-09  test 5.86e-01
  the same with ridge 1e-5: test 4.00e-02
  bias-variance (degree 1): bias^2 0.1799 + variance 0.0269 + noise 0.0400 = 0.2468  vs simulated error 0.2461
  symmetric loss:   decision at p=0.4 -> 0, p=0.6 -> 1
  asymmetric loss:  decision at p=0.4 -> 1, p=0.6 -> 1
  entropy([0.5, 0.5]) = 0.693147  (ln 2 = 0.693147)
  KL([0.7,0.3] || [0.5,0.5]) = 0.082283
  MI(correlated 2x2) = 0.693147  MI(independent) = 0.000000
```

To grade the reference, put `check.py` and the reference `intro.py` in one directory and
run there:

```bash
mkdir /tmp/prml-check && cp check.py solutions/intro.py /tmp/prml-check/
cd /tmp/prml-check && python3 check.py --all
```

`check.py` never imports this directory; it carries its own polynomial evaluator, its own
mean squared error and its own noise, so a passing run means the *learned* code agrees
with arithmetic done independently of it.

# solutions

The reference implementation of `math/prml/02-distributions`. This directory is for the
learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 distributions.py       # the demo
```

Expected output (`python3 distributions.py`):

```text
Distributions, conjugacy and density estimation — measurements
  Beta(1,1) + 3 heads / 1 tail -> Beta(4, 2), mean 0.6667
  Beta(1,1) + 3 heads / 0 tails -> Beta(4, 1), mean 0.8000
  Dirichlet(1,1,1) + [2,1,1] -> [3.0, 2.0, 2.0]
  gaussian_mle(0..9): mean 4.5000, variance(1/N) 8.2500  (unbiased 9.1667)
  sequential posterior: mu 0.44705882, tau 1.88888889
  batch posterior:      mu 0.44705882, tau 1.88888889
  Bernoulli sufficient stats (5, 3.0), eta 0.405465, A'(eta) 0.600000
  KDE peak/mid ratio: h=0.15 -> 129.3 (spiky), h=4.0 -> 1.00 (oversmooth)
  E[MLE variance] over 20000 samples of 8: 3.4930  vs (N-1)/N sigma^2 = 3.5000
```

To grade the reference, put `check.py` and the reference `distributions.py` in one
directory and run there:

```bash
mkdir /tmp/prml02-check && cp check.py solutions/distributions.py /tmp/prml02-check/
cd /tmp/prml02-check && python3 check.py --all
```

`check.py` never imports this directory; it carries its own hand-computed posteriors, its
own precision-weighted batch posterior and its own Gaussian noise, so a passing run means
the *learned* code agrees with arithmetic done independently of it.

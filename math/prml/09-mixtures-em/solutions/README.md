# solutions

The reference implementation of `math/prml/09-mixtures-em`. This directory is for the
learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 mixtures.py       # the demo
```

Expected output (`python3 mixtures.py`):

```text
K-means centroids: [-6.009, -0.125, 6.073]
GMM means: [-6.009, -0.125, 6.073]
GMM weights: [0.333, 0.333, 0.333]
GMM log-likelihood first -> last: -373.987 -> -233.136 monotone: True
Bernoulli mixture thetas: [[0.141, 0.879, 0.113], [0.964, 0.083, 0.9]] weights: [0.549, 0.451]
logpdf(0 | 0, var): [1.384, 3.686, 8.291] (-> +inf)
min variance floored -> 0.5  unfloored -> 1e-12
bad init log-likelihood: -316.838  best of 8 restarts: -174.261
```

Small floating-point differences are fine; the recovery is the point, not the last
digits.

To grade the reference, put `check.py` and the reference `mixtures.py` in one directory
and run there:

```bash
mkdir /tmp/prml09-check && cp check.py solutions/mixtures.py /tmp/prml09-check/
cd /tmp/prml09-check && python3 check.py --all
```

`check.py` never imports this directory. It generates its own synthetic mixtures,
asserts on the returned log-likelihood sequence (requiring several entries so an
overwritten or single-value sequence cannot pass) that it never decreases, and matches
components to the generating ones by sorting the means, so a passing run means the
*learned* code agrees with data and arithmetic prepared independently of it.

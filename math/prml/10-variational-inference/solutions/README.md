# solutions

The reference implementation of `math/prml/10-variational-inference`. This directory
is for the learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 variational.py       # the demo
```

Expected output (`python3 variational.py`):

```text
mean-field q(mu): mu = 1.522 (true 1.500), E[tau] = 0.475 (true 0.500)
ELBO -725.242 -> -722.918 over 4 sweeps, monotone: True, <= log evidence -722.917: True
variational GMM means: [-5.85, -0.08, 6.06]
ELBO -382.029 -> -306.247, monotone: True
rho = 0.50: fitted marginal variances 0.7500, true 1.0 (understated by 25.0%)
rho = 0.90: fitted marginal variances 0.1900, true 1.0 (understated by 81.0%)
rho = 0.99: fitted marginal variances 0.0199, true 1.0 (understated by 98.0%)
```

Small floating-point differences are fine; the shrinking variance is the point, not
the last digits.

To grade the reference, put `check.py` and the reference `variational.py` in one
directory and run there:

```bash
mkdir /tmp/prml10-check && cp check.py solutions/variational.py /tmp/prml10-check/
cd /tmp/prml10-check && python3 check.py --all
```

`check.py` never imports this directory. It generates its own synthetic data,
recomputes the exact Normal--Gamma log evidence independently, asserts on the returned
ELBO sequence (requiring several entries so an overwritten or single-value sequence
cannot pass) that it never decreases, and compares the mean-field variances against the
closed-form marginals of a correlated Gaussian, so a passing run means the *learned*
code agrees with data and arithmetic prepared independently of it.

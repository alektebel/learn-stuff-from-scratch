# solutions

The reference implementation of `math/prml/11-sampling`. This directory is for the
learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 sampling.py       # the demo
```

Expected output (`python3 sampling.py`, fixed seeds so it is reproducible):

```text
Rejection sampling, Beta(2, 3) target via Uniform(0, 1), M = 16/9
  sample mean 0.3976 (target 0.4000), variance 0.0398 (target 0.0400)
  acceptance rate 0.5667 (target 1/M = 0.5625)
Importance sampling, E[X^2] of N(0, 1) with a N(0, 1) proposal
  plain estimate 1.0039 (unbiased, target 1.0)
  self-normalised 1.0039, ESS 20000
Correlated 2-D Gaussian, rho = 0.95
  HMC  ESS/gradient      = 0.06417 (1001 over 15600 gradients)
  RW-MH ESS/target eval  = 0.00661 (103 over 15601 evaluations)
Importance sampling of E[1/(1 + X^2)] for a Cauchy target (0.5)
  N(0, 1) proposal  (light): estimate 0.4909 (self-normalised 0.5952), max weight 25, ESS 1979
  power-law proposal (heavy): estimate 0.5132 (self-normalised 0.5022), max weight 1.9, ESS 2854
```

To grade the reference, put `check.py` and the reference `sampling.py` in one
directory and run there:

```bash
mkdir /tmp/prml11-check && cp check.py solutions/sampling.py /tmp/prml11-check/
cd /tmp/prml11-check && python3 check.py --all
```

`check.py` never imports this directory; it carries its own Beta density and
moments, its own Student-t density and sampler, its own correlated-Gaussian
precision matrix, and the known value `E[1/(1 + X^2)] = 1/2` for the Cauchy, so a
passing run means the *learned* code agrees with arithmetic done independently of
it.

# solutions

The reference implementation of `math/prml/13-sequential`. This directory is for the
learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 sequential.py       # the demo
```

Expected output (`python3 sequential.py`):

```text
Sequential models from scratch

HMM  pi [0.6, 0.4]  A [[0.7, 0.3], [0.4, 0.6]]  B [[0.9, 0.1], [0.2, 0.8]]  obs [0, 0, 1, 1, 0, 1, 1, 1]
  forward-backward marginals:
    t=0  [0.8966, 0.1034]
    t=1  [0.8314, 0.1686]
    t=2  [0.1357, 0.8643]
    t=3  [0.1203, 0.8797]
    t=4  [0.6525, 0.3475]
    t=5  [0.107, 0.893]
    t=6  [0.0581, 0.9419]
    t=7  [0.0856, 0.9144]
  Viterbi path: [0, 0, 1, 1, 0, 1, 1, 1]
  Baum-Welch log-likelihood -5.8728 -> -3.7442 over 20 iterations
    new A: [[0.394, 0.606], [0.0, 1.0]]
    new B: [[1.0, 0.0], [0.213, 0.787]]

Kalman / RTS vs exact batch Gaussian posterior
  (filtered matches batch only at the last step; smoothed matches at every step)
  t=0  filtered mean [0.0816, 0.1165] (err 7.52e-02)   smoothed mean [0.1569, 0.0496] (err 4.86e-17)
  t=1  filtered mean [0.2701, -0.1403] (err 1.20e-01)   smoothed mean [0.1958, -0.0206] (err 2.78e-17)
  t=2  filtered mean [0.0558, 0.1147] (err 5.41e-02)   smoothed mean [0.1099, 0.1154] (err 6.94e-17)
  t=3  filtered mean [0.1708, 0.0882] (err 5.55e-17)   smoothed mean [0.1708, 0.0882] (err 5.55e-17)

Limit: unscaled forward after 1200 steps = 0.0 (underflow), scaled = [0.5, 0.5] (stays normalised)
```

To grade the reference, put `check.py` and the reference `sequential.py` in one directory
and run there:

```bash
mkdir /tmp/prml13-check && cp check.py solutions/sequential.py /tmp/prml13-check/
cd /tmp/prml13-check && python3 check.py --all
```

`check.py` never imports this directory. It carries its own brute-force path enumeration,
its own seeded synthetic HMM, its own exact batch-Gaussian posterior and its own unscaled
forward recursion, so a passing run means the *learned* code agrees with arithmetic done
independently of it.

## Notes on the implementation

- `forward` returns `(alphas, cs)` where `alphas[t]` sums to one and `cs[t]` is the step
  likelihood; `forward_backward` multiplies them back together. `backward` recomputes the
  same `cs` by calling `forward`, so the two scalings cannot drift apart.
- `_add` and `_sub` operate on matrices; mean-vector updates add componentwise in place
  because a state mean is a plain list, not a row.
- `baum_welch` records `logliks[0]` under the starting parameters and one entry per M-step,
  so the trajectory starts at the fit it was asked to improve on.
- `_inv` is Gauss-Jordan with partial pivoting; all matrices here are small and
  well-conditioned. A singular matrix raises rather than returning garbage.

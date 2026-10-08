# Solutions

Reference implementation for the interior-point module. Copy into the module root to
run the checker against it:

```
cp solutions/interior.py check.py /tmp/ip/
cd /tmp/ip && python3 check.py --all
```

All five steps pass.

## Expected demo output

`python3 solutions/interior.py`:

```
equality-constrained Newton
  x = [1.25, 1.75]  residual = 0.00e+00
log-barrier LP (min -x1 - x2)
  enumeration optimum p* = -4.5
  t=     1  c^T x = -3.172013  m/t = 5
  t=    10  c^T x = -4.284877  m/t = 0.5
  t=   100  c^T x = -4.479728  m/t = 0.05
  t=  1000  c^T x = -4.497998  m/t = 0.005
barrier outer loop: measured gap vs m/t
  t=1e+00  measured gap = 1.328e+00  m/t = 5.000e+00  ratio = 0.266
  t=1e+01  measured gap = 2.151e-01  m/t = 5.000e-01  ratio = 0.430
  t=1e+02  measured gap = 2.027e-02  m/t = 5.000e-02  ratio = 0.405
  t=1e+03  measured gap = 2.002e-03  m/t = 5.000e-03  ratio = 0.400
  t=1e+04  measured gap = 2.000e-04  m/t = 5.000e-04  ratio = 0.400
  t=1e+05  measured gap = 2.000e-05  m/t = 5.000e-05  ratio = 0.400
  t=1e+06  measured gap = 2.000e-06  m/t = 5.000e-06  ratio = 0.400
  t=1e+07  measured gap = 1.980e-07  m/t = 5.000e-07  ratio = 0.396
phase-I feasibility
  feasible LP  -> True
  infeasible LP-> False
m/t directly: cone min x1 + x2 s.t. x1 >= 0, x2 >= 0
  t=1e+00  gap = 2.000e+00  m/t = 2.000e+00  ratio = 1.000
  t=1e+01  gap = 2.000e-01  m/t = 2.000e-01  ratio = 1.000
  t=1e+02  gap = 2.000e-02  m/t = 2.000e-02  ratio = 1.000
  t=1e+03  gap = 2.000e-03  m/t = 2.000e-03  ratio = 1.000
  t=1e+04  gap = 2.000e-04  m/t = 2.000e-04  ratio = 1.000
  t=1e+05  gap = 2.000e-05  m/t = 2.000e-05  ratio = 1.000
  t=1e+06  gap = 2.000e-06  m/t = 2.000e-06  ratio = 1.000
  t=1e+07  gap = 1.980e-07  m/t = 2.000e-07  ratio = 0.990
```

## What the demo measures

* The equality-constrained quadratic lands on `(1.25, 1.75)` on `x1 + x2 = 3` in one
  Newton step (residual 0).
* On the pentagon the barrier value walks `-3.17, -4.28, -4.48, -4.50` toward the
  enumeration optimum `-4.5` as `t` doubles and redoubles.
* The measured suboptimality against `m/t` is bounded above by `1` and settles at
  `0.4 = 2/5`: only two constraints are active at the optimum, and the proof of the
  `m/t` bound sums over those. On the cone, where both constraints are active, the
  ratio is exactly `1.000`.
* `phase_one` accepts the pentagon and rejects `x1 + x2 <= 1` with `x1 + x2 >= 3`.

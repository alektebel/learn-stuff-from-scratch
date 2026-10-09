# solutions

The reference implementation of `math/optimization/01-convexity`. This directory is for
the learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 convexity.py       # the demo
```

Expected output (`python3 convexity.py`):

```text
Classification (Jensen + PSD Hessian at the centre):
  ok  x^2             convex=True  expected=True  jensen gap=+0.000e+00
  ok  abs(x)          convex=True  expected=True  jensen gap=+0.000e+00
  ok  x^4             convex=True  expected=True  jensen gap=+0.000e+00
  ok  exp(x)          convex=True  expected=True  jensen gap=+0.000e+00
  ok  log-sum-exp     convex=True  expected=True  jensen gap=+0.000e+00
  ok  geometric-mean  convex=False expected=False jensen gap=+3.044e-01
  ok  -x^2            convex=False expected=False jensen gap=+3.657e+00
  ok  x*y             convex=False expected=False jensen gap=+2.327e+00
  ok  sqrt(abs(x))    convex=False expected=False jensen gap=+2.617e-01
  9/9 correct

The naive sublevel test is fooled:
  sqrt(abs(x)) sublevel sets look convex: True  (quasiconvex, not convex)
  classify(sqrt(abs(x))) = False
  -x^2 sublevel sets look convex: False
```

To grade the reference, put `check.py` and the reference `convexity.py` in one directory
and run there:

```bash
mkdir /tmp/opt-check && cp check.py solutions/convexity.py /tmp/opt-check/
cd /tmp/opt-check && python3 check.py --all
```

`check.py` never imports this directory; it keeps its own chords (`_ref_gap`) and its own
reference eigenvalues, so a passing run means the *learned* code agrees with arithmetic
done independently of it.

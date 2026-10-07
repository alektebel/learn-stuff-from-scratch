# solutions

The reference implementation of `math/linalg/03-spectral-theorem`. This directory is for
the learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 spectral.py       # the demo
```

Expected output (`python3 spectral.py`):

```text
The spectral theorem, polar decomposition and SVD — measurements
  symmetric [[2,1],[1,2]]: eigenvalues [1.0, 3.0]  (expected [1, 3])
    Q orthogonal = True
  rotated diag(3,1,1): eigenvalues [1.0, 1.0, 3.0]  Q orthogonal = True (basis-independent)
  positive_sqrt([[4,2],[2,3]]) squared residual = 1.776e-15
  polar [[3,1],[1,2]]: Q orthogonal = True, max|A - Q P| = 1.332e-15
  svd diag(3,2): S = [3.0, 2.0] descending = True, U orthogonal = True, V orthogonal = True
  svd rank-1 [[1,1],[1,1]]: S = [2.0, 0.0], U orthogonal = True (zero singular value completed)
```

To grade the reference, put `check.py` and the reference `spectral.py` in one directory
and run there:

```bash
mkdir /tmp/spectral-check && cp check.py solutions/spectral.py /tmp/spectral-check/
cd /tmp/spectral-check && python3 check.py --all
```

`check.py` never imports this directory; it keeps its own matrix product, its own
orthonormality test and its own randomised PSD probe, so a passing run means the *learned*
code agrees with arithmetic done independently of it.

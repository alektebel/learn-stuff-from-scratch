# Eigenvalues From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, standard
library only (it uses `fractions.Fraction` for the exact road and `cmath`/`math` for the
numerical one). Run it from the module directory:

```bash
python3 solutions/eigenvalues.py
```

Expected output:

```
Eigenvalues, eigenvectors and diagonalisability — measurements
  characteristic polynomial of [[2, 1], [0, 2]]: ['1', '-4', '4']  (expected ['1', '-4', '4'])
  eigenvalues of the Jordan block: ['2', '2']  eigenspace dimension = 1
  Jordan block diagonalisable = False   identity 2x2 diagonalisable = True
  [[0,1],[1,0]] = P D P^-1 with D = [['-1', '0'], ['0', '1']]
  QR eigenvalues of [[2, 1], [1, 2]]: [1.0, 3.0]  (expected [1, 3])
  Wilkinson W_20: Newton+deflation error = 9.197e-01  QR companion error = 2.466e-02
  the polynomial route is worse by a factor 37.3
```

The line that carries the accept criterion is the third: the Jordan block
`[[2,1],[0,2]]` has one distinct eigenvalue and is **not** diagonalisable (its
eigenspace is 1-dimensional), while the identity has one distinct eigenvalue and **is**
diagonalisable (its eigenspace is 2-dimensional). Counting distinct eigenvalues gets the
identity wrong; counting algebraic multiplicities gets the Jordan block wrong. Only the
sum of eigenspace dimensions gets both right.

The next line shows the exact factorisation: for `[[0,1],[1,0]]`, `P` has the two
eigenvectors as columns and `D = diag(-1, 1)`, and `P D P⁻¹` reconstructs the matrix over
the rationals exactly.

The last two lines are the dual limit case. On Wilkinson's polynomial `W₂₀`, the
coefficient route — form the coefficients, then run Newton's method with forward
deflation — has a largest root error near `0.92`, while the shifted QR eigensolver applied
to the companion matrix stays near `0.025`: a factor of about 37. The roots are
ill-conditioned as functions of the coefficients; working on the matrix avoids forming
them.

Note the two error figures are printed by the same experiment and can vary only in the
last digits across platforms. If your run differs in the factor, recompute both: the
polynomial route must remain the worse one.

## Grade yourself

Run the checker against these files in a scratch directory:

```bash
cd math/linalg/02-eigenvalues
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 9/9 passing
```

`check.py` never imports `solutions/`; it computes every exact reference value with its
own arithmetic (the characteristic polynomial by cofactor expansion of `det(x I − A)`,
independent of the Faddeev-LeVerrier recurrence) and states its numerical tolerances at
the assertions. Its resistance to planted bugs is documented in the parent README
(`_build/mutations.py`).

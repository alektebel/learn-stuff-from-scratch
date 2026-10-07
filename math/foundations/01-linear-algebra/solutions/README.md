# Linear Algebra From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no
dependencies. Run it from the module directory:

```bash
python3 solutions/elimination.py
```

Expected output:

```
Linear algebra from scratch — measurements
  solve      x = [2.0, 3.0, -1.0]  residual 0.00e+00
  rank       1 of 2 rows, null-space dim 2
  inverse    max|A·A⁻¹ − I| = 1.78e-15
  det        -1.000000
  small pivot  naive x₁ = 0.000000 (wrong) · pivoted x₁ = 1.000000
```

The last line is the whole module in one measurement: on the system

```
[ 1e-18   1 ] [x₁]   [1]
[  1      1 ] [x₂] = [2]
```

the naive elimination (bottom, `_no_pivot` inside the demo) uses `1e-18` as a pivot and
returns `x₁ = 0`; partial pivoting swaps in the `1` and returns `x₁ = 1`. The residual of
the first system is printed as `0.00e+00` because the solution is exact in binary
floating point.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/foundations/01-linear-algebra
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 10/10 passing
```

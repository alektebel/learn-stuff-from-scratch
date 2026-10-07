# Analytic Geometry From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no
dependencies. Run it from the module directory:

```bash
python3 solutions/geometry.py
```

Expected output:

```
Analytic geometry from scratch — measurements
  inner      <e₁,e₂>_A = 1.000  angle = 60.000°
  project    max|P²−P| = 5.55e-17  max|P−Pᵀ| = 5.55e-17  max|Bᵀr| = 4.44e-16
  gram-schm  max|QᵀQ−I| = 2.22e-16
  CGS vs MGS max|QᵀQ−I| = 5.00e-01  vs  7.07e-09
  rotations  det R₂ = 1.000000  det R₃ = 1.000000  |R₃v|−|v| = 4.4e-16
```

Two lines carry the chapter. The first: with `A = [[2,1],[1,2]]` the angle between `e₁`
and `e₂` is `60°`, not `90°` — the inner product, not the picture, defines the angle. The
fourth: on the Läuchli matrix (`ε = 1e-8`) classical Gram-Schmidt is off orthonormality by
`0.5` while modified is off by `7e-9`; the modified version uses the partially reduced
vector in each inner product, and that is the whole difference.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/foundations/02-analytic-geometry
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 10/10 passing
```

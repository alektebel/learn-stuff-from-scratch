# Vector Spaces From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, standard
library only (it uses `fractions.Fraction`, so every answer is exact). Run it from the
module directory:

```bash
python3 solutions/vector_spaces.py
```

Expected output:

```
Vector spaces and linear maps from scratch — measurements
  d/dx on P_2: D^2 nonzero = True  D^3 zero = True  nilpotency index = 3
  d/dx on P_4: D^4 nonzero = True  D^5 zero = True  nilpotency index = 5
  d/dx (3 + 2x + 5x^2 - x^4) = [2, 10, 0, -4, 0]  (expected [2, 10, 0, -4, 0])
  change of basis max|S^-1 A S - S A S^-1| = 15
  rank-nullity dim V = dim null + dim range: 100/100 random maps
```

The two lines that carry the module are the last two. **Change of basis**: for a fixed
random `S` and a non-commuting `A`, `S⁻¹ A S` and `S A S⁻¹` differ by 15 in the largest
entry — the inverse really does have to be on the left, and a wrong order is not a small
error. **Rank-nullity**: for 100 random maps between spaces of different dimension,
`dim V = dim null T + dim range T` holds exactly, with `dim V` the number of columns, not
the number of rows.

The first two lines are the limit case: differentiation on `P_n` satisfies `Dⁿ ≠ 0` and
`Dⁿ⁺¹ = 0`, so its nilpotency index is `n+1` (3 for `P_2`, 5 for `P_4`). Run the demo for
other `n` by editing the loop; the pattern never changes.

## Grade yourself

Run the checker against these files in a scratch directory:

```bash
cd math/linalg/01-vector-spaces
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 8/8 passing
```

`check.py` never imports `solutions/`; it computes every reference value with its own
exact rational arithmetic. Its resistance to planted bugs is documented in the parent
README (`_build/mutations.py`).

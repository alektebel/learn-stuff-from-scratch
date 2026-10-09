# Conditioning and Stability From Scratch

Skill-tree node **`linalg-05-conditioning-stability`**. Builds the distinction
between a *problem's* conditioning and an *algorithm's* stability, then makes it
concrete with LU factorization, partial pivoting and the growth factor.

Sources, restated and never copied: Trefethen & Bau, *Numerical Linear Algebra*,
lectures 12–15 (condition number of a problem, stability of an algorithm,
forward versus backward error) and lectures 20–21 (Gaussian elimination, partial
pivoting, growth factor). The Wilkinson growth matrix is the `gfpp` matrix
(Wilkinson 1961; see also Cleve Moler's write-up), verified here to have growth
`2^(n-1)`.

## How to run

```
python3 check.py          # stop at the first unimplemented step
python3 check.py --all    # run every step
python3 check.py 3 5      # run steps 3 through 5
python3 stability.py      # the demo, once implemented
```

`check.py` never imports `solutions/`; it carries its own matrix product,
Gaussian elimination and Gauss–Jordan inverse, so every reference value is
computed independently of your code.

## Steps

| # | implement in | what it proves |
|---|--------------|----------------|
| 1 | `stability.py` | LU with and without pivoting reconstruct `A` and solve a known system (`A = P^T L U`) |
| 2 | `stability.py` | **ACCEPT**: on 100 random problems `forward <= condition * backward`, up to the `n*eps` floor; the condition number uses one norm and the backward error is relative |
| 3 | `stability.py` | the `gfpp` (Wilkinson) matrix has growth factor `2^(n-1)` under partial pivoting for `n = 3,4,5` |
| 4 | `stability.py` | **limit case (a)**: on the well-conditioned `[[1e-18,1],[1,1]]`, no-pivot LU blows up while partial pivoting is exact |
| 5 | `stability.py` | **limit case (b)**: the Hilbert matrix is ill-conditioned but partial pivoting is still backward stable (`backward error ~ eps`) |

## Design decisions

- **One norm for both factors.** `condition_number` is `||A||_inf * ||A^-1||_inf`.
  Mixing `||A||_1` with `||A^-1||_inf` silently inflates the number and weakens
  every inequality that uses it; step 2 checks the norm consistency directly.
- **Permutation as a matrix.** `lu_partial_pivot` returns `(L, U, P)` with
  `P A = L U`; `lu_nopivot` returns `P = I`. This makes `A = P^T L U` a single
  product, at the cost of `O(n^2)` storage for `P`.
- **Own inverse.** `condition_number` computes `A^-1` with Gauss–Jordan
  elimination with partial pivoting, so the module stays pure stdlib.
- **Growth denominator is `max|A|`, not `max|U|`.** Normalising by `max|U|`
  makes the ratio identically 1 and hides the entire phenomenon; a mutation
  plants exactly that bug.
- **The extremal matrix is `gfpp`, not the "subdiagonal + corner".** The loose
  description (unit diagonal, `-1` subdiagonal, `1` top-right corner) has growth
  only 2; ones in the *whole* last column with a subdiagonal gives growth `n`;
  the strict lower triangle filled with `-1` is what doubles at each step to
  `2^(n-1)`. Verified numerically before writing.
- **Backward-error floor in `perturbation_experiment`.** The exact bound is
  `forward <= condition * backward * (1 + forward)`; when the computed residual
  happens to round to a tiny fraction of `eps` the raw ratio spikes even though
  the solution is excellent, so the denominator is floored at `n * eps`.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py math/linalg/05-conditioning-stability math/linalg/05-conditioning-stability/_build/mutations.py`

| planted bug | caught by step |
|-------------|----------------|
| `lu_nopivot` silently performs partial pivoting (unstable case becomes stable) | 4 |
| `growth_factor` normalises by `max|U|` instead of `max|A|` | 3 |
| `condition_number` mixes `||A||_1` with `||A^-1||_inf` | 2 |
| `backward_error` drops the `||A|| ||x||` normalisation | 2 |
| `wilkinson_growth` puts the last-column ones in the wrong place (growth stays 1) | 3 |

## Questions (answer them yourself; the checker does not)

1. Both limit cases have small forward error under partial pivoting. One has a
   small condition number and one a huge one. Which error is smaller, and why
   does that not contradict `forward <= condition * backward`?
2. The bound `forward <= condition * backward` has no algorithmic constant in
   it. Where did the growth factor go? (Hint: it is inside the "backward" part
   of the bound for Gaussian elimination, which is `O(growth * eps)`.)
3. For `[[1e-18,1],[1,1]]`, what exactly is the multiplier that destroys the
   no-pivot solve, and what is the first digit it loses?
4. Why does `gfpp` never swap under partial pivoting, and what would complete
   pivoting do to its growth factor?

## Limits

- Norms are the infinity and 1-norms; the 2-norm condition number (a ratio of
  singular values) can differ by up to a factor `n`.
- `_inverse` is a dense `O(n^3)` Gauss–Jordan elimination, not an iterative
  refinement; for extremely ill-conditioned matrices its own error is visible.
- The accept experiment uses random dense matrices. Random data rarely
  approaches the worst case, which is exactly why the Wilkinson matrix and the
  tiny-pivot matrix are constructed deterministically instead.
- Growth factor is a worst-case *bound ingredient*; a large growth factor does
  not by itself make a particular right-hand side inaccurate (step 5 hints at
  this).

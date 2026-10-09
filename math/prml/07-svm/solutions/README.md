# Solutions — support vector machines

`svm.py` is the reference implementation of the graded functions, plus the given
scaffolding (`_clip`, `dual_objective`, `_project`) and the demo. Run the checker
against it by copying `svm.py` and `check.py` into one directory:

```bash
python3 check.py --all   # 5/5 passing
```

## Expected demo output

`python3 svm.py` from this directory prints:

```
Separable set, soft margin C = 10, linear kernel
  alphas = [0.0, 0.0, 2.0, 2.0, 0.0]
  support vectors = [2, 3], b = -1.000000
  margin 2/||w|| = 1.000000
  f(-2.0) = -5.000000   t = -1   margin = +5.000000
  f(-1.0) = -3.000000   t = -1   margin = +3.000000
  f(+0.0) = -1.000000   t = -1   margin = +1.000000
  f(+1.0) = +1.000000   t = +1   margin = +1.000000
  f(+2.0) = +3.000000   t = +1   margin = +3.000000

Non-separable set: hard versus soft margin
  hard margin: infeasible -> the hard margin is infeasible: the dual is unbounded below on non-separable data
  soft margin C = 1: b = 1.000000, margin = inf
  alphas = [0.5, 1.0, 0.5] (x = 1 saturates at C; x = 0, 2 are free on-margin support vectors)
```

What the lines show:

- The separable set `[-2, -1, 0, 1, 2]` with labels `-,-,-,+,+` has two support
  vectors, the points `x = 0` and `x = 1` sitting exactly on the margin
  (`t f(x) = 1`). Every other point has `a_i = 0` and a margin `> 1`.
- The margin `2 / ||w|| = 1` with `b = -1`: the boundary is at `x = 1/2`, halfway
  between the two support vectors.
- On the non-separable set `[0, 1, 2]` with labels `+,-,+`, the hard margin has no
  solution (the dual is unbounded below), so `smo` raises. The soft margin `C = 1`
  returns `a = [0.5, 1, 0.5]`: weight on all three conflicting points, and the
  decision function is a constant (here `w = 0`), so the reported geometric margin
  is infinite. That degeneracy is a genuine property of the tiny linear problem, not
  a bug; step 4 uses an RBF kernel where the soft margin stays finite.

The exact floating-point digits depend on the platform; the qualitative behaviour
and the pass/fail verdicts do not.

## How it works

- **SMO.** Each iteration picks a KKT-violating point `i`, a random second point
  `j`, and solves the two-variable subproblem in closed form before clipping to the
  feasible box `[L, H]`. A full pass with no changes, repeated `max_passes` times,
  means the KKT conditions hold; by convexity that is the dual optimum.
- **Support vectors.** The complementary slackness conditions make `a_i = 0` for
  every non-support vector, so `support_vectors` is just the threshold `a_i > tol`.
- **Bias.** Every free support vector gives a candidate
  `b = t_i - sum_j a_j t_j k(x_i, x_j)`; the reference averages the candidates.
- **Margin.** `||w||^2 = sum_ij a_i a_j t_i t_j k(x_i, x_j)` is assembled from the
  support vectors and the margin is `2 / ||w||`, cross-checked against the linear
  primal `2 / |sum_i a_i t_i x_i|`.

## Mutation testing

```bash
python3 .claude/skills/graded-module/scripts/mutate.py \
    math/prml/07-svm math/prml/07-svm/_build/mutations.py
```

prints `CAUGHT` for all five planted bugs. A `MISSED` line would mean a check is too
weak; strengthen the check, never the mutation.

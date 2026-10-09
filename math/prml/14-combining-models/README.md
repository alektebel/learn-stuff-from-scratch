# Combining models: CART, AdaBoost and bagging

Ensemble methods from scratch. Implements chapter 14 of Bishop, *Pattern
Recognition and Machine Learning* (`bishop:14`). The argument is restated here,
never copied: classification trees grown by minimising a weighted impurity,
AdaBoost's exponential reweighting of a weak learner, and bootstrap aggregation
of trees.

**Status: not built.** `combine.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`combine.py`, eleven graded functions. The purity helpers (`_impurity`,
`_majority`), the demo and its data builders are given: they are infrastructure,
not the learners themselves.

| Function | What it does |
|---|---|
| `gini(ps)` | Gini impurity `1 - sum p^2` for a group's class proportions |
| `entropy(ps)` | Shannon entropy `-sum p log2 p` in bits (a second impurity) |
| `best_split(Xs, ys, weights, impurity, min_leaf)` | the feature/threshold minimising the **weighted** child impurity |
| `fit_tree(Xs, ys, depth, min_leaf, weights, impurity)` | recursive CART; returns a nested `{feature, threshold, left, right, label}` node |
| `predict_tree(tree, x)` | walk a fitted tree to a leaf |
| `decision_stump(Xs, ys, weights)` | the best depth-1 weak learner and its weighted error |
| `predict_stump(stump, x)` | apply a one-level cut |
| `adaboost(Xs, ys, rounds)` | the stumps, alphas, error trajectory and bounds |
| `adaboost_predict(result, Xs)` | the combined sign vote as 0/1 |
| `bagging(Xs, ys, n_models, rng, depth, min_leaf)` | bootstrap-aggregated trees and the ensemble error |
| `bagging_predict(models, x)` | the ensemble's majority vote |

Trees and stumps are plain dicts so the checker can inspect them without sharing
code: a tree node carries `feature`, `threshold`, `left`, `right`, `label`, and a
leaf has `feature is None`; a stump is the same shape with constant labels as its
"children".

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A
step that asserts and fails is a **FAIL**; an exception is an **ERROR**. The
checks import your `combine.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | a CART tree fits a separable set with zero error and its first split strictly improves the impurity; with lopsided weights `best_split` returns the **weighted** optimum the checker computes by brute force |
| 2 | the depth-1 stump is a valid weak learner (`0 < eps < 0.5`) matching the checker's brute-force best cut, and `alpha_t = 0.5 ln((1 - eps_t)/eps_t)` |
| 3 | **ACCEPT**: AdaBoost's training error is non-increasing and bounded by `prod_t 2 sqrt(eps_t (1 - eps_t))`; the reported bound matches an independent product, `exp(-2 sum_t gamma_t^2)` holds and is looser, and the final weights match an independent replay of the renormalised update |
| 4 | **ACCEPT**: bootstrap resampling makes the base trees differ and the bagged ensemble beats a single overfit tree on held-out data |
| 5 | **LIMIT**: with two mislabelled points, AdaBoost's weight mass concentrates on them, their weights exceed every clean point's, and the boosted classifier fits the noisy labels exactly |

The checker carries its own `_best_split_ref`, `_best_stump_ref` and
`_weights_ref`, so the accept criteria are measured against independent
implementations, not against a restatement of yours.

## Design decisions

- **A shared node schema for trees and stumps.** Stumps store constant `left` /
  `right` labels instead of child nodes, so `predict_stump` is a one-level
  `predict_tree` and the checker can replay AdaBoost without your pruning code.
- **Weighted impurity everywhere.** `best_split` divides the weighted child
  impurities by the total weight; with `weights=None` the "weights" are plain
  counts. This is the one function that also serves `fit_tree` and, via weighted
  majorities, the stump.
- **`min_leaf` guards the split search.** No candidate that would leave fewer
  than `min_leaf` points on a side is considered; a node that cannot split becomes
  a majority leaf.
- **0/1 targets outside, +1/-1 inside AdaBoost.** The public data uses 0/1 labels;
  the reweighting `w_i *= exp(-alpha y_i h_i)` needs signs, so `adaboost` converts
  once and returns the internal labels.
- **Bagging samples with replacement, `n` draws per model.** With-replacement
  bootstrap is what makes the base trees differ; drawing a permutation leaves the
  ensemble equal to a single tree and kills the variance reduction.
- **The product bound is the headline ACCEPT; the exponential bound is the
  tighter theory.** `2 sqrt(eps(1-eps)) = sqrt(1 - 4 gamma^2) <= exp(-2 gamma^2)`,
  so the product of the first is below `exp(-2 sum gamma^2)`.

## Mutation table

Every planted bug in `_build/mutations.py` is caught by the step it names:

| Mutation | Caught by |
|---|---|
| `best_split` minimises the plain count, ignoring the weights | step 1 (split and score disagree with the weighted brute force) |
| `alpha` drops the log (`0.5 (1-eps)/eps`) | step 2 (alpha differs from `0.5 ln((1-eps)/eps)`) |
| the weight update never renormalises | step 3 (the returned weights are not a distribution and miss the replay) |
| bagging samples without replacement | step 4 (the base trees are identical and the ensemble does not improve) |
| the limit case reports an even weight spread | step 5 (no concentration, no weight above `2/n`) |

## Open questions (no answers here)

- A single test-set split decides step 4's accept. Why is bagging's advantage a
  statement about the *variance* of the base learner, and when does averaging bias
  instead?
- Step 5 shows the weights concentrating on mislabelled points. What does the
  combined classifier's decision function converge to as the rounds grow, and why
  is that not the Bayes rule?
- `best_split` scans midpoint thresholds and is therefore `O(n log n)` per feature.
  What changes if the tree is allowed to split on a subset of features (random
  forests), and why does that trade bias for variance?
- AdaBoost minimises the exponential loss. Where does that loss's sensitivity to
  label noise come from, and how do the weights on the mislabelled points behave as
  `rounds -> infinity`?

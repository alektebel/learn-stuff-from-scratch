"""Combining models from scratch: CART, AdaBoost and bagging.

Pure standard library (``math`` and ``random`` only). In this template every
graded function raises ``NotImplementedError``; ``check.py`` grades them and
``solutions/combine.py`` is the reference.

The three learners share one interface contract:

* a *tree node* is a plain dict::

      {"feature": int|None, "threshold": float|None,
       "left": node|None, "right": node|None, "label": int}

  ``feature is None`` marks a leaf and ``label`` holds its prediction.

* a *stump* is the same shape but its children are constant labels::

      {"feature": int|None, "threshold": float|None,
       "left": label, "right": label, "label": label}

Run ``python3 combine.py`` for a small end-to-end demo.
"""

import math
import random


# ---------------------------------------------------------------------------
# Impurity measures
# ---------------------------------------------------------------------------

def gini(ps):
    """Gini impurity ``1 - sum p^2`` for an iterable of class proportions."""
    # TODO: Gini impurity of a group: 1 - sum_c p_c^2, where p_c is the fraction of the group in class c. It is the default split criterion.
    raise NotImplementedError("gini")


def entropy(ps):
    """Shannon entropy in bits, ``-sum p log2 p`` (0 log 0 = 0)."""
    # TODO: Shannon entropy -sum_c p_c log2 p_c in bits; skip classes with p = 0 so you never take log(0). A second, interchangeable impurity measure.
    raise NotImplementedError("entropy")


def _impurity(ys, weights, measure):
    """Impurity of a group given raw labels and optional weights."""
    total = 0.0
    counts = {}
    if weights is None:
        for y in ys:
            counts[y] = counts.get(y, 0.0) + 1.0
        total = float(len(ys))
    else:
        for y, w in zip(ys, weights):
            counts[y] = counts.get(y, 0.0) + w
            total += w
    if total <= 0.0:
        return 0.0
    return measure([c / total for c in counts.values()])


def _majority(ys, weights=None):
    """Weighted majority label; ties fall back to the smallest label."""
    totals = {}
    if weights is None:
        for y in ys:
            totals[y] = totals.get(y, 0.0) + 1.0
    else:
        for y, w in zip(ys, weights):
            totals[y] = totals.get(y, 0.0) + w
    best_y = None
    best_w = None
    for y, w in totals.items():
        if best_w is None or w > best_w + 1e-15 or (
                abs(w - best_w) <= 1e-15 and y < best_y):
            best_y, best_w = y, w
    return best_y


# ---------------------------------------------------------------------------
# CART
# ---------------------------------------------------------------------------

def best_split(Xs, ys, weights=None, impurity=gini, min_leaf=1):
    """Best feature/threshold by *weighted* impurity.

    Candidate thresholds are the midpoints of consecutive distinct values of a
    feature. Returns ``(feature, threshold, score)`` where ``score`` is
    ``(W_left * imp_left + W_right * imp_right) / W_total`` (with ``W`` plain
    counts when ``weights is None``), or ``None`` if no split is possible.
    """
    # TODO: Try every feature and every midpoint between consecutive distinct values. Score a cut by the WEIGHTED child impurity (W_left * imp_left + W_right * imp_right) / W_total; plain counts are wrong whenever sample weights are passed. Return (feature, threshold, score) for the minimum, or None if no cut leaves min_leaf points on each side.
    raise NotImplementedError("best_split")


def fit_tree(Xs, ys, depth, min_leaf=1, weights=None, impurity=gini):
    """Fit a CART classifier and return the root nested-dict node."""
    # TODO: Recursive CART. At each node take the (weighted) majority label, stop on depth 0, a pure node, or no valid split, otherwise split on best_split and recurse on the two partitions. Return the nested dict {feature, threshold, left, right, label}.
    raise NotImplementedError("fit_tree")


def predict_tree(tree, x):
    """Walk a fitted tree to a leaf and return its label."""
    # TODO: Walk from the root: while feature is not None, go left when x[feature] <= threshold and right otherwise; return the leaf's label.
    raise NotImplementedError("predict_tree")


# ---------------------------------------------------------------------------
# AdaBoost
# ---------------------------------------------------------------------------

def decision_stump(Xs, ys, weights):
    """Best depth-1 weak learner under ``weights``.

    Returns ``(stump, error)`` where ``error`` is the weighted fraction of
    points the stump gets wrong. Each side of every axis cut is labelled by its
    weighted majority, so the chosen stump is the best single cut available.
    """
    # TODO: Depth-1 AdaBoost learner. For every feature and midpoint cut, label each side with its WEIGHTED majority and score the weighted fraction misclassified. Return (stump, error); a stump is {feature, threshold, left, right, label} with constant labels in the leaves. A good stump has error < 0.5.
    raise NotImplementedError("decision_stump")


def predict_stump(stump, x):
    """Apply a stump: leaf if ``feature is None``, else an axis-aligned cut."""
    # TODO: Apply a stump like a one-level tree: leaf if feature is None, otherwise left when x[feature] <= threshold and right otherwise.
    raise NotImplementedError("predict_stump")


def adaboost(Xs, ys, rounds):
    """Discrete AdaBoost over decision stumps.

    Returns a dict with ``stumps``, ``alphas``, ``errors`` (each stump's
    weighted error), ``train_err`` (the combined classifier's 0/1 error after
    each round), ``bound`` (the product bound
    ``prod_t 2 sqrt(eps_t (1-eps_t))``), ``exp_bound``
    (``exp(-2 sum_t gamma_t^2)`` with ``gamma_t = 1/2 - eps_t``),
    ``weights`` (final normalised sample weights), ``weight_hist`` (the weights
    after each round) and ``labels`` (the internal +-1 targets).
    """
    # TODO: Discrete AdaBoost. Start with uniform weights; each round take the best stump (error eps), set alpha = 0.5 ln((1 - eps)/eps), multiply w_i *= exp(-alpha y_i h_t(x_i)) with targets y in {+1,-1}, and RENORMALISE the weights. Record the combined classifier's training error, the product bound prod 2 sqrt(eps(1-eps)) and exp(-2 sum gamma^2), gamma = 1/2 - eps.
    raise NotImplementedError("adaboost")


def adaboost_predict(result, Xs):
    """Combined AdaBoost prediction (0/1) for each row of ``Xs``."""
    # TODO: Combined vote: predict 1 when sum_t alpha_t h_t(x) >= 0, else 0.
    raise NotImplementedError("adaboost_predict")


# ---------------------------------------------------------------------------
# Bagging
# ---------------------------------------------------------------------------

def bagging(Xs, ys, n_models, rng, depth=6, min_leaf=1):
    """Bootstrap-aggregate CART trees (sampling *with* replacement).

    Returns ``(models, train_error)``: the list of bootstrap trees and the
    majority-vote training error of the ensemble.
    """
    # TODO: For each of n_models draw n indices WITH replacement (rng.randrange), fit a tree on the bootstrap sample, then return (models, train_error). Uniform resampling without replacement would make every tree identical and defeat the variance reduction.
    raise NotImplementedError("bagging")


def bagging_predict(models, x):
    """Majority vote (0/1) of an ensemble of trees on one point."""
    # TODO: Majority vote of the ensemble on one point: 1 when more than half the trees predict 1, else 0.
    raise NotImplementedError("bagging_predict")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _diagonal_grid():
    """A 3x3 grid labelled by ``x0 + x1 > 0`` (no single stump is perfect)."""
    xs = [[float(i), float(j)] for i in (-1, 0, 1) for j in (-1, 0, 1)]
    ys = [1 if x[0] + x[1] > 0.0 else 0 for x in xs]
    return xs, ys


def _noisy_columns():
    """Two clean columns plus two flipped points: AdaBoost's noise limit case."""
    xs, ys = [], []
    for x0 in (-1.0, 1.0):
        for x1 in (-1.0, -0.5, 0.0, 0.5, 1.0):
            xs.append([x0, x1])
            ys.append(1 if x0 > 0 else 0)
    ys[1] = 1 - ys[1]
    ys[7] = 1 - ys[7]
    return xs, ys


def demo():
    print("CART")
    xs = [[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [2.0, 1.0],
          [3.0, 2.0], [4.0, 3.0], [4.0, 2.0], [5.0, 3.0]]
    ys = [0, 0, 0, 0, 1, 1, 1, 1]
    tree = fit_tree(xs, ys, depth=3)
    print("  fit:", [predict_tree(tree, x) for x in xs], "(want", ys, ")")
    print("  best split:", best_split(xs, ys), "vs parent gini", gini([0.5, 0.5]))

    print("\nAdaBoost (3x3 diagonal grid, weak stumps)")
    gx, gy = _diagonal_grid()
    res = adaboost(gx, gy, rounds=10)
    print("  errors :", [round(e, 4) for e in res["errors"]])
    print("  alphas :", [round(a, 4) for a in res["alphas"]])
    print("  train  :", res["train_err"])
    print("  bound  : prod 2 sqrt(eps(1-eps)) =", round(res["bound"], 6))
    print("  exp    : exp(-2 sum gamma^2)   =", round(res["exp_bound"], 6))

    print("\nBagging (noisy 1-D threshold)")
    train_x, train_y = _noisy_threshold(200, 0.20, random.Random(11))
    test_x, test_y = _noisy_threshold(400, 0.20, random.Random(22))
    single = fit_tree(train_x, train_y, depth=6)
    err_single = sum(predict_tree(single, x) != y
                     for x, y in zip(test_x, test_y)) / len(test_y)
    models, _ = bagging(train_x, train_y, 25, random.Random(11), depth=6)
    err_bag = sum(bagging_predict(models, x) != y
                  for x, y in zip(test_x, test_y)) / len(test_y)
    print(f"  single tree test error : {err_single:.3f}")
    print(f"  bagged  test error     : {err_bag:.3f}")

    print("\nLIMIT: AdaBoost under label noise")
    nx, ny = _noisy_columns()
    noise_res = adaboost(nx, ny, rounds=300)
    true = [1 if x[0] > 0 else 0 for x in nx]
    noise_idx = [i for i, y in enumerate(ny) if y != true[i]]
    w = noise_res["weights"]
    print("  final training error  :", noise_res["train_err"][-1], "(overfits noise)")
    print("  max sample weight     :", round(max(w), 4),
          f"(uniform would be {1.0 / len(w):.4f})")
    print("  weight on noise points:", round(sum(w[i] for i in noise_idx), 4))
    print("  noise indices         :", noise_idx,
          "weights", [round(w[i], 4) for i in noise_idx])


def _noisy_threshold(n, noise, rng):
    xs, ys = [], []
    for _ in range(n):
        x = rng.random()
        y = 1 if x > 0.5 else 0
        if rng.random() < noise:
            y = 1 - y
        xs.append([x])
        ys.append(y)
    return xs, ys


if __name__ == "__main__":
    demo()

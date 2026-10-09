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
    return 1.0 - sum(p * p for p in ps)


def entropy(ps):
    """Shannon entropy in bits, ``-sum p log2 p`` (0 log 0 = 0)."""
    total = 0.0
    for p in ps:
        if p > 1e-15:
            total -= p * math.log2(p)
    return total


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
    n = len(ys)
    if n < 2 or not Xs or len(Xs[0]) == 0:
        return None
    total_w = float(n) if weights is None else float(sum(weights))
    best = None
    for j in range(len(Xs[0])):
        values = sorted({float(Xs[i][j]) for i in range(n)})
        for lo, hi in zip(values, values[1:]):
            t = (lo + hi) / 2.0
            left = [i for i in range(n) if Xs[i][j] <= t]
            right = [i for i in range(n) if Xs[i][j] > t]
            if len(left) < min_leaf or len(right) < min_leaf:
                continue
            if weights is None:
                wl, wr = float(len(left)), float(len(right))
                il = _impurity([ys[i] for i in left], None, impurity)
                ir = _impurity([ys[i] for i in right], None, impurity)
            else:
                wl = sum(weights[i] for i in left)
                wr = sum(weights[i] for i in right)
                il = _impurity([ys[i] for i in left],
                               [weights[i] for i in left], impurity)
                ir = _impurity([ys[i] for i in right],
                               [weights[i] for i in right], impurity)
            score = (wl * il + wr * ir) / total_w
            if best is None or score < best[2] - 1e-15:
                best = (j, t, score)
    return best


def fit_tree(Xs, ys, depth, min_leaf=1, weights=None, impurity=gini):
    """Fit a CART classifier and return the root nested-dict node."""
    if not ys:
        return {"feature": None, "threshold": None,
                "left": None, "right": None, "label": 0}
    label = _majority(ys, weights)
    leaf = {"feature": None, "threshold": None,
            "left": None, "right": None, "label": label}
    if depth <= 0 or len(set(ys)) <= 1 or len(ys) < 2 * min_leaf:
        return leaf
    split = best_split(Xs, ys, weights, impurity, min_leaf)
    if split is None:
        return leaf
    j, t, _ = split
    left_idx = [i for i in range(len(ys)) if Xs[i][j] <= t]
    right_idx = [i for i in range(len(ys)) if Xs[i][j] > t]
    if not left_idx or not right_idx:
        return leaf
    node = {"feature": j, "threshold": t, "left": None, "right": None,
            "label": label}
    node["left"] = fit_tree(
        [Xs[i] for i in left_idx], [ys[i] for i in left_idx], depth - 1,
        min_leaf, None if weights is None else [weights[i] for i in left_idx],
        impurity)
    node["right"] = fit_tree(
        [Xs[i] for i in right_idx], [ys[i] for i in right_idx], depth - 1,
        min_leaf, None if weights is None else [weights[i] for i in right_idx],
        impurity)
    return node


def predict_tree(tree, x):
    """Walk a fitted tree to a leaf and return its label."""
    while tree["feature"] is not None:
        if x[tree["feature"]] <= tree["threshold"]:
            tree = tree["left"]
        else:
            tree = tree["right"]
    return tree["label"]


# ---------------------------------------------------------------------------
# AdaBoost
# ---------------------------------------------------------------------------

def decision_stump(Xs, ys, weights):
    """Best depth-1 weak learner under ``weights``.

    Returns ``(stump, error)`` where ``error`` is the weighted fraction of
    points the stump gets wrong. Each side of every axis cut is labelled by its
    weighted majority, so the chosen stump is the best single cut available.
    """
    n = len(ys)
    total_w = float(sum(weights))
    best = None
    for j in range(len(Xs[0])):
        values = sorted({float(Xs[i][j]) for i in range(n)})
        for lo, hi in zip(values, values[1:]):
            t = (lo + hi) / 2.0
            left = [i for i in range(n) if Xs[i][j] <= t]
            right = [i for i in range(n) if Xs[i][j] > t]
            if not left or not right:
                continue
            ll = _majority([ys[i] for i in left], [weights[i] for i in left])
            rl = _majority([ys[i] for i in right], [weights[i] for i in right])
            err = 0.0
            for i in left:
                if ys[i] != ll:
                    err += weights[i]
            for i in right:
                if ys[i] != rl:
                    err += weights[i]
            err /= total_w
            if best is None or err < best[1] - 1e-15:
                stump = {"feature": j, "threshold": t, "left": ll, "right": rl,
                         "label": ll}
                best = (stump, err)
    if best is None:
        label = _majority(ys, weights)
        stump = {"feature": None, "threshold": None,
                 "left": label, "right": label, "label": label}
        err = sum(w for y, w in zip(ys, weights) if y != label) / total_w
        return stump, err
    return best


def predict_stump(stump, x):
    """Apply a stump: leaf if ``feature is None``, else an axis-aligned cut."""
    if stump["feature"] is None:
        return stump["label"]
    if x[stump["feature"]] <= stump["threshold"]:
        return stump["left"]
    return stump["right"]


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
    n = len(ys)
    labels = [1 if y >= 0.5 else -1 for y in ys]
    w = [1.0 / n] * n
    stumps, alphas, errors, traj, gammas, weight_hist = [], [], [], [], [], []
    bound = 1.0
    for _ in range(rounds):
        stump, eps = decision_stump(Xs, labels, w)
        if eps <= 1e-12 or eps >= 0.5 - 1e-12:
            break
        alpha = 0.5 * math.log((1.0 - eps) / eps)
        stumps.append(stump)
        alphas.append(alpha)
        errors.append(eps)
        gammas.append(0.5 - eps)
        bound *= 2.0 * math.sqrt(eps * (1.0 - eps))
        new_w = []
        for i in range(n):
            pred = predict_stump(stump, Xs[i])
            new_w.append(w[i] * math.exp(-alpha * labels[i] * pred))
        total = sum(new_w)
        w = [v / total for v in new_w]
        weight_hist.append(list(w))
        wrong = 0
        for i in range(n):
            score = sum(a * predict_stump(s, Xs[i])
                        for s, a in zip(stumps, alphas))
            if (1 if score >= 0.0 else -1) != labels[i]:
                wrong += 1
        traj.append(wrong / n)
    exp_bound = math.exp(-2.0 * sum(g * g for g in gammas))
    return {"stumps": stumps, "alphas": alphas, "errors": errors,
            "train_err": traj, "bound": bound, "exp_bound": exp_bound,
            "weights": w, "weight_hist": weight_hist, "labels": labels}


def adaboost_predict(result, Xs):
    """Combined AdaBoost prediction (0/1) for each row of ``Xs``."""
    out = []
    for x in Xs:
        score = sum(a * predict_stump(s, x)
                    for s, a in zip(result["stumps"], result["alphas"]))
        out.append(1 if score >= 0.0 else 0)
    return out


# ---------------------------------------------------------------------------
# Bagging
# ---------------------------------------------------------------------------

def bagging(Xs, ys, n_models, rng, depth=6, min_leaf=1):
    """Bootstrap-aggregate CART trees (sampling *with* replacement).

    Returns ``(models, train_error)``: the list of bootstrap trees and the
    majority-vote training error of the ensemble.
    """
    n = len(ys)
    models = []
    for _ in range(n_models):
        idx = [rng.randrange(n) for _ in range(n)]
        models.append(fit_tree([Xs[i] for i in idx], [ys[i] for i in idx],
                               depth, min_leaf))
    wrong = 0
    for x, y in zip(Xs, ys):
        votes = sum(predict_tree(m, x) for m in models)
        pred = 1 if 2 * votes > n_models else 0
        if pred != y:
            wrong += 1
    return models, wrong / n


def bagging_predict(models, x):
    """Majority vote (0/1) of an ensemble of trees on one point."""
    votes = sum(predict_tree(m, x) for m in models)
    return 1 if 2 * votes > len(models) else 0


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

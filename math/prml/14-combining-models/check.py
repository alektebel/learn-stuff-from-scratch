"""
Progress checker for the PRML-combining-models templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that
is simply the next thing to write. Nothing here imports solutions/. It tests YOUR
code.

The checker carries its own weighted-impurity brute force (``_best_split_ref`` and
``_best_stump_ref``) and its own AdaBoost weight recursion (``_weights_ref``), so
the accept criteria are measured against independent implementations, not against a
restatement of the learner's. The accept criteria are: AdaBoost's training error
decreases monotonically and is bounded by the product
``prod_t 2 sqrt(eps_t (1-eps_t))`` (and by ``exp(-2 sum_t gamma_t^2)``), and bagging
reduces the variance of a single overfit tree. The limit case is AdaBoost under
label noise: the weights concentrate on the mislabelled points and the ensemble
overfits them.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# The checker's own references (never the learner's)
# ---------------------------------------------------------------------------

def _impurity_ref(ys, ws, measure):
    """Impurity of a weighted group, computed from counts (the checker's way)."""
    total = 0.0
    counts = {}
    for y, w in zip(ys, ws):
        counts[y] = counts.get(y, 0.0) + w
        total += w
    if total <= 0.0:
        return 0.0
    return measure([c / total for c in counts.values()])


def _gini_ref(ps):
    return 1.0 - sum(p * p for p in ps)


def _best_split_ref(Xs, ys, weights=None, min_leaf=1):
    """Brute-force best weighted split; returns ``(feature, threshold, score)``."""
    n = len(ys)
    total = float(n) if weights is None else float(sum(weights))
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
                wl = float(len(left))
                wr = float(len(right))
                il = _impurity_ref([ys[i] for i in left], [1.0] * len(left), _gini_ref)
                ir = _impurity_ref([ys[i] for i in right], [1.0] * len(right), _gini_ref)
            else:
                wl = sum(weights[i] for i in left)
                wr = sum(weights[i] for i in right)
                il = _impurity_ref([ys[i] for i in left], [weights[i] for i in left], _gini_ref)
                ir = _impurity_ref([ys[i] for i in right], [weights[i] for i in right], _gini_ref)
            score = (wl * il + wr * ir) / total
            if best is None or score < best[2] - 1e-15:
                best = (j, t, score)
    return best


def _maj_ref(ys, ws):
    totals = {}
    for y, w in zip(ys, ws):
        totals[y] = totals.get(y, 0.0) + w
    return max(sorted(totals), key=lambda y: totals[y])


def _best_stump_ref(Xs, ys, weights):
    """Brute-force best weighted stump; returns ``(feature, threshold, error)``."""
    n = len(ys)
    total = float(sum(weights))
    best = None
    for j in range(len(Xs[0])):
        values = sorted({float(Xs[i][j]) for i in range(n)})
        for lo, hi in zip(values, values[1:]):
            t = (lo + hi) / 2.0
            left = [i for i in range(n) if Xs[i][j] <= t]
            right = [i for i in range(n) if Xs[i][j] > t]
            if not left or not right:
                continue
            ll = _maj_ref([ys[i] for i in left], [weights[i] for i in left])
            rl = _maj_ref([ys[i] for i in right], [weights[i] for i in right])
            err = (sum(weights[i] for i in left if ys[i] != ll)
                   + sum(weights[i] for i in right if ys[i] != rl)) / total
            if best is None or err < best[2] - 1e-15:
                best = (j, t, err)
    return best


def _apply_stump_ref(stump, x):
    if stump["feature"] is None:
        return stump["label"]
    if x[stump["feature"]] <= stump["threshold"]:
        return stump["left"]
    return stump["right"]


def _weights_ref(Xs, ys, stumps, alphas):
    """Reproduce the AdaBoost weight recursion from the returned weak learners."""
    n = len(ys)
    labels = [1 if y >= 0.5 else -1 for y in ys]
    w = [1.0 / n] * n
    for stump, alpha in zip(stumps, alphas):
        new_w = []
        for i in range(n):
            new_w.append(w[i] * math.exp(-alpha * labels[i]
                                         * _apply_stump_ref(stump, Xs[i])))
        total = sum(new_w)
        w = [v / total for v in new_w]
    return w


def _close(a, b, tol):
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# Fixed data (deterministic)
# ---------------------------------------------------------------------------

# Two well-separated clusters; one feature0 cut separates them perfectly.
TREE_XS = [[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [2.0, 1.0],
           [3.0, 2.0], [4.0, 3.0], [4.0, 2.0], [5.0, 3.0]]
TREE_YS = [0, 0, 0, 0, 1, 1, 1, 1]

# Interleaved labels with lopsided weights. The weighted-best split is at 1.5
# (grouping the two heavy points) while the plain-count best split is at 0.5,
# so this set exposes any unweighted shortcut in best_split.
WS_XS = [[0.0], [1.0], [2.0], [3.0]]
WS_YS = [0, 1, 0, 1]
WS_W = [1.0, 10.0, 10.0, 1.0]

# A 3x3 grid labelled by x0 + x1 > 0: no single stump is perfect, so several
# rounds are needed and the error falls in steps.
ADA_XS = [[float(i), float(j)] for i in (-1, 0, 1) for j in (-1, 0, 1)]
ADA_YS = [1 if x[0] + x[1] > 0.0 else 0 for x in ADA_XS]


def _noisy_threshold(n, noise, seed):
    """1-D threshold rule with symmetric label noise."""
    rng = random.Random(seed)
    xs, ys = [], []
    for _ in range(n):
        x = rng.random()
        y = 1 if x > 0.5 else 0
        if rng.random() < noise:
            y = 1 - y
        xs.append([x])
        ys.append(y)
    return xs, ys


# ---------------------------------------------------------------------------
# Step 1: a CART tree fits separable data, and splits help
# ---------------------------------------------------------------------------

def check_decision_tree() -> None:
    from combine import gini, best_split, fit_tree, predict_tree

    tree = fit_tree(TREE_XS, TREE_YS, depth=3)
    preds = [predict_tree(tree, x) for x in TREE_XS]
    assert preds == list(TREE_YS), (
        "the tree must fit this separable training set with zero error; "
        f"got {preds}, want {TREE_YS}")

    parent = gini([0.5, 0.5])
    split = best_split(TREE_XS, TREE_YS)
    assert split is not None, "a split exists for this set, best_split returned None"
    assert split[2] < parent - 1e-9, (
        "the best split must strictly improve the impurity over the parent node; "
        f"split score {split[2]:.6f} is not below the parent gini {parent:.6f}")

    # Weighted worst case: the split that minimises *weighted* impurity is at
    # 1.5, not the plain-count optimum at 0.5.
    got = best_split(WS_XS, WS_YS, WS_W)
    want = _best_split_ref(WS_XS, WS_YS, WS_W)
    assert got is not None, "best_split must find the weighted split"
    assert _close(got[2], want[2], 1e-9), (
        "best_split must score a candidate by the WEIGHTED child impurity "
        "(sum_i w_i * imp(child) / sum_i w_i), not by plain counts: "
        f"got score {got[2]:.6f}, want {want[2]:.6f}")
    assert got[0] == want[0] and _close(got[1], want[1], 1e-9), (
        "best_split must return the weighted-optimal feature/threshold; with these "
        f"lopsided weights that is {want[:2]}, but got {got[:2]}")


# ---------------------------------------------------------------------------
# Step 2: the decision stump and the AdaBoost step size
# ---------------------------------------------------------------------------

def check_stump_and_alpha() -> None:
    from combine import decision_stump, predict_stump, adaboost

    stump, eps = decision_stump(WS_XS, WS_YS, WS_W)
    assert stump is not None, "decision_stump must return a stump"
    assert 0.0 < eps < 0.5, (
        "the stump must be a valid weak learner on this signal: its weighted error "
        f"must lie strictly in (0, 0.5), got {eps:.6f}")
    assert stump["feature"] == 0, (
        f"the only informative feature is 0, got feature {stump['feature']}")
    ref = _best_stump_ref(WS_XS, WS_YS, WS_W)
    assert ref is not None and _close(eps, ref[2], 1e-9), (
        "the stump must be the weighted-majority cut that minimises the weighted "
        f"error: got eps {eps:.6f}, want {ref[2]:.6f}")

    result = adaboost(WS_XS, WS_YS, rounds=3)
    assert result["errors"], "adaboost must record at least one boosting round"
    e0 = result["errors"][0]
    a0 = result["alphas"][0]
    want = 0.5 * math.log((1.0 - e0) / e0)
    assert _close(a0, want, 1e-9), (
        "alpha_t must be 0.5 ln((1 - eps_t) / eps_t), the exact discrete-AdaBoost "
        f"step size: got {a0:.6f}, want {want:.6f} for eps = {e0:.6f}")
    # predict_stump must be the inverse of the stump's structure.
    for i, x in enumerate(WS_XS):
        side = "left" if x[0] <= stump["threshold"] else "right"
        assert predict_stump(stump, x) == stump[side], (
            f"predict_stump must apply the axis cut at feature {stump['feature']} "
            f"threshold {stump['threshold']}")


# ---------------------------------------------------------------------------
# Step 3 (ACCEPT): AdaBoost's error falls and obeys the product bound
# ---------------------------------------------------------------------------

def check_adaboost_bound() -> None:
    from combine import adaboost

    result = adaboost(ADA_XS, ADA_YS, rounds=10)
    traj = result["train_err"]
    assert len(traj) >= 3, (
        "this diagonal grid needs several boosting rounds; the error trajectory is "
        f"too short: {traj}")
    assert traj[-1] < traj[0], (
        "boosting must actually improve the combined classifier; the error did not "
        f"fall: {traj}")

    for t in range(1, len(traj)):
        assert traj[t] <= traj[t - 1] + 1e-12, (
            "the ACCEPT: AdaBoost's training error must be non-increasing round by "
            f"round; it rose from {traj[t - 1]} at round {t} to {traj[t]}")

    # Independent product bound from the reported per-round errors.
    bound = 1.0
    for eps in result["errors"]:
        bound *= 2.0 * math.sqrt(eps * (1.0 - eps))
    assert _close(result["bound"], bound, 1e-9), (
        "the reported bound must be the product prod_t 2 sqrt(eps_t (1 - eps_t)); "
        f"got {result['bound']:.6f}, want {bound:.6f}")
    assert traj[-1] <= result["bound"] + 1e-9, (
        "the ACCEPT: AdaBoost's training error is bounded by prod_t "
        f"2 sqrt(eps_t (1-eps_t)); error {traj[-1]:.6f} > bound {result['bound']:.6f}")

    # gamma_t = 1/2 - eps_t; the exponential bound also holds and is looser.
    gamma2 = sum((0.5 - eps) ** 2 for eps in result["errors"])
    exp_bound = math.exp(-2.0 * gamma2)
    assert _close(result["exp_bound"], exp_bound, 1e-9), (
        "the exponential bound exp(-2 sum_t gamma_t^2) must be reported "
        f"(gamma_t = 1/2 - eps_t): got {result['exp_bound']:.6f}, want {exp_bound:.6f}")
    assert result["bound"] <= result["exp_bound"] + 1e-9, (
        "2 sqrt(eps(1-eps)) = sqrt(1 - 4 gamma^2) <= exp(-2 gamma^2), so the product "
        f"bound must be no larger than the exponential one: {result['bound']:.6f} "
        f"vs {result['exp_bound']:.6f}")

    # The truth we froze present in the mutation: dropping the renormalisation breaks
    # the invariant that the sample distribution stays a distribution.
    total = sum(result["weights"])
    assert _close(total, 1.0, 1e-9), (
        "the AdaBoost weight update must renormalise the sample weights after every "
        f"round; the returned weights sum to {total:.6f}, not 1")
    want_w = _weights_ref(ADA_XS, ADA_YS, result["stumps"], result["alphas"])
    assert all(_close(a, b, 1e-9) for a, b in zip(result["weights"], want_w)), (
        "the final weights must be the renormalised exponential reweighting "
        "w_i *= exp(-alpha_t y_i h_t(x_i)): they disagree with an independent "
        f"replay; got {result['weights']}, want {want_w}")


# ---------------------------------------------------------------------------
# Step 4 (ACCEPT): bagging reduces variance
# ---------------------------------------------------------------------------

def check_bagging_variance() -> None:
    from combine import fit_tree, predict_tree, bagging, bagging_predict

    depth = 6
    n_models = 25
    train_x, train_y = _noisy_threshold(200, 0.20, seed=11)
    test_x, test_y = _noisy_threshold(400, 0.20, seed=22)

    single = fit_tree(train_x, train_y, depth=depth)
    single_err = sum(predict_tree(single, x) != y
                     for x, y in zip(test_x, test_y)) / len(test_y)
    models, _ = bagging(train_x, train_y, n_models, random.Random(11), depth=depth)
    assert len(models) == n_models, (
        f"bagging must return {n_models} base models, got {len(models)}")
    ens_err = sum(bagging_predict(models, x) != y
                  for x, y in zip(test_x, test_y)) / len(test_y)

    differ = False
    for a in range(len(models)):
        for b in range(a + 1, len(models)):
            for x in test_x:
                if predict_tree(models[a], x) != predict_tree(models[b], x):
                    differ = True
                    break
            if differ:
                break
        if differ:
            break
    assert differ, (
        "bootstrap resampling must make the base trees differ; here every tree is "
        "identical, which happens when the bootstrap draws WITHOUT replacement "
        "(or no resampling at all)")

    assert ens_err < single_err - 1e-9, (
        "the ACCEPT: averaging bootstrap trees must reduce variance and beat a single "
        f"overfit tree on held-out data; single {single_err:.4f} vs bagged "
        f"{ens_err:.4f}")


# ---------------------------------------------------------------------------
# Step 5 (LIMIT): AdaBoost under label noise concentrates on the noise
# ---------------------------------------------------------------------------

def _noisy_columns():
    """Two clean columns labelled by ``x0 > 0`` plus two flipped points."""
    xs, ys = [], []
    for x0 in (-1.0, 1.0):
        for x1 in (-1.0, -0.5, 0.0, 0.5, 1.0):
            xs.append([x0, x1])
            ys.append(1 if x0 > 0 else 0)
    ys[1] = 1 - ys[1]   # (-1, -0.5) labelled 1
    ys[7] = 1 - ys[7]   # (+1, +0.5) labelled 0
    return xs, ys


def check_label_noise_limit() -> None:
    from combine import adaboost

    xs, ys = _noisy_columns()
    true = [1 if x[0] > 0.0 else 0 for x in xs]
    noise_idx = [i for i, y in enumerate(ys) if y != true[i]]
    result = adaboost(xs, ys, rounds=300)
    w = result["weights"]
    assert len(w) == len(ys), "weights must be one per training point"
    n = len(w)

    max_w = max(w)
    assert max_w > 2.0 / n, (
        "the LIMIT CASE: as boosting runs, the maximum sample weight must grow well "
        f"above the uniform 1/n = {1.0 / n:.4f}; the largest weight is only "
        f"{max_w:.4f}")

    top = sorted(range(n), key=lambda i: -w[i])[:len(noise_idx)]
    assert set(top) == set(noise_idx), (
        "the mislabelled points must carry the largest weights; the top "
        f"{len(noise_idx)} weights sit on {sorted(top)} but the noise is at "
        f"{noise_idx} (weights {[round(w[i], 4) for i in range(n)]})")

    noise_weight = sum(w[i] for i in noise_idx)
    assert noise_weight > 0.4, (
        "the weight mass must concentrate on the mislabelled points; they carry only "
        f"{noise_weight:.4f} of the total, not the {len(noise_idx) / n:.4f} of a "
        "uniform spread")

    min_noise = min(w[i] for i in noise_idx)
    max_clean = max(w[i] for i in range(n) if i not in noise_idx)
    assert min_noise > max_clean, (
        "every mislabelled point must outweigh every clean point once boosting has "
        f"concentrated; min noise {min_noise:.4f} <= max clean {max_clean:.4f}")

    assert result["train_err"][-1] <= 1e-12, (
        "the LIMIT CASE reports overfitting to noise: the boosted classifier must "
        f"fit the noisy training labels perfectly (0 training error), got "
        f"{result['train_err'][-1]}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("combine.py", "a CART tree fits separable data and splits improve the impurity", check_decision_tree),
    ("combine.py", "the decision stump is valid and alpha is the AdaBoost step size", check_stump_and_alpha),
    ("combine.py", "ACCEPT: AdaBoost's error falls and obeys the product bound", check_adaboost_bound),
    ("combine.py", "ACCEPT: bagging reduces variance over a single tree", check_bagging_variance),
    ("combine.py", "LIMIT: label noise concentrates AdaBoost's weights on noise", check_label_noise_limit),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}PRML Combining Models From Scratch — progress check{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built ensemble methods from scratch.{RESET}")
        print(f"  {GREY}Run solutions/combine.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

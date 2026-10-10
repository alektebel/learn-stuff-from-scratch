"""Evals From Scratch — stage 7: what the judge is worth

SOLUTION. Kappa is the only statistic here that survives a skewed label set,
and the sweep is the only threshold choice that has a reason attached to it.
Both are three lines; the naive versions are shorter and wrong.
"""

DEFAULT_THRESHOLDS = (1.5, 2.5, 3.5, 4.5)


def confusion(judgments, labels):
    judgments, labels = list(judgments), list(labels)
    if len(judgments) != len(labels):
        raise ValueError(
            f"{len(judgments)} judgments against {len(labels)} labels: they are "
            f"the same rows in the same order")
    tp = fp = tn = fn = 0
    for judged, labelled in zip(judgments, labels):
        if judged and labelled:
            tp += 1
        elif judged:
            fp += 1
        elif labelled:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def agreement(judgments, labels):
    conf = confusion(judgments, labels)
    total = sum(conf.values())
    return (conf["tp"] + conf["tn"]) / total if total else 0.0


def cohen_kappa(judgments, labels):
    judgments, labels = list(judgments), list(labels)
    n = len(judgments)
    if n == 0:
        return 0.0
    conf = confusion(judgments, labels)
    observed = (conf["tp"] + conf["tn"]) / n
    judge_pass = (conf["tp"] + conf["fp"]) / n
    label_pass = (conf["tp"] + conf["fn"]) / n
    chance = judge_pass * label_pass + (1 - judge_pass) * (1 - label_pass)
    if abs(1.0 - chance) < 1e-12:
        return 1.0 if abs(observed - 1.0) < 1e-12 else 0.0
    return (observed - chance) / (1.0 - chance)


def _scores(conf):
    tp, fp, fn = conf["tp"], conf["fp"], conf["fn"]
    precision = 1.0 if tp == 0 and fp == 0 else (tp / (tp + fp) if tp else 0.0)
    recall = 1.0 if tp == 0 and fn == 0 else (tp / (tp + fn) if tp else 0.0)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def threshold_for(scores, labels, thresholds=None):
    scores, labels = list(scores), list(labels)
    if len(scores) != len(labels):
        raise ValueError(
            f"{len(scores)} scores against {len(labels)} labels")
    candidates = list(DEFAULT_THRESHOLDS if thresholds is None else thresholds)
    if not scores:
        raise ValueError(
            "no labelled rows: a sweep over no data reports a perfect F1 for "
            "every threshold, and whichever one it picks means nothing")
    if not candidates:
        raise ValueError("no thresholds to sweep")

    sweep = []
    for threshold in sorted(candidates):
        conf = confusion([score >= threshold for score in scores], labels)
        precision = conf["tp"] / (conf["tp"] + conf["fp"]) if conf["tp"] + conf["fp"] else 1.0
        recall = conf["tp"] / (conf["tp"] + conf["fn"]) if conf["tp"] + conf["fn"] else 1.0
        sweep.append({"threshold": threshold, "f1": _scores(conf),
                      "precision": precision, "recall": recall,
                      "confusion": conf})

    best = max(sweep, key=lambda row: (row["f1"], -row["threshold"]))
    return {"threshold": best["threshold"], "f1": best["f1"],
            "precision": best["precision"], "recall": best["recall"],
            "confusion": best["confusion"], "sweep": sweep}

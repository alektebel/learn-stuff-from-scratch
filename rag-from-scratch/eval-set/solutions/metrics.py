"""Retrieval metrics, abstention metrics and paired comparison (step 0 of the RAG plan).

Implements the metric half of `rag-from-scratch/README.md` step 0: recall@k, MRR,
nDCG@k, abstention precision and recall, latency, and a paired per-query comparison
helper whose statistics are copied from `harness-lab/eval/stats.py` (same formulas, a
separate copy: a graded module must not import across module boundaries).

DESIGN DECISION - recall for a no-answer query is defined as 0.0, not undefined.
    There is nothing to recall, so the family is excluded from being "good" and the
    abstention metrics are what grade it. The alternative (skipping undefined queries)
    makes the overall number silent about a family the system may be failing. Cost: the
    overall recall is dragged down by design; read it next to the abstention numbers.

DESIGN DECISION - nDCG uses exponential gain and a log2 discount.
    gain = 2^rel - 1, discount = 1/log2(rank + 1) with rank starting at 1. This is the
    standard Jarvelin & Kekalainen (2002) formulation and matches `sklearn`'s default
    for the binary case. Alternatives (linear gain, no discount) inflate the score and
    stop distinguishing a good top rank from a bad one; check.py holds this exact
    formulation to hand-computed values.

DESIGN DECISION - MRR reports the first relevant hit only.
    It answers "how far down is the first thing that matters", which is what a reranker
    or an answer stage depends on. It is blind to how many other relevant documents were
    found, so it is always reported alongside recall@k.

DESIGN DECISION - abstention is graded as a classification of *queries*.
    A prediction is "abstain" iff the ranked list is empty. For no-answer queries an
    abstention is a true positive; for answerable queries it is a false positive.
    Precision is over the abstentions the system chose; recall is over the queries that
    truly had no answer. Cost: a system that abstains on everything scores recall 1.0,
    so precision must be read with it.

DESIGN DECISION - paired comparison, not two independent samples.
    Two retrievers run on the same queries. The variance between queries dominates, and
    pairing cancels it; only the per-query differences carry signal. We copy the Wilson
    interval and exact McNemar test from the harness-lab and add a paired bootstrap over
    continuous per-query scores, seeded so the same inputs give the same interval.

Run the demo to print a measurement: `python3 solutions/metrics.py`.
"""
from __future__ import annotations

import math
import random
from statistics import NormalDist

_Z = NormalDist()


def recall_at_k(ranked, relevance, k):
    """Fraction of relevant documents that appear in the top k.

    `ranked` is a list of doc_ids best-first; `relevance` maps doc_id -> grade. Empty
    relevance (a no-answer query) is 0.0 by definition, and k <= 0 returns 0.0.
    """
    relevant = set(relevance)
    if not relevant or k <= 0:
        return 0.0
    top = set(ranked[:k])
    hits = len(top & relevant)
    return hits / len(relevant)


def mrr(ranked, relevance):
    """Reciprocal rank of the first relevant document, 0.0 if none is ranked.

    Rank is 1-based, so the first hit scores 1.0, the second 0.5, and so on.
    """
    relevant = set(relevance)
    for rank, doc_id in enumerate(ranked, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def _gain(grade):
    return 2.0 ** grade - 1.0


def ndcg_at_k(ranked, relevance, k):
    """Normalised discounted cumulative gain at k with exponential gain and log2 discount."""
    if not relevance or k <= 0:
        return 0.0
    dcg = 0.0
    for rank, doc_id in enumerate(ranked[:k], start=1):
        grade = relevance.get(doc_id, 0.0)
        if grade:
            dcg += _gain(grade) / math.log2(rank + 1)
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(_gain(grade) / math.log2(rank + 1) for rank, grade in enumerate(ideal, start=1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def abstention_metrics(predictions, queries):
    """Grade abstention as a per-query decision.

    `predictions` maps qid -> ranked list; an empty list means "I do not know".
    Returns tp (correct abstention), fp (abstained on an answerable query), fn (answered
    a no-answer query), tn, the abstention count, and precision/recall.
    """
    tp = fp = fn = tn = 0
    for q in queries:
        ranked = predictions.get(q["qid"], [])
        abstained = len(ranked) == 0
        is_no_answer = len(q["relevance"]) == 0
        if is_no_answer and abstained:
            tp += 1
        elif is_no_answer and not abstained:
            fn += 1
        elif not is_no_answer and abstained:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "abstentions": tp + fp,
        "precision": precision, "recall": recall,
    }


def latency_stats(samples):
    """Count, mean, median, p95 and max of latency samples (nearest-rank p95)."""
    xs = sorted(float(x) for x in samples)
    n = len(xs)
    if n == 0:
        return {"count": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}

    def percentile(p):
        return xs[min(n - 1, math.ceil(p * n) - 1)]

    return {
        "count": n,
        "mean": sum(xs) / n,
        "median": percentile(0.5),
        "p95": percentile(0.95),
        "max": xs[-1],
    }


def evaluate(ranked_by_qid, queries, k=10, latencies=None):
    """Assemble per-query and per-family recall@k, MRR and nDCG@k, plus abstention
    and (optionally) latency. `ranked_by_qid` maps qid -> ranked doc_id list."""
    per_query = {}
    grouped = {}
    for q in queries:
        ranked = ranked_by_qid.get(q["qid"], [])
        scores = {
            "recall@k": recall_at_k(ranked, q["relevance"], k),
            "mrr": mrr(ranked, q["relevance"]),
            "ndcg@k": ndcg_at_k(ranked, q["relevance"], k),
        }
        per_query[q["qid"]] = scores
        grouped.setdefault(q["type"], []).append(scores)

    def average(items):
        if not items:
            return {key: 0.0 for key in ("recall@k", "mrr", "ndcg@k")}
        return {key: sum(item[key] for item in items) / len(items) for key in items[0]}

    result = {
        "k": k,
        "overall": average(list(per_query.values())),
        "by_type": {family: average(items) for family, items in grouped.items()},
        "per_query": per_query,
        "abstention": abstention_metrics(ranked_by_qid, queries),
    }
    if latencies is not None:
        result["latency"] = latency_stats(latencies)
    return result


def wilson_interval(successes, n, confidence=0.95):
    """Wilson score interval. Copied from harness-lab/eval/stats.py: unlike the normal
    approximation it stays inside [0, 1] and behaves at 0/n and n/n."""
    if n == 0:
        return (0.0, 1.0)
    z = _Z.inv_cdf(1 - (1 - confidence) / 2)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, centre - half), 12), round(min(1.0, centre + half), 12))


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value. Copied from harness-lab/eval/stats.py:
    b = pairs only A passed, c = only B passed; under H0 each discordant pair is a fair
    coin, so this is a binomial test."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired_bootstrap_ci(scores_a, scores_b, n_resamples=2000, seed=0, confidence=0.95):
    """Percentile bootstrap CI for the mean paired difference `a - b`.

    Resamples whole query positions (the pair is the unit), so it inherits pairing. Seeded
    so the same inputs give the same interval and check.py can compare exactly. Returns
    (mean_difference, low, high).
    """
    n = len(scores_a)
    if n != len(scores_b):
        raise ValueError("paired comparison needs two equally long score lists")
    if n == 0:
        return (0.0, 0.0, 0.0)
    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    mean = sum(diffs) / n
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        means.append(total / n)
    means.sort()
    alpha = (1 - confidence) / 2
    lo = means[min(n_resamples - 1, int(alpha * n_resamples))]
    hi = means[min(n_resamples - 1, int((1 - alpha) * n_resamples))]
    return (mean, lo, hi)


def main() -> None:
    ranked = ["b", "a", "c"]
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    print(f"ranked={ranked} relevance={relevance}")
    print(f"recall@2={recall_at_k(ranked, relevance, 2):.4f} mrr={mrr(ranked, relevance):.4f} "
          f"ndcg@3={ndcg_at_k(ranked, relevance, 3):.4f}")
    a = [1.0, 0.0, 1.0, 0.5]
    b = [0.0, 0.0, 0.5, 0.0]
    print(f"paired diff a-b = {paired_bootstrap_ci(a, b, seed=1)}")


if __name__ == "__main__":
    main()

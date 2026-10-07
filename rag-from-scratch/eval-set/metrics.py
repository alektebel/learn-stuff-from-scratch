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
    # TODO: Distinct relevant docs in ranked[:k] over |relevance|; empty relevance or k <= 0 -> 0.0 (a no-answer query has nothing to recall).
    raise NotImplementedError("recall_at_k")


def mrr(ranked, relevance):
    """Reciprocal rank of the first relevant document, 0.0 if none is ranked.

    Rank is 1-based, so the first hit scores 1.0, the second 0.5, and so on.
    """
    # TODO: 1/(1-based rank) of the first ranked doc in relevance, else 0.0. Do not count from zero.
    raise NotImplementedError("mrr")


def _gain(grade):
    return 2.0 ** grade - 1.0


def ndcg_at_k(ranked, relevance, k):
    """Normalised discounted cumulative gain at k with exponential gain and log2 discount."""
    # TODO: gain = 2**grade - 1, discount = 1/log2(rank + 1) with rank from 1; divide by the same sum over the grades sorted descending, truncated to k.
    raise NotImplementedError("ndcg_at_k")


def abstention_metrics(predictions, queries):
    """Grade abstention as a per-query decision.

    `predictions` maps qid -> ranked list; an empty list means "I do not know".
    Returns tp (correct abstention), fp (abstained on an answerable query), fn (answered
    a no-answer query), tn, the abstention count, and precision/recall.
    """
    # TODO: An empty ranked list is an abstention. On a no-answer query it is tp, otherwise fn; abstaining on an answerable query is fp. Precision over abstentions, recall over no-answer queries.
    raise NotImplementedError("abstention_metrics")


def latency_stats(samples):
    """Count, mean, median, p95 and max of latency samples (nearest-rank p95)."""
    # TODO: Sort the samples; count, mean, median (p50), p95 and max with the nearest-rank rule; an empty sample is all zeros.
    raise NotImplementedError("latency_stats")


def evaluate(ranked_by_qid, queries, k=10, latencies=None):
    """Assemble per-query and per-family recall@k, MRR and nDCG@k, plus abstention
    and (optionally) latency. `ranked_by_qid` maps qid -> ranked doc_id list."""
    # TODO: Per query compute recall@k, mrr and ndcg@k; average overall and per q['type']; attach abstention_metrics and, if given, latency_stats.
    raise NotImplementedError("evaluate")


def wilson_interval(successes, n, confidence=0.95):
    """Wilson score interval. Copied from harness-lab/eval/stats.py: unlike the normal
    approximation it stays inside [0, 1] and behaves at 0/n and n/n."""
    # TODO: Wilson score interval (copy the formula from harness-lab/eval/stats.py): it stays in [0, 1] and returns exactly 0 at 0/n, 1 at n/n.
    raise NotImplementedError("wilson_interval")


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value. Copied from harness-lab/eval/stats.py:
    b = pairs only A passed, c = only B passed; under H0 each discordant pair is a fair
    coin, so this is a binomial test."""
    # TODO: Two-sided exact McNemar: 2 * sum_{i<=min(b,c)} C(b+c, i) / 2**(b+c), capped at 1.0; no discordant pairs -> 1.0.
    raise NotImplementedError("mcnemar_exact")


def paired_bootstrap_ci(scores_a, scores_b, n_resamples=2000, seed=0, confidence=0.95):
    """Percentile bootstrap CI for the mean paired difference `a - b`.

    Resamples whole query positions (the pair is the unit), so it inherits pairing. Seeded
    so the same inputs give the same interval and check.py can compare exactly. Returns
    (mean_difference, low, high).
    """
    # TODO: Resample query positions with random.Random(seed), return (mean(a-b), percentile CI low, high); the pair is the unit, so require equal lengths.
    raise NotImplementedError("paired_bootstrap_ci")


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

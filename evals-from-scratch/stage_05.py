"""Evals From Scratch — stage 5: ranking metrics, and the ideal that is not ideal

DESIGN DECISION — nDCG's denominator is the best ranking of ALL the relevant
    documents, not of the ones you retrieved.
    nDCG is DCG / IDCG, and the IDCG is the ideal ordering of the whole
    judgement set. Compute it from the retrieved pool instead and a system that
    returns one highly relevant document and nothing else scores 1.0 — perfect
    by its own standard, useless in practice. This is the single most common way
    an nDCG number ends up inflated, and it inflates the worst systems most.

DESIGN DECISION — graded relevance is why nDCG exists.
    recall@k and MRR treat every relevant document as equal; nDCG weights a
    "perfect" answer above a "partial" one and discounts by position. Use it
    when your judgements are graded, and do not use it when they are binary
    (it degenerates into a rank-weighted recall with a denominator nobody can
    explain).

TODO: implement

    recall_at_k(relevant, retrieved, k) -> float
        |relevant ∩ retrieved[:k]| / |relevant|; 0.0 when nothing is relevant.

    mrr(queries) -> float
        `queries` is an iterable of {"retrieved": [key, ...], "relevant": set or
        list} dicts (one per query). A query contributes 1/rank of the FIRST
        relevant key in `retrieved` (rank counted from 1), and 0.0 when nothing
        relevant was retrieved. The mean over the queries.

    dcg(gains) -> float
        sum over positions i (1-based) of (2 ** gain - 1) / log2(i + 1).

    ndcg(retrieved, relevance, k=None) -> float
        `relevance` maps key -> graded gain (>= 0). DCG over retrieved[:k] using
        the gains; IDCG over EVERY key in `relevance` sorted by gain descending
        and truncated to k. 0.0 when no key has a positive gain.
        A key the relevance map does not contain has gain 0.
"""


def recall_at_k(relevant, retrieved, k):
    raise NotImplementedError("stage 5: implement recall_at_k()")


def mrr(queries):
    raise NotImplementedError("stage 5: implement mrr()")


def dcg(gains):
    raise NotImplementedError("stage 5: implement dcg()")


def ndcg(retrieved, relevance, k=None):
    raise NotImplementedError("stage 5: implement ndcg()")

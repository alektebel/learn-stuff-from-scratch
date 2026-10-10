"""RAG From Scratch — stage 5 solution: reciprocal rank fusion."""


def reciprocal_rank_fusion(rankings, k=60):
    scores = {}
    first = {}
    for ranking in rankings:
        for pos, doc in enumerate(ranking, start=1):
            if doc not in first:
                first[doc] = len(first)
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + pos)
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], first[kv[0]]))
    return ordered

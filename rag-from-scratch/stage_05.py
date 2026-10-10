"""RAG From Scratch — stage 5: reciprocal rank fusion

DESIGN DECISION — fuse ranks, not scores.
    A BM25 score of 12.4 and a cosine of 0.71 are not comparable quantities.
    Their ranks are. RRF throws away the scale, which is exactly why it works
    across retrievers that disagree about units.

TODO: implement `reciprocal_rank_fusion(rankings, k=60)`.

    rankings: a list of ranked id lists (best first), one per retriever.
    For each list, for position p (1-based): score[id] += 1 / (k + p).
    Return [(id, score)] sorted by score descending, ties by first appearance.
"""


def reciprocal_rank_fusion(rankings, k=60):
    raise NotImplementedError("stage 5: implement reciprocal_rank_fusion()")

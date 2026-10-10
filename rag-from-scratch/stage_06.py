"""RAG From Scratch — stage 6: reranking and MRR

The retriever optimises for cheap recall; the reranker looks at the query and
the candidate together and fixes the order. Measure it, do not assert it: MRR
before vs after is the whole point of the stage.

TODO: implement `overlap_score`, `rerank`, `mrr`.

    overlap_score(query_tokens, doc_tokens) = |query ∩ doc| / |query|
    rerank(query_tokens, candidates, k=10)
        candidates: [(id, doc_tokens)] in retriever order
        -> [(id, score)] by overlap_score descending, ties keep retriever order
    mrr(ranked_ids, relevant) -> 1 / rank of the first relevant id, else 0.0
"""


def overlap_score(query_tokens, doc_tokens):
    raise NotImplementedError("stage 6: implement overlap_score()")


def rerank(query_tokens, candidates, k=10):
    raise NotImplementedError("stage 6: implement rerank()")


def mrr(ranked_ids, relevant):
    raise NotImplementedError("stage 6: implement mrr()")

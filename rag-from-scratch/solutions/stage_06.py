"""RAG From Scratch — stage 6 solution: reranking and MRR."""


def overlap_score(query_tokens, doc_tokens):
    if not query_tokens:
        return 0.0
    q = set(query_tokens)
    return len(q & set(doc_tokens)) / len(q)


def rerank(query_tokens, candidates, k=10):
    scored = []
    for order, (cid, toks) in enumerate(candidates):
        scored.append((cid, overlap_score(query_tokens, toks), order))
    scored.sort(key=lambda x: (-x[1], x[2]))
    return [(cid, score) for cid, score, _ in scored[:k]]


def mrr(ranked_ids, relevant):
    for i, cid in enumerate(ranked_ids, start=1):
        if cid in relevant:
            return 1.0 / i
    return 0.0

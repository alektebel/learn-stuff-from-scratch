"""RAG From Scratch — stage 4 solution: BM25."""

import math


def bm25_scores(query_tokens, docs_tokens, k1=1.5, b=0.75):
    n = len(docs_tokens)
    if n == 0:
        return []
    lengths = [len(d) for d in docs_tokens]
    avg = sum(lengths) / n
    df = {}
    for doc in docs_tokens:
        for t in set(doc):
            df[t] = df.get(t, 0) + 1
    scores = []
    for doc, dl in zip(docs_tokens, lengths):
        total = 0.0
        for t in query_tokens:
            if t not in df:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            tf = doc.count(t)
            denom = tf + k1 * (1 - b + b * (dl / avg if avg else 0.0))
            if denom:
                total += idf * (tf * (k1 + 1)) / denom
        scores.append(total)
    return scores

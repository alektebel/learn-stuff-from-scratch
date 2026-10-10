"""RAG From Scratch — stage 4: BM25 lexical scoring

Why still lexical? Dense retrieval is bad at rare exact tokens — part numbers,
error codes, surnames. BM25 is bad at paraphrase. You are about to fuse them
(stage 5), and you cannot fuse what you have not built.

TODO: implement `bm25_scores(query_tokens, docs_tokens, k1=1.5, b=0.75)`.

    For each doc:
      idf(t)  = ln(1 + (N - df + 0.5) / (df + 0.5))     always >= 0
      tf(t)   = number of times t occurs in the doc
      norm    = tf + k1 * (1 - b + b * dl / avgdl)
      score  += idf * (tf * (k1 + 1)) / norm
    Return one score per document. A query term absent from a doc contributes 0.
"""


def bm25_scores(query_tokens, docs_tokens, k1=1.5, b=0.75):
    raise NotImplementedError("stage 4: implement bm25_scores()")

"""Graded hints for the RAG project-1 BM25 templates.

Each entry maps a function the learner must write to a one-line hint. Everything not
listed here (the token regex and constants, `_flatten_queries`, `_eval_set_path`,
`_import_metrics`, the demo) is provided scaffolding: it is not the point of the
exercise, and the checks lean on it.
"""

HINTS = {
    "bm25.py": {
        "tokenize": (
            "Lower-case the text and return `TOKEN_RE.findall(...)`: [a-z0-9]+ tokens in "
            "order. No stemming, no stopword list — it must be deterministic."
        ),
        "build_inverted_index": (
            "For each doc, tokenize title + body, store its length, and for each term "
            "store its frequency under postings[term][doc_id]. Return the postings map, "
            "the doc_lengths map and the mean length."
        ),
        "idf": (
            "df = number of documents containing the term; return "
            "math.log(1 + (n_docs - df + 0.5) / (df + 0.5)). The +0.5 smoothing keeps a "
            "term that occurs in every document from driving the score to zero or below."
        ),
        "bm25_score": (
            "Sum over the query's tokens: skip a token the document does not contain; "
            "otherwise add idf * tf*(k1+1) / (tf + k1*(1 - b + b*dl/avg_dl)). Missing "
            "tokens contribute nothing, so a no-overlap document scores exactly 0.0."
        ),
        "BM25Retriever.retrieve": (
            "Take the query text and its filters (an explicit `filters` argument wins); "
            "keep documents passing `_passes_filters`; score each with `bm25_score`; drop "
            "score 0 (that is the abstention); sort by (-score, doc_id) and return the "
            "top k."
        ),
        "evaluate_bm25": (
            "Flatten the query families, rank every query with BM25Retriever, then return "
            "`metrics.evaluate(ranked_by_qid, queries, k)` from the shared eval set."
        ),
    },
}

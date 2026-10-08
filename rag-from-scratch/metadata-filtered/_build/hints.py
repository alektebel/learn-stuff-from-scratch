"""Graded hints for the RAG project-2 metadata-filtered templates.

Each entry maps a function or method the learner must write to a one-line hint.
Everything not listed here (the token regex and constants, `_eval_set_solutions`,
`_doc_text`, `_row_values`, `_COLUMNS`, `_corpus_stats`, `_bm25`, `_flatten_queries`,
`_import_metrics`, `FilteredRetriever.__init__`, `_split`, `_score`, `_rank`, `_top`,
the demo) is provided scaffolding: it is not the point of the exercise, and the checks
lean on it.
"""

HINTS = {
    "filtered.py": {
        "tokenize": (
            "Lower-case the text and return `TOKEN_RE.findall(...)`: [a-z0-9]+ tokens in "
            "order. Identical to the sibling stages' tokeniser."
        ),
        "load_documents": (
            "Import the eval set's `corpus`, call `generate_corpus(seed)`, take its "
            "`documents`, and for each doc set `doc['superseded']` to "
            "`doc.get('superseded_by') is not None` when that key is absent."
        ),
        "build_db": (
            "Connect, `CREATE TABLE documents` with the `_COLUMNS`, `executemany` the "
            "`_row_values` of every doc, then loop `FILTERABLE` and "
            "`CREATE INDEX idx_documents_<column> ON documents(<column>)`. Commit and "
            "return the connection."
        ),
        "_where_clause": (
            "Collect `column = ?` clauses with a parallel params list. Use "
            "`substr(date, 1, 4) = ?` for 'year', an integer 1/0 for 'superseded', and "
            "equality for the other whitelisted columns; return ('1=1', []) when empty."
        ),
        "selectivity": (
            "`SELECT COUNT(*)` the table, then `SELECT COUNT(*) ... WHERE _where_clause`; "
            "return the ratio (0.0 for an empty corpus)."
        ),
        "FilteredRetriever._passes": (
            "Look up the doc and check every filter key: 'year' against `date[:4]`, "
            "'superseded' as a boolean, otherwise `doc.get(key) == value`. Return False "
            "on the first mismatch."
        ),
        "FilteredRetriever.pre_filter": (
            "Split the query, tokenize, then `SELECT doc_id FROM documents WHERE "
            "_where_clause(filters)`; `_rank` those ids (BM25, drop zero scores) and "
            "return the top k. This is the filter-first plan."
        ),
        "FilteredRetriever.post_filter": (
            "`_rank` the whole corpus, slice the top k, then keep only ids where "
            "`_passes(id, filters)`. Do NOT refill to k: the shortfall is the point."
        ),
        "FilteredRetriever.filter_aware": (
            "For each filter key `COUNT(*)` its predicate and keep the smallest; SELECT "
            "the ids matching just that predicate; if there is more than one predicate, "
            "re-check the full filter with `_passes`; then `_rank` and return the top k."
        ),
        "evaluate": (
            "Build one `FilteredRetriever`, and for each strategy rank every query "
            "(passing its own filters) and call the eval set's `metrics.evaluate`. For "
            "the `filtered` family also average the number of results returned. Return "
            "one metrics dict per strategy plus `mean_results`."
        ),
    },
}

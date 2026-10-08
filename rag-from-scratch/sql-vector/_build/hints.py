"""Graded hints for the RAG project-5 SQL + vector templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/sql-vector rag-from-scratch/sql-vector/_build/hints.py

Everything not listed here (the text helpers, `_quote`, `_columns`, `_known_values`,
`_apply`, `_filter_clauses`, `_metric`, the sibling-bm25 import and its fallback, the
eval-set loaders, `_same`, and the demo) is provided scaffolding: it is not the point of
the exercise and the checks lean on it.
"""

HINTS = {
    "router.py": {
        "load_tables":
            "Open a `sqlite3.connect(path)`. For each table name in sorted(...) create "
            "`CREATE TABLE IF NOT EXISTS <name> (<quoted columns>)` with no declared "
            "affinity (so integers stay integers), then `executemany` the rows with `?` "
            "placeholders. Commit and return the connection.",
        "classify":
            "Return \"structured\" when the text carries an aggregation/superlative "
            "signal `_AGG_WORDS`, or `_LIST` together with a `_STRUCTURED_ONLY_WORDS` "
            "table word, or a vendor risk phrase; otherwise \"unstructured\". Keep the "
            "signals as whole-word keyword tests so the route is deterministic and the "
            "cost (brittleness) stays documented.",
        "to_sql":
            "Resolve `_metric(lowered)` first. If it is None, handle vendor questions "
            "(count, or list filtered by `_filter_clauses`) and dimension counts, else "
            "return None. If a metric is named, take superlatives (`_MAX` -> DESC, `_MIN` "
            "-> ASC, GROUP BY dimension ORDER BY SUM(metric) LIMIT 1), then totals/means "
            "(`SUM`/`AVG`), grouped when 'by'/'per' names the dimension. Build every "
            "value with `_filter_clauses` and return `(sql, tuple(params))`; never "
            "interpolate the question text into the SQL.",
        "answer_structured":
            "Call `to_sql`; return None when it does. Execute with the bound params. "
            "Return the bare value for a one-row one-column result, else the list of row "
            "tuples. No rows is None (abstain); a genuine COUNT of 0 stays 0.",
        "route_and_answer":
            "Route with `classify`. Structured: return a dict tagged \"structured\" with "
            "the SQL answer, an empty document list and the templated sql/params. "
            "Unstructured: return a dict tagged \"unstructured\" with a None answer and "
            "`retrieve(question, k, documents)`.",
        "retrieve":
            "Import the sibling `../bm25` (`_try_import_bm25`); if present build a "
            "BM25Retriever over `documents` and return `retriever.retrieve(question, "
            "k=k)`, otherwise return `_local_retrieve(question, k, documents)`.",
        "evaluate":
            "Load the tables, score each structured question with `answer_structured` "
            "against its expected value (a None expected is correct only when the router "
            "abstains), and when `query_sets` is given route every query with "
            "`route_and_answer`, count the routes and score the retrieved document lists "
            "with the shared `metrics.evaluate`. Return both halves separately.",
    },
}

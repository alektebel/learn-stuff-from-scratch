"""Graded hints for the RAG project-7 corrective-RAG templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/corrective rag-from-scratch/corrective/_build/hints.py

Everything not listed here (the tokeniser and text helpers, the local BM25 ``_local_rank``,
``_consensus``, the sibling ``../bm25`` import with its fallback, the eval-set locator and
the metric helpers, and ``demo``) is provided scaffolding: it is not the point of the
exercise and the checks lean on it.
"""

HINTS = {
    "corrective.py": {
        "load_eval_set":
            "Locate the shared eval set's ``solutions/`` (pathlib, with an ``RAG_EVAL_SET`` "
            "override), add it to ``sys.path``, import ``corpus``/``metrics``/``queries``, "
            "generate ``corpus.generate_corpus(seed)``, build the query sets and return "
            "the documents, the family dict, the flattened query list and the metrics "
            "module.",
        "quality_gate":
            "Return \"weak\" when ``results`` is empty, when ``results[0]['score']`` is "
            "below ``threshold``, or when ``_consensus(results[:GATE_TOPK])`` is below "
            "``GATE_OVERLAP``; otherwise \"ok\". Read only ``results`` — never the query's "
            "relevance judgments.",
        "rewrite_prf":
            "Start from the original query terms. For each of the top ``top_n`` results, "
            "count each non-stopword term once per document (a set per result). Sort the "
            "candidates by ``(-count, term)`` and append up to ``n_terms`` of them, "
            "skipping stopwords and terms already in the query. Return original + added.",
        "build_second_corpus":
            "Return a fresh list of the module's ``SECOND_CORPUS`` documents, copying each "
            "dict so a caller cannot mutate the constant.",
        "retrieve_primary":
            "Score the documents with ``_local_rank(terms, documents, filters)`` (filters "
            "come from a dict query). When the sibling ``../bm25`` imports, reorder those "
            "result dicts by its ranked doc_ids. Return at most ``k``; a document matching "
            "no query term scores 0 and is dropped.",
        "retrieve_second":
            "Return the first ``k`` results of ``_local_rank(_query_terms(query), "
            "documents or build_second_corpus(), {})`` — no metadata filters on the "
            "external corpus.",
        "corrective_retrieve":
            "Retrieve the primary and gate it. Keep it (path \"raw\") when the gate is ok. "
            "Otherwise rewrite with PRF and retry: if the retry gates ok use it "
            "(path \"rewritten\"). Otherwise try the second corpus (path \"fallback\"). If "
            "nothing helps, keep the retry or the primary — or abstain when empty. Tag the "
            "returned dict with the path and the abstained flag.",
        "evaluate":
            "For every query, get both ``retrieve_primary`` and ``corrective_retrieve``, "
            "record the two ranked id lists against ``_relevance_map(query)``, count the "
            "corrective path or the abstention, and aggregate recall@k/MRR/nDCG@k per "
            "family and overall. The gate and the path decision must not read the "
            "judgments.",
    },
}

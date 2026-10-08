"""Graded hints for the RAG project-1 LSA templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/lsa rag-from-scratch/lsa/_build/hints.py
"""

HINTS = {
    "lsa.py": {
        "tokenize":
            "lower-case then re.findall(r\"[a-z0-9]+\", ...): the same tokeniser BM25 "
            "uses, so the two stages are comparable.",
        "build_term_document":
            "Return (sorted vocabulary, N x D raw-count matrix row-major): count tokens "
            "of title + body per document, keyed by the sorted vocabulary.",
        "_idf_vector":
            "Smoothed BM25 idf per column: log(1 + (N - df + 0.5) / (df + 0.5)).",
        "_l2":
            "Divide by the Euclidean norm and leave the all-zero vector as zeros.",
        "tf_idf":
            "Multiply every count by its column's idf, then L2-normalise each row so "
            "cosine is a dot product.",
        "jacobi":
            "Cyclic Jacobi: repeatedly zero the largest off-diagonal entry with a "
            "rotation, accumulating the rotations into the eigenvector columns.",
        "eig_sorted":
            "Sort jacobi's eigenpairs by eigenvalue descending and return "
            "(values, vectors) with vectors[i] the eigenvector for values[i].",
        "_canonical_signs":
            "Flip each vector so its largest-magnitude entry is positive; an eigenvector "
            "and its negation are equally valid.",
        "_gram":
            "Return X @ X^T when left_vectors is True (N x N), else X^T @ X (D x D).",
        "_default_components":
            "A coarse rank that actually truncates: max(1, min(100, n_docs // 4)).",
        "fit_lsa":
            "tf-idf the counts, subtract the per-term mean, take the truncated SVD from "
            "whichever Gram matrix is smaller, and return terms, idf, mean, components "
            "V_k (k x D), singular values, L2-normalised document embeddings and the "
            "Gram size actually decomposed.",
        "embed_query":
            "tf-idf the query with the model's idf, L2-normalise, centre by the model "
            "mean, project onto V_k and L2-normalise; a query with no known token "
            "returns zeros.",
        "LsaRetriever.__init__":
            "Fit one LSA model and cache doc_id -> embedding.",
        "LsaRetriever._passes_filters":
            "Same pre-retrieval metadata rules as BM25: year compares the date prefix, "
            "the rest compare the field.",
        "LsaRetriever.retrieve":
            "Cosine is the dot product of the query and document embeddings; keep "
            "score > 0, sort by (-score, doc_id), return the top k (empty means abstain).",
        "_flatten_queries":
            "Accept the eval set's family dict (lexical, semantic, filtered, multi_hop, "
            "no_answer) or an already-flat query list.",
        "_eval_set_path":
            "Locate ../eval-set/solutions relative to this file (or one level up).",
        "_import_metrics":
            "Add the eval-set path to sys.path once and import its metrics module.",
        "evaluate":
            "Fit one retriever, retrieve k per query, and return metrics.evaluate(...) — "
            "the same dictionary shape BM25 returns.",
        "_row":
            "Pick the overall row or by_type[family] from a metrics result.",
        "demo":
            "Run LSA on seed 0 next to the lexical baseline (and BM25 if the sibling "
            "stage is present) and print the per-family table.",
    },
}

"""Graded hints for the RAG project-3 RERANKING templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/reranking rag-from-scratch/reranking/_build/hints.py
"""

HINTS = {
    "rerank.py": {
        "_query_text":
            "Return query['text'] for a dict query, else str(query).",
        "_squash":
            "Map a real number into (-1, 1) with x/(1+abs(x)); non-finite becomes 0.0.",
        "_cosine":
            "Cosine of the term-frequency vectors of two token lists; 0.0 if either is "
            "empty or has zero norm.",
        "_phrase_hit":
            "Tokenise query and document, join with spaces, and return 1.0 if the query "
            "string occurs contiguously in the document string.",
        "features":
            "Build the values dict keyed by FEATURE_NAMES: stage_score and dense_cosine "
            "squashed from the context (0.0 without one), lexical_cosine, term_coverage, "
            "idf_coverage via context.idf (1.0 without one), exact_phrase, title_match, "
            "length_ratio against context.avg_length (or the default), and is_current "
            "from the absence of superseded_by. Return a list in FEATURE_NAMES order.",
        "FeatureContext.__init__":
            "Store the documents, tokens, term frequencies and lengths; set avg_length "
            "(from the argument, else the mean length); build or store idf; and keep the "
            "stage/dense scorers, defaulting to the local BM25 and a constant 0.0.",
        "FeatureContext._compute_idf":
            "Return term -> smoothed BM25 idf log(1+(N-df+0.5)/(df+0.5)) over the stored "
            "document tokens.",
        "FeatureContext._idf_value":
            "Return and validate the idf for a term, supporting both a callable and a "
            "mapping; non-finite becomes 0.0.",
        "FeatureContext.idf":
            "Delegate to _idf_value(term).",
        "FeatureContext._local_bm25":
            "Okapi BM25 over the stored term frequencies, lengths and idf, with k1=1.5 "
            "and b=0.75; used when no stage_scorer is injected.",
        "FeatureContext.stage_score":
            "Return float(self._stage(query_text, doc)).",
        "FeatureContext.dense_cosine":
            "Return float(self._dense(query_text, doc)).",
        "Reranker.__init__":
            "Store the context, iterations, lr and l2; start weights at zero, bias at "
            "0.0, and loss_history empty.",
        "Reranker._sigmoid":
            "Numerically stable logistic function (branch on the sign of z).",
        "Reranker.score_vector":
            "Return bias plus the dot product of the weights and the vector.",
        "Reranker.fit":
            "For a fixed number of iterations accumulate the logistic-loss gradient "
            "(probability - label) over the (vector, label) examples, take the mean, add "
            "the L2 term, and step the weights and bias; record the mean loss each "
            "iteration. No randomness.",
        "Reranker.score":
            "Return score_vector(features(query, doc, self.context)).",
        "Reranker.rerank":
            "Normalise candidates to doc_ids, look each document up in the context (an "
            "empty document if absent), score it, sort by (-score, doc_id), and return "
            "the first k. Only candidates may appear; [] for an empty list.",
        "load_eval_set":
            "Locate ../eval-set/solutions, import corpus/queries/metrics, generate seed "
            "0, build the query sets, and return {corpus, query_sets, queries, metrics}; "
            "cache the result.",
        "build_retriever":
            "Import the sibling bm25 and return BM25Retriever(corpus) — the first stage.",
        "build_context":
            "Import the sibling bm25 and (if present) lsa; build the BM25 index and the "
            "LSA embeddings once; return a FeatureContext whose stage scorer is "
            "bm25_score and whose dense scorer dot-products the query and document "
            "embeddings.",
        "first_stage":
            "Use the given retriever, or lazily build the sibling-BM25 retriever over the "
            "shared eval set, and return retriever.retrieve(query, k=k, filters=filters).",
        "choose_split":
            "For each family in order, sort its queries by qid and alternate them into "
            "train and eval; send no_answer queries to eval only. Return the two qid "
            "lists; they must be disjoint.",
        "train_and_evaluate":
            "Choose the split; build examples from the train queries' candidate lists "
            "labelled by relevance; fit a Reranker; then for each eval query record the "
            "base top-k and the reranked top-k, accumulate first-stage recall@depth over "
            "answerable queries, and return base/reranked metrics, the model, the qids, "
            "and the ceiling.",
        "find_ceiling_case":
            "For each answerable query, append deterministic clone documents that repeat "
            "the query's tokens (so BM25 ranks them first) and return the first query "
            "whose relevant document is outside retriever.retrieve(query, depth), with "
            "the candidates, augmented documents and retriever.",
        "demo":
            "Load the shared eval set, train and evaluate with k=5, print the per-family "
            "base-vs-reranked recall/MRR/nDCG table and the first-stage ceiling, then "
            "find and print a ceiling query with and without the excluded document "
            "injected as a candidate.",
    },
}

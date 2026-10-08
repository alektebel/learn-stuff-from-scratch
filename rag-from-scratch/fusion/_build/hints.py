"""Graded hints for the RAG project-1 FUSION templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/fusion rag-from-scratch/fusion/_build/hints.py
"""

HINTS = {
    "fusion.py": {
        "_as_keys":
            "Accept a ranking as either keys or (key, score) pairs; return the plain "
            "list of keys so a stage may expose either form.",
        "_passes_filters":
            "Same pre-retrieval metadata rules as BM25 and LSA: year compares the date "
            "prefix, the other keys compare the field.",
        "_sort_ranked":
            "Drop score <= 0, then sort by (-score, key) so ties break by key ascending.",
        "rrf":
            "For each ranking position (1-based) add weight / (k + position) to that "
            "key's fused score; missing keys get no term. Sort by (-score, key).",
        "normalize_scores":
            "Detect mapping / pairs / plain numbers; minmax: (v - min)/(max - min) with a "
            "constant list mapping to 0.0; zscore: (v - mean)/population-std with zero "
            "variance mapping to 0.0. Preserve keys.",
        "weighted_fusion":
            "Normalise each retriever's collection on its own, multiply by its weight and "
            "sum into one mapping; keys a retriever did not score contribute 0.0. Sort by "
            "(-score, key).",
        "_Bm25Stage.__init__":
            "Store the documents, tokeniser and k1/b; build token counts, lengths, "
            "average length, smoothed idf and per-document term frequencies.",
        "_Bm25Stage.scored":
            "Okapi score over the query tokens with saturating tf and length "
            "normalisation; apply filters, keep score > 0, sort by (-score, doc_id).",
        "_LsaStage.__init__":
            "Wrap the sibling LsaRetriever (default components when none are given) and "
            "keep its document list.",
        "_LsaStage.scored":
            "Project the query with the retriever's own embed_query, dot it with each "
            "document embedding, apply filters, keep score > 0, sort by (-score, doc_id).",
        "_sibling_solutions":
            "Locate ../<name>/solutions relative to this file or one level up; raise "
            "FileNotFoundError if the sibling stage is absent.",
        "_import_sibling":
            "Add the sibling solutions directory to sys.path once and import it by name.",
        "load_stages":
            "Import the ../bm25 and ../lsa solutions, build one stage adapter per retriever "
            "on the corpus, and return them keyed bm25/lsa with their modules.",
        "HybridRetriever.__init__":
            "Accept the corpus or a document list and an optional injected stages dict "
            "(otherwise call load_stages); cache doc_id -> document.",
        "HybridRetriever._score_lists":
            "Ask each stage in STAGE_ORDER for its scored candidates and return their "
            "per-stage mappings.",
        "HybridRetriever.retrieve":
            "Fuse the two stages with rrf or weighted_fusion, apply weights (equal by "
            "default), and return the top k doc_ids; an empty fusion means abstain.",
        "_eval_set_solutions":
            "Locate ../eval-set/solutions relative to this file or one level up.",
        "_import_metrics":
            "Add the eval-set path to sys.path once and import its metrics module.",
        "_flatten_queries":
            "Accept the eval set's family dict (lexical, semantic, filtered, multi_hop, "
            "no_answer) or an already-flat query list.",
        "_binom_two_sided":
            "Exact two-sided sign-test p-value: 2 * P(X <= min(wins, losses)) under "
            "Binomial(n, 0.5), capped at 1.0.",
        "paired_comparison":
            "Per query compare the two per-query metric dicts: count wins/losses/ties, the "
            "win rate over decided pairs, the mean difference and the sign-test p-value.",
        "evaluate":
            "Build the stages once; run RRF, weighted fusion, BM25 alone and LSA alone over "
            "the flattened queries; return the RRF metrics dict with a 'methods' dict and "
            "the overall/per-family paired comparisons.",
        "_paired_overall":
            "For each fusion method versus each single stage, pair the per-query metric "
            "across all queries.",
        "_paired_by_type":
            "Same paired comparison, restricted to each query family's qids.",
        "_row":
            "Pick the overall row or by_type[family] from a metrics result.",
        "demo":
            "Run the shared eval set on seed 0, print the per-family BM25/LSA/RRF/weighted "
            "recall table and the paired win/loss/tie counts next to each single stage.",
    },
}

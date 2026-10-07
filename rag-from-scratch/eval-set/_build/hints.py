"""Graded hints for the RAG step-0 evaluation-set templates.

Each entry maps a function the learner must write to a one-line hint. Everything not
listed here (constants, `_current`, `_by`, `tokenize`, `_passes_filters`) is provided:
it is scaffolding that is not the point of the exercise, and the checks lean on it.
"""

HINTS = {
    "corpus.py": {
        "generate_corpus": (
            "Use random.Random(seed) only; build BASE_DOCS documents in index order, "
            "append a revision for every REVISION_EVERY-th document, then emit entities, "
            "typed relations and the tables. Never iterate a set: the output must be "
            "byte-identical for the same seed."
        ),
    },
    "queries.py": {
        "build_query_sets": (
            "Return the five families. Every answerable relevance must be built from "
            "_current() (superseded versions excluded) and every no_answer relevance must "
            "be {}; the filtered judgments must satisfy their own region/year filter."
        ),
    },
    "metrics.py": {
        "recall_at_k": (
            "Distinct relevant docs in ranked[:k] over |relevance|; empty relevance or "
            "k <= 0 -> 0.0 (a no-answer query has nothing to recall)."
        ),
        "mrr": (
            "1/(1-based rank) of the first ranked doc in relevance, else 0.0. Do not "
            "count from zero."
        ),
        "ndcg_at_k": (
            "gain = 2**grade - 1, discount = 1/log2(rank + 1) with rank from 1; divide "
            "by the same sum over the grades sorted descending, truncated to k."
        ),
        "abstention_metrics": (
            "An empty ranked list is an abstention. On a no-answer query it is tp, "
            "otherwise fn; abstaining on an answerable query is fp. Precision over "
            "abstentions, recall over no-answer queries."
        ),
        "latency_stats": (
            "Sort the samples; count, mean, median (p50), p95 and max with the "
            "nearest-rank rule; an empty sample is all zeros."
        ),
        "evaluate": (
            "Per query compute recall@k, mrr and ndcg@k; average overall and per q['type']; "
            "attach abstention_metrics and, if given, latency_stats."
        ),
        "wilson_interval": (
            "Wilson score interval (copy the formula from harness-lab/eval/stats.py): it "
            "stays in [0, 1] and returns exactly 0 at 0/n, 1 at n/n."
        ),
        "mcnemar_exact": (
            "Two-sided exact McNemar: 2 * sum_{i<=min(b,c)} C(b+c, i) / 2**(b+c), capped "
            "at 1.0; no discordant pairs -> 1.0."
        ),
        "paired_bootstrap_ci": (
            "Resample query positions with random.Random(seed), return "
            "(mean(a-b), percentile CI low, high); the pair is the unit, so require equal "
            "lengths."
        ),
    },
    "baseline.py": {
        "LexicalBaseline.retrieve": (
            "Tokenize the query text; keep documents passing _passes_filters; score by "
            "the number of distinct shared tokens; drop zero scores (that is the "
            "abstention); sort by (-score, doc_id) and return the top k."
        ),
    },
}

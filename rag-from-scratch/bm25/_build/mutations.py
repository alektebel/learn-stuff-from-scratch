"""Mutation tests for the RAG project-1 BM25 checker.

Each entry is a classic mistake for the mechanism: the exact text is planted into a copy
of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/bm25 rag-from-scratch/bm25/_build/mutations.py
"""

MUTATIONS = [
    # idf uses the raw document frequency instead of the smoothed BM25 form: a common
    # term's idf collapses to 0 and the hand-computed value in step 2 is wrong.
    (
        "idf uses df instead of the smoothed BM25 form",
        "bm25.py",
        "    return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))",
        "    return math.log(n_docs / df) if df else 0.0",
        "2",
    ),
    # b is ignored, so length normalisation disappears: a long document scores the same
    # as a short one with the same term frequency (step 3 catches it).
    (
        "bm25_score drops the length normalisation (b term)",
        "bm25.py",
        "        denominator = tf + k1 * (1 - b + b * doc_length / avg_length)",
        "        denominator = tf + k1",
        "3",
    ),
    # The index is keyed by document instead of by term: posting lists are not lists.
    (
        "inverted index keys by document instead of term",
        "bm25.py",
        "            postings.setdefault(term, {})[doc_id] = tf",
        "            postings.setdefault(doc_id, {})[term] = tf",
        "1",
    ),
    # retrieve never ranks: candidates come back in corpus order.
    (
        "retrieve returns documents in corpus order (no ranking)",
        "bm25.py",
        "        scored.sort(key=lambda pair: (-pair[0], pair[1]))\n",
        "",
        "4",
    ),
    # The zero-score filter is relaxed, so a query with no matching term returns the
    # whole (filtered) corpus instead of abstaining.
    (
        "no-match case returns the whole corpus instead of empty",
        "bm25.py",
        "            if score > 0:",
        "            if score >= 0:",
        "6",
    ),
]

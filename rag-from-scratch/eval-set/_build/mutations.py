"""Mutation tests for the RAG step-0 evaluation-set checker.

Each entry is a classic mistake for the mechanism: the exact text is planted into a copy
of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/eval-set rag-from-scratch/eval-set/_build/mutations.py
"""

MUTATIONS = [
    # nDCG without the log discount: gains are summed flat, so a bad ranking looks ideal.
    (
        "nDCG without the log discount",
        "metrics.py",
        "            dcg += _gain(grade) / math.log2(rank + 1)",
        "            dcg += _gain(grade)",
        "6",
    ),
    # MRR counting ranks from zero: the first hit at position 2 scores 1.0, not 0.5.
    (
        "MRR counting rank 0",
        "metrics.py",
        "    for rank, doc_id in enumerate(ranked, start=1):",
        "    for rank, doc_id in enumerate(ranked, start=0):",
        "5",
    ),
    # The ground truth keeps the superseded versions, so returning a stale policy is a hit.
    (
        "superseded docs left in the ground truth",
        "queries.py",
        '    return [d for d in corpus["documents"] if not d.get("superseded_by")]',
        '    return [d for d in corpus["documents"] if True]',
        "4",
    ),
    # A no-answer query is given a non-empty relevance, so abstention recall is meaningless.
    (
        "no-answer query given non-empty relevance",
        "queries.py",
        '            "relevance": {},',
        '            "relevance": {current[0]["doc_id"]: 2.0},',
        "4",
    ),
    # Abstention flips: returning a document on a no-answer query counts as correct.
    (
        "abstention counts a returned document as correct",
        "metrics.py",
        "        abstained = len(ranked) == 0",
        "        abstained = len(ranked) > 0",
        "8",
    ),
    # The generator draws from the global RNG, so the same seed is not reproducible.
    (
        "corpus generator not seeded (uses global random)",
        "corpus.py",
        "    rng = random.Random(seed)",
        "    rng = random",
        "1",
    ),
    # Version chains are built but never flagged, so the exclusion invariant is vacuous.
    (
        "superseded flag never set",
        "corpus.py",
        '        old["superseded_by"] = new["doc_id"]',
        '        old["superseded_by"] = None',
        "2",
    ),
    # The baseline returns every candidate, so it never abstains on a no-answer query.
    (
        "baseline never abstains",
        "baseline.py",
        "            if score > 0:",
        "            if score >= 0:",
        "12",
    ),
    # The baseline ignores k and returns the whole ranked list.
    (
        "baseline ignores the k limit",
        "baseline.py",
        "        return [doc_id for _score, doc_id in scored[:k]]",
        "        return [doc_id for _score, doc_id in scored]",
        "11",
    ),
]

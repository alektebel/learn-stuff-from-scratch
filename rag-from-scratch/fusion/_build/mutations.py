"""Mutation tests for the RAG project-1 FUSION checker.

Each entry is a classic mistake for the fusion mechanism: the exact text is planted into
a copy of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/fusion rag-from-scratch/fusion/_build/mutations.py
"""

MUTATIONS = [
    # RRF must add 1/(k + rank), not the rank itself; the hand-computed scores in step 1
    # are then wrong (and later ranks dominate absurdly).
    (
        "rrf uses rank instead of 1/(k+rank)",
        "fusion.py",
        "            scores[key] = scores.get(key, 0.0) + weight / (k + position)",
        "            scores[key] = scores.get(key, 0.0) + weight * position",
        "1",
    ),
    # The per-retriever weight is ignored, so a lexical-only / dense-only weighting can no
    # longer change the order (step 1 checks the weighted order exactly).
    (
        "rrf ignores the per-retriever weights",
        "fusion.py",
        "            scores[key] = scores.get(key, 0.0) + weight / (k + position)",
        "            scores[key] = scores.get(key, 0.0) + 1.0 / (k + position)",
        "1",
    ),
    # Min-max forgets to subtract the minimum, so the lowest value is not 0.0 and the
    # hand-computed combined ranking in step 2 is wrong.
    (
        "normalize_scores forgets the min (min-max is not anchored at 0)",
        "fusion.py",
        "        out = [0.0] * len(values) if span == 0.0 else [(v - low) / span for v in values]",
        "        out = [0.0] * len(values) if span == 0.0 else [v / span for v in values]",
        "2",
    ),
    # The zero-span guard is removed: a constant score list divides by zero (step 2 hits
    # the constant-list case explicitly).
    (
        "normalize_scores divides by zero on a constant score list",
        "fusion.py",
        "        out = [0.0] * len(values) if span == 0.0 else [(v - low) / span for v in values]",
        "        out = [(v - low) / span for v in values]",
        "2",
    ),
    # Weighted fusion adds the raw, unnormalised scores (BM25 scores dwarf cosines), so
    # the hand-computed combination in step 2 no longer comes out.
    (
        "weighted_fusion adds raw scores without normalising",
        "fusion.py",
        "        normalised = normalize_scores(scores, method=norm)",
        "        normalised = dict(scores)",
        "2",
    ),
    # The second stage is dropped entirely: fusion degenerates to BM25, and step 3's
    # dense-only document can no longer be recovered.
    (
        "the hybrid drops the second stage (degenerates to BM25)",
        "fusion.py",
        "        for name in STAGE_ORDER:",
        "        for name in STAGE_ORDER[:1]:",
        "3",
    ),
    # When no stage returns a candidate the retriever hands back the whole corpus instead
    # of abstaining (step 6 checks the both-empty case returns []).
    (
        "the no-answer step returns the whole corpus",
        "fusion.py",
        "        return [key for key, _score in fused[:k]]",
        "        if not fused:\n"
        "            return [doc[\"doc_id\"] for doc in self.documents][:k]\n"
        "        return [key for key, _score in fused[:k]]",
        "6",
    ),
]

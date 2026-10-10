"""Graded hints for the RAG project-8 Self-RAG templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/self-rag rag-from-scratch/self-rag/_build/hints.py

Everything not listed here (the tokeniser and text helpers, ``_local_rank``, the retriever
factory, ``_extractive_answer``, ``OverlapReflectionModel``, the eval-set locator, the
scoring helpers and ``demo``) is provided scaffolding: it is not the point of the exercise.
"""

HINTS = {
    "self_rag.py": {
        "should_retrieve":
            "Fail-safe defaults: a query with no content terms is False; no model is True. "
            "Otherwise ask ``model.retrieve_decision(question)`` and return True when it is "
            "None (an unclear answer means retrieve, since retrieval can only add evidence).",
        "grade_evidence":
            "Keep the passages where ``model.relevance(question, passage['text'])`` is true, "
            "in retrieval order — a subsequence of ``passages``. Return ``[]`` when fewer "
            "than ``min_relevant`` remain.",
        "check_support":
            "True when ``answer`` and ``evidence`` are non-empty and at least one passage "
            "satisfies ``model.support(question, answer, passage['text'])``. Relevance and "
            "support are different questions: an irrelevant-looking passage can support.",
        "self_rag_answer":
            "Return early with path ``no_retrieve`` when ``should_retrieve`` is false. "
            "Otherwise retrieve ``k`` passages and loop up to ``max_attempts``: grade the "
            "evidence, build the extractive answer from the first relevant passage, and "
            "check support on it; when supported set path ``answered`` and stop, when not "
            "drop that passage and retry. Return path ``abstain`` with the retrieved ids. "
            "Read only ``query['text']`` and ``query['filters']`` — never its relevance.",
        "evaluate":
            "For every query run ``self_rag_answer`` and count its path; a query with "
            "judgments is correct when its evidence is relevant, a ``no_answer`` query when "
            "it abstains. Aggregate accuracy per family, overall answer accuracy on the "
            "answerable families, and abstention precision/recall. The loop decides; this "
            "function only scores.",
    },
}

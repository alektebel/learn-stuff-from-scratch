"""Mutation tests for the RAG project-7 corrective-RAG checker.

Each entry is a classic mistake for one mechanism of the pipeline: the exact text is
planted into a copy of the solutions and the named check step must report a failure (✗).
Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/corrective rag-from-scratch/corrective/_build/mutations.py

Every mutated step that must catch its bug runs on hand-built results or a hand-built
corpus, so the harness works in a bare temporary directory without the shared eval set or
the sibling bm25 (the eval-set loader is scaffolding the checks do not depend on for the
mutated step; step 4's label-leak check is the self-contained half of that step).
"""

MUTATIONS = [
    # The gate never fires, so a weak first stage is called ok and the correction is never
    # attempted (step 1 requires a near-zero result list to be "weak").
    (
        "quality_gate always returns ok",
        "corrective.py",
        '    top_score = results[0].get("score", 0.0)\n'
        '    if top_score < threshold or _consensus(results[:GATE_TOPK]) < GATE_OVERLAP:\n'
        '        return "weak"\n'
        '    return "ok"',
        '    top_score = results[0].get("score", 0.0)\n'
        '    return "ok"',
        "1",
    ),
    # PRF returns the query unchanged, so the relevant document the raw query missed stays
    # missed (step 2 asserts the expansion adds a top-document term and finds it).
    (
        "rewrite_prf returns the original terms (no expansion)",
        "corrective.py",
        '    original = _query_terms(query, terms)\n'
        '    present = set(original)\n'
        '    counts = Counter()',
        '    original = _query_terms(query, terms)\n'
        '    return original\n'
        '    present = set(original)\n'
        '    counts = Counter()',
        "2",
    ),
    # The second corpus is never consulted, so a query only it can answer abstains
    # (step 3 requires the path to be "fallback" and the document to come from it).
    (
        "the fallback never runs",
        "corrective.py",
        '            fallback = retrieve_second(query, k)',
        '            fallback = []',
        "3",
    ),
    # The fallback searches the primary corpus it was supposed to escape, so the external
    # answer is never found (step 3 checks the returned document is not a primary one).
    (
        "the fallback returns the primary corpus",
        "corrective.py",
        '            fallback = retrieve_second(query, k)',
        '            fallback = retrieve_primary(query, k, documents)',
        "3",
    ),
    # When every path fails the pipeline returns the whole primary corpus instead of
    # abstaining (step 6 requires a no-answer query to stay empty).
    (
        "abstention returns the whole corpus",
        "corrective.py",
        '            else:\n'
        '                chosen, path = [], "abstain"',
        '            else:\n'
        '                chosen, path = (\n'
        '                    [{"doc_id": d["doc_id"], "score": 0.0, "terms": []}\n'
        '                     for d in (documents or [])], "raw")',
        "6",
    ),
    # The path count is decided from the test judgments, so the reported behaviour of the
    # correction depends on the labels it is graded against (step 4 blanks the labels and
    # requires the path counts to be unchanged).
    (
        "evaluate decides the path from the test judgments (leak)",
        "corrective.py",
        '        if corrective["abstained"]:\n'
        '            abstained += 1\n'
        '        else:\n'
        '            paths[corrective["path"]] += 1',
        '        if corrective["abstained"]:\n'
        '            abstained += 1\n'
        '        elif set(corrective["documents"]) & set(relevant):\n'
        '            paths["raw"] += 1\n'
        '        else:\n'
        '            paths["fallback"] += 1',
        "4",
    ),
]

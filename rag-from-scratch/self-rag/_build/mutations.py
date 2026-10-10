"""Mutation tests for the RAG project-8 Self-RAG checker.

Each entry is a classic mistake for one mechanism of the loop: the exact text is planted
into a copy of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/self-rag rag-from-scratch/self-rag/_build/mutations.py

Every mutated step runs on hand-built passages and scripted reflection models, so the
harness works in a bare temporary directory without the shared eval set — including step
4's self-contained label-leak half.
"""

MUTATIONS = [
    # The retrieve decision ignores the model, so a clear "no" still retrieves (step 1
    # requires ScriptModel(retrieve=False) to be False).
    (
        "should_retrieve always retrieves",
        "self_rag.py",
        "    return True if decision is None else bool(decision)",
        "    return True",
        "1",
    ),
    # Grading keeps every passage, so irrelevant evidence reaches the answer (step 2
    # requires the relevant-only subsequence).
    (
        "grade_evidence ignores the model",
        "self_rag.py",
        '    relevant = [p for p in passages if model.relevance(question, p["text"])]',
        "    relevant = list(passages)",
        "2",
    ),
    # Support is assumed, so an unsupported draft is answered (step 3 requires the
    # unsupported branch to retry and then abstain).
    (
        "check_support always returns True",
        "self_rag.py",
        '    return any(model.support(question, answer, passage["text"]) for passage in evidence)',
        "    return True",
        "3",
    ),
    # The retrieve decision is ignored, so a no-retrieve call answers from nothing
    # (step 3 requires path no_retrieve).
    (
        "self_rag_answer ignores should_retrieve",
        "self_rag.py",
        '    if not should_retrieve(question, model):\n'
        '        result["path"] = "no_retrieve"\n'
        "        return result",
        '    if False:\n'
        '        result["path"] = "no_retrieve"\n'
        "        return result",
        "3",
    ),
    # A draft is answered even when unsupported, so relevance alone produces an answer
    # (step 5 requires the over-eager model to abstain).
    (
        "self_rag_answer answers without support",
        "self_rag.py",
        '        if result["supported"]:',
        "        if True:",
        "5",
    ),
    # Path counting is decided from the judgments, so blanking the labels moves the path
    # counts (step 4's self-contained leak half).
    (
        "evaluate decides the path from the relevance labels (leak)",
        "self_rag.py",
        "            outcome = self_rag_answer(query, retriever, model, k=k)\n"
        '            paths[outcome["path"]] += 1',
        "            outcome = self_rag_answer(query, retriever, model, k=k)\n"
        '            paths[outcome["path"] if query.get("relevance") else "abstain"] += 1',
        "4",
    ),
]

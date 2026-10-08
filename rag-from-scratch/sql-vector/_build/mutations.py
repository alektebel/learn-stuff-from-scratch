"""Mutation tests for the RAG project-5 SQL + vector checker.

Each entry is a classic mistake for one mechanism of the router: the exact text is
planted into a copy of the solutions and the named check step must report a failure (✗).
Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/sql-vector rag-from-scratch/sql-vector/_build/mutations.py

Every mutated step runs on the hand-built toy corpus, so the harness works in a bare
temporary directory without the shared eval set or the sibling bm25 (the retrieval
fallback and the eval-set loaders are scaffolding that the checks do not depend on for the
mutated step).
"""

MUTATIONS = [
    # The router never decides "structured", so every SQL question is sent to retrieval
    # (step 2 asserts the structured hand-built list classifies correctly).
    (
        "the router always returns unstructured",
        "router.py",
        '    text = _text(question)\n'
        '    if _has(text, _AGG_WORDS):\n'
        '        return "structured"',
        '    text = _text(question)\n'
        '    return "unstructured"\n'
        '    if _has(text, _AGG_WORDS):\n'
        '        return "structured"',
        "2",
    ),
    # The superlative orders ascending, so "which region has the most revenue" returns the
    # minimum instead of the maximum (step 3 checks a hand-computed top region).
    (
        "to_sql orders the superlative ascending (MIN instead of MAX)",
        "router.py",
        '    order = None\n'
        '    if _has(lowered, _MAX):\n'
        '        order = "DESC"',
        '    order = None\n'
        '    if _has(lowered, _MAX):\n'
        '        order = "ASC"',
        "3",
    ),
    # The year value is concatenated into the SQL string instead of being bound, so a
    # hostile question leaks into the statement (step 5's parameterisation case).
    (
        "to_sql interpolates the question's year into the SQL string",
        "router.py",
        '        if match:\n'
        '            clauses.append(f"{_quote(\'year\')} = ?")\n'
        '            params.append(int(match.group(1)))',
        '        if match:\n'
        '            clauses.append(f"{_quote(\'year\')} = {match.group(1)}")',
        "5",
    ),
    # One table is silently skipped while loading, so SQLite no longer mirrors the corpus
    # (step 1 compares the set of tables, their columns and their row counts).
    (
        "load_tables drops the vendors table",
        "router.py",
        '    for name in sorted(corpus.get("tables", {})):\n'
        '        spec = corpus["tables"][name]',
        '    for name in sorted(corpus.get("tables", {})):\n'
        '        if name == "vendors":\n'
        '            continue\n'
        '        spec = corpus["tables"][name]',
        "1",
    ),
    # An unsupported question no longer abstains but returns a fabricated 0 (steps 3 and 6
    # both require None for the unknown-column question).
    (
        "answer_structured returns 0 instead of None for an unsupported question",
        "router.py",
        '    prepared = to_sql(question, conn)\n'
        '    if prepared is None:\n'
        '        return None',
        '    prepared = to_sql(question, conn)\n'
        '    if prepared is None:\n'
        '        return 0',
        "3",
    ),
    # route_and_answer ignores the router and always retrieves, so structured questions
    # never reach SQL (step 4 asserts the self-contained structured route).
    (
        "route_and_answer sends every question to retrieval",
        "router.py",
        '    route = classify(question)\n'
        '    if route == "structured":',
        '    route = classify(question)\n'
        '    route = "unstructured"\n'
        '    if route == "structured":',
        "4",
    ),
]

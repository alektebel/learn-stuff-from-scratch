"""Mutation tests for the RAG project-2 metadata-filtered checker.

Each entry is a classic mistake for the mechanism: the exact text is planted into a copy
of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/metadata-filtered rag-from-scratch/metadata-filtered/_build/mutations.py
"""

MUTATIONS = [
    # The filter is dropped from the candidate query: pre_filter ranks the whole corpus
    # and returns documents that do not satisfy the metadata constraints (step 2).
    (
        "pre_filter forgets the SQL WHERE clause",
        "filtered.py",
        '        where, params = _where_clause(filters)\n'
        '        rows = self.conn.execute(\n'
        '            f"SELECT doc_id FROM documents WHERE {where}", params).fetchall()',
        '        where, params = "1=1", []\n'
        '        rows = self.conn.execute(\n'
        '            f"SELECT doc_id FROM documents WHERE {where}", params).fetchall()',
        "2",
    ),
    # Year compared as a two-character substring instead of the four-character date
    # prefix: a 2024 document is admitted by a year=2023 filter (step 2).
    (
        "year compared as a substring instead of the date prefix",
        "filtered.py",
        '        if key == "year":\n'
        '            clauses.append("substr(date, 1, 4) = ?")\n'
        '            params.append(str(value))',
        '        if key == "year":\n'
        '            clauses.append("date LIKE ?")\n'
        '            params.append("%" + str(value)[:2] + "%")',
        "2",
    ),
    # build_db never creates the indexes, so no filter can be answered by a seek (step 1).
    (
        "build_db never creates the secondary indexes",
        "filtered.py",
        '    for column in FILTERABLE:\n'
        '        conn.execute(\n'
        '            f"CREATE INDEX idx_documents_{column} ON documents({column})")',
        '    pass',
        "1",
    ),
    # post_filter refills to k with whichever documents it ranked, including
    # non-matching ones, so a selective filter no longer returns only matches (step 5).
    (
        "post_filter pads its result back up to k with non-matching docs",
        "filtered.py",
        '        window = self._top(ranked, k)\n'
        '        return [doc_id for doc_id in window if self._passes(doc_id, filters)]',
        '        window = self._top(ranked, k)\n'
        '        kept = [doc_id for doc_id in window if self._passes(doc_id, filters)]\n'
        '        for doc_id in ranked:\n'
        '            if len(kept) >= k:\n'
        '                break\n'
        '            if doc_id not in kept:\n'
        '                kept.append(doc_id)\n'
        '        return self._top(kept, k)',
        "5",
    ),
    # filter_aware degenerates to post_filter, so it inherits the shortfall instead of
    # keeping the index navigable (step 5).
    (
        "filter_aware degenerates to post_filter",
        "filtered.py",
        '        text, filters = self._split(query, filters)\n'
        '        terms = tokenize(text)\n'
        '        if not terms:\n'
        '            return self._top([], k)\n'
        '\n'
        '        predicates = []',
        '        text, filters = self._split(query, filters)\n'
        '        terms = tokenize(text)\n'
        '        if not terms:\n'
        '            return self._top([], k)\n'
        '\n'
        '        return self.post_filter(query, k, filters)\n'
        '        predicates = []',
        "5",
    ),
    # The zero-score filter is relaxed, so a query with no matching term abstains by
    # returning the whole (filtered) corpus instead of [] (step 6).
    (
        "no-match case returns the whole corpus instead of empty",
        "filtered.py",
        '            if score > 0.0:',
        '            if score >= 0.0:',
        "6",
    ),
    # The access-level predicate is skipped, so an access filter leaks across
    # authorisation levels (step 2; tenant isolation must not be bypassable).
    (
        "pre_filter ignores the access_level filter",
        "filtered.py",
        '        elif key in FILTERABLE:\n'
        '            clauses.append(f"{key} = ?")',
        '        elif key in FILTERABLE and key != "access_level":\n'
        '            clauses.append(f"{key} = ?")',
        "2",
    ),
    # The superseded predicate is inverted, so a "fresh only" filter returns the stale
    # documents and vice versa (step 2).
    (
        "the superseded predicate is inverted",
        "filtered.py",
        '        elif key == "superseded":\n'
        '            clauses.append("superseded = ?")\n'
        '            params.append(1 if value else 0)',
        '        elif key == "superseded":\n'
        '            clauses.append("superseded = ?")\n'
        '            params.append(0 if value else 1)',
        "2",
    ),
    # post_filter filters the *whole* ranking instead of the top-k window, which
    # quietly repairs the anti-pattern the exercise is about (step 5).
    (
        "post_filter filters the full ranking instead of the top-k window",
        "filtered.py",
        '        window = self._top(ranked, k)\n'
        '        return [doc_id for doc_id in window if self._passes(doc_id, filters)]',
        '        return self._top(\n'
        '            [doc_id for doc_id in ranked if self._passes(doc_id, filters)], k)',
        "5",
    ),
]

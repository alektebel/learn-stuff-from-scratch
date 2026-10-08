"""Mutation tests for the RAG project-1 LSA checker.

Each entry is a classic mistake for the mechanism: the exact text is planted into a copy
of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/lsa rag-from-scratch/lsa/_build/mutations.py
"""

MUTATIONS = [
    # tf_idf pads the term weight with 1.0 instead of the document-frequency idf, so the
    # hand-computed values in step 2 are wrong (and every term counts the same).
    (
        "tf_idf forgets the idf factor",
        "lsa.py",
        "        vec = [row[j] * idf[j] for j in range(len(row))]",
        "        vec = [float(row[j]) for j in range(len(row))]",
        "2",
    ),
    # The sorting layer is bypassed, so jacobi's eigenpairs come back in rotation order:
    # the "top k" components are no longer the largest singular values (step 3).
    (
        "eig_sorted returns jacobi's eigenpairs unsorted",
        "lsa.py",
        "    order = sorted(range(n), key=lambda i: (-values[i], i))",
        "    order = list(range(n))",
        "3",
    ),
    # The requested rank is ignored and every non-zero component is kept, so the
    # reconstruction in step 3 is a different (larger) subspace.
    (
        "fit_lsa uses more components than requested",
        "lsa.py",
        "    rank = max(0, min(k, n_docs, n_terms))",
        "    rank = max(0, min(n_docs, n_terms))",
        "3",
    ),
    # The term means are never subtracted: the model is a plain SVD of the tf-idf matrix
    # and the stored mean/centre is wrong (step 3 compares both).
    (
        "fit_lsa drops the centring of the term-document matrix",
        "lsa.py",
        "    mean = [sum(row[j] for row in weighted) / n_docs for j in range(n_terms)] if n_docs else [0.0] * n_terms\n"
        "    centred = [[row[j] - mean[j] for j in range(n_terms)] for row in weighted]",
        "    mean = [0.0] * n_terms\n"
        "    centred = [[row[j] for j in range(n_terms)] for row in weighted]",
        "3",
    ),
    # The query embedding is returned un-normalised, so the cosine comparison becomes a
    # magnitude-sensitive dot product (step 4 checks the unit-norm contract).
    (
        "embed_query forgets to L2-normalise (cosine becomes a dot product)",
        "lsa.py",
        "    return _l2(coords)",
        "    return coords",
        "4",
    ),
    # The zero-score filter is relaxed, so a query with no known token returns the whole
    # (filtered) corpus instead of abstaining (step 6).
    (
        "no-match case returns the whole corpus instead of empty",
        "lsa.py",
        "            if score > 0.0:",
        "            if score >= 0.0:",
        "6",
    ),
    # D > N (more terms than documents) is forced through the large term-space Gram
    # matrix: the model reports the wrong Gram size and decomposes the wrong matrix
    # (step 6).
    (
        "the D > N case uses the large term-space Gram matrix",
        "lsa.py",
        "        if n_docs <= n_terms:",
        "        if n_docs > n_terms:",
        "6",
    ),
]

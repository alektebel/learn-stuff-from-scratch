"""Mutation tests for the RAG project-6 knowledge-graph + vector checker.

Each entry is a classic mistake for one mechanism of the graph: the exact text is planted
into a copy of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/knowledge-graph rag-from-scratch/knowledge-graph/_build/mutations.py

The steps mutated here (1-4, 6) run on a hand-built corpus or on the self-contained first
half of step 4, so the harness works in a bare temporary directory without the shared
eval set or the sibling bm25 (``hybrid_retrieve`` falls back to its local BM25).
"""

MUTATIONS = [
    # A predicate type is silently dropped while loading, so the store no longer mirrors
    # the corpus's typed triples (step 1 compares the counts and the relation set).
    (
        "the triple store drops the reports_to predicate type",
        "graph.py",
        '    for subject, predicate, object in corpus.get("relations", []):\n'
        '        relation = (subject, predicate, object)\n'
        '        relations.append(relation)\n'
        '        store.add(subject, predicate, object)',
        '    for subject, predicate, object in corpus.get("relations", []):\n'
        '        if predicate == "reports_to":\n'
        '            continue\n'
        '        relation = (subject, predicate, object)\n'
        '        relations.append(relation)\n'
        '        store.add(subject, predicate, object)',
        "1",
    ),
    # Entity names match by a prefix substring instead of whole words, so "engineers"
    # links the "Engineering" department (step 2's word-boundary case).
    (
        "entity linking matches by substring, so 'engineers' links 'Engineering'",
        "graph.py",
        '        pattern = _BOUNDARY.format(re.escape(name))\n'
        '        if re.search(pattern, text):',
        '        pattern = _BOUNDARY.format(re.escape(name))\n'
        '        if name in text or name[:6] in text:',
        "2",
    ),
    # Documents are returned regardless of any link, so every query's graph stage becomes
    # a whole-corpus scan (step 2 selects the linked subset exactly).
    (
        "documents_for_entities returns every document regardless of link",
        "graph.py",
        '    wanted = set(entity_ids)\n'
        '    found = []\n'
        '    for document in documents:\n'
        '        if wanted & set(document.get("entity_ids", ())):\n'
        '            found.append(document["doc_id"])\n'
        '    return sorted(found)',
        '    wanted = set(entity_ids)\n'
        '    found = []\n'
        '    for document in documents:\n'
        '        if True:\n'
        '            found.append(document["doc_id"])\n'
        '    return sorted(found)',
        "2",
    ),
    # The hop limit is ignored: the walk runs until the connected component is exhausted,
    # so a three-hop node appears in the two-hop answer (step 3 fixes a chain where the
    # third hop is a distinct node).
    (
        "multi_hop ignores the hop limit (returns the whole component)",
        "graph.py",
        '    distance = _hop_distances(start_ids, hops, store)\n'
        '    starts = set(start_ids)\n'
        '    return sorted(node for node in distance if node not in starts)',
        '    distance = _hop_distances(start_ids, len(store.match()) + 1, store)\n'
        '    starts = set(start_ids)\n'
        '    return sorted(node for node in distance if node not in starts)',
        "3",
    ),
    # The lexical half of the hybrid is dropped, so the result is no longer a superset of
    # the lexical candidates the first stage found (step 4's union assertion).
    (
        "hybrid_retrieve drops the lexical half",
        "graph.py",
        '    lexical = lexical_retrieve(query, k=depth, documents=documents)',
        '    lexical = []',
        "4",
    ),
    # The abstention path hands back every entity when the query names none, turning a
    # no-answer query into a whole-graph scan (step 6 pins the empty result).
    (
        "the abstention path returns every entity",
        "graph.py",
        '    entity_ids = link_entities(query, store.entities)\n'
        '    if not entity_ids:\n'
        '        return []',
        '    entity_ids = link_entities(query, store.entities)\n'
        '    if not entity_ids:\n'
        '        entity_ids = [entity["id"] for entity in store.entities]',
        "6",
    ),
]

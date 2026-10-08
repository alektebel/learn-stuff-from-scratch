"""Graded hints for the RAG project-6 knowledge-graph templates.

Each listed function keeps its signature and docstring; its body is replaced by the hint
below. Regenerate the template with:

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        rag-from-scratch/knowledge-graph rag-from-scratch/knowledge-graph/_build/hints.py

Everything not listed here (the tokeniser, constants, `_eval_set_solutions`,
`_load_corpus`, `_import_metrics`, `_hop_distances`, `_try_import_bm25`,
`_passes_filters`, `_local_retrieve`, `_flatten_queries`, `TripleStore.__init__`, the
demo) is provided scaffolding: it is not the point of the exercise, and the checks lean
on it.
"""

HINTS = {
    "graph.py": {
        "TripleStore.add":
            "Stringify the three components, add the tuple to the seen set and append it "
            "to the triple list only when it is new; return self.",
        "TripleStore.match":
            "Scan the triples and keep those whose every non-None component equals the "
            "argument; return the matches sorted as a list of tuples.",
        "TripleStore.neighbours":
            "Scan the triples (respecting an optional predicate) and collect the other "
            "endpoint when the node is the subject or the object; return the distinct "
            "nodes sorted.",
        "load_graph":
            "Copy corpus['entities'] and build a name->id map (lower-cased names); add "
            "every corpus relation to a new TripleStore(entities=entities) and collect it "
            "in `relations`. For each document, resolve its topics / department / author "
            "to entity ids, record them as `entity_ids`, and add the derived "
            "(doc_id, 'about'|'owned_by'|'authored_by', entity_id) triples to the store "
            "and to `doc_links`. Return the entities, relations, documents, doc_links and "
            "store.",
        "link_entities":
            "Lower-case the query text; for each entity whose name is non-empty test "
            "`re.search(_BOUNDARY.format(re.escape(name)), text)` and collect the id. "
            "Return the deduplicated ids sorted; nothing matched is [].",
        "multi_hop":
            "Call `_hop_distances(start_ids, hops, store)` and return the sorted node ids "
            "it assigned a distance to, excluding the start ids themselves.",
        "documents_for_entities":
            "Keep the doc_id of every document whose `entity_ids` intersects the wanted "
            "set; return them sorted. No intersection (and an empty input) is [].",
        "lexical_retrieve":
            "Import the sibling `../bm25` (`_try_import_bm25`); if present, build a "
            "BM25Retriever over `documents` and return `retriever.retrieve(query, k=k)`, "
            "otherwise return `_local_retrieve(query, k, documents)`.",
        "graph_retrieve":
            "Link the query's entity names with `link_entities(query, store.entities)`; "
            "return [] when none link. Otherwise take `_hop_distances(entity_ids, "
            "HOP_LIMIT, store)`, keep document nodes inside the limit, and union in "
            "`documents_for_entities` over the entity_ids plus the non-document nodes "
            "within HOP_LIMIT-1. Sort by (distance, doc_id) and slice to k.",
        "hybrid_retrieve":
            "Ask both stages for the full pool (depth=len(documents)); build `fused` by "
            "adding 1/(RRF_K+rank) for each lexical result and GRAPH_WEIGHT/(RRF_K+rank) "
            "for each graph result (so the keys are exactly the union), sort by "
            "(-score, doc_id) and return the top k.",
        "evaluate":
            "Flatten the queries, build the graph once, run lexical_retrieve, "
            "graph_retrieve and hybrid_retrieve per query, and return the shared "
            "`metrics.evaluate` result under 'lexical', 'graph' and 'hybrid' alongside "
            "the predictions, k and graph data.",
    },
}

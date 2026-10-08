"""Mutation tests for the RAG project-1 HNSW checker.

Each entry is a classic mistake for the mechanism: the exact text is planted into a copy
of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/hnsw rag-from-scratch/hnsw/_build/mutations.py
"""

MUTATIONS = [
    # `l2` returns the squared distance. It is monotone, so exact ranking survives, but
    # it is not the metric the API promises; step 1 pins it to hand-computed roots.
    (
        "l2 returns the squared distance",
        "hnsw.py",
        "    return math.sqrt(total)",
        "    return total",
        "1",
    ),
    # Upper layers are given no forward links, so the "highways" are disconnected and
    # the graph is only layer 0 with extra empty bookkeeping. Step 2 asserts the
    # upper-layer links are bidirectional.
    (
        "insert never links a node at the upper layers",
        "hnsw.py",
        "        self.layers[layer][key].update(neighbours)",
        "        self.layers[layer][key].update(neighbours if layer == 0 else set())",
        "2",
    ),
    # `search` ignores ef and always runs greedy depth-1 descent: recall collapses and
    # stops improving as ef grows. Step 3 measures recall across ef.
    (
        "search ignores ef and always does greedy depth-1 descent",
        "hnsw.py",
        "        found = self._search_layer(vector, [entry], exploration, 0)",
        "        found = self._search_layer(vector, [entry], 1, 0)",
        "3",
    ),
    # `search` fabricates the query's own key as the nearest neighbour. Step 2 passes a
    # query whose key is not in the index and asserts it never comes back.
    (
        "search returns the query's own key as its nearest neighbour",
        "hnsw.py",
        "        return [(key, distance) for distance, key in found[:k]]",
        "        own = query.get(\"key\") if isinstance(query, dict) else None\n"
        "        if own is not None:\n"
        "            found = [(0.0, own)] + [(distance, key) for distance, key in found\n"
        "                                    if key != own]\n"
        "        return [(key, distance) for distance, key in found[:k]]",
        "2",
    ),
    # `recall_at_k` divides by the number of returned neighbours instead of the exact
    # set, so a single lucky hit claims perfect recall. Step 3 checks the denominator by
    # hand before measuring.
    (
        "recall_at_k divides by the wrong count",
        "hnsw.py",
        "    return len(set(approx_keys) & exact) / len(exact)",
        "    return (len(set(approx_keys) & exact) / len(set(approx_keys))\n"
        "            if approx_keys else 0.0)",
        "3",
    ),
    # The selective-filter helper skips filtering and returns the whole ANN list. Step 6
    # asks for a filter that matches nothing and asserts the shortfall.
    (
        "selective filter returns the whole corpus instead of the filtered shortfall",
        "hnsw.py",
        "    return [key for key in keys if key in by_id and _passes_filters(by_id[key], filters)]",
        "    return list(keys)",
        "6",
    ),
]

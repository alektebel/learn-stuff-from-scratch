"""Graded hints for the RAG project-1 HNSW templates.

Each entry maps a function the learner must write to a one-line hint. Everything not
listed here (``_FILTER_KEYS``, ``_passes_filters``, ``_flatten_queries``,
``_eval_set_path``, ``_import_metrics``, ``_row``) is provided scaffolding: it is not the
point of the exercise and the checks lean on it.
"""

HINTS = {
    "hnsw.py": {
        "l2": (
            "Accumulate (a[i]-b[i])**2 and return math.sqrt(...). The square root is the "
            "point: the squared distance is monotone but is not the metric the API (and "
            "step 1) require."
        ),
        "cosine": (
            "dot / (|a| |b|), then 1 - that. Return 0.0 when either norm is zero (the "
            "zero vector has no direction), and clamp to [0, 2]."
        ),
        "HnswIndex.__init__": (
            "Store dim/M/M0=2*M/ef_construction, seed random.Random(seed), set "
            "ml = 1/ln(M), and initialise layers=[], vectors={}, keys=[], a per-key "
            "insertion sequence, entry=None, max_level=-1, distance_calls=0."
        ),
        "HnswIndex.insert": (
            "Assign level = floor(-ln(1-random())/ln(M)). Create the layers up to that "
            "level and add the key to each. If the index was empty, it becomes the entry. "
            "Otherwise greedily descend from the entry through layers above the new "
            "level, then for each layer down to 0 run an ef_construction-bounded search, "
            "take the closest M (2M on layer 0), link both ways and prune each neighbour "
            "back to budget. Promote to entry if the level is a new maximum."
        ),
        "HnswIndex.search": (
            "Reset distance_calls, greedily descend from the entry through the upper "
            "layers, run an ef-bounded layer-0 search, and return the best k as "
            "(key, distance) pairs. ef defaults to max(k, 10); do not silently raise an "
            "explicit ef to k, because the small-ef miss is the lesson."
        ),
        "exact_search": (
            "Compute l2 to every vector, sort by (distance, position) for determinism, "
            "and return the first k as (key, distance). This is the ground truth; the "
            "index must not call it."
        ),
        "recall_at_k": (
            "len(set(approx) & set(exact)) / len(set(exact)), or 0.0 when exact is empty. "
            "Dividing by the approximate count turns one lucky hit into perfect recall."
        ),
        "build_lsa_index": (
            "Tokenise title + body with [a-z0-9]+; build the count matrix; tf-idf with "
            "the smoothed BM25 idf and L2-normalise the rows; subtract the column mean; "
            "take the truncated SVD from the smaller Gram matrix with Jacobi; project "
            "the centred rows onto the retained right singular vectors; L2-normalise. "
            "Return (doc_ids, embeddings, model)."
        ),
        "embed_query": (
            "Fold the query in: tokenise, multiply by the stored idf, L2-normalise, "
            "subtract the stored mean, project onto the components, L2-normalise. No "
            "known token -> the zero vector."
        ),
        "metadata_filter": (
            "Build doc_id -> document once and keep the keys that pass _passes_filters. "
            "This runs AFTER the ANN search, so a selective filter legitimately returns "
            "fewer than k."
        ),
        "evaluate": (
            "Fit LSA, build and populate an HnswIndex with the document embeddings, fold "
            "each query into the same space, search, apply metadata_filter to the ANN "
            "keys (a zero-vector query abstains), then return metrics.evaluate(...) plus "
            "mean_distance_calls."
        ),
        "demo": (
            "Build the eval-set LSA index, sweep ef over a few values and print mean "
            "recall@10 against exact search and the mean distance calls per query; then "
            "print the family metrics from evaluate and the mean work. Report the numbers "
            "as measured."
        ),
    },
}

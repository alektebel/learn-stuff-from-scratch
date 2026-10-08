"""Mutation tests for the RAG project-3 RERANKING checker.

Each entry is a classic mistake for a learned reranker: the exact text is planted into a
copy of the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/reranking rag-from-scratch/reranking/_build/mutations.py
"""

MUTATIONS = [
    # A reranker that forgets to reorder is just the first stage again: step 2 hands it
    # a candidate order whose first item is the distractor and requires it to be reversed.
    (
        "rerank echoes the candidate order (no-op, never reorders)",
        "rerank.py",
        "        return [doc_id for _score, doc_id in scored[:max(0, k)]]",
        "        return _as_keys(candidates)[:max(0, k)]",
        "2",
    ),
    # A feature that is dropped to a constant contributes nothing; step 1 requires every
    # feature to vary across the toy documents.
    (
        "term_coverage is dropped to a constant",
        "rerank.py",
        '        "term_coverage": coverage,',
        '        "term_coverage": 0.0,',
        "1",
    ),
    # Scoring the whole corpus instead of the candidate list lets the reranker invent
    # documents the first stage never returned; step 3 requires a subset.
    (
        "rerank re-scores the whole corpus instead of the candidates",
        "rerank.py",
        "        for doc_id in _as_keys(candidates):",
        '        for doc_id in [doc["doc_id"] for doc in self.context.documents]:',
        "3",
    ),
    # Weights pinned at zero: the model never learns, the loss is flat and the base order
    # is never reversed (step 2 checks both the loss and the final order).
    (
        "fit leaves the weights at zero and never learns",
        "rerank.py",
        "                self.weights[index] -= self.lr * (gradients[index] * scale\n"
        "                                                  + self.l2 * self.weights[index])",
        "                self.weights[index] = 0.0",
        "2",
    ),
    # An empty first stage means abstain; returning the corpus invents results. Step 6
    # pins that a no-answer query stays [] through the reranker.
    (
        "the abstention path returns the whole candidate list",
        "rerank.py",
        "        scored.sort(key=lambda pair: (-pair[0], pair[1]))\n"
        "        return [doc_id for _score, doc_id in scored[:max(0, k)]]",
        "        scored.sort(key=lambda pair: (-pair[0], pair[1]))\n"
        "        if not scored and self.context is not None:\n"
        '            return [doc["doc_id"] for doc in self.context.documents][:max(0, k)]\n'
        "        return [doc_id for _score, doc_id in scored[:max(0, k)]]",
        "6",
    ),
    # Letting the evaluation queries leak into training turns the held-out metric into
    # training accuracy; step 4 asserts the split is disjoint before anything else.
    (
        "the split leaks: evaluation queries are also trained on",
        "rerank.py",
        "    return train, evaluation",
        "    return list(train) + list(evaluation), evaluation",
        "4",
    ),
    # Weights pinned to a constant while only the bias learns: the loss still falls and
    # the separable toy example is still ordered correctly, so this passes the naive
    # assertions. Step 2 trains on the swapped labels and requires the order to flip,
    # which only an example-dependent fit can do.
    (
        "fit pins the weights to a constant and only learns the bias",
        "rerank.py",
        "            for index in range(n_features):\n"
        "                self.weights[index] -= self.lr * (gradients[index] * scale\n"
        "                                                  + self.l2 * self.weights[index])",
        "            for index in range(n_features):\n"
        "                self.weights[index] = 1.0",
        "2",
    ),
]

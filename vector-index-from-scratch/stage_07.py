"""Vector Index From Scratch — stage 7: the walk, and ef

DESIGN DECISION — ef is a pool width, not a result count.
    `ef` is how many candidates the layer-0 search keeps alive while it explores;
    `k` is how many rows you are allowed to return. The two are different
    numbers, and `ef < k` cannot return k rows no matter how good the graph is —
    refuse it rather than return a short list. Raising ef is the dial that buys
    recall: the walk explores wider, the returned k are drawn from a better
    pool, and the cost is more distance computations. That trade is the whole
    object of this course.

DESIGN DECISION — keep the best rows seen, not the node the walk stopped at.
    The walk ends at a local minimum of the greedy walk, and a better neighbour
    found one hop earlier is still an answer you already paid for. Collect into
    a bounded pool (evicting the worst when it is full) and sort it at the end,
    rather than returning where you happened to stop.

    Inside `build` you needed a version of this walk already, with the pool
    fixed at ef_construction. Here it is explicit, and the checks measure it:
    exhaustive when the pool is the whole corpus, and better than the exact
    answer's recall target as ef grows.

TODO: implement

    search(graph, query, k, ef) -> [(key, score)]
        descending by score, ties broken by key ascending (the keys here are
        arbitrary; "ascending key" is deterministic where insertion order is
        not available).

        ef < k -> ValueError. ef is not capped: ef >= number of nodes is an
        exhaustive scan and must return exactly what the exact index returns,
        row for row — same rows, same order.

        The walk: at every layer above 0, move greedily to the neighbour closest
        to the query for as long as that improves the position; then at layer 0
        run a best-first search that keeps up to ef candidates and never visits
        a node twice. A node's score is the dot product with the query (unit
        vectors). Return the k best rows seen.

        The graph is the dict stage 6 returned: "entry" is the key to start
        from, "vectors" is {key: unit vector}. Anything else in it is internal
        to build(). Calling search twice with the same arguments must return the
        same rows and must not mutate the graph.
"""


def search(graph, query, k, ef):
    raise NotImplementedError("stage 7: implement search()")

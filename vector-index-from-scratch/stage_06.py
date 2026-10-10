"""Vector Index From Scratch — stage 6: the HNSW graph, built not searched

DESIGN DECISION — the links are the data structure, so keep them undirected.
    When a node's neighbour list is full you prune the farthest neighbour — and
    a prune that only edits one side leaves a one-way link: the walk can enter
    through it and never leave. The two lists then disagree about the graph, and
    the search's behaviour depends on which node it happened to arrive from.
    Remove the reverse edge too. It costs a lookup and makes the structure
    checkable: "j is a neighbour of k" and "k is a neighbour of j" are the same
    statement, at every layer.

DESIGN DECISION — the level distribution is the hierarchy.
    A node's level is floor(-ln(u) * mL) with u uniform in (0, 1) and
    mL = 1 / ln(M), so levels thin out geometrically: the top layer is a few
    nodes whose job is to cross the space in a handful of hops, and the walk in
    stage 7 descends through them. Get this wrong — give every node the same
    level, or add one to every level — and nothing fails loudly; you have simply
    built a flat graph that costs the same as a scan. The check looks for the
    thinning distribution.

    ef_construction = 32 is fixed: how wide the candidate search is while the
    graph is being built. Wider is a better graph for more build time, and it is
    not the parameter this course tunes — the search's `ef` is (stage 7).

TODO: implement

    build(vectors, M, seed, mL=None, ef_construction=32) -> graph
        `vectors` is a dict {key: unit vector}; insertion order is the build
        order (Python keeps it). Returns a dict with at least:

            "entry"    the key with the highest level (ties: inserted first)
            "vectors"  a dict {key: unit vector} — copies, so a caller editing
                       its own dict cannot change this index's answers

        The rest of the representation is yours; the accessors below define it,
        not the check.

        A node with level L exists at every layer 0..L and is linked at each of
        them. Degree caps: 2*M at layer 0, M above it; prune by distance when
        full, symmetrically. M <= 1 has no mL (ln 1 == 0) -> ValueError.
        mL=0.0 makes every level 0 — a flat graph, and legal.

    neighbors(graph, key, layer) -> list[str]
        sorted, [] when the key exists but has no neighbours there; KeyError for
        a key that is not in the graph.

    level(graph, key) -> int      KeyError for an unknown key
    layers(graph) -> list[int]    the layers that exist, ascending (0 always)

    Insertion, per key, in order: descend from the entry point to the node's
    level with a greedy walk, then at each layer from min(level, top) down to 0
    search a candidate pool (ef_construction wide), link the M nearest
    (2*M at layer 0), and raise the entry point if this node is the new highest.
"""


def build(vectors, M, seed, mL=None, ef_construction=32):
    raise NotImplementedError("stage 6: implement build()")


def neighbors(graph, key, layer):
    raise NotImplementedError("stage 6: implement neighbors()")


def level(graph, key):
    raise NotImplementedError("stage 6: implement level()")


def layers(graph):
    raise NotImplementedError("stage 6: implement layers()")

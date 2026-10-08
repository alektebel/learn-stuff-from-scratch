"""HNSW — the approximate nearest-neighbour stage of RAG project 1 (hybrid search).

The pipeline is BM25 -> LSA -> HNSW -> fusion. BM25 and LSA rank documents; LSA turns
every document into a short dense vector. HNSW (Malkov & Yashunin, *Efficient and robust
approximate nearest neighbor search using Hierarchical Navigable Small World graphs*,
2016/2018) is the index that finds the nearest of those vectors cheaply: a multlayer
navigable small-world graph whose upper layers are sparse "highways" and whose bottom
layer holds every point.

This module is wired to the shared step-0 evaluation set (`../eval-set`). It indexes the
LSA document embeddings of that corpus and is measured on the same queries the BM25 and
LSA stages are measured on; `evaluate` returns the same metrics dictionary they return,
plus the mean number of distance computations per query (the work the approximation
spends).

Every function and method below that raises ``NotImplementedError`` is yours to write.
The scaffolding (`_FILTER_KEYS`, `_passes_filters`, `_flatten_queries`, `_eval_set_path`,
`_import_metrics`, `_row`) is provided: it is not the point of the exercise and the
checks lean on it. Run ``python3 check.py`` after each step; the docstrings walk through
the design and `_build/hints.py` has a one-line hint per function.

DESIGN DECISION - distance is a real metric: `l2` returns the Euclidean distance (the
    square root) and `cosine` returns the cosine distance ``1 - cos`` in [0, 2]. Both are
    non-negative and zero only for identical points/directions, so search orders by
    "smaller is closer" with no special case. Cost: a square root per comparison;
    returning the squared distance would rank identically for exact search but is NOT the
    metric the checker pins down (it is planted as a mutation).

DESIGN DECISION - node level is geometric: ``floor(-ln(U) / ln(M))`` for U uniform in
    (0, 1]. Higher layers hold exponentially fewer nodes, so a greedy descent crosses
    the space in O(log N) hops. Cost: the graph depends on the seed, so the seed is a
    constructor argument and every check is deterministic.

DESIGN DECISION - links are bidirectional and pruned to the closest M (2M on layer 0).
    Insert runs an ef_construction-bounded search at every layer down from the entry,
    links both ways, and prunes each touched neighbour list back to its budget. Cost:
    building is O(N * ef_construction * M * log N); ef_construction is the knob.

DESIGN DECISION - the index records ``distance_calls`` so recall can be read against the
    work that bought it. A run that returns a perfect answer but touches every vector is
    a linear scan wearing a graph costume; the checks assert the work is sub-linear.

DESIGN DECISION - metadata filtering happens AFTER the ANN search, never inside it. The
    graph has no filter awareness: ask for the top k, then drop non-matching documents. A
    very selective filter therefore returns fewer than k results (possibly none). Step 6
    of check.py measures that shortfall instead of pretending the filter is free.

DESIGN DECISION - the LSA fit is re-derived here rather than imported from the sibling
    solution at ``../lsa/solutions/lsa.py``. This module must run when only it and
    ``../eval-set`` are present (the checker and mutation suite use that layout), so it
    carries the same compact tf-idf + centred truncated-SVD pipeline. Cost: the two
    copies must agree on the tokeniser and the idf.
"""
from __future__ import annotations


# The metadata keys the eval-set queries filter on. Kept identical to BM25/LSA so the
# three stages filter the same way and their comparison is meaningful.
_FILTER_KEYS = ("region", "year", "department", "access_level")


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def l2(a, b):
    """Euclidean distance between two equal-length vectors.

    Return ``sqrt(sum((a[i] - b[i]) ** 2))``: the true metric, not its square. It is
    symmetric and zero exactly when the two vectors are equal.
    """
    raise NotImplementedError("l2: Euclidean distance (not the squared distance)")


def cosine(a, b):
    """Cosine *distance* ``1 - cos(a, b)`` in [0, 2].

    Smaller is closer: identical direction -> 0, orthogonal -> 1, opposite -> 2. A zero
    vector has no direction; return 0.0 when either vector is the zero vector. That
    convention is what makes LSA's zero (no-match) query equidistant from every document
    and lets the pipeline treat it as an abstention.
    """
    raise NotImplementedError("cosine: 1 - cos, with the zero-vector convention")


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------

class HnswIndex:
    """A multilayer navigable small-world index over fixed-length vectors.

    ``layers[level]`` maps a key to the set of its neighbour keys on that layer;
    ``layers[0]`` contains every key. ``entry`` is the key every search starts from and
    ``max_level`` is the highest layer that exists. ``distance_calls`` counts every
    distance evaluation and is reset by ``search``.
    """

    def __init__(self, dim, M=16, ef_construction=200, seed=0):
        raise NotImplementedError(
            "HnswIndex.__init__: an RNG, layers/entry/keys/max_level/distance_calls")

    def insert(self, vector, key=None):
        """Add ``vector`` under ``key`` (auto-assigned from the insertion order).

        Give the node a geometric level, greedily descend from the current entry to that
        level, then at every layer the node belongs to run an ef_construction-bounded
        search and link it both ways, pruning each neighbour list back to its budget
        (``M``, or ``2*M`` at layer 0). A node that reaches a new top level becomes the
        new entry. Reject vectors whose length is not ``dim`` and duplicate keys.
        """
        raise NotImplementedError(
            "HnswIndex.insert: geometric level, descent, per-layer linking + pruning")

    def search(self, query, k, ef=None):
        """Return the ``k`` closest stored ``(key, distance)`` pairs, closest first.

        Greedily descend the upper layers, run an ef-bounded search on layer 0 and keep
        the best ``k``. ``ef`` defaults to ``max(k, 10)``; larger values explore more of
        the graph for the same k. An explicit ``ef`` below k returns fewer than k results:
        that is the honest small-ef miss, not a bug. Reset ``self.distance_calls`` to 0
        before searching so callers can audit the work. The query may be a plain vector
        or a mapping with a ``vector`` field; never fabricate the query's own key into
        the result.
        """
        raise NotImplementedError(
            "HnswIndex.search: descend, ef-search layer 0, return k sorted results")


# ---------------------------------------------------------------------------
# Reference and metrics
# ---------------------------------------------------------------------------

def exact_search(vectors, keys, query, k):
    """Brute force: compute every distance and return the ``k`` closest.

    ``vectors`` and ``keys`` are parallel lists. Return the same shape as
    ``HnswIndex.search`` (``[(key, distance), ...]``, closest first) so the two compare
    directly. This is the ground truth HNSW is measured against: the index must not call
    it.
    """
    raise NotImplementedError("exact_search: brute force the whole corpus")


def recall_at_k(approx_keys, exact_keys):
    """Fraction of the exact top-k keys the approximate result recovered.

    ``len(set(approx) & set(exact)) / len(exact)`` when ``exact`` is non-empty, else
    0.0. The denominator is the exact set; dividing by the approximate count would let a
    result that returned one lucky hit claim perfect recall.
    """
    raise NotImplementedError("recall_at_k: |intersection| / |exact|")


# ---------------------------------------------------------------------------
# Wiring to the eval set
# ---------------------------------------------------------------------------

def build_lsa_index(docs, k, seed=0):
    """Fit LSA on ``docs`` and return ``(keys, vectors, model)`` for HNSW to index.

    The embeddings are the LSA document coordinates from the sibling stage. Re-derive
    the same compact LSA fit here (tf-idf on the shared tokeniser, centring, truncated
    SVD by Jacobi on the smaller Gram matrix) so this module runs with only
    ``../eval-set`` next to it; the README documents that choice. Put the fitted model
    in the returned triple so queries can be folded into the same basis.
    """
    raise NotImplementedError("build_lsa_index: LSA document embeddings + model")


def embed_query(text, model):
    """Project a raw query string into the fitted LSA space (fold-in), L2-normalised.

    A query with no known token returns the zero vector, which ``cosine`` treats as
    equidistant from everything and ``evaluate`` treats as an abstention.
    """
    raise NotImplementedError("embed_query: fold a query into the LSA basis")


# ---------------------------------------------------------------------------
# Metadata filtering (post-ANN) and the eval-set wiring
# ---------------------------------------------------------------------------

def _passes_filters(doc, filters):
    """Scaffolding: the eval set's metadata predicate (region/year/department/access)."""
    if not filters:
        return True
    for key in _FILTER_KEYS:
        if key not in filters:
            continue
        value = filters[key]
        if key == "year":
            if doc.get("date", "")[:4] != str(value):
                return False
        elif doc.get(key) != value:
            return False
    return True


def metadata_filter(keys, filters, documents):
    """Keep only ``keys`` whose document passes ``filters`` (applied AFTER the ANN).

    A very selective filter shrinks the result below the requested k, possibly to zero.
    Return the filtered keys, in the original order.
    """
    raise NotImplementedError("metadata_filter: post-filter the ANN keys by metadata")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(corpus, queries, k=10, n_components=None, M=16, ef_construction=200,
             ef=None, seed=0):
    """Index the corpus's LSA embeddings and score every query family with HNSW.

    Return the shared metrics dictionary (``overall``, ``by_type``, ``abstention``,
    ``per_query``) — the shape BM25's ``evaluate_bm25`` and LSA's ``evaluate`` return —
    plus ``"mean_distance_calls"``, the average number of distance evaluations per query.
    Apply metadata filters AFTER the ANN search.
    """
    raise NotImplementedError("evaluate: index LSA embeddings, score, add mean work")


def _flatten_queries(queries):
    """Scaffolding: accept the eval set's family dict or an already-flat query list."""
    if isinstance(queries, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [q for family in order for q in queries.get(family, [])]
    return list(queries)


def _eval_set_path():
    """Scaffolding: locate the shared eval set's solutions directory."""
    import pathlib

    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here.parent / "eval-set" / "solutions",
                      here.parent.parent / "eval-set" / "solutions"):
        if (candidate / "metrics.py").is_file():
            return candidate
    raise FileNotFoundError(
        "cannot find the shared eval set at ../eval-set/solutions relative to "
        f"{here}: run the module from inside rag-from-scratch/ or copy check.py next to "
        "the eval set.")


def _import_metrics():
    """Scaffolding: import the eval set's metrics module, adding it to sys.path once."""
    import sys

    path = str(_eval_set_path())
    if path not in sys.path:
        sys.path.insert(0, path)
    import metrics

    return metrics


def _row(result, family):
    """Scaffolding: one family's metrics (or the overall row) from a metrics dict."""
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print honest recall@k and distance-computation numbers on the shared eval set."""
    raise NotImplementedError("demo: report recall@k and mean distance calls by ef")


if __name__ == "__main__":
    demo()

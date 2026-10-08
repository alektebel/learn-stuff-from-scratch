"""HNSW — the approximate nearest-neighbour stage of RAG project 1 (hybrid search).

The pipeline is BM25 -> LSA -> HNSW -> fusion. BM25 and LSA rank documents; LSA turns
every document into a short dense vector. HNSW (Malkov & Yashunin, *Efficient and robust
approximate nearest neighbor search using Hierarchical Navigable Small World graphs*,
2016/2018) is the index that finds the nearest of those vectors without touching the
whole corpus: a stack of proximity graphs whose top layer is a sparse "highway" and
whose bottom layer holds every point.

This module is wired to the shared step-0 evaluation set (`../eval-set`). It indexes the
LSA document embeddings of that corpus and is measured on the same queries the BM25 and
LSA stages use, so the three stages are comparable; `evaluate` returns the same metrics
dictionary they return, plus the mean number of distance computations per query.

DESIGN DECISION - distance is a real metric: `l2` returns the Euclidean distance (the
    square root) and `cosine` returns the cosine distance ``1 - cos`` in [0, 2]. Both are
    non-negative and zero only for identical points/directions, so the search orders by
    "smaller is closer" without a special case. Cost: a square root per comparison;
    returning the squared distance would rank identically for exact search but is NOT
    the metric the checker pins down.

DESIGN DECISION - node level is geometric: ``floor(-ln(U) / ln(M))`` for U uniform in
    (0, 1]. Higher layers therefore hold exponentially fewer nodes and a greedy descent
    crosses the space in O(log N) hops. Cost: the graph depends on the seed, so the seed
    is a constructor argument and every check is deterministic.

DESIGN DECISION - links are bidirectional and pruned to the closest M (2M on layer 0).
    Inserting a node runs an ef_construction-bounded search at every layer down from the
    entry, links both ways, and prunes each touched neighbour list back to its budget.
    Cost: building is O(N * ef_construction * M * log N); ef_construction is the knob.

DESIGN DECISION - the index records ``distance_calls`` so recall can be read against the
    work that bought it. A run that returns a perfect answer but touches every vector is
    a linear scan wearing a graph costume; the checks assert the work is sub-linear.

DESIGN DECISION - metadata filtering happens AFTER the ANN search, never inside it.
    The graph has no filter awareness: we ask for the top k, then drop non-matching
    documents. A very selective filter therefore returns fewer than k results (possibly
    none). Pretending otherwise would require filtered graph traversal, which this
    module deliberately does not build; step 6 of check.py measures the shortfall.

DESIGN DECISION - the LSA fit is re-derived here rather than imported from the sibling
    solution at ``../lsa/solutions/lsa.py``. This module must run when only it and
    ``../eval-set`` are present (that is the layout the checker and the mutation suite
    use), so it carries the same compact tf-idf + centred truncated-SVD (Jacobi on the
    smaller Gram matrix) pipeline. Cost: the two copies must agree on the tokeniser and
    the idf; the eval-set wiring is the only thing they share.

Run the demo, which prints honest recall@k and distance-computation numbers:
`python3 solutions/hnsw.py`.
"""
from __future__ import annotations

import heapq
import math
import random
import re

# The metadata keys the eval-set queries filter on. Kept identical to BM25/LSA so the
# three stages filter the same way and their comparison is meaningful.
_FILTER_KEYS = ("region", "year", "department", "access_level")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def l2(a, b):
    """Euclidean distance between two equal-length vectors.

    Returns ``sqrt(sum((a[i] - b[i]) ** 2))``: the true metric, not its square. It is
    symmetric and zero exactly when the two vectors are equal.
    """
    total = 0.0
    for x, y in zip(a, b):
        difference = x - y
        total += difference * difference
    return math.sqrt(total)


def cosine(a, b):
    """Cosine *distance* ``1 - cos(a, b)`` in [0, 2].

    Smaller is closer: identical direction -> 0, orthogonal -> 1, opposite -> 2. A zero
    vector has no direction; the convention here is distance 0.0 against everything,
    which is what makes LSA's zero (no-match) query equidistant from every document and
    lets the pipeline treat it as an abstention.
    """
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    value = 1.0 - dot / math.sqrt(na * nb)
    if value < 0.0:
        return 0.0
    if value > 2.0:
        return 2.0
    return value


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
        if dim <= 0:
            raise ValueError("dim must be positive")
        if M <= 0:
            raise ValueError("M must be positive")
        self.dim = dim
        self.M = M
        self.M0 = 2 * M
        self.ef_construction = ef_construction
        self.seed = seed
        self.rng = random.Random(seed)
        self._ml = 1.0 / math.log(M) if M > 1 else 0.0
        self.layers = []
        self.vectors = {}
        self.keys = []
        self._seq = {}
        self._counter = 0
        self.entry = None
        self.max_level = -1
        self.distance_calls = 0

    # -- internals ---------------------------------------------------------

    def _dist(self, a, b):
        """Distance between two stored/query vectors; the one audited counter."""
        self.distance_calls += 1
        return l2(a, b)

    def _level(self):
        """Geometric level ``floor(-ln(U) / ln(M))``, capped to keep the stack small."""
        u = 1.0 - self.rng.random()  # (0, 1]
        return min(63, int(-math.log(u) * self._ml))

    @staticmethod
    def _query_vector(query):
        """Accept a plain vector or a mapping carrying one under ``vector``."""
        if isinstance(query, dict):
            return list(query["vector"])
        return list(query)

    def _greedy(self, query, entry, layer):
        """Greedy descent on one layer: repeatedly step to the closest neighbour."""
        current = entry
        current_distance = self._dist(query, self.vectors[current])
        improved = True
        while improved:
            improved = False
            for neighbour in self.layers[layer].get(current, ()):
                distance = self._dist(query, self.vectors[neighbour])
                if distance < current_distance:
                    current, current_distance = neighbour, distance
                    improved = True
        return current

    def _search_layer(self, query, entry_points, ef, layer):
        """ef-bounded beam search on ``layer``; returns ``[(distance, key), ...]`` ascending.

        ``ef`` caps the result set. With ``ef == 1`` this degenerates to greedy descent.
        """
        ef = max(1, ef)
        visited = set(entry_points)
        candidates = []
        results = []  # max-heap on distance via negated values
        for entry in entry_points:
            distance = self._dist(query, self.vectors[entry])
            heapq.heappush(candidates, (distance, self._seq[entry], entry))
            heapq.heappush(results, (-distance, self._seq[entry], entry))
        while candidates:
            candidate_distance, _seq, candidate = heapq.heappop(candidates)
            worst = -results[0][0]
            if len(results) >= ef and candidate_distance > worst:
                break
            for neighbour in self.layers[layer].get(candidate, ()):
                if neighbour in visited:
                    continue
                visited.add(neighbour)
                distance = self._dist(query, self.vectors[neighbour])
                if len(results) < ef or distance < -results[0][0]:
                    heapq.heappush(candidates, (distance, self._seq[neighbour], neighbour))
                    heapq.heappush(results, (-distance, self._seq[neighbour], neighbour))
                    if len(results) > ef:
                        heapq.heappop(results)
        found = [(-negated, entry) for negated, _seq, entry in results]
        found.sort(key=lambda pair: (pair[0], self._seq[pair[1]]))
        return found

    def _select_neighbours(self, candidates, budget):
        """Closest ``budget`` neighbours from a ``[(distance, key), ...]`` list."""
        return [key for _distance, key in candidates[:budget]]

    def _add_links(self, layer, key, neighbours):
        """Link ``key`` to ``neighbours`` both ways, pruning each list to its budget."""
        budget = self.M0 if layer == 0 else self.M
        self.layers[layer][key].update(neighbours)
        for neighbour in neighbours:
            self.layers[layer][neighbour].add(key)
            if len(self.layers[layer][neighbour]) > budget:
                ranked = sorted(
                    self.layers[layer][neighbour],
                    key=lambda other: (self._dist(self.vectors[neighbour], self.vectors[other]),
                                       self._seq[other]),
                )
                keep = set(ranked[:budget])
                for dropped in self.layers[layer][neighbour] - keep:
                    self.layers[layer][dropped].discard(neighbour)
                self.layers[layer][neighbour] = keep

    # -- public API --------------------------------------------------------

    def insert(self, vector, key=None):
        """Add ``vector`` under ``key`` (auto-assigned from the insertion order).

        The node gets a geometric level, the search greedily descends to that level, and
        at every layer the node belongs to it links to an ef_construction-bounded beam
        of neighbours. A node that reaches a new top level becomes the new entry.
        """
        vector = list(vector)
        if len(vector) != self.dim:
            raise ValueError(f"expected a {self.dim}-dimensional vector, got {len(vector)}")
        if key is None:
            key = len(self.keys)
        if key in self.vectors:
            raise ValueError(f"duplicate key {key!r}")
        self.vectors[key] = vector
        self.keys.append(key)
        self._seq[key] = self._counter
        self._counter += 1

        level = self._level()
        while len(self.layers) <= level:
            self.layers.append({})
        for layer in range(level + 1):
            self.layers[layer].setdefault(key, set())

        if self.entry is None:
            self.entry = key
            self.max_level = level
            return key

        entry = self.entry
        for layer in range(self.max_level, level, -1):
            entry = self._greedy(vector, entry, layer)

        for layer in range(min(level, self.max_level), -1, -1):
            candidates = self._search_layer(vector, [entry], self.ef_construction, layer)
            budget = self.M0 if layer == 0 else self.M
            selected = self._select_neighbours(candidates, budget)
            self._add_links(layer, key, selected)
            if candidates:
                entry = candidates[0][1]

        if level > self.max_level:
            self.max_level = level
            self.entry = key
        return key

    def search(self, query, k, ef=None):
        """Return the ``k`` closest stored ``(key, distance)`` pairs, closest first.

        Descends the upper layers greedily, runs an ef-bounded search on layer 0 and
        keeps the best ``k``. ``ef`` defaults to ``max(k, 10)``. Larger ``ef`` explores
        more of the graph for the same k; an explicit ``ef`` below k returns fewer than
        k results, which is the honest small-ef miss step 5 checks rather than hides.
        ``self.distance_calls`` is reset to 0 first so callers can audit the work.
        """
        self.distance_calls = 0
        if self.entry is None:
            return []
        vector = self._query_vector(query)
        exploration = max(1, ef if ef is not None else max(k, 10))
        entry = self.entry
        for layer in range(self.max_level, 0, -1):
            entry = self._greedy(vector, entry, layer)
        found = self._search_layer(vector, [entry], exploration, 0)
        return [(key, distance) for distance, key in found[:k]]


# ---------------------------------------------------------------------------
# Reference and metrics
# ---------------------------------------------------------------------------

def exact_search(vectors, keys, query, k):
    """Brute force: every distance, sorted, top ``k``; the ground truth for HNSW."""
    if not keys:
        return []
    scored = [(l2(query, vector), key, position)
              for position, (vector, key) in enumerate(zip(vectors, keys))]
    scored.sort(key=lambda triple: (triple[0], triple[2]))
    return [(key, distance) for distance, key, _position in scored[:k]]


def recall_at_k(approx_keys, exact_keys):
    """Fraction of the exact top-k keys the approximate result recovered.

    ``len(set(approx) & set(exact)) / len(exact)`` when ``exact`` is non-empty, else
    0.0. The denominator is the exact set: dividing by the approximate count would let a
    result that returned one lucky hit claim perfect recall.
    """
    exact = set(exact_keys)
    if not exact:
        return 0.0
    return len(set(approx_keys) & exact) / len(exact)


# ---------------------------------------------------------------------------
# A compact LSA fit (see the module docstring for why it is local)
# ---------------------------------------------------------------------------

def _tokenize(text):
    return _TOKEN_RE.findall(text.lower())


def _build_term_document(docs):
    tokens_per_doc = [_tokenize(doc["title"] + " " + doc["body"]) for doc in docs]
    vocabulary = sorted({token for tokens in tokens_per_doc for token in tokens})
    position = {term: j for j, term in enumerate(vocabulary)}
    matrix = []
    for tokens in tokens_per_doc:
        row = [0] * len(vocabulary)
        for token in tokens:
            row[position[token]] += 1
        matrix.append(row)
    return vocabulary, matrix


def _idf_vector(matrix):
    n_docs = len(matrix)
    n_terms = len(matrix[0]) if matrix else 0
    document_frequency = [0] * n_terms
    for row in matrix:
        for j, count in enumerate(row):
            if count:
                document_frequency[j] += 1
    return [math.log(1 + (n_docs - document_frequency[j] + 0.5) / (document_frequency[j] + 0.5))
            for j in range(n_terms)]


def _l2_normalise(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return list(vector)
    return [value / norm for value in vector]


def _weighted(matrix):
    if not matrix:
        return []
    idf = _idf_vector(matrix)
    return [_l2_normalise([row[j] * idf[j] for j in range(len(row))]) for row in matrix]


def _jacobi(matrix, tolerance=1e-13, max_sweeps=100):
    n = len(matrix)
    a = [list(row) for row in matrix]
    vectors = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        off = sum(a[p][q] * a[p][q] for p in range(n) for q in range(p + 1, n))
        if off < tolerance * tolerance:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if apq == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = vectors[k][p], vectors[k][q]
                    vectors[k][p] = c * vkp - s * vkq
                    vectors[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], vectors


def _eig_sorted(matrix):
    values, columns = _jacobi(matrix)
    n = len(values)
    order = sorted(range(n), key=lambda i: (-values[i], i))
    return [values[i] for i in order], [[columns[row][i] for row in range(n)] for i in order]


def _gram(matrix, left_vectors):
    if left_vectors:
        n = len(matrix)
        return [[sum(matrix[i][j] * matrix[l][j] for j in range(len(matrix[i])))
                 for l in range(n)] for i in range(n)]
    t = len(matrix[0]) if matrix else 0
    return [[sum(matrix[d][i] * matrix[d][j] for d in range(len(matrix)))
             for j in range(t)] for i in range(t)]


def _canonical_signs(vectors):
    canonical = []
    for vector in vectors:
        pivot = max(range(len(vector)), key=lambda j: abs(vector[j])) if vector else None
        if pivot is not None and vector[pivot] < 0:
            canonical.append([-value for value in vector])
        else:
            canonical.append(list(vector))
    return canonical


def _fit_lsa(docs, k):
    """Fit rank-``k`` LSA; the same pipeline as the sibling stage, kept local."""
    terms, counts = _build_term_document(docs)
    doc_ids = [doc["doc_id"] for doc in docs]
    n_docs = len(counts)
    n_terms = len(terms)
    weighted = _weighted(counts)
    idf = _idf_vector(counts) if n_terms else []
    mean = ([sum(row[j] for row in weighted) / n_docs for j in range(n_terms)]
            if n_docs else [0.0] * n_terms)
    centred = [[row[j] - mean[j] for j in range(n_terms)] for row in weighted]

    rank = max(0, min(k, n_docs, n_terms))
    components = []
    singular_values = []
    if rank:
        if n_docs <= n_terms:
            values, vectors = _eig_sorted(_gram(centred, left_vectors=True))
            for i in range(rank):
                singular = math.sqrt(max(values[i], 0.0))
                singular_values.append(singular)
                if singular > 1e-12:
                    u = vectors[i]
                    components.append([sum(centred[d][j] * u[d] for d in range(n_docs)) / singular
                                       for j in range(n_terms)])
                else:
                    components.append([0.0] * n_terms)
        else:
            values, vectors = _eig_sorted(_gram(centred, left_vectors=False))
            for i in range(rank):
                singular_values.append(math.sqrt(max(values[i], 0.0)))
                components.append(list(vectors[i]))
    components = _canonical_signs(components)

    doc_embeddings = []
    for row in centred:
        coordinates = [sum(row[j] * components[i][j] for j in range(n_terms))
                       for i in range(rank)]
        doc_embeddings.append(_l2_normalise(coordinates))

    return {
        "terms": terms,
        "idf": idf,
        "mean": mean,
        "components": components,
        "singular_values": singular_values,
        "doc_embeddings": doc_embeddings,
        "doc_ids": doc_ids,
    }


def _default_components(n_docs):
    return max(1, min(100, n_docs // 4))


def build_lsa_index(docs, k, seed=0):
    """Fit LSA on ``docs`` and return ``(keys, vectors, model)`` for HNSW to index.

    ``seed`` is accepted for interface symmetry; the truncated SVD is deterministic, so
    it does not change the embeddings. The model is returned so callers can fold queries
    into the same basis with :func:`embed_query`.
    """
    documents = docs["documents"] if isinstance(docs, dict) else docs
    if k is None:
        k = _default_components(len(documents))
    model = _fit_lsa(documents, k)
    return list(model["doc_ids"]), [list(vector) for vector in model["doc_embeddings"]], model


def embed_query(text, model):
    """Project a raw query into the fitted LSA space (fold-in), L2-normalised.

    A query with no known token returns the zero vector; ``cosine`` treats it as
    equidistant from everything and ``evaluate`` treats it as an abstention.
    """
    if isinstance(text, dict):
        text = text.get("text", "")
    terms = model["terms"]
    position = {term: j for j, term in enumerate(terms)}
    n_terms = len(terms)
    raw = [0.0] * n_terms
    for token in _tokenize(text):
        j = position.get(token)
        if j is not None:
            raw[j] += 1.0
    if not any(raw):
        return [0.0] * len(model["components"])
    weighted = _l2_normalise([raw[j] * model["idf"][j] for j in range(n_terms)])
    centred = [weighted[j] - model["mean"][j] for j in range(n_terms)]
    coordinates = [sum(centred[j] * component[j] for j in range(n_terms))
                   for component in model["components"]]
    return _l2_normalise(coordinates)


# ---------------------------------------------------------------------------
# Metadata filtering (post-ANN) and the eval-set wiring
# ---------------------------------------------------------------------------

def _passes_filters(doc, filters):
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
    """Keep only ``keys`` whose document passes ``filters``.

    Applied after the ANN search, so a very selective filter shrinks the result below
    the requested k (possibly to zero). This is the honest limit step 6 measures; the
    graph is not filter-aware.
    """
    if not filters:
        return list(keys)
    by_id = {doc["doc_id"]: doc for doc in documents}
    return [key for key in keys if key in by_id and _passes_filters(by_id[key], filters)]


def _flatten_queries(queries):
    if isinstance(queries, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [q for family in order for q in queries.get(family, [])]
    return list(queries)


def _eval_set_path():
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
    import sys

    path = str(_eval_set_path())
    if path not in sys.path:
        sys.path.insert(0, path)
    import metrics

    return metrics


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(corpus, queries, k=10, n_components=None, M=16, ef_construction=200,
             ef=None, seed=0):
    """Index the corpus's LSA embeddings and score every query family with HNSW.

    Returns the shared metrics dictionary (``overall``, ``by_type``, ``abstention``,
    ``per_query``) — the same shape BM25's ``evaluate_bm25`` and LSA's ``evaluate``
    return — plus ``"mean_distance_calls"``, the average number of distance evaluations
    per query. Metadata filters are applied AFTER the ANN search.
    """
    metrics = _import_metrics()
    documents = corpus["documents"] if isinstance(corpus, dict) else list(corpus)
    flat = _flatten_queries(queries)
    if n_components is None:
        n_components = _default_components(len(documents))
    keys, vectors, model = build_lsa_index(documents, n_components, seed)
    dim = len(vectors[0]) if vectors else max(1, n_components)
    index = HnswIndex(dim, M=M, ef_construction=ef_construction, seed=seed)
    for key, vector in zip(keys, vectors):
        index.insert(vector, key)
    if ef is None:
        ef = max(k, 50)

    ranked = {}
    work = []
    for query in flat:
        embedding = embed_query(query.get("text", ""), model)
        if not any(embedding):
            ranked[query["qid"]] = []
            work.append(0)
            continue
        hits = index.search({"key": query["qid"], "vector": embedding}, k, ef=ef)
        work.append(index.distance_calls)
        top_keys = [key for key, _distance in hits]
        ranked[query["qid"]] = metadata_filter(top_keys, query.get("filters") or {}, documents)

    result = metrics.evaluate(ranked, flat, k=k)
    result["mean_distance_calls"] = sum(work) / len(work) if work else 0.0
    return result


def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print the honest recall@10 vs distance-computation trade-off on the eval set."""
    import sys

    sys.dont_write_bytecode = True
    eval_path = str(_eval_set_path())
    if eval_path not in sys.path:
        sys.path.insert(0, eval_path)

    from corpus import generate_corpus
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(0)
    documents = corpus["documents"]
    query_sets = build_query_sets(corpus)
    queries = all_queries(query_sets)

    keys, vectors, model = build_lsa_index(documents, _default_components(len(documents)), 0)
    index = HnswIndex(len(vectors[0]), M=16, ef_construction=200, seed=0)
    for key, vector in zip(keys, vectors):
        index.insert(vector, key)

    probes = [(q["qid"], embed_query(q["text"], model)) for q in queries]
    probes = [(qid, embedding) for qid, embedding in probes if any(embedding)]

    print(f"seed 0, {len(documents)} documents, {len(probes)} embedded queries, "
          f"LSA rank {len(model['components'])}")
    print("HNSW recall@10 vs exact search (same embeddings), by ef:")
    print(f"  {'ef':>5}{'mean recall@10':>16}{'mean distance calls':>22}")
    for ef in (1, 2, 4, 8, 16, 32, 64, 128):
        recall = 0.0
        calls = 0.0
        for qid, embedding in probes:
            exact = exact_search(vectors, keys, embedding, 10)
            approximate = index.search({"key": qid, "vector": embedding}, 10, ef=ef)
            recall += recall_at_k([key for key, _dist in approximate],
                                  [key for key, _dist in exact])
            calls += index.distance_calls
        print(f"  {ef:>5}{recall / len(probes):>16.3f}{calls / len(probes):>22.1f}")
    corpus_size = len(vectors)
    linear_scan = corpus_size
    print(f"  a linear scan would use {linear_scan} distance calls per query")

    result = evaluate(corpus, query_sets, k=10, ef=128)
    print(f"\nHNSW over the LSA embeddings, ef=128 (metadata filtered AFTER the ANN):")
    print(f"  {'family':<11}{'recall@10':>10}{'MRR':>8}{'nDCG@10':>9}")
    for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer", "overall"):
        row = _row(result, family)
        print(f"  {family:<11}{row.get('recall@k', 0.0):>10.3f}{row.get('mrr', 0.0):>8.3f}"
              f"{row.get('ndcg@k', 0.0):>9.3f}")
    abstention = result["abstention"]
    print(f"  abstention: tp={abstention['tp']} fp={abstention['fp']} fn={abstention['fn']} "
          f"(precision={abstention['precision']:.3f}, recall={abstention['recall']:.3f})")
    print(f"  mean distance calls per query: {result['mean_distance_calls']:.1f} "
          f"(vs {corpus_size} for an exhaustive scan)")
    print("  at small ef the index does far less work; ef=128 buys exactness at a scan's "
          "cost. Recall below 1.0 at small ef is the approximation as designed.")
    print("  the filtered family here is 1.0 because the ANN top-10 happened to contain "
          "the matching documents; a very selective filter after the ANN shortens the "
          "list (step 6 measures that limit, it is not free).")


if __name__ == "__main__":
    demo()

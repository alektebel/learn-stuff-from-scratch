"""Knowledge graph + vector — RAG project 6 of the from-scratch track.

The shared evaluation set carries, beside the document text, a small company knowledge
graph: entities (people, departments, topics) and typed triples between them
(``PER-00 works_in DEP-00``, ``DEP-00 owns TOP-00``, ``PER-00 reports_to PER-01``). This
project turns that into a **triple store** with typed adjacency, links the query's words
to entity ids, walks the graph a bounded number of hops, and returns the documents the
walked-to entities are linked to. The graph's document candidates are then **merged with
the lexical first stage** (the sibling ``../bm25`` retriever) and the union is ranked —
"knowledge-graph + vector" here means graph expansion *and* lexical retrieval, never one
alone.

The pipeline's node and edge types:

  * entity nodes  — ``PER-*`` (person), ``DEP-*`` (department), ``TOP-*`` (topic); these
    are exactly ``corpus["entities"]``.
  * document nodes — ``DOC-*`` from ``corpus["documents"]``.
  * relation edges — the corpus's typed triples verbatim: ``works_in``, ``reports_to``
    and ``owns``.
  * document-link edges, derived here — every document is ``about`` each of its topics,
    ``owned_by`` its department and ``authored_by`` its author. These are what make the
    graph reach documents; without them a traversal would only ever reach entities.

DESIGN DECISION - the graph is a directed triple store, but traversal is undirected.
    A fact is stored directionally (``PER-00 reports_to PER-01`` says who reports to
    whom), which is what a triple means. Retrieval, however, wants "everything connected
    to this entity": the multi-hop question asks for the documents the *report* wrote,
    which is only reachable against the ``reports_to`` arrow. ``neighbours`` therefore
    returns the other endpoint of any incident edge (optionally filtered by predicate),
    so one traversal direction reaches both the manager and their reports. Cost: the
    direction of a predicate is lost to traversal, so a predicate whose direction
    carries the question's meaning would need a dedicated, directional query instead.

DESIGN DECISION - hop-bounded breadth-first search, not a full connected-component walk.
    The graph's whole component is a few hundred nodes; returning all of it for every
    query would be a corpus scan wearing a graph costume. A two-hop limit keeps the
    expansion local and makes the project's central claim measurable ("the graph adds
    nothing on non-multi-hop questions"). The hop bound is enforced by tracking the BFS
    depth; a walk that ignores it is a bug the checker constructs and catches. Cost: a
    genuinely long multi-hop question (three or four edges) is unreachable, and the
    limit has to be tuned per graph.

DESIGN DECISION - the lexical first stage is the sibling ``../bm25`` retriever, with a
    self-contained BM25 fallback when the sibling is absent.
    Reusing the exact stage the other projects reuse keeps the comparison honest; the
    fallback (k1=1.5, b=0.75, the same tokeniser) lets the graph-only path and the hand
    checks run in a tree that holds only ``knowledge-graph/`` and a test corpus, which is
    what the mutation harness needs. Cost: a little duplicated scoring code.

DESIGN DECISION - hybrid retrieval forms the union of the lexical and graph candidate
    sets, then ranks that union with reciprocal rank fusion.
    The contract the checker asserts is `hybrid ⊇ lexical ∪ graph`: the graph may only
    ever *add* candidates, never silently drop what the lexical stage found (nor the
    reverse). RRF is used because the two stages are rankers, not calibrated scores, and
    it is the same fusion rule the sibling ``../fusion`` project builds. Cost: RRF
    ignores how much better one rank is than the next, and a graph candidate the lexical
    stage ranked 40th can outrank the lexical stage's own 3rd if the graph ranked it
    first.

DESIGN DECISION - graph candidates are ordered by hop distance, then doc_id, and the
    fusion weight of the graph is 1.0.
    A document one edge from the named entity is more likely to be the answer than one
    two edges away, so the distance is the graph's only relevance signal; ties fall back
    to doc_id so every run is byte-identical. Cost: the graph has no scoring model of its
    own, so within one hop distance it cannot say which document is better.

Run the demo with ``python3 solutions/graph.py``. It prints the honest lexical / graph /
hybrid numbers per query family and the two limit cases: a non-multi-hop query whose
graph expansion adds nothing (or only noise), and a multi-hop question whose connecting
edge is absent, where graph-only correctly returns ``[]``.
"""
from __future__ import annotations

import math
import os
import pathlib
import re
import sys
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")

#: A name matches only on whole words: the lookarounds reject a match that continues with
#: (or is preceded by) another alphanumeric character, so "engineers" never links
#: "Engineering".
_BOUNDARY = r"(?<![a-z0-9]){}(?![a-z0-9])"

_FAMILY_ORDER = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
_FILTER_KEYS = ("region", "year", "department", "access_level")

HOP_LIMIT = 2       # graph edges a query may traverse from its linked entities
RRF_K = 60          # reciprocal-rank-fusion constant
GRAPH_WEIGHT = 1.0  # weight of the graph stage in the fusion
RESULT_DEPTH = 5    # documents returned by the ranked stages
K1, B = 1.5, 0.75   # constants of the fallback Okapi BM25


def tokenize(text):
    """Lower-cased alphanumeric tokens, in order, punctuation dropped.

    Identical to the sibling stages' tokeniser so the graph is measured over documents
    made of exactly the same tokens as BM25 and LSA.
    """
    return TOKEN_RE.findall(str(text).lower())


# ---------------------------------------------------------------------------
# the triple store
# ---------------------------------------------------------------------------

class TripleStore:
    """A small in-memory triple store with typed adjacency.

    Triples are ``(subject, predicate, object)`` strings and duplicates are ignored.
    ``entities`` (a list of ``{"id", "name", "type"}`` dicts) is carried alongside so the
    query linker knows which names to resolve; a hand-built store may leave it empty.

    Ordering is deterministic everywhere: ``match`` returns the matching triples sorted
    and ``neighbours`` returns the adjacent nodes sorted, so two runs over the same
    triples produce byte-identical output with no seed and no hash iteration.
    """

    def __init__(self, triples=None, entities=None):
        self.entities = [dict(entity) for entity in entities] if entities else []
        self._triples = []
        self._seen = set()
        for triple in triples or []:
            self.add(*triple)

    def add(self, subject, predicate, object):
        """Add the triple unless it is already present; return ``self``."""
        # TODO: Stringify the three components, add the tuple to the seen set and append it to the triple list only when it is new; return self.
        raise NotImplementedError("TripleStore.add")

    def match(self, subject=None, predicate=None, object=None):
        """Return every stored triple matching the given components, sorted.

        A component left as ``None`` is a wildcard, so ``match(subject="PER-00")``
        returns all triples whose subject is ``PER-00`` and ``match()`` returns all of
        them. The result is a sorted list of tuples.
        """
        # TODO: Scan the triples and keep those whose every non-None component equals the argument; return the matches sorted as a list of tuples.
        raise NotImplementedError("TripleStore.match")

    def neighbours(self, node, predicate=None):
        """The nodes joined to ``node`` by an edge, optionally of one predicate.

        The adjacency is undirected: for an edge ``(node, p, other)`` and for an edge
        ``(other, p, node)`` alike, ``other`` is a neighbour. Passing ``predicate``
        restricts the walk to that predicate type (typed adjacency). The result is a
        sorted list of distinct node ids.
        """
        # TODO: Scan the triples (respecting an optional predicate) and collect the other endpoint when the node is the subject or the object; return the distinct nodes sorted.
        raise NotImplementedError("TripleStore.neighbours")


# ---------------------------------------------------------------------------
# loading the shared evaluation set
# ---------------------------------------------------------------------------

def _eval_set_solutions():
    """Locate the shared eval set's runnable fixture (its ``solutions/`` dir)."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = []
    env = os.environ.get("RAG_EVAL_SET")
    if env:
        candidates.append(pathlib.Path(env) / "solutions")
        candidates.append(pathlib.Path(env))
    candidates += [
        here.parent / "eval-set" / "solutions",          # .../solutions/
        here.parent.parent / "eval-set" / "solutions",   # .../<module>/
    ]
    for path in candidates:
        if path is not None and (path / "metrics.py").is_file():
            return path
    raise FileNotFoundError(
        "cannot find the shared eval set at ../eval-set/solutions relative to "
        f"{here}: run from inside rag-from-scratch/ or set RAG_EVAL_SET.")


def _load_corpus(seed=0):
    """Load ``corpus.generate_corpus(seed)`` from the shared eval set."""
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import corpus

    return corpus.generate_corpus(seed)


def _import_metrics():
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import metrics

    return metrics


def load_graph(corpus=None):
    """Build the knowledge graph from an eval-set corpus (``seed 0`` when omitted).

    Returns a dict with:

      * ``entities``   — the corpus entities, copied (person / department / topic).
      * ``relations``  — the corpus's typed triples, as ``(subject, predicate, object)``.
      * ``documents``  — the corpus documents, each augmented with ``entity_ids``: the
        sorted ids of the entities it is linked to (its topics, its department, its
        author).
      * ``doc_links``  — the derived document edges, as ``(doc_id, predicate, entity)``
        with predicates ``about``, ``owned_by`` and ``authored_by``.
      * ``store``      — a :class:`TripleStore` holding the relations *and* the derived
        document links, with ``store.entities`` set to the entity list.

    Every edge is a documented type: ``works_in`` / ``reports_to`` / ``owns`` are the
    corpus's relations, ``about`` / ``owned_by`` / ``authored_by`` are derived here. The
    document links are what let a bounded traversal reach documents, so they are stored
    in the same store as the entity facts.
    """
    # TODO: Copy corpus['entities'] and build a name->id map (lower-cased names); add every corpus relation to a new TripleStore(entities=entities) and collect it in `relations`. For each document, resolve its topics / department / author to entity ids, record them as `entity_ids`, and add the derived (doc_id, 'about'|'owned_by'|'authored_by', entity_id) triples to the store and to `doc_links`. Return the entities, relations, documents, doc_links and store.
    raise NotImplementedError("load_graph")


# ---------------------------------------------------------------------------
# entity linking and traversal
# ---------------------------------------------------------------------------

def link_entities(query, entities):
    """Resolve the entity ids named by ``query`` (case-insensitive, whole words).

    ``query`` may be the eval set's query dict or a raw string. An entity links when its
    name occurs in the query as a whole word (word-boundary on both sides), so
    "access control" links ``TOP-*`` and a query containing "engineers" does *not* link
    the "Engineering" department. The matching ids are returned sorted, deduplicated, and
    an empty list is the honest answer when the query names no known entity.
    """
    # TODO: Lower-case the query text; for each entity whose name is non-empty test `re.search(_BOUNDARY.format(re.escape(name)), text)` and collect the id. Return the deduplicated ids sorted; nothing matched is [].
    raise NotImplementedError("link_entities")


def _hop_distances(start_ids, hops, store):
    """Scaffolding: BFS distances from the starts, at most ``hops`` edges away.

    Returns a dict node -> edge distance (the start nodes sit at 0). The walk stops at
    ``hops`` by construction; :func:`multi_hop` and :func:`graph_retrieve` both build on
    it so the hop limit has exactly one definition.
    """
    starts = set(start_ids)
    distance = {node: 0 for node in starts}
    frontier = set(starts)
    for depth in range(1, max(0, int(hops)) + 1):
        nxt = set()
        for node in sorted(frontier):
            nxt.update(store.neighbours(node))
        nxt = {node for node in nxt if node not in distance}
        if not nxt:
            break
        for node in nxt:
            distance[node] = depth
        frontier = nxt
    return distance


def multi_hop(start_ids, hops, store):
    """The nodes reachable from ``start_ids`` in 1..``hops`` edges, sorted.

    The starts themselves are excluded (a node reached back along a cycle is still a
    start, so it stays out). The hop limit is the contract: a node three edges away is
    absent from a two-hop result even though it is in the same connected component, and
    nothing beyond ``hops`` edges is ever returned.
    """
    # TODO: Call `_hop_distances(start_ids, hops, store)` and return the sorted node ids it assigned a distance to, excluding the start ids themselves.
    raise NotImplementedError("multi_hop")


def documents_for_entities(entity_ids, documents):
    """The documents directly linked to any of ``entity_ids``, sorted by doc_id.

    A document is linked to an entity when the entity's id is in the document's derived
    ``entity_ids`` (an ``about`` / ``owned_by`` / ``authored_by`` edge). An id that links
    to no document — and an empty ``entity_ids`` — returns ``[]`` rather than every
    document, which is the abstention the checker pins.
    """
    # TODO: Keep the doc_id of every document whose `entity_ids` intersects the wanted set; return them sorted. No intersection (and an empty input) is [].
    raise NotImplementedError("documents_for_entities")


# ---------------------------------------------------------------------------
# the two stages and the hybrid
# ---------------------------------------------------------------------------

_BM25_CACHE = [None, False]


def _try_import_bm25():
    """Import the sibling ``../bm25`` solution, or return None when it is absent."""
    if _BM25_CACHE[1] is not False:
        return _BM25_CACHE[0]
    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here.parent / "bm25" / "solutions",
                      here.parent.parent / "bm25" / "solutions"):
        if (candidate / "bm25.py").is_file():
            path = str(candidate)
            if path not in sys.path:
                sys.path.insert(0, path)
            import importlib

            _BM25_CACHE[0] = importlib.import_module("bm25")
            break
    _BM25_CACHE[1] = True
    return _BM25_CACHE[0]


def _passes_filters(document, filters):
    """The metadata predicate the fallback retriever applies before scoring."""
    for key in _FILTER_KEYS:
        if key not in (filters or {}):
            continue
        value = filters[key]
        if key == "year":
            if str(document.get("date", ""))[:4] != str(value):
                return False
        elif document.get(key) != value:
            return False
    return True


def _local_retrieve(query, k, documents):
    """Scaffolding: a self-contained Okapi BM25 ranker (the sibling's stand-in)."""
    if isinstance(query, dict):
        text = query.get("text", "")
        filters = query.get("filters") or {}
    else:
        text, filters = str(query), {}
    terms = tokenize(text)
    if not terms:
        return []
    n_docs = len(documents)
    term_counts = []
    document_frequency = Counter()
    for document in documents:
        counts = Counter(tokenize(
            str(document.get("title", "")) + " " + str(document.get("body", ""))))
        term_counts.append(counts)
        for term in set(counts):
            document_frequency[term] += 1
    average = (sum(sum(counts.values()) for counts in term_counts) / n_docs
               if n_docs else 1.0) or 1.0
    scored = []
    for document, counts in zip(documents, term_counts):
        if not _passes_filters(document, filters):
            continue
        length = sum(counts.values()) or 1
        score = 0.0
        for term in terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            idf = math.log(
                1.0 + (n_docs - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5))
            score += idf * (frequency * (K1 + 1.0)) / (
                frequency + K1 * (1.0 - B + B * length / average))
        if score > 0.0:
            scored.append((score, document["doc_id"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [doc_id for _score, doc_id in scored[:max(0, k)]]


def lexical_retrieve(query, k, documents):
    """The lexical first stage: up to ``k`` doc_ids best-first, ``[]`` to abstain.

    Uses the sibling ``../bm25`` retriever (metadata filters and the empty-result
    abstention included), matching every other stage in the project; if the sibling is
    not present in this tree it falls back to a self-contained BM25 over the same tokens.
    """
    # TODO: Import the sibling `../bm25` (`_try_import_bm25`); if present, build a BM25Retriever over `documents` and return `retriever.retrieve(query, k=k)`, otherwise return `_local_retrieve(query, k, documents)`.
    raise NotImplementedError("lexical_retrieve")


def graph_retrieve(query, k, store, documents):
    """The graph stage: the documents within :data:`HOP_LIMIT` edges of the query.

    The query's entity names are linked first; a query that names no entity returns
    ``[]`` (the graph has nothing to expand from, and inventing the whole graph would
    turn a no-answer query into a full corpus scan). Otherwise the graph candidates are
    the document nodes inside the hop limit, plus the documents directly linked to an
    entity that is itself within ``HOP_LIMIT - 1`` edges (so the document is within the
    limit too). Candidates are ordered by hop distance, then doc_id. Deterministic.
    """
    # TODO: Link the query's entity names with `link_entities(query, store.entities)`; return [] when none link. Otherwise take `_hop_distances(entity_ids, HOP_LIMIT, store)`, keep document nodes inside the limit, and union in `documents_for_entities` over the entity_ids plus the non-document nodes within HOP_LIMIT-1. Sort by (distance, doc_id) and slice to k.
    raise NotImplementedError("graph_retrieve")


def hybrid_retrieve(query, k, store, documents):
    """Fuse the lexical and graph stages over their **union**, then rank.

    Both stages are asked for the full candidate pool (``len(documents)`` deep), so the
    pool is exactly ``set(lexical) | set(graph)`` *before* any ranking — the graph can
    add candidates but can never remove a lexical one, and vice versa. The union is then
    ranked by reciprocal rank fusion, ``score(d) = sum(1/(RRF_K + rank))`` over the
    stages that returned ``d``, with the graph weighted by :data:`GRAPH_WEIGHT`; ties
    break by doc_id. An empty pool (both stages abstained) returns ``[]``.
    """
    # TODO: Ask both stages for the full pool (depth=len(documents)); build `fused` by adding 1/(RRF_K+rank) for each lexical result and GRAPH_WEIGHT/(RRF_K+rank) for each graph result (so the keys are exactly the union), sort by (-score, doc_id) and return the top k.
    raise NotImplementedError("hybrid_retrieve")


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

def _flatten_queries(queries):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(queries, dict):
        return [query for family in _FAMILY_ORDER for query in queries.get(family, [])]
    return list(queries)


def evaluate(corpus, query_sets, k=RESULT_DEPTH, graph_data=None):
    """Score the lexical-only, graph-only and hybrid systems on the shared eval set.

    ``corpus`` is ``corpus.generate_corpus(seed)`` (or a document list) and ``query_sets``
    is ``queries.build_query_sets(corpus)`` or a flat query list. Returns a dict with the
    shared metrics (``overall``, ``by_type``, ``per_query``, ``abstention``) under
    ``lexical`` / ``graph`` / ``hybrid``, the ``ranked`` predictions, the ``k``, and the
    built ``graph_data``. Every stage is deterministic, so repeated calls are equal.
    """
    # TODO: Flatten the queries, build the graph once, run lexical_retrieve, graph_retrieve and hybrid_retrieve per query, and return the shared `metrics.evaluate` result under 'lexical', 'graph' and 'hybrid' alongside the predictions, k and graph data.
    raise NotImplementedError("evaluate")


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print the honest per-family numbers and the graph-adds-nothing limit case."""
    sys.dont_write_bytecode = True
    eval_set = _eval_set_solutions()
    if str(eval_set) not in sys.path:
        sys.path.insert(0, str(eval_set))
    from corpus import generate_corpus
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(0)
    query_sets = build_query_sets(corpus)
    queries = all_queries(query_sets)
    graph_data = load_graph(corpus)
    documents = graph_data["documents"]
    store = graph_data["store"]

    print(f"seed 0, {len(documents)} documents, {len(queries)} queries; "
          f"{len(graph_data['entities'])} entities, {len(graph_data['relations'])} "
          f"relations, {len(graph_data['doc_links'])} derived document links")
    print(f"graph: triple store, {HOP_LIMIT} hops, fusion RRF(k={RRF_K}) "
          f"with graph weight {GRAPH_WEIGHT}")

    result = evaluate(corpus, query_sets, k=RESULT_DEPTH, graph_data=graph_data)

    header = (f"{'family':<11}{'lex r@5':>9}{'grph r@5':>10}{'hyb r@5':>9}"
              f"{'lex MRR':>9}{'grph MRR':>10}{'hyb MRR':>9}"
              f"{'lex nDCG':>10}{'grph nDCG':>11}{'hyb nDCG':>10}")
    print("\n" + header)
    for family in _FAMILY_ORDER + ("overall",):
        lex = _row(result["lexical"], family)
        grph = _row(result["graph"], family)
        hyb = _row(result["hybrid"], family)
        print(f"{family:<11}{lex.get('recall@k', 0.0):>9.3f}"
              f"{grph.get('recall@k', 0.0):>10.3f}{hyb.get('recall@k', 0.0):>9.3f}"
              f"{lex.get('mrr', 0.0):>9.3f}{grph.get('mrr', 0.0):>10.3f}"
              f"{hyb.get('mrr', 0.0):>9.3f}"
              f"{lex.get('ndcg@k', 0.0):>10.3f}{grph.get('ndcg@k', 0.0):>11.3f}"
              f"{hyb.get('ndcg@k', 0.0):>10.3f}")
    print("multi_hop is called out above: it is the one family the graph is supposed to "
          "help.")
    print("reported as measured: the graph is not assumed to win; on lexical and "
          "semantic it often adds nothing or only noise.")

    print("\nabstention (a prediction is empty):")
    for name in ("lexical", "graph", "hybrid"):
        abstention = result[name]["abstention"]
        print(f"  {name:<8} tp={abstention['tp']} fp={abstention['fp']} "
              f"fn={abstention['fn']} precision={abstention['precision']:.3f} "
              f"recall={abstention['recall']:.3f}")

    print("\nlimit case 1 — a query whose words name no entity expands to nothing:")
    lexical_queries = [query for query in queries if query["type"] == "lexical"]
    if lexical_queries:
        query = lexical_queries[0]
        graph_docs = graph_retrieve(query, len(documents), store, documents)
        relevant = set(query["relevance"])
        added = len(graph_docs)
        print(f"  {query['qid']}: graph-only candidates {added}, relevant "
              f"{len(set(graph_docs) & relevant)} (the policy code is not an entity)")
        print(f"  hybrid still answers it from the lexical stage: "
              f"recall@5={result['hybrid']['per_query'][query['qid']]['recall@k']:.3f}")

    print("\nlimit case 2 — a graph expansion that adds noise:")
    noise_query = {"text": "Engineering", "filters": {}, "relevance": {}}
    noise_docs = graph_retrieve(noise_query, len(documents), store, documents)
    print(f"  query {noise_query['text']!r} reaches {len(noise_docs)} documents by "
          f"following any edge; only the ones about the department's topics answer it, "
          "the rest is noise the lexical stage never asked for")

    print("\nlimit case 3 — a multi-hop question whose connecting edge is absent:")
    broken = {
        "entities": [
            {"id": "PER-00", "name": "A. Rivera", "type": "person"},
            {"id": "PER-01", "name": "B. Okafor", "type": "person"},
        ],
        "relations": [],  # the reports_to edge that joins them is missing
        "documents": [{
            "doc_id": "DOC-0000", "title": "beta report", "body": "beta beta",
            "department": "", "author": "B. Okafor", "topics": [],
        }],
    }
    broken_graph = load_graph(broken)
    question = {"text": "Which documents did A. Rivera own, and what did the person "
                        "reporting to them write about?"}
    answerable = documents_for_entities(["PER-01"], broken_graph["documents"])
    reached = graph_retrieve(question, len(broken_graph["documents"]),
                             broken_graph["store"], broken_graph["documents"])
    print(f"  the question is answerable from the corpus ({answerable}) but the graph "
          f"returns {reached}: without the reports_to edge the report is unreachable")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    demo()

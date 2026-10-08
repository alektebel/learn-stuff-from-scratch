"""
Progress checker for the RAG project-6 knowledge-graph + vector templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports this module's own solutions/; it
tests YOUR template. The shared eval set lives in ``../eval-set`` and is imported from
its ``solutions/`` exactly the way the sibling stages reach it. Steps 1-3 and 5-6 run on
hand-built corpora (``load_graph`` accepts a corpus dict) and never touch the eval set,
so the mutation harness can run them in a bare temporary directory; step 4 is the only
end-to-end check, and its first half is also self-contained.

The checks are deliberately adversarial:

* step 1 demands the loaded counts equal the corpus entities/relations, exercises
  ``match``/``neighbours`` on a hand-built store, and requires the typed adjacency;
* step 2 pins whole-word entity linking ("engineers" must not link "Engineering") and
  that ``documents_for_entities`` returns the linked subset, never the whole corpus;
* step 3 builds a chain whose third hop is a distinct node, so an implementation that
  ignores the hop limit and returns the whole connected component fails;
* step 4 asserts, per query, that the hybrid candidate set is a superset of the union of
  the two stages' sets — then reports lexical / graph / hybrid numbers honestly, with the
  multi-hop family called out and no claim that the graph wins;
* step 5 constructs the graph-adds-nothing limit case (a lexical query the graph cannot
  help), a graph expansion that adds noise, and a multi-hop question whose connecting
  edge is absent, where graph-only correctly returns [];
* step 6 pins abstention: a query naming no entity and a no-answer query stay [] through
  the hybrid.
"""
import os
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, Dict, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

MAX_STEP = 6
FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")


def _find_eval_set():
    """Locate the shared evaluation set (the dir or its solutions/) as a pathlib.Path."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = []
    env = os.environ.get("RAG_EVAL_SET")
    if env:
        candidates.append(pathlib.Path(env))
    candidates += [
        here.parent / "eval-set",
        here / "eval-set",
        here.parent.parent / "eval-set",
    ]
    for base in candidates:
        for cand in (base / "solutions", base):
            if (cand / "metrics.py").is_file() and (cand / "corpus.py").is_file():
                return cand
    raise FileNotFoundError(
        "cannot find the shared eval set. Expected it at ../eval-set (or "
        "../eval-set/solutions) relative to check.py, or set RAG_EVAL_SET. "
        f"Looked from {here}.")


def _load_eval_set():
    """Import the eval set's modules, adding its directory to sys.path once."""
    path = str(_find_eval_set())
    if path not in sys.path:
        sys.path.insert(0, path)
    import baseline
    import corpus
    import metrics
    import queries

    return corpus, queries, metrics, baseline


# ---------------------------------------------------------------------------
# Hand-built corpora (steps 1-3 and 5-6 need no eval set)
# ---------------------------------------------------------------------------

def _toy_corpus():
    """A six-entity, three-document corpus that exercises every node and edge type."""
    entities = [
        {"id": "PER-00", "name": "A. Rivera", "type": "person"},
        {"id": "PER-01", "name": "B. Okafor", "type": "person"},
        {"id": "DEP-00", "name": "Engineering", "type": "department"},
        {"id": "DEP-01", "name": "Finance", "type": "department"},
        {"id": "TOP-00", "name": "access control", "type": "topic"},
        {"id": "TOP-01", "name": "data retention", "type": "topic"},
    ]
    relations = [
        ["PER-00", "works_in", "DEP-00"],
        ["PER-01", "works_in", "DEP-01"],
        ["PER-00", "reports_to", "PER-01"],
        ["DEP-00", "owns", "TOP-00"],
        ["DEP-01", "owns", "TOP-01"],
    ]
    documents = [
        {"doc_id": "DOC-0000", "title": "alpha report", "body": "alpha alpha",
         "department": "Engineering", "author": "A. Rivera",
         "topics": ["access control"], "region": "EMEA", "date": "2025-01-01",
         "access_level": "public"},
        {"doc_id": "DOC-0001", "title": "beta report", "body": "beta beta",
         "department": "Finance", "author": "B. Okafor",
         "topics": ["data retention"], "region": "AMER", "date": "2025-02-01",
         "access_level": "internal"},
        {"doc_id": "DOC-0002", "title": "gamma report", "body": "gamma gamma",
         "department": "Engineering", "author": "A. Rivera",
         "topics": [], "region": "EMEA", "date": "2025-03-01",
         "access_level": "public"},
    ]
    return {"entities": entities, "relations": relations, "documents": documents,
            "tables": {}}


def _broken_corpus():
    """Two people with no edge between them and only the report has a document."""
    return {
        "entities": [
            {"id": "PER-00", "name": "A. Rivera", "type": "person"},
            {"id": "PER-01", "name": "B. Okafor", "type": "person"},
        ],
        "relations": [],
        "documents": [
            {"doc_id": "DOC-0000", "title": "beta report", "body": "beta beta",
             "department": "", "author": "B. Okafor", "topics": []},
        ],
        "tables": {},
    }


# ---------------------------------------------------------------------------
# Step 1: the triple store and the loaded counts
# ---------------------------------------------------------------------------

def check_triple_store() -> None:
    import graph

    toy = _toy_corpus()
    built = graph.load_graph(toy)

    assert len(built["entities"]) == len(toy["entities"]), (
        f"load_graph returned {len(built['entities'])} entities for a corpus with "
        f"{len(toy['entities'])}")
    assert [tuple(r) for r in built["relations"]] == [tuple(r) for r in toy["relations"]], (
        "the loaded relations must be the corpus's typed triples, in order; got "
        f"{built['relations']}")
    assert any(predicate == "reports_to"
               for _s, predicate, _o in built["relations"]), (
        "every predicate type must be loaded, including reports_to")

    stored = built["store"].match()
    assert len(stored) == len(built["relations"]) + len(built["doc_links"]), (
        f"the store holds {len(stored)} triples but {len(built['relations'])} relations "
        f"+ {len(built['doc_links'])} document links were built")
    for relation in built["relations"]:
        assert relation in set(stored), f"the relation {relation} is missing from the store"
    assert {p for _s, p, _o in built["doc_links"]} == {
        "about", "owned_by", "authored_by"}, (
        "the derived document links must use the about / owned_by / authored_by "
        f"predicates; got {sorted({p for _s, p, _o in built['doc_links']})}")
    assert built["store"].entities == built["entities"], (
        "the store must carry the entity list so the linker can resolve names")

    # A hand-built store: match is exact on each component and neighbours is typed.
    store = graph.TripleStore()
    store.add("a", "p", "b")
    store.add("a", "p", "c")
    store.add("d", "q", "b")
    store.add("a", "p", "b")  # duplicate, ignored
    assert set(store.match(subject="a")) == {("a", "p", "b"), ("a", "p", "c")}, (
        f"match(subject='a') returned {store.match(subject='a')}")
    assert set(store.match(object="b")) == {("a", "p", "b"), ("d", "q", "b")}, (
        f"match(object='b') returned {store.match(object='b')}")
    assert set(store.match(predicate="p")) == {("a", "p", "b"), ("a", "p", "c")}, (
        f"match(predicate='p') returned {store.match(predicate='p')}")
    assert set(store.match("a", "p", "b")) == {("a", "p", "b")}
    assert len(store.match()) == 3, "a duplicate triple must not be stored twice"

    assert store.neighbours("a") == ["b", "c"], (
        f"neighbours('a') must be the undirected, sorted adjacency ['b', 'c'], got "
        f"{store.neighbours('a')}")
    assert store.neighbours("a", "p") == ["b", "c"], (
        f"neighbours('a', 'p') returned {store.neighbours('a', 'p')}")
    assert store.neighbours("a", "q") == [], (
        "neighbours filtered by a predicate the node does not use must be empty")
    assert store.neighbours("b") == ["a", "d"], (
        f"neighbours('b') must reach both endpoints (undirected), got "
        f"{store.neighbours('b')}")

    try:
        corpus_mod, _queries, _metrics, _baseline = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the toy "
              "corpus only")
        return
    corpus = corpus_mod.generate_corpus(0)
    real = graph.load_graph(corpus)
    assert len(real["entities"]) == len(corpus["entities"]), (
        f"seed-0 entities: loaded {len(real['entities'])}, corpus "
        f"{len(corpus['entities'])}")
    assert set(map(tuple, real["relations"])) == set(map(tuple, corpus["relations"])), (
        "the seed-0 relations must match the corpus exactly (a dropped predicate type "
        "changes this count)")
    assert len(real["store"].match()) == len(real["relations"]) + len(real["doc_links"])
    print(f"      seed 0: {len(real['entities'])} entities, {len(real['relations'])} "
          f"relations, {len(real['doc_links'])} derived document links")


# ---------------------------------------------------------------------------
# Step 2: whole-word entity linking and the linked-document subset
# ---------------------------------------------------------------------------

def check_entity_linking() -> None:
    import graph

    built = graph.load_graph(_toy_corpus())
    entities = built["entities"]
    documents = built["documents"]

    assert graph.link_entities("Who wrote the A. Rivera report?", entities) == ["PER-00"], (
        "the author's name must link to their person id")
    assert graph.link_entities("What is the Engineering policy?", entities) == ["DEP-00"], (
        "a department name must link to its department id")
    assert graph.link_entities("access control for everyone", entities) == ["TOP-00"], (
        "a topic name must link to its topic id")
    assert graph.link_entities("A. Rivera works in Engineering", entities) == [
        "DEP-00", "PER-00"], "multiple named entities link together, sorted"
    assert graph.link_entities("a. rivera", entities) == ["PER-00"], (
        "linking must be case-insensitive")

    # Whole-word: "engineers" is not "Engineering".
    assert graph.link_entities("The engineers gathered in the lobby.",
                               entities) == [], (
        "a query containing 'engineers' must NOT link the 'Engineering' department by "
        "substring; entity names match on whole words only")
    assert graph.link_entities("nothing here maps to an entity", entities) == [], (
        "a query naming no known entity must return []")

    assert graph.documents_for_entities(["TOP-00"], documents) == ["DOC-0000"]
    assert graph.documents_for_entities(["PER-01"], documents) == ["DOC-0001"]
    assert graph.documents_for_entities(["DEP-00"], documents) == [
        "DOC-0000", "DOC-0002"], "Engineering owns two documents in the toy corpus"
    assert graph.documents_for_entities(["PER-99"], documents) == [], (
        "an unknown entity id links to no document")
    assert graph.documents_for_entities([], documents) == [], (
        "no entities must return no documents, not the whole corpus")


# ---------------------------------------------------------------------------
# Step 3: the hop limit is respected
# ---------------------------------------------------------------------------

def check_multi_hop() -> None:
    import graph

    store = graph.TripleStore()
    for triple in (("a", "p", "b"), ("b", "p", "c"), ("c", "p", "d"), ("a", "q", "e")):
        store.add(*triple)

    assert graph.multi_hop(["a"], 0, store) == [], "zero hops reaches nothing"
    assert graph.multi_hop(["a"], 1, store) == ["b", "e"], (
        f"one hop from a must be ['b', 'e'], got {graph.multi_hop(['a'], 1, store)}")
    assert graph.multi_hop(["a"], 2, store) == ["b", "c", "e"], (
        f"two hops from a must be ['b', 'c', 'e'], got "
        f"{graph.multi_hop(['a'], 2, store)}")
    assert graph.multi_hop(["a"], 3, store) == ["b", "c", "d", "e"], (
        f"three hops from a must be ['b', 'c', 'd', 'e'], got "
        f"{graph.multi_hop(['a'], 3, store)}")
    assert "d" not in graph.multi_hop(["a"], 2, store), (
        "d is three edges away, so a two-hop walk must not reach it: the hop limit is "
        "the contract, not a hint")
    assert set(graph.multi_hop(["a"], 3, store)) > set(graph.multi_hop(["a"], 2, store)), (
        "the construction must make the connected component strictly larger than the "
        "two-hop set, otherwise an implementation that ignores the limit is not caught")
    assert graph.multi_hop(["b"], 1, store) == ["a", "c"], (
        f"one hop from b must be ['a', 'c'], got {graph.multi_hop(['b'], 1, store)}")
    assert graph.multi_hop(["a"], 3, store) == graph.multi_hop(["a"], 3, store), (
        "multi_hop must be deterministic")


# ---------------------------------------------------------------------------
# Step 4: end to end on the shared eval set; the hybrid is a union
# ---------------------------------------------------------------------------

def _candidate_union(module, store, documents, query, depth):
    """Return (lexical, graph, hybrid) candidate sets at full depth for one query."""
    lexical = set(module.lexical_retrieve(query, depth, documents))
    graph_set = set(module.graph_retrieve(query, depth, store, documents))
    hybrid = set(module.hybrid_retrieve(query, depth, store, documents))
    return lexical, graph_set, hybrid


def check_eval_set_end_to_end() -> None:
    import graph

    # (a) The union contract, on a self-contained corpus, before touching the eval set.
    built = graph.load_graph(_toy_corpus())
    store, documents = built["store"], built["documents"]
    depth = len(documents)

    lexical_query = {"qid": "T-LEX", "text": "alpha", "filters": {},
                     "relevance": {"DOC-0000": 2.0}}
    lexical, graph_set, hybrid = _candidate_union(
        graph, store, documents, lexical_query, depth)
    assert lexical, "the lexical stage must find the 'alpha' document"
    assert graph_set == set(), "'alpha' names no entity; the graph must add nothing"
    assert hybrid >= lexical | graph_set, (
        "the hybrid candidate set must contain the union of the lexical and graph "
        f"sets; lexical={sorted(lexical)}, graph={sorted(graph_set)}, "
        f"hybrid={sorted(hybrid)}. The graph may only add candidates, never drop the "
        "lexical stage's.")

    entity_query = {"qid": "T-ENT", "text": "A. Rivera", "filters": {},
                    "relevance": {"DOC-0000": 2.0, "DOC-0002": 2.0}}
    lexical2, graph2, hybrid2 = _candidate_union(
        graph, store, documents, entity_query, depth)
    assert {"DOC-0000", "DOC-0002"} <= graph2, (
        f"A. Rivera authored DOC-0000 and DOC-0002; graph-only got {sorted(graph2)}")
    assert hybrid2 >= lexical2 | graph2

    # (b) The shared evaluation set.
    try:
        corpus_mod, queries_mod, metrics, _baseline = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the union "
              "contract on the toy corpus only")
        return

    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)
    built = graph.load_graph(corpus)
    store, documents = built["store"], built["documents"]
    depth = len(documents)
    known = {document["doc_id"] for document in documents}

    for query in queries:
        lexical, graph_set, hybrid = _candidate_union(
            graph, store, documents, query, depth)
        assert hybrid >= lexical | graph_set, (
            f"{query['qid']}: the hybrid must contain the union of the lexical and graph "
            f"candidates (|lex|={len(lexical)}, |graph|={len(graph_set)}, "
            f"|hybrid|={len(hybrid)})")
        assert hybrid <= known and lexical <= known and graph_set <= known, (
            f"{query['qid']}: a stage returned a doc_id outside the corpus")

    result = graph.evaluate(corpus, query_sets, k=5)

    # evaluate(...) must agree with an independent recomputation on the shared metrics.
    recomputed = {
        "lexical": {q["qid"]: graph.lexical_retrieve(q, 5, documents)
                    for q in queries},
        "graph": {q["qid"]: graph.graph_retrieve(q, 5, store, documents)
                  for q in queries},
        "hybrid": {q["qid"]: graph.hybrid_retrieve(q, 5, store, documents)
                   for q in queries},
    }
    for family in ("lexical", "graph", "hybrid"):
        expected = metrics.evaluate(recomputed[family], queries, k=5)
        for metric in ("recall@k", "mrr", "ndcg@k"):
            assert abs(result[family]["overall"][metric]
                       - expected["overall"][metric]) < 1e-12, (
                f"evaluate's {family} {metric} disagrees with a recomputation over the "
                "shared metrics")

    print(f"      seed 0, {len(documents)} documents, {len(built['entities'])} entities, "
          f"{len(built['relations'])} relations, {len(built['doc_links'])} document "
          f"links; k=5")
    header = (f"      {'family':<11}{'lex r@5':>9}{'grph r@5':>10}{'hyb r@5':>9}"
              f"{'lex MRR':>9}{'grph MRR':>10}{'hyb MRR':>9}"
              f"{'lex nDCG':>10}{'grph nDCG':>11}{'hyb nDCG':>10}")
    print(header)
    for family in FAMILIES + ("overall",):
        lex = result["lexical"]["overall"] if family == "overall" \
            else result["lexical"]["by_type"].get(family, {})
        grph = result["graph"]["overall"] if family == "overall" \
            else result["graph"]["by_type"].get(family, {})
        hyb = result["hybrid"]["overall"] if family == "overall" \
            else result["hybrid"]["by_type"].get(family, {})
        print(f"      {family:<11}{lex.get('recall@k', 0.0):>9.3f}"
              f"{grph.get('recall@k', 0.0):>10.3f}{hyb.get('recall@k', 0.0):>9.3f}"
              f"{lex.get('mrr', 0.0):>9.3f}{grph.get('mrr', 0.0):>10.3f}"
              f"{hyb.get('mrr', 0.0):>9.3f}"
              f"{lex.get('ndcg@k', 0.0):>10.3f}{grph.get('ndcg@k', 0.0):>11.3f}"
              f"{hyb.get('ndcg@k', 0.0):>10.3f}")
    print("      multi_hop is called out above; the numbers are reported as measured and "
          "the graph is NOT assumed to win")


# ---------------------------------------------------------------------------
# Step 5: the graph-adds-nothing limit case and the missing connecting edge
# ---------------------------------------------------------------------------

def check_limit_case() -> None:
    import graph

    built = graph.load_graph(_toy_corpus())
    store, documents = built["store"], built["documents"]

    # A lexical query: the policy word names no entity, so graph-only is empty and the
    # expansion cannot add a relevant document.
    lexical_query = {"text": "What does alpha require?", "filters": {},
                     "relevance": {"DOC-0000": 2.0}}
    graph_docs = graph.graph_retrieve(lexical_query, len(documents), store, documents)
    assert graph_docs == [], (
        f"a query naming no entity must expand to nothing, got {graph_docs}")
    assert not (set(graph_docs) & set(lexical_query["relevance"])), (
        "the graph added a relevant document on a non-multi-hop query")

    # A graph expansion that adds candidates the question does not want: naming the
    # department reaches its topics' documents *and* every document it owns.
    noise_query = {"text": "Engineering", "filters": {},
                   "relevance": {"DOC-0000": 2.0}}
    noise_docs = graph.graph_retrieve(noise_query, len(documents), store, documents)
    assert noise_docs, "naming the Engineering department must reach its documents"
    noise = set(noise_docs) - set(noise_query["relevance"])
    assert noise, "the construction must show the graph adding a non-relevant document"

    # The multi-hop question needs the reports_to edge; without it the report's
    # document is unreachable and graph-only abstains.
    broken = graph.load_graph(_broken_corpus())
    question = {"text": "Which documents did A. Rivera own, and what did the person "
                        "reporting to them write about?", "filters": {},
                "relevance": {"DOC-0000": 1.0}}
    reached = graph.graph_retrieve(question, len(broken["documents"]),
                                   broken["store"], broken["documents"])
    assert reached == [], (
        "with the reports_to edge absent, graph-only must return [] rather than invent "
        f"a path; got {reached}")
    assert graph.documents_for_entities(["PER-00"], broken["documents"]) == [], (
        "A. Rivera has no document in the broken corpus")
    assert graph.documents_for_entities(["PER-01"], broken["documents"]) == [
        "DOC-0000"], "the answer exists in the corpus, but only the missing edge reaches it"

    print(f"      lexical query {lexical_query['text']!r}: graph-only candidates "
          f"{len(graph_docs)} (adds no relevant document)")
    print(f"      query {noise_query['text']!r}: graph-only reaches "
          f"{len(noise_docs)} documents, {len(noise)} of them not relevant (noise)")
    print(f"      multi-hop question with the reports_to edge absent: graph-only "
          f"{reached}; the answer {sorted(graph.documents_for_entities(['PER-01'], broken['documents']))} "
          "is in the corpus but unreachable")


# ---------------------------------------------------------------------------
# Step 6: abstention — the graph does not invent results
# ---------------------------------------------------------------------------

def check_abstention() -> None:
    import graph

    built = graph.load_graph(_toy_corpus())
    store, documents = built["store"], built["documents"]

    assert graph.link_entities("zzzq nowhere", built["entities"]) == [], (
        "a query naming no known entity must link to no entity")
    assert graph.graph_retrieve({"text": "zzzq nowhere", "filters": {},
                                 "relevance": {}}, 5, store, documents) == [], (
        "graph_retrieve on a query naming no entity must abstain (return []), not "
        "return every entity's documents")
    assert graph.hybrid_retrieve({"text": "zzzq nowhere", "filters": {},
                                  "relevance": {}}, 5, store, documents) == [], (
        "the hybrid must abstain when both stages abstain")
    assert graph.documents_for_entities(["NOPE-99"], documents) == [], (
        "an unknown entity must not resolve to the corpus")

    try:
        corpus_mod, queries_mod, _metrics, _baseline = _load_eval_set()
    except FileNotFoundError:
        return
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    built = graph.load_graph(corpus)
    store, documents = built["store"], built["documents"]

    abstaining = [query for query in query_sets["no_answer"]
                  if not graph.lexical_retrieve(query, 100, documents)]
    assert abstaining, (
        "expected at least one no-answer query the lexical stage abstains on; if this "
        "fails the shared corpus changed and this check needs updating")
    query = abstaining[0]
    assert graph.graph_retrieve(query, 5, store, documents) == [], (
        f"the no-answer query {query['qid']} names no entity, so the graph must abstain")
    assert graph.hybrid_retrieve(query, 5, store, documents) == [], (
        f"the no-answer query {query['qid']} must stay empty through the hybrid")
    print(f"      {len(abstaining)} no-answer queries abstain at the lexical stage and "
          "stay empty through the graph and the hybrid")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("graph.py", "the triple store, typed adjacency and the loaded corpus counts", check_triple_store),
    ("graph.py", "whole-word entity linking and the linked-document subset", check_entity_linking),
    ("graph.py", "multi-hop traversal respects the hop limit", check_multi_hop),
    ("graph.py", "end to end on the shared eval set; the hybrid is a union", check_eval_set_end_to_end),
    ("graph.py", "the graph adds nothing (or noise); a missing edge returns []", check_limit_case),
    ("graph.py", "abstention survives the graph and the hybrid", check_abstention),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}RAG from scratch, project 6 — knowledge graph + vector{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<10} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<10} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<10} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — knowledge graph + vector is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

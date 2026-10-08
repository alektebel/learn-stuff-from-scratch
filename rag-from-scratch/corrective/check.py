"""
Progress checker for the RAG project-7 corrective-RAG templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports this module's own ``solutions/``; it
tests YOUR template. The shared eval set lives in ``../eval-set`` and is imported from its
``solutions/`` exactly the way the sibling stages reach it. Steps 1, 2, 3, 5 and 6 run on
hand-built corpora and never touch the eval set, so the mutation harness can run them in a
bare temporary directory. Step 4's first half is the same — a self-contained leak check —
and only its second half needs the eval set.

The checks are deliberately adversarial:

* step 1 pins the gate on hand-built result lists: a strong first stage is ``"ok"``, a weak
  one (nothing matched, or the top-k disagree) is ``"weak"``, deterministically and with no
  eval set in sight;
* step 2 pins pseudo-relevance feedback on a hand-built corpus where the relevant document
  shares a term with the *top* documents but not with the raw query, and requires the
  expansion to exclude stopwords and to actually retrieve it;
* step 3 builds a query whose answer lives only in the second corpus and requires the
  primary stage alone to miss it and ``retrieve_second`` to find it;
* step 4 (a) re-runs the evaluation with the relevance labels blanked and requires the path
  counts to be unchanged: any judgment-reading that actually moves a routing decision fails
  here (the check is behavioural, so a peek that leaves every path unchanged is not caught),
  and
  (b) reports the raw vs corrective recall@k, MRR and nDCG@k per family on the shared eval
  set, asserting only that the corrective result is a valid retrieval, never that it wins;
* step 5 constructs the limit cases: PRF query drift (the expansion adds an off-topic term
  and the rewritten query loses a document the raw one ranked first) and a weak query whose
  rewrite cannot help and whose fallback is empty (the result is the primary's, or empty,
  never an invention);
* step 6 pins abstention: a query nothing answers stays empty through every path, and the
  rewrite and the fallback cannot manufacture a result.
"""
import os
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

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
    import corpus
    import metrics
    import queries

    return corpus, queries, metrics


# ---------------------------------------------------------------------------
# Hand-built corpora (every step except 4b needs no eval set)
# ---------------------------------------------------------------------------

def _result(doc_id, score, terms):
    """A first-stage result, in the shape ``quality_gate`` and ``rewrite_prf`` read."""
    return {"doc_id": doc_id, "score": score, "terms": terms}


def _tiny_corpus():
    """Three documents where the relevant one shares a term with the top docs only."""
    return [
        {"doc_id": "D1", "title": "access control policy",
         "body": "access control policy alpha"},
        {"doc_id": "D2", "title": "access control permissions",
         "body": "access control permissions matrix"},
        {"doc_id": "D3", "title": "authorization matrix",
         "body": "authorization permissions matrix"},
    ]


def _drift_corpus():
    """A relevant document, an off-topic neighbour, and fillers that raise the idf.

    ``R`` is the only relevant document for the query "widget" and the raw stage ranks it
    first. ``X`` also contains "widget" so PRF reads it and pulls "gadget"/"sprocket" into
    the query; ``Y`` then contains those terms and overtakes ``R``.
    """
    documents = [
        {"doc_id": "R", "title": "widget", "body": "widget"},
        {"doc_id": "X", "title": "widget gadget sprocket",
         "body": "widget gadget sprocket"},
        {"doc_id": "Y", "title": "gadget sprocket", "body": "gadget sprocket"},
    ]
    for n in range(6):
        term = f"filler{n}"
        documents.append({"doc_id": f"F{n}", "title": term, "body": term})
    return documents


def _primary_doc(doc_id, text):
    return {"doc_id": doc_id, "title": text, "body": text}


# ---------------------------------------------------------------------------
# Step 1: the quality gate
# ---------------------------------------------------------------------------

def check_gate() -> None:
    import corrective

    strong = [
        _result("S1", 5.0, ["access", "control", "alpha"]),
        _result("S2", 4.0, ["access", "control", "policy"]),
        _result("S3", 3.0, ["access", "control", "review"]),
    ]
    weak = [
        _result("W1", 0.10, ["zeta"]),
        _result("W2", 0.05, ["omega"]),
        _result("W3", 0.02, ["kappa"]),
    ]
    disagreeing = [
        _result("G1", 9.0, ["alpha"]),
        _result("G2", 9.0, ["beta"]),
        _result("G3", 9.0, ["gamma"]),
    ]
    assert corrective.quality_gate(strong) == "ok", (
        "a strong first stage (high scores, the top documents agree) must be ok")
    assert corrective.quality_gate(weak) == "weak", (
        "a first stage whose top score is near zero must be weak")
    assert corrective.quality_gate([]) == "weak", (
        "an empty first stage must be weak")
    assert corrective.quality_gate(disagreeing) == "weak", (
        "a high score cannot hide a top-k that shares no terms")
    assert corrective.quality_gate(weak) == corrective.quality_gate(weak), (
        "the gate must be deterministic")
    print("      strong -> ok, near-zero -> weak, empty -> weak, disjoint top-k -> weak")

    # (The gate must not need the eval set: this step never loads it.)


# ---------------------------------------------------------------------------
# Step 2: pseudo-relevance feedback
# ---------------------------------------------------------------------------

def check_prf() -> None:
    import corrective

    documents = _tiny_corpus()
    raw = corrective.retrieve_primary("access control", 5, documents)
    raw_ids = [item["doc_id"] for item in raw]
    assert "D3" not in raw_ids, (
        f"the raw query already found D3; the hand-built case is not testing PRF: {raw_ids}")

    expanded = corrective.rewrite_prf("access control", raw, 3, ["access", "control"])
    assert "access" in expanded and "control" in expanded, (
        "PRF must keep the original query terms")
    assert "permissions" in expanded, (
        f"the expansion must include a term from the top documents, got {expanded}")
    assert all(term not in corrective.STOPWORDS for term in expanded), (
        f"the expansion must exclude stopwords, got {expanded}")
    top_terms = set()
    for item in raw[:3]:
        top_terms |= set(item["terms"])
    assert set(expanded) - set(corrective.tokenize("access control")) <= top_terms, (
        f"every added term must come from the top documents: {expanded}")
    assert expanded == corrective.rewrite_prf(
        "access control", raw, 3, ["access", "control"]), (
        "PRF must be deterministic")
    assert expanded != corrective.tokenize("access control"), (
        "PRF must actually expand the query")

    rewritten = corrective.retrieve_primary(expanded, 5, documents)
    rewritten_ids = [item["doc_id"] for item in rewritten]
    assert "D3" in rewritten_ids, (
        f"the rewritten query must retrieve the document the raw one missed: {rewritten_ids}")
    print(f"      raw {raw_ids} -> expansion {expanded} -> rewritten {rewritten_ids}")


# ---------------------------------------------------------------------------
# Step 3: the second-corpus fallback
# ---------------------------------------------------------------------------

def check_fallback() -> None:
    import corrective

    second = corrective.build_second_corpus()
    assert isinstance(second, list) and second, (
        "build_second_corpus must return a non-empty list of documents")
    probe = second[0]
    primary = [_primary_doc("P1", "company travel and expense policy")]

    raw = corrective.retrieve_primary(probe["title"], 5, primary)
    assert raw == [], (
        f"the primary corpus must not answer the fallback probe, got "
        f"{[item['doc_id'] for item in raw]}")
    found = corrective.retrieve_second(probe["title"], 5, second)
    assert [item["doc_id"] for item in found][:1] == [probe["doc_id"]], (
        f"retrieve_second must find {probe['doc_id']} for its own title, got "
        f"{[item['doc_id'] for item in found]}")

    tag = corrective.corrective_retrieve(probe["title"], 5, primary)
    assert tag["path"] == "fallback", (
        f"a query only the second corpus answers must be tagged fallback, got "
        f"path={tag['path']!r}")
    assert tag["documents"] == [probe["doc_id"]], (
        f"the fallback must return the second-corpus document, got {tag['documents']}")
    assert probe["doc_id"] not in {document["doc_id"] for document in primary}, (
        "the returned document must not be one of the primary documents")
    print(f"      primary misses {probe['title']!r}; fallback returns {probe['doc_id']}")


# ---------------------------------------------------------------------------
# Step 4: end to end, and the label-leak check
# ---------------------------------------------------------------------------

def _blanked(query_sets):
    """A copy of the query sets with every relevance judgment removed."""
    if isinstance(query_sets, dict):
        return {family: [{**query, "relevance": {}} for query in items]
                for family, items in query_sets.items()}
    return [{**query, "relevance": {}} for query in query_sets]


def _self_contained_queries():
    return {
        "lexical": [
            {"qid": "L1", "text": "alpha access control", "type": "lexical",
             "filters": {}, "relevance": {"A": 2.0}},
            {"qid": "L2", "text": "beta data retention", "type": "lexical",
             "filters": {}, "relevance": {"B": 2.0}},
        ],
        "no_answer": [
            {"qid": "N1", "text": "zzzq nothing", "type": "no_answer",
             "filters": {}, "relevance": {}},
        ],
    }


def check_end_to_end() -> None:
    import corrective

    # (a) Self-contained: validity, path accounting and the label-leak check.
    documents = [
        {"doc_id": "A", "title": "alpha access control",
         "body": "alpha access control policy"},
        {"doc_id": "B", "title": "beta data retention",
         "body": "beta data retention policy"},
        {"doc_id": "C", "title": "gamma encryption", "body": "gamma encryption standard"},
    ]
    query_sets = _self_contained_queries()
    result = corrective.evaluate(query_sets, documents, k=5)
    valid = {document["doc_id"] for document in documents}
    valid |= {document["doc_id"] for document in corrective.build_second_corpus()}
    for record in result["records"]:
        assert set(record["corrective"]) <= valid, (
            f"the corrective pipeline returned a document from no corpus: {record}")
    assert result["n"] == 3, f"evaluate counted {result['n']} queries, expected 3"
    assert sum(result["paths"].values()) + result["abstained"] == result["n"], (
        f"path counts {result['paths']} plus {result['abstained']} abstentions do not sum "
        f"to {result['n']}")

    blanked = corrective.evaluate(_blanked(query_sets), documents, k=5)
    assert blanked["paths"] == result["paths"], (
        f"the path counts changed when the relevance labels were blanked "
        f"({result['paths']} -> {blanked['paths']}): the gate or the path decision is "
        "reading the test judgments, which is a leak")
    assert blanked["abstained"] == result["abstained"], (
        "the abstention count changed when the labels were blanked: a leak")
    print("      self-contained: validity, path accounting and the label-leak check pass")

    # (b) The shared evaluation set.
    try:
        corpus_mod, queries_mod, metrics = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the "
              "self-contained half only")
        return

    corpus = corpus_mod.generate_corpus(0)
    documents = corpus["documents"]
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)
    result = corrective.evaluate(query_sets, documents, k=5)
    assert result["n"] == len(queries), (
        f"evaluate scored {result['n']} queries, the set has {len(queries)}")
    for record in result["records"]:
        assert set(record["corrective"]) <= result["valid_ids"], (
            f"query {record['qid']} returned an invented document "
            f"{record['corrective']}")

    ranked = {record["qid"]: record["raw"] for record in result["records"]}
    shared = metrics.evaluate(ranked, queries, k=5)
    assert abs(shared["overall"]["recall@k"]
               - result["raw"]["overall"]["recall@k"]) < 1e-9, (
        "the local raw recall does not match the shared metrics module, so the two "
        "reports disagree on the same rankings")
    assert sum(result["paths"].values()) + result["abstained"] == result["n"], (
        f"path counts {result['paths']} plus {result['abstained']} abstentions do not sum "
        f"to {result['n']}")

    print(f"      seed 0: {len(documents)} primary + "
          f"{len(corrective.build_second_corpus())} external documents, "
          f"{result['n']} queries")
    header = (f"      {'family':<11}{'n':>3}{'raw r@5':>10}{'cor r@5':>10}"
              f"{'raw mrr':>9}{'cor mrr':>9}{'raw ndcg':>10}{'cor ndcg':>10}")
    print(header)
    for family in FAMILIES:
        raw = result["raw"].get(family)
        cor = result["corrective"].get(family)
        if not raw:
            continue
        print(f"      {family:<11}{raw['n']:>3}"
              f"{raw['recall@k']:>10.3f}{cor['recall@k']:>10.3f}"
              f"{raw['mrr']:>9.3f}{cor['mrr']:>9.3f}"
              f"{raw['ndcg@k']:>10.3f}{cor['ndcg@k']:>10.3f}")
    print(f"      {'overall':<11}{result['n']:>3}"
          f"{result['raw']['overall']['recall@k']:>10.3f}"
          f"{result['corrective']['overall']['recall@k']:>10.3f}"
          f"{result['raw']['overall']['mrr']:>9.3f}"
          f"{result['corrective']['overall']['mrr']:>9.3f}"
          f"{result['raw']['overall']['ndcg@k']:>10.3f}"
          f"{result['corrective']['overall']['ndcg@k']:>10.3f}")
    print(f"      paths: {result['paths']} abstained={result['abstained']} "
          "(reported as measured; the corrective pipeline is not assumed to win — on "
          "this easy set it may tie)")


# ---------------------------------------------------------------------------
# Step 5: the limit cases — query drift and a correction that cannot help
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    import corrective

    # (a) PRF drift: a query the raw stage got right is degraded by the expansion.
    documents = _drift_corpus()
    raw = corrective.retrieve_primary("widget", 5, documents)
    raw_ids = [item["doc_id"] for item in raw]
    assert raw_ids and raw_ids[0] == "R", (
        f"the raw stage must rank the relevant document R first, got {raw_ids}")
    assert corrective.quality_gate(raw) == "ok", (
        "the raw stage is strong here, so the gate is ok and the pipeline would keep it")

    expanded = corrective.rewrite_prf("widget", raw, 2, ["widget"])
    added = [term for term in expanded if term != "widget"]
    assert added, "PRF must add the neighbour's terms to the query"
    assert any(term in ("gadget", "sprocket") for term in added), (
        f"the off-topic neighbour's terms are not in the expansion: {expanded}")
    rewritten = corrective.retrieve_primary(expanded, 5, documents)
    rewritten_ids = [item["doc_id"] for item in rewritten]
    assert rewritten_ids[0] != "R", (
        f"drift was expected: the rewritten query should no longer rank R first, got "
        f"{rewritten_ids}")
    print(f"      drift: raw {raw_ids} (R first) -> expansion {added} -> "
          f"rewritten {rewritten_ids} (R loses the top rank)")

    # (b) A weak query the rewrite cannot help and the fallback cannot answer.
    primary = [_primary_doc("P1", "alpha report")]
    tag = corrective.corrective_retrieve("zzzq nonexistent topic", 5, primary)
    assert tag["path"] == "abstain" and tag["documents"] == [], (
        f"a weak query with no rewrite help and no fallback must stay empty, got {tag}")
    partial = corrective.corrective_retrieve("alpha", 5, primary)
    assert partial["documents"] == ["P1"], (
        f"when the rewrite cannot help, the primary result is kept, not replaced or "
        f"invented; got {partial['documents']}")
    assert partial["path"] in ("raw", "rewritten"), (
        f"the kept result is the primary's, not the second corpus's: {partial['path']}")
    print(f"      no help: 'zzzq nonexistent topic' -> {tag['documents']}; "
          f"'alpha' -> {partial['documents']} (path {partial['path']!r})")


# ---------------------------------------------------------------------------
# Step 6: abstention — the rewrite and the fallback invent nothing
# ---------------------------------------------------------------------------

def check_abstention() -> None:
    import corrective

    primary = [_primary_doc("P1", "alpha report")]
    for query in ("zzzq nonexistent topic", "qqqq wwww vvvv"):
        tag = corrective.corrective_retrieve(query, 5, primary)
        assert tag["documents"] == [] and tag["abstained"], (
            f"the no-answer query {query!r} must return nothing, got {tag}")
        assert tag["path"] == "abstain", (
            f"the no-answer query {query!r} must abstain, got path {tag['path']!r}")
        assert corrective.retrieve_second(query, 5) == [], (
            f"the second corpus must not match the no-answer query {query!r}")
    print("      hand-built no-answer queries stay empty through the rewrite and fallback")

    try:
        corpus_mod, queries_mod, _metrics = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the "
              "hand-built abstention only")
        return

    corpus = corpus_mod.generate_corpus(0)
    documents = corpus["documents"]
    query_sets = queries_mod.build_query_sets(corpus)
    abstaining = [query for query in query_sets["no_answer"]
                  if not corrective.retrieve_primary(query, 5, documents)]
    assert abstaining, (
        "expected at least one no-answer query the primary stage abstains on; if this "
        "fails the shared corpus changed and this check needs updating")
    for query in abstaining:
        tag = corrective.corrective_retrieve(query, 5, documents)
        assert tag["documents"] == [] and tag["abstained"], (
            f"the no-answer query {query['qid']} must stay empty through every path, "
            f"got {tag}")
    corrected = sum(1 for query in query_sets["no_answer"]
                    if corrective.corrective_retrieve(query, 5, documents)["abstained"])
    print(f"      through the pipeline: {corrected}/{len(query_sets['no_answer'])} "
          f"no-answer queries abstain (the raw primary abstains on "
          f"{len(abstaining)}/{len(query_sets['no_answer'])}). Recall is 0 by "
          "construction; the pipeline does not manufacture a hit.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("corrective.py", "the score/consensus quality gate, on hand-built results", check_gate),
    ("corrective.py", "PRF expansion retrieves what the raw query missed", check_prf),
    ("corrective.py", "a query only the second corpus answers goes to the fallback", check_fallback),
    ("corrective.py", "end to end on the shared eval set; the path counts do not leak labels", check_end_to_end),
    ("corrective.py", "the limit cases: query drift, and a correction that cannot help", check_limit_cases),
    ("corrective.py", "abstention survives the rewrite and the fallback", check_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 7 — corrective RAG (offline){RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — corrective RAG is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

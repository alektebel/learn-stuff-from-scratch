"""
Progress checker for the RAG project-2 metadata-filtered templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The eval set lives in `../eval-set` as its own graded module. Its top-level files are
templates, so the checks import the modules from `../eval-set/solutions` (the graded
reference) and only add that directory to `sys.path` lazily, inside the one check that
needs it. Steps 1-3 and 5-6 run on hand-built corpora and never touch the eval set, so
the mutation harness can run them in a bare temporary directory. Step 4 is the only
end-to-end check.

The checks are deliberately adversarial: step 1 reads the SQLite catalogue to demand a
secondary index on every filterable column, step 2 pins the exact order of a tiny
pre-filtered ranking and forbids a non-matching document, step 3 holds the three
strategies to the same answer, step 5 constructs the selective-filter shortfall instead
of hoping a random query hits it, and step 6 makes abstention explicit.
"""
import math
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


def _close(got, want, what, tol=1e-9):
    assert abs(got - want) < tol, f"{what}: got {got!r}, expected {want!r}"


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
# Hand-built documents (steps 1-3, 5-6 need no eval set)
# ---------------------------------------------------------------------------

def _doc(doc_id, title, body, department, date, author, region, access_level,
         superseded=False):
    return {
        "doc_id": doc_id, "title": title, "body": body,
        "department": department, "date": date, "author": author,
        "region": region, "access_level": access_level, "superseded": superseded,
    }


def _tiny_docs():
    return [
        _doc("d1", "alpha alpha", "beta", "Engineering", "2023-05-01", "A", "EMEA",
             "public"),
        _doc("doc-2023", "alpha", "beta", "Engineering", "2024-01-01", "A", "EMEA",
             "public"),
        _doc("d3", "alpha", "beta", "HR", "2023-01-01", "B", "AMER", "internal"),
        _doc("d4", "alpha", "gamma", "Engineering", "2023-06-01", "C", "APAC", "public"),
    ]


def _moderate_docs():
    docs = []
    for i in range(4):
        docs.append(_doc(f"e{i}", "alpha", "beta", "Engineering", "2023-01-01",
                         "A", "EMEA", "public"))
    for i in range(4):
        docs.append(_doc(f"g{i}", "beta", "gamma", "Finance", "2023-01-01",
                         "B", "AMER", "internal"))
    return docs


def _selective_docs():
    docs = []
    for i in range(69):
        year = 2000 + (i % 20)
        docs.append(_doc(f"g{i:03d}", "common common common", "common common",
                         "General", f"{year:04d}-01-01", "A", "AMER", "public"))
    docs.append(_doc("target", "alpha common", "uniqueterm", "Special", "2026-01-01",
                     "Z", "EMEA", "restricted"))
    return docs


def _doc_matches(doc, filters):
    """The ground-truth filter predicate, independent of the module under test."""
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if key == "year":
            if str(doc.get("date", ""))[:4] != str(value):
                return False
        elif key == "superseded":
            if bool(doc.get("superseded")) != (1 if value else 0):
                return False
        elif doc.get(key) != value:
            return False
    return True


# ---------------------------------------------------------------------------
# Step 1: the SQLite schema and its secondary indexes
# ---------------------------------------------------------------------------

def check_schema_and_indexes() -> None:
    import filtered

    docs = _tiny_docs()
    conn = filtered.build_db(docs)

    stored = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert stored == len(docs), (
        f"the documents table holds {stored} rows for a {len(docs)}-document corpus")

    columns = {row[1] for row in conn.execute("PRAGMA table_info('documents')")}
    for required in ("doc_id", "title", "body") + filtered.FILTERABLE:
        assert required in columns, (
            f"the documents table is missing the {required!r} column; columns={columns}")

    indexed = set()
    for index in conn.execute("PRAGMA index_list('documents')").fetchall():
        name = index[1]
        for column in conn.execute(f"PRAGMA index_info('{name}')").fetchall():
            indexed.add(column[2])
    missing = [column for column in filtered.FILTERABLE if column not in indexed]
    assert not missing, (
        f"no secondary index covers {missing}; a pre-data filter cannot be answered "
        f"without a scan. PRAGMA index_list shows indexed columns {sorted(indexed)}. "
        "build_db must CREATE INDEX on every filterable column.")


# ---------------------------------------------------------------------------
# Step 2: pre_filter picks exactly the matches, in the right order
# ---------------------------------------------------------------------------

def check_pre_filter_exact() -> None:
    import filtered

    docs = _tiny_docs()
    retriever = filtered.FilteredRetriever(docs)
    filters = {"department": "Engineering", "year": 2023}

    got = retriever.pre_filter("alpha", k=10, filters=filters)
    assert got == ["d1", "d4"], (
        f"pre_filter('alpha', department=Engineering, year=2023) must return "
        f"['d1', 'd4'] (d1 has the higher tf), got {got!r}")
    for doc_id in ("doc-2023", "d3"):
        assert doc_id not in got, (
            f"pre_filter returned {doc_id!r}, which does not satisfy the filter "
            f"{filters!r}: the SQL WHERE clause is missing or wrong")

    # A wrong-year document that merely *contains* the year string must not leak in.
    assert "doc-2023" not in retriever.pre_filter(
        "alpha", k=10, filters={"year": 2023, "department": "Engineering"}), (
        "a document dated 2024 was admitted by a year=2023 filter: the year is being "
        "compared as a substring instead of as the date prefix")

    # A filter with no extra constraint is the whole set, still ranked, still matching.
    only_dept = retriever.pre_filter("alpha", k=10, filters={"department": "HR"})
    assert only_dept == ["d3"], f"department=HR must give ['d3'], got {only_dept!r}"

    # Every filterable column must actually restrict the result: a learner who wires
    # only department/year leaks across access levels and freshness (tenant isolation
    # is a filter that must not be bypassable).
    internal = retriever.pre_filter("alpha", k=10, filters={"access_level": "internal"})
    assert internal == ["d3"], (
        f"filter access_level='internal' must return only d3, got {internal!r}: an "
        "access-level filter that is ignored returns the whole corpus")
    by_author = retriever.pre_filter("alpha", k=10, filters={"author": "B"})
    assert by_author == ["d3"], f"filter author='B' must return only d3, got {by_author!r}"
    fresh = retriever.pre_filter("alpha", k=10, filters={"superseded": False})
    assert set(fresh) == {"d1", "doc-2023", "d3", "d4"}, (
        f"filter superseded=False must return every fresh document, got {fresh!r}")
    stale = retriever.pre_filter("alpha", k=10, filters={"superseded": True})
    assert stale == [], (
        "filter superseded=True must return nothing (no tiny document is superseded), "
        f"got {stale!r}: the superseded predicate is inverted")


# ---------------------------------------------------------------------------
# Step 3: the three strategies agree on a moderate filter
# ---------------------------------------------------------------------------

def check_strategies_agree() -> None:
    import filtered

    docs = _moderate_docs()
    retriever = filtered.FilteredRetriever(docs)
    filters = {"department": "Engineering"}
    k = 3

    pre = retriever.pre_filter("alpha", k=k, filters=filters)
    post = retriever.post_filter("alpha", k=k, filters=filters)
    aware = retriever.filter_aware("alpha", k=k, filters=filters)

    assert pre == post == aware, (
        f"on a moderate filter the three strategies must agree, got pre={pre!r}, "
        f"post={post!r}, filter_aware={aware!r}")
    assert len(pre) == k, f"the moderate filter should fill k={k}, got {len(pre)}"
    for strategy, result in (("pre_filter", pre), ("post_filter", post),
                             ("filter_aware", aware)):
        for doc_id in result:
            assert _doc_matches(retriever.by_id[doc_id], filters), (
                f"{strategy} returned {doc_id!r}, which does not satisfy {filters!r}")


# ---------------------------------------------------------------------------
# Step 4: end to end on the shared eval set's `filtered` family
# ---------------------------------------------------------------------------

def check_eval_filtered_family() -> None:
    import filtered

    corpus_mod, queries_mod, metrics, _baseline = _load_eval_set()
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)
    filtered_queries = [q for q in queries if q["type"] == "filtered"]
    assert filtered_queries, "the eval set must contain filtered queries"

    docs = corpus["documents"]
    by_id = {doc["doc_id"]: doc for doc in docs}
    loaded = filtered.load_documents(0)
    assert len(loaded) == len(docs), (
        f"load_documents returned {len(loaded)} documents, the corpus has {len(docs)}")

    retriever = filtered.FilteredRetriever(docs)
    k = 10
    strategies = ("pre_filter", "post_filter", "filter_aware")
    measured = {}
    mean_results = {}
    for name in strategies:
        ranked = {q["qid"]: getattr(retriever, name)(
            q, k=k, filters=q.get("filters", {})) for q in queries}
        for q in queries:
            result = ranked[q["qid"]]
            assert len(result) <= k, (
                f"{name} returned {len(result)} results for k={k}")
            for doc_id in result:
                assert doc_id in by_id, f"{name} returned unknown doc_id {doc_id!r}"
                assert _doc_matches(by_id[doc_id], q.get("filters", {})), (
                    f"{name} returned {doc_id!r} for query {q['qid']}, which does not "
                    f"satisfy its filter {q.get('filters', {})!r}")
        measured[name] = metrics.evaluate(ranked, queries, k=k)
        mean_results[name] = (
            sum(len(ranked[q["qid"]]) for q in filtered_queries)
            / len(filtered_queries))

    # Reproducibility: the module's own evaluate(...) must agree with the recomputation.
    combined = filtered.evaluate(corpus, query_sets, k=k)
    for name in strategies:
        assert name in combined and "mean_results" in combined, (
            "evaluate must return one metrics dict per strategy plus mean_results")
        recomputed = measured[name]["by_type"]["filtered"]
        reported = combined[name]["by_type"]["filtered"]
        _close(reported["recall@k"], recomputed["recall@k"],
               f"{name} reported vs recomputed filtered recall@k")
        _close(reported["mrr"], recomputed["mrr"],
               f"{name} reported vs recomputed filtered MRR")
        _close(reported["ndcg@k"], recomputed["ndcg@k"],
               f"{name} reported vs recomputed filtered nDCG@k")
        _close(combined["mean_results"][name], mean_results[name],
               f"{name} reported vs recomputed mean results")

    assert mean_results["post_filter"] <= mean_results["pre_filter"] + 1e-12, (
        "post_filter cannot return more results than pre_filter on the same filter")

    print(f"      seed 0, {len(docs)} documents, {len(filtered_queries)} filtered "
          f"queries, k={k}")
    print(f"      {'strategy':<14}{'recall@k':>10}{'MRR':>9}{'nDCG@k':>9}"
          f"{'mean results':>14}")
    for name in strategies:
        family = measured[name]["by_type"]["filtered"]
        print(f"      {name:<14}{family['recall@k']:>10.3f}{family['mrr']:>9.3f}"
              f"{family['ndcg@k']:>9.3f}{mean_results[name]:>14.2f}")
    print("      the numbers above are reported as measured; no strategy is assumed "
          "to win")


# ---------------------------------------------------------------------------
# Step 5: a very selective filter exposes the post-filter shortfall
# ---------------------------------------------------------------------------

def check_selective_filter_shortfall() -> None:
    import filtered

    docs = _selective_docs()
    retriever = filtered.FilteredRetriever(docs)
    filters = {"department": "Special"}
    k = 10

    sel = filtered.selectivity(retriever.conn, filters)
    assert sel <= 1.0 / 66.0 + 1e-12, (
        f"the construction must be very selective (<= 1/66), got {sel!r}")
    matching = [d["doc_id"] for d in docs if _doc_matches(d, filters)]
    assert len(matching) == 1 and matching == ["target"], matching

    pre = retriever.pre_filter("common", k=k, filters=filters)
    post = retriever.post_filter("common", k=k, filters=filters)
    aware = retriever.filter_aware("common", k=k, filters=filters)

    assert pre == ["target"], (
        f"pre_filter must reach the one matching document under a selective filter, "
        f"got {pre!r}")
    assert aware == pre, (
        f"filter_aware must reach the same documents as pre_filter (otherwise it has "
        f"degenerated to post_filter): pre={pre!r}, filter_aware={aware!r}")
    assert post == [], (
        f"under this construction the one matching document ranks below the global "
        f"top-{k} window, so post_filter sees none of it and must return []; it returned "
        f"{post!r}. A post_filter that instead filters the whole ranking has quietly "
        "fixed the anti-pattern this exercise is about.")
    for strategy, result in (("pre_filter", pre), ("post_filter", post),
                             ("filter_aware", aware)):
        for doc_id in result:
            assert _doc_matches(retriever.by_id[doc_id], filters), (
                f"{strategy} returned {doc_id!r}, which does not satisfy {filters!r}")

    print(f"      selective filter {filters!r}: {len(matching)} of {len(docs)} "
          f"documents, selectivity {sel:.4f}")
    print(f"      query 'common', k={k}: pre_filter={pre!r} filter_aware={aware!r} "
          f"post_filter={post!r} (returned {len(post)} < k)")


# ---------------------------------------------------------------------------
# Step 6: no-match filters and no-lexical-match queries abstain
# ---------------------------------------------------------------------------

def check_abstention() -> None:
    import filtered

    retriever = filtered.FilteredRetriever(_tiny_docs())
    strategies = ("pre_filter", "post_filter", "filter_aware")

    for name in strategies:
        result = getattr(retriever, name)(
            "alpha", k=10, filters={"department": "Nowhere"})
        assert result == [], (
            f"{name} returned {result!r} for a department filter matching no document; "
            "it must abstain (return []) rather than fall back to the corpus")
        result = getattr(retriever, name)(
            "alpha", k=10, filters={"year": 1999})
        assert result == [], (
            f"{name} returned {result!r} for a year filter matching no document")

    for name in strategies:
        for query in ({"text": "zzzq nonexistent", "filters": {}}, "zzzq nonexistent"):
            result = getattr(retriever, name)(query, k=10)
            assert result == [], (
                f"{name} returned {result!r} for a query with no lexical match in the "
                "corpus; a zero-score query must abstain")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("filtered.py", "the SQLite schema and a secondary index per filterable column", check_schema_and_indexes),
    ("filtered.py", "pre_filter returns exactly the matching documents, in order", check_pre_filter_exact),
    ("filtered.py", "pre/post/filter-aware agree on a moderate filter", check_strategies_agree),
    ("filtered.py", "end to end on the shared eval set's filtered family", check_eval_filtered_family),
    ("filtered.py", "a very selective filter exposes the post-filter shortfall", check_selective_filter_shortfall),
    ("filtered.py", "no-match filters and no-lexical-match queries abstain", check_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 2 — metadata-filtered RAG{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — metadata-filtered RAG is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

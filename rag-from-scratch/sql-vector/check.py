"""
Progress checker for the RAG project-5 SQL + vector templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports this module's own solutions/; it
tests YOUR template. The shared eval set lives in ``../eval-set`` and is imported from
its ``solutions/`` exactly the way the sibling stages reach it. Steps 1-3 and 5-6 run on
a hand-built corpus (``load_tables`` accepts a corpus dict) and never touch the eval set,
so the mutation harness can run them in a bare temporary directory; step 4's first half is
also self-contained and only its second half needs the eval set.

The checks are deliberately adversarial:

* step 1 demands the SQLite tables mirror the corpus exactly — column names in order,
  row counts, and a sample cell — on a hand-built corpus and on the shared one;
* step 2 pins the router on questions whose signals are clear, reports accuracy on a
  held-out list, and asserts the floor stated in README.md (0.90) *before* the result is
  known;
* step 3 pins each supported shape against an answer hand-computed from the rows, and
  requires an unknown column to abstain with None rather than raise or guess;
* step 4 routes structured questions through ``route_and_answer`` (so a router that sends
  them to retrieval scores zero) and reports the shared retrieval recall@k for the
  unstructured half honestly, without claiming the router is perfect;
* step 5 constructs the limit cases: an ambiguous question misrouted each way, a question
  naming a column that does not exist abstaining, and a hostile question carrying SQL
  being parameterised instead of executed;
* step 6 pins abstention: an unsupported structured question returns None, and a
  no-answer unstructured query stays empty through the router.
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
ROUTER_FLOOR = 0.90       # predicted in README.md before running the checker
STRUCTURED_FLOOR = 0.80   # structured-question accuracy floor for the end-to-end check
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
# Hand-built corpus (steps 1-3 and 5-6 need no eval set)
# ---------------------------------------------------------------------------

def _toy_corpus():
    """A four-row revenue table, three departments and three vendors, plus documents.

    The values are chosen so every supported shape has a hand-computable answer: total
    2025 revenue 500000, average headcount 25, two high-risk vendors, EMEA the top
    revenue region in 2025, Finance the smallest department.
    """
    tables = {
        "revenue_by_region": {
            "columns": ["region", "year", "quarter", "amount_usd"],
            "rows": [
                ["EMEA", 2024, 1, 100000],
                ["EMEA", 2025, 1, 300000],
                ["AMER", 2025, 1, 200000],
                ["APAC", 2024, 1, 50000],
            ],
        },
        "headcount_by_department": {
            "columns": ["department", "year", "headcount"],
            "rows": [
                ["Engineering", 2025, 40],
                ["Finance", 2025, 10],
                ["Sales", 2025, 25],
            ],
        },
        "vendors": {
            "columns": ["vendor_id", "name", "region", "risk_level"],
            "rows": [
                ["VEN-001", "Northwind", "EMEA", "low"],
                ["VEN-002", "Acme", "AMER", "high"],
                ["VEN-003", "Sakura", "APAC", "high"],
            ],
        },
    }
    documents = [
        {"doc_id": "DOC-0000", "title": "alpha report", "body": "alpha access control",
         "topics": ["access control"], "region": "EMEA", "date": "2025-01-01",
         "department": "Engineering", "author": "A. Rivera", "access_level": "public",
         "code": "POL-0001"},
        {"doc_id": "DOC-0001", "title": "beta report", "body": "beta data retention",
         "topics": ["data retention"], "region": "AMER", "date": "2025-02-01",
         "department": "Finance", "author": "B. Okafor", "access_level": "internal",
         "code": "POL-0002"},
        {"doc_id": "DOC-0002", "title": "gamma report", "body": "gamma encryption",
         "topics": ["encryption standard"], "region": "EMEA", "date": "2025-03-01",
         "department": "Engineering", "author": "A. Rivera", "access_level": "public",
         "code": "POL-0003"},
    ]
    return {"tables": tables, "documents": documents, "entities": [], "relations": []}


def _same(got, expected):
    """Structural equality with a float tolerance for AVG-style answers."""
    if isinstance(got, list) and isinstance(expected, list):
        if len(got) != len(expected):
            return False
        return all(_same(a, b) for a, b in zip(got, expected))
    if isinstance(got, (int, float)) and isinstance(expected, (int, float)) \
            and not isinstance(got, bool) and not isinstance(expected, bool):
        return abs(float(got) - float(expected)) < 1e-9
    return got == expected


def _eval_structured(corpus):
    """Structured questions with answers computed in pure Python from the corpus rows.

    This is the independent oracle: it never asks the SQL under test for its expected
    value. The last item is unsupported and must be answered with abstention.
    """
    revenue = corpus["tables"]["revenue_by_region"]["rows"]
    headcount = corpus["tables"]["headcount_by_department"]["rows"]
    vendors = corpus["tables"]["vendors"]["rows"]

    total_2025 = sum(row[3] for row in revenue if row[1] == 2025)
    by_region = {}
    for row in revenue:
        if row[1] == 2025:
            by_region[row[0]] = by_region.get(row[0], 0) + row[3]
    top_region = sorted(by_region, key=lambda name: (-by_region[name], name))[0]
    grouped = sorted((name, by_region[name]) for name in by_region)
    average_head = sum(row[2] for row in headcount) / len(headcount)
    low_dept = sorted(headcount, key=lambda row: (row[2], row[0]))[0][0]
    high_risk = sorted(row[1] for row in vendors if row[3] == "high")

    return [
        {"question": "What is the total revenue in 2025?", "expected": total_2025},
        {"question": "What is the average headcount in 2025?",
         "expected": average_head},
        {"question": "How many vendors are there?", "expected": len(vendors)},
        {"question": "How many vendors have high risk?", "expected": len(high_risk)},
        {"question": "List vendors with risk high",
         "expected": [(name,) for name in high_risk]},
        {"question": "Which region has the most revenue in 2025?",
         "expected": top_region},
        {"question": "Which department has the least headcount?", "expected": low_dept},
        {"question": "What is the total revenue by region in 2025?",
         "expected": grouped},
        {"question": "What is the total salary by region in 2025?", "expected": None},
    ]


# ---------------------------------------------------------------------------
# Step 1: the corpus tables exist in SQLite, with the right shape
# ---------------------------------------------------------------------------

def check_sqlite_load() -> None:
    import router

    toy = _toy_corpus()
    conn = router.load_tables(toy)
    stored = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for name in toy["tables"]:
        assert name in stored, f"the corpus table {name!r} was not created"
    assert stored == set(toy["tables"]), (
        f"load_tables created {sorted(stored)}, expected exactly "
        f"{sorted(toy['tables'])}")
    for name, spec in toy["tables"].items():
        columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{name}")')]
        assert columns == spec["columns"], (
            f"{name}: columns {columns} != corpus {spec['columns']}")
        count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        assert count == len(spec["rows"]), (
            f"{name}: {count} rows loaded, corpus has {len(spec['rows'])}")

    sample = conn.execute(
        'SELECT amount_usd FROM revenue_by_region '
        'WHERE region=? AND year=? AND quarter=?', ("EMEA", 2025, 1)).fetchone()
    assert sample is not None and sample[0] == 300000, (
        f"the sample cell (EMEA, 2025, Q1) must be 300000, got {sample}")
    assert conn.execute(
        'SELECT SUM(amount_usd) FROM revenue_by_region WHERE year=2025'
    ).fetchone()[0] == 500000, "integer values must stay integers through SQLite"

    try:
        corpus_mod, _queries, _metrics = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the toy "
              "corpus only")
        return
    corpus = corpus_mod.generate_corpus(0)
    real = router.load_tables(corpus)
    for name, spec in corpus["tables"].items():
        columns = [row[1] for row in real.execute(f'PRAGMA table_info("{name}")')]
        assert columns == spec["columns"], (
            f"seed-0 {name}: columns {columns} != corpus {spec['columns']}")
        count = real.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        assert count == len(spec["rows"]), (
            f"seed-0 {name}: {count} rows loaded, corpus has {len(spec['rows'])}")
    print(f"      seed 0: {len(corpus['tables'])} tables loaded "
          f"({', '.join(sorted(corpus['tables']))})")


# ---------------------------------------------------------------------------
# Step 2: the router's routes, and the predicted floor
# ---------------------------------------------------------------------------

_ROUTING_CASES = [
    ("How many vendors are there?", "structured"),
    ("What is the average headcount in 2025?", "structured"),
    ("Which region has the most revenue in 2025?", "structured"),
    ("Which department has the least headcount?", "structured"),
    ("What is the total revenue by region in 2025?", "structured"),
    ("List vendors with risk high", "structured"),
    ("What does POL-0001 require?", "unstructured"),
    ("Who is allowed into our systems and buildings? (topic: access control)",
     "unstructured"),
    ("vendor onboarding policy for EMEA in 2025", "unstructured"),
    ("What is our policy on interstellar freight insurance?", "unstructured"),
    ("How did EMEA do in 2025?", "unstructured"),
]

_HELD_OUT_CASES = [
    ("How many high-risk vendors are there?", "structured"),
    ("What is the total amount in 2024?", "structured"),
    ("Which region has the lowest revenue?", "structured"),
    ("Show vendors with risk medium", "structured"),
    ("What is the average revenue per region?", "structured"),
    ("Explain the escrow rules for orbital debris cleanup.", "unstructured"),
    ("What is the process for a lunar office relocation?", "unstructured"),
    ("third-party risk management overview", "unstructured"),
    ("Who approves submarine fleet purchases?", "unstructured"),
    ("What does the travel reimbursement policy say?", "unstructured"),
]


def check_router() -> None:
    import router

    for question, expected in _ROUTING_CASES:
        got = router.classify(question)
        assert got == expected, (
            f"classify({question!r}) returned {got!r}, expected {expected!r}")

    correct = 0
    for question, expected in _HELD_OUT_CASES:
        got = router.classify(question)
        if got == expected:
            correct += 1
        else:
            print(f"      miss: {question!r} -> {got!r} (expected {expected!r})")
    accuracy = correct / len(_HELD_OUT_CASES)
    assert accuracy >= ROUTER_FLOOR, (
        f"router accuracy on the held-out list is {accuracy:.3f}, below the floor "
        f"{ROUTER_FLOOR} predicted in README.md before the result was known")
    print(f"      router accuracy on the held-out list: {accuracy:.3f} "
          f"({correct}/{len(_HELD_OUT_CASES)}), floor {ROUTER_FLOOR}")


# ---------------------------------------------------------------------------
# Step 3: to_sql produces the right SQL for each supported shape
# ---------------------------------------------------------------------------

def check_text_to_sql() -> None:
    import router

    assert isinstance(router.SUPPORTED_SHAPES, (list, tuple)) \
        and len(router.SUPPORTED_SHAPES) >= 5, (
        "SUPPORTED_SHAPES must declare the templated shapes")
    conn = router.load_tables(_toy_corpus())

    scalar_cases = [
        ("What is the total revenue in 2025?", 500000),
        ("What is the average headcount?", 25.0),
        ("How many vendors are there?", 3),
        ("How many vendors have high risk?", 2),
        ("Which region has the most revenue in 2025?", "EMEA"),
        ("Which department has the least headcount?", "Finance"),
    ]
    for question, expected in scalar_cases:
        got = router.answer_structured(question, conn)
        assert _same(got, expected), (
            f"answer_structured({question!r}) returned {got!r}, expected {expected!r}")

    grouped = router.answer_structured(
        "What is the total revenue by region in 2025?", conn)
    assert grouped == [("AMER", 200000), ("EMEA", 300000)], (
        f"total revenue by region in 2025 returned {grouped!r}")

    listed = router.answer_structured("List vendors with risk high", conn)
    assert listed == [("Acme",), ("Sakura",)], (
        f"list high-risk vendors returned {listed!r}")

    prepared = router.to_sql("What is the total revenue in 2025?", conn)
    assert isinstance(prepared, tuple) and len(prepared) == 2, (
        "to_sql must return a (sql, params) pair")
    sql, params = prepared
    assert isinstance(sql, str) and params == (2025,), (
        f"to_sql bound {params!r} for a 2025 question")

    # An unknown column and an unsupported phrasing abstain; they do not raise or guess.
    for question in ("What is the total salary by region in 2025?",
                     "How many widgets are there?",
                     "zzzq nothing at all"):
        assert router.to_sql(question, conn) is None, (
            f"to_sql({question!r}) must return None for an unsupported shape")
        assert router.answer_structured(question, conn) is None, (
            f"answer_structured({question!r}) must abstain with None")
    print("      all supported shapes matched their hand-computed answers; unsupported "
          "shapes abstained")


# ---------------------------------------------------------------------------
# Step 4: end to end — structured through SQL, unstructured through retrieval
# ---------------------------------------------------------------------------

def _route_structured(router, questions, conn, documents):
    """Route each structured question and count the correct SQL answers."""
    correct = 0
    for item in questions:
        tag = router.route_and_answer(item["question"], conn, documents, k=5)
        if tag["route"] == "structured" and _same(tag["answer"], item["expected"]):
            correct += 1
    return correct


def check_end_to_end() -> None:
    import router

    # (a) Self-contained: the router must actually send structured questions to SQL.
    toy = _toy_corpus()
    conn = router.load_tables(toy)
    documents = toy["documents"]
    toy_questions = [
        {"question": "What is the total revenue in 2025?", "expected": 500000},
        {"question": "Which region has the most revenue in 2025?", "expected": "EMEA"},
        {"question": "How many vendors are there?", "expected": 3},
    ]
    correct = _route_structured(router, toy_questions, conn, documents)
    accuracy = correct / len(toy_questions)
    assert accuracy >= STRUCTURED_FLOOR, (
        f"only {correct}/{len(toy_questions)} structured questions were answered through "
        "the SQL route; route_and_answer must not send them to retrieval")

    # (b) The shared evaluation set.
    try:
        corpus_mod, queries_mod, metrics = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the SQL route "
              "on the toy corpus only")
        return

    corpus = corpus_mod.generate_corpus(0)
    conn = router.load_tables(corpus)
    documents = corpus["documents"]
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)

    structured = _eval_structured(corpus)
    correct = _route_structured(router, structured, conn, documents)
    structured_accuracy = correct / len(structured)
    assert structured_accuracy >= STRUCTURED_FLOOR, (
        f"structured accuracy is {structured_accuracy:.3f}, below {STRUCTURED_FLOOR}")

    ranked = {}
    routing = {"structured": 0, "unstructured": 0}
    for query in queries:
        tag = router.route_and_answer(query, conn, documents, k=5)
        routing[tag["route"]] += 1
        ranked[query["qid"]] = tag["documents"]
    result = metrics.evaluate(ranked, queries, k=5)
    assert routing["unstructured"] >= 1, (
        "at least some unstructured questions must be routed to retrieval; got "
        f"{routing}")
    assert result["overall"]["recall@k"] > 0.0, (
        "the retrieval half answered none of the unstructured questions")

    print(f"      seed 0: structured accuracy {structured_accuracy:.3f} "
          f"({correct}/{len(structured)}), routing {routing}")
    print(f"      unstructured retrieval: recall@5={result['overall']['recall@k']:.3f} "
          f"mrr={result['overall']['mrr']:.3f} over {len(queries)} queries")
    for family in FAMILIES:
        stats = result["by_type"].get(family, {})
        print(f"        {family:<11} n={len(query_sets.get(family, [])):>2} "
              f"recall@5={stats.get('recall@k', 0.0):.3f} "
              f"mrr={stats.get('mrr', 0.0):.3f}")
    print("      reported as measured: the router is a brittle keyword template and is "
          "not assumed to be perfect")


# ---------------------------------------------------------------------------
# Step 5: the limit cases — misrouting, abstention, and hostile SQL
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    import router

    toy = _toy_corpus()
    conn = router.load_tables(toy)
    documents = toy["documents"]

    # (a) A structured question phrased without any signal goes to retrieval.
    vague = "How did EMEA do in 2025?"
    assert router.classify(vague) == "unstructured", (
        f"{vague!r} carries no signal; it must be routed to retrieval")
    tag = router.route_and_answer(vague, conn, documents, k=5)
    assert tag["route"] == "unstructured" and tag["answer"] is None, (
        f"{vague!r} should go to retrieval and return no SQL answer, got {tag}")
    vague_route = tag["route"]

    # (a') A prose question that happens to carry a signal goes to SQL and abstains.
    prose = "Which document has the most detail about access control?"
    assert router.classify(prose) == "structured", (
        f"{prose!r} carries the 'most' signal and is misrouted to SQL by construction")
    tag = router.route_and_answer(prose, conn, documents, k=5)
    assert tag["route"] == "structured" and tag["answer"] is None \
        and tag["documents"] == [], (
        f"{prose!r} should be sent to SQL and abstain, got {tag}")

    # (b) A question naming a column that does not exist abstains rather than guessing.
    unknown = "What is the total salary by region in 2025?"
    assert router.to_sql(unknown, conn) is None, (
        "a question about an unknown column must not be templated")
    assert router.answer_structured(unknown, conn) is None, (
        "an unknown column must abstain with None, not return a wrong number")

    # (c) A hostile question carrying SQL is parameterised, not executed.
    before = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    hostile = "What is the total revenue in 2025; DROP TABLE vendors; --"
    prepared = router.to_sql(hostile, conn)
    assert prepared is not None, "the hostile question still has a supported shape"
    sql, params = prepared
    assert "drop" not in sql.lower(), f"the question leaked into the SQL: {sql!r}"
    assert ";" not in sql and "2025" not in sql, (
        f"the question text must not be concatenated into the SQL: {sql!r}")
    assert params == (2025,), f"the only bound value should be the year, got {params!r}"
    assert _same(router.answer_structured(hostile, conn), 500000)
    after = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    assert after == before, "the vendors table was dropped: the statement was executed"

    quoted = "What is the total revenue in region EMEA' OR '1'='1"
    prepared = router.to_sql(quoted, conn)
    assert prepared is not None and "'" not in prepared[0], (
        "the quoted region value must be bound, not interpolated")
    assert all("'" not in str(value) for value in prepared[1]), (
        f"a quote reached the parameters: {prepared[1]!r}")

    print(f"      misroute to retrieval: {vague!r} -> {vague_route} "
          "(the SQL answer is unreachable)")
    print(f"      misroute to SQL: {prose!r} -> structured, abstains")
    print(f"      unknown column {unknown!r} -> None (abstains)")
    print("      hostile SQL was parameterised: "
          f"params={params!r}, vendors rows still {after}")


# ---------------------------------------------------------------------------
# Step 6: abstention — the router does not invent results
# ---------------------------------------------------------------------------

def check_abstention() -> None:
    import router

    toy = _toy_corpus()
    conn = router.load_tables(toy)
    documents = toy["documents"]

    unsupported = "What is the total salary by department?"
    assert router.to_sql(unsupported, conn) is None, (
        "an unsupported structured question must return None from to_sql")
    assert router.answer_structured(unsupported, conn) is None, (
        "an unsupported structured question must abstain with None")
    tag = router.route_and_answer(unsupported, conn, documents, k=5)
    assert tag["answer"] is None, (
        f"the router answered an unsupported question: {tag}")
    assert router.to_sql("What is the median salary of vendors?", conn) is None, (
        "a question the shapes do not cover must abstain")

    try:
        corpus_mod, queries_mod, _metrics = _load_eval_set()
    except FileNotFoundError:
        query = {"text": "zzzq nowhere", "filters": {}, "relevance": {}}
        tag = router.route_and_answer(query, conn, documents, k=5)
        assert tag["route"] == "unstructured" and tag["documents"] == [], (
            f"a no-answer query must abstain through the router, got {tag}")
        print("      shared eval set not available; checked toy abstention only")
        return

    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    conn = router.load_tables(corpus)
    documents = corpus["documents"]
    abstaining = [query for query in query_sets["no_answer"]
                  if not router.retrieve(query, 100, documents)]
    assert abstaining, (
        "expected at least one no-answer query the lexical stage abstains on; if this "
        "fails the shared corpus changed and this check needs updating")
    query = abstaining[0]
    tag = router.route_and_answer(query, conn, documents, k=5)
    assert tag["route"] == "unstructured", (
        f"the no-answer query {query['qid']} carries no SQL signal")
    assert tag["documents"] == [] and tag["answer"] is None, (
        f"the no-answer query {query['qid']} must stay empty through the router, "
        f"got documents={tag['documents']!r} answer={tag['answer']!r}")
    no_answer = query_sets["no_answer"]
    routed_empty = sum(
        1 for item in no_answer
        if router.route_and_answer(item, conn, documents, k=5)["documents"] == [])
    print(f"      abstention through the router: {routed_empty}/{len(no_answer)} no-answer "
          f"queries return nothing (the raw lexical stage abstains on "
          f"{len(abstaining)}/{len(no_answer)}). Recall is 0 by construction because "
          "no-answer relevance is empty; precision is 1.0 by the same construction. "
          "Unsupported structured questions return None.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("router.py", "the corpus tables exist in SQLite with the right shape", check_sqlite_load),
    ("router.py", "the deterministic router and its predicted floor", check_router),
    ("router.py", "to_sql templates each supported shape; unknown columns abstain", check_text_to_sql),
    ("router.py", "structured questions answer through SQL; unstructured go to retrieval", check_end_to_end),
    ("router.py", "the limit cases: misrouting, unknown columns, hostile SQL", check_limit_cases),
    ("router.py", "abstention survives the router", check_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 5 — SQL + vector{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — SQL + vector is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""SQL + vector — RAG project 5 of the from-scratch track.

Half of this project's questions are about **structured facts** — "which region had the
most revenue in 2025?", "how many high-risk vendors are there?" — and half are about
prose documents. A retrieval system that answers only one half is answering the wrong
half of the eval set. This project builds a **router** that sends the structured half to
SQLite (created and populated from the shared eval set's ``tables``) and the rest to the
lexical stage (the sibling ``../bm25`` retriever, exactly the way the sibling stages reuse
it). The returned value is *tagged* with the route it took, so a caller can tell an SQL
answer from a ranked document list.

DESIGN DECISION - the router is a deterministic keyword template, and the LLM variant is
    explicitly deferred.
    ``classify`` looks for a table/column word (``revenue``, ``headcount``, ``vendors``,
    ``department``…) or an aggregation/superlative word (``how many``, ``total``,
    ``average``, ``most``, ``least``…). It needs no model, no training data and no
    network, so the whole project runs under stdlib Python. Cost: it is brittle. A
    structured question phrased without a signal ("How did EMEA do in 2025?") is routed to
    retrieval, and a prose question that happens to contain "most" is routed to SQL; both
    limit cases are constructed and shown by ``check.py`` and ``demo()``. A trained
    classifier or an LLM function-call router is the honest next step and is left out on
    purpose.

DESIGN DECISION - the text-to-SQL here is a fixed set of *shapes*, never an interpolation
    of the question.
    ``SUPPORTED_SHAPES`` enumerates the question forms this project can answer:
    ``count_rows`` (how many vendors), ``count_filter`` (how many high-risk vendors),
    ``total`` / ``average`` (optionally grouped ``by region``/``by department``),
    ``group_max`` / ``group_min`` (which region has the most revenue) and ``list_filter``
    (list vendors with risk high). ``to_sql`` returns ``(sql, params)`` with every value
    bound as a ``?`` placeholder; the question text is *never* concatenated into the SQL
    string, so a hostile question such as
    ``"total revenue in 2025; DROP TABLE vendors; --"`` can only ever change the bound
    year, not the statement. A question naming an unknown column (``salary``) or an
    unknown entity abstains with ``None`` rather than guessing or raising.

DESIGN DECISION - a question the router sends to SQL but that matches no shape abstains
    (``answer_structured`` returns ``None``) instead of falling back to retrieval.
    This keeps the two stages honest and measurable: the checker can tell that the router
    dropped the ball instead of hiding it behind a retriever. Cost: an end-to-end system
    would prefer a fallback; that is a documented future step, not a quiet default.

DESIGN DECISION - SQLite stores the corpus tables with no declared affinity, so integers
    stay integers.
    ``load_tables`` creates one table per ``corpus["tables"]`` entry, in sorted name order,
    so ``SUM(amount_usd)`` is integer arithmetic and two runs produce identical rows. Cost:
    there is no schema typing beyond what the generator wrote, and a caller that needs
    types must declare them.

Run the demo with ``python3 solutions/router.py``. It prints the router's measured
accuracy on a set of structured questions whose expected answers were computed from the
rows, the recall of the shared eval set's unstructured families, and the three limit
cases (a misrouted question each way, an unknown column that abstains, and a hostile SQL
question that is parameterised).
"""
from __future__ import annotations

import math
import os
import pathlib
import re
import sqlite3
import sys
from collections import Counter

if not sys.dont_write_bytecode:
    sys.dont_write_bytecode = True

TOKEN_RE = re.compile(r"[a-z0-9]+")

#: The two routes ``classify`` can return.
ROUTES = ("structured", "unstructured")

#: The question shapes ``to_sql`` knows how to template.
SUPPORTED_SHAPES = (
    "count_rows",
    "count_filter",
    "total",
    "average",
    "group_max",
    "group_min",
    "list_filter",
)

#: The router's signals. A question is structured when it asks for an aggregation
#: (:data:`_AGG_WORDS`), when it asks to list a table on a known word (:data:`_LIST`
#: plus :data:`_TABLE_WORDS`), or when it asks about vendor risk. A bare table word on
#: its own is *not* enough: "vendor onboarding" is a topic in the shared corpus, not a
#: query about the vendors table.
_TABLE_WORDS = (
    "revenue", "revenues", "amount", "amount_usd", "headcount", "headcounts",
    "employee", "employees", "vendor", "vendors", "department", "departments",
    "region", "regions", "quarter", "quarterly", "risk", "risk_level",
)
_AGG_WORDS = (
    "how many", "how much", "number of", "count", "average", "avg", "mean",
    "total", "sum", "combined", "most", "least", "highest", "lowest", "largest",
    "smallest", "maximum", "minimum", "max", "min", "top", "bottom", "fewer",
)
_STRUCTURED_ONLY_WORDS = ("vendor", "vendors", "region", "regions", "department",
                          "departments", "headcount", "revenue", "amount")
_COUNT = ("how many", "how much", "number of", "count")
_TOTAL = ("total", "sum", "combined")
_AVERAGE = ("average", "avg", "mean")
_MAX = ("most", "highest", "largest", "maximum", "greatest", "top")
_MIN = ("least", "lowest", "smallest", "minimum", "fewest", "bottom")
_LIST = ("list", "show", "name", "named")
_RISK_LEVELS = ("low", "medium", "high")

# Fallback retriever constants, identical to the sibling stages' BM25.
K1, B = 1.5, 0.75
_FILTER_KEYS = ("region", "year", "department", "access_level")


# ---------------------------------------------------------------------------
# small text helpers
# ---------------------------------------------------------------------------

def _text(question):
    """The raw question text, whether a query dict or a string."""
    if isinstance(question, dict):
        return str(question.get("text", ""))
    return str(question)


def _has(text, words):
    """True when any of ``words`` occurs in ``text`` on whole words only."""
    lowered = text.lower()
    for word in words:
        pattern = r"(?<![a-z0-9_])" + re.escape(word.lower()) + r"(?![a-z0-9_])"
        if re.search(pattern, lowered):
            return True
    return False


# ---------------------------------------------------------------------------
# loading the corpus tables into SQLite
# ---------------------------------------------------------------------------

def _quote(identifier):
    """Quote a trusted SQL identifier (a corpus table or column name)."""
    return '"' + str(identifier).replace('"', '""') + '"'


def load_tables(corpus, path=":memory:"):
    """Create and populate one SQLite table per ``corpus["tables"]`` entry.

    Each entry is ``{"columns": [...], "rows": [[...], ...]}``; the table is created
    without a declared affinity so an integer cell stays an integer and ``SUM`` is exact,
    then every row is inserted. Tables are created in sorted name order and ``path``
    defaults to an in-memory database, so two calls with the same corpus produce the same
    connection contents. Returns the ``sqlite3.Connection``.
    """
    conn = sqlite3.connect(path)
    for name in sorted(corpus.get("tables", {})):
        spec = corpus["tables"][name]
        columns = list(spec.get("columns", []))
        rows = list(spec.get("rows", []))
        column_sql = ", ".join(_quote(column) for column in columns)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {_quote(name)} ({column_sql})")
        if rows:
            placeholders = ", ".join("?" for _ in columns)
            conn.executemany(
                f"INSERT INTO {_quote(name)} VALUES ({placeholders})", rows)
    conn.commit()
    return conn


def _columns(conn, table):
    """The column names of ``table``, in order."""
    return [row[1] for row in conn.execute(f"PRAGMA table_info({_quote(table)})")]


def _known_values(conn, table, column):
    """The distinct non-null values of a trusted column, sorted."""
    rows = conn.execute(
        f"SELECT DISTINCT {_quote(column)} FROM {_quote(table)} "
        f"WHERE {_quote(column)} IS NOT NULL")
    return sorted({row[0] for row in rows})


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------

def classify(question):
    """Return ``"structured"`` or ``"unstructured"`` for ``question``.

    Structured means one of the aggregation/superlative signals is present, or the
    question asks to list a known table (``_LIST`` + ``_TABLE_WORDS``), or it asks about
    vendor risk. Anything else is unstructured. All signals are keyword tests, so the
    route is deterministic and offline but brittle — see the module docstring's first
    design decision for the cost and the deferred classifier variant.
    """
    text = _text(question)
    if _has(text, _AGG_WORDS):
        return "structured"
    if _has(text, _LIST) and _has(text, _STRUCTURED_ONLY_WORDS):
        return "structured"
    if _has(text, ("risk", "risk_level")) and _has(text, ("vendor", "vendors")):
        return "structured"
    return "unstructured"


# ---------------------------------------------------------------------------
# text to SQL (parameterised templates)
# ---------------------------------------------------------------------------

def _apply(sql, clauses):
    """Append a WHERE clause built from already parameterised ``clauses``."""
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return sql


def _filter_clauses(text, conn, table):
    """The parameterised WHERE clauses named by ``text`` for a trusted ``table``.

    Values are matched against the table's own distinct values and bound as ``?``; the
    question text is never placed into the SQL. Only columns that exist in the table are
    considered.
    """
    columns = _columns(conn, table)
    clauses = []
    params = []
    if "year" in columns:
        match = re.search(r"\b(20\d{2})\b", text)
        if match:
            clauses.append(f"{_quote('year')} = ?")
            params.append(int(match.group(1)))
    if "quarter" in columns:
        match = re.search(r"\bq([1-4])\b", text) or \
            re.search(r"\bquarter\s*([1-4])\b", text)
        if match:
            clauses.append(f"{_quote('quarter')} = ?")
            params.append(int(match.group(1)))
    for column in ("region", "department", "risk_level"):
        if column not in columns:
            continue
        for value in _known_values(conn, table, column):
            if _has(text, [str(value)]):
                clauses.append(f"{_quote(column)} = ?")
                params.append(value)
    return clauses, params


def _metric(text):
    """Resolve the numeric metric a structured question is about, or ``None``.

    Returns ``{"table", "metric", "dimension"}`` for the two numeric tables; an unknown
    metric (``salary``, ``profit``) resolves to ``None`` so the caller abstains.
    """
    if _has(text, ("revenue", "revenues", "amount", "amount_usd")):
        return {"table": "revenue_by_region", "metric": "amount_usd",
                "dimension": "region"}
    if _has(text, ("headcount", "headcounts", "employee", "employees")):
        return {"table": "headcount_by_department", "metric": "headcount",
                "dimension": "department"}
    return None


def to_sql(question, conn):
    """Template ``question`` into ``(sql, params)``, or ``None`` when unsupported.

    Only the shapes in :data:`SUPPORTED_SHAPES` are produced. Every literal taken from the
    question is bound as a ``?`` parameter, and a question naming an unknown column or
    entity returns ``None`` instead of guessing (or raising). The module docstring's
    second design decision records why this is a fixed template set and not an
    interpolator.
    """
    text = _text(question)
    lowered = text.lower()
    if not lowered.strip():
        return None

    metric = _metric(lowered)

    # -- vendors: counts and filtered lists (only when no numeric metric is named) ----
    if metric is None and _has(lowered, ("vendor", "vendors")):
        clauses, params = _filter_clauses(lowered, conn, "vendors")
        if _has(lowered, _COUNT):
            sql = _apply(f"SELECT COUNT(*) FROM {_quote('vendors')}", clauses)
            return sql, tuple(params)
        if _has(lowered, ("risk", "risk_level")) or _has(lowered, _LIST):
            sql = _apply(f"SELECT {_quote('name')} FROM {_quote('vendors')}", clauses)
            sql += f" ORDER BY {_quote('name')}"
            return sql, tuple(params)
        return None

    # -- counts of dimensions, when no numeric metric is named -------------------------
    if metric is None and _has(lowered, _COUNT):
        if _has(lowered, ("region", "regions")):
            return (f"SELECT COUNT(DISTINCT {_quote('region')}) "
                    f"FROM {_quote('revenue_by_region')}"), ()
        if _has(lowered, ("department", "departments")):
            return (f"SELECT COUNT(DISTINCT {_quote('department')}) "
                    f"FROM {_quote('headcount_by_department')}"), ()
        return None

    if metric is None:
        return None
    table = metric["table"]
    column = metric["metric"]
    dimension = metric["dimension"]
    clauses, params = _filter_clauses(lowered, conn, table)

    # -- superlatives: which <dimension> has the most / least ------------------
    order = None
    if _has(lowered, _MAX):
        order = "DESC"
    elif _has(lowered, _MIN):
        order = "ASC"
    if order is not None:
        sql = _apply(f"SELECT {_quote(dimension)} FROM {_quote(table)}", clauses)
        sql += (f" GROUP BY {_quote(dimension)}"
                f" ORDER BY SUM({_quote(column)}) {order} LIMIT 1")
        return sql, tuple(params)

    # -- totals and averages, optionally grouped -------------------------------
    if _has(lowered, _TOTAL):
        function = "SUM"
    elif _has(lowered, _AVERAGE):
        function = "AVG"
    else:
        return None
    grouped = _has(lowered, ("by", "per")) and _has(
        lowered, (dimension, dimension + "s"))
    if grouped:
        sql = (f"SELECT {_quote(dimension)}, {function}({_quote(column)}) "
               f"FROM {_quote(table)}")
        sql = _apply(sql, clauses)
        sql += f" GROUP BY {_quote(dimension)} ORDER BY {_quote(dimension)}"
    else:
        sql = f"SELECT {function}({_quote(column)}) FROM {_quote(table)}"
        sql = _apply(sql, clauses)
    return sql, tuple(params)


def answer_structured(question, conn):
    """Run the templated SQL for ``question`` and return its answer, or ``None``.

    A scalar aggregate is returned bare; a grouped query is returned as a list of tuples.
    An unsupported question (``to_sql`` returned ``None``) or a query matching zero rows
    abstains with ``None``. An empty ``COUNT`` legitimately returns ``0``.
    """
    prepared = to_sql(question, conn)
    if prepared is None:
        return None
    sql, params = prepared
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return None
    if len(rows) == 1 and len(rows[0]) == 1:
        return rows[0][0]
    return [tuple(row) for row in rows]


# ---------------------------------------------------------------------------
# the lexical stage (the sibling ../bm25, with a self-contained fallback)
# ---------------------------------------------------------------------------

_BM25_CACHE = [None, False]


def _try_import_bm25():
    """Import the sibling ``../bm25`` solution, or return ``None`` when absent."""
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


def _local_retrieve(question, k, documents):
    """Scaffolding: a self-contained Okapi BM25 ranker (the sibling's stand-in)."""
    if isinstance(question, dict):
        text = question.get("text", "")
        filters = question.get("filters") or {}
    else:
        text, filters = str(question), {}
    terms = TOKEN_RE.findall(str(text).lower())
    if not terms:
        return []
    n_docs = len(documents)
    term_counts = []
    document_frequency = Counter()
    for document in documents:
        counts = Counter(TOKEN_RE.findall(
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


def retrieve(question, k, documents):
    """The lexical stage: up to ``k`` best-first doc_ids, ``[]`` to abstain.

    Uses the sibling ``../bm25`` (metadata filters and the empty-result abstention
    included); if the sibling is not in this tree it falls back to a self-contained BM25
    over the same tokens, so the mutation harness can run in a bare directory.
    """
    bm25 = _try_import_bm25()
    if bm25 is not None:
        return bm25.BM25Retriever(documents).retrieve(question, k=k)
    return _local_retrieve(question, k, documents)


# ---------------------------------------------------------------------------
# the router
# ---------------------------------------------------------------------------

def route_and_answer(question, conn, documents, k=5):
    """Answer ``question`` through the route ``classify`` chose, tagged with the route.

    Structured questions go to SQLite and the result is
    ``{"route": "structured", "answer": <scalar/rows/None>, "documents": [], ...}``;
    unstructured questions go to the lexical stage and the result is
    ``{"route": "unstructured", "answer": None, "documents": [...]}``. The tag lets a
    caller evaluate the two halves separately, which is what makes the router's mistakes
    visible instead of invisible.
    """
    route = classify(question)
    if route == "structured":
        prepared = to_sql(question, conn)
        return {
            "route": "structured",
            "answer": answer_structured(question, conn),
            "documents": [],
            "sql": prepared[0] if prepared is not None else None,
            "params": prepared[1] if prepared is not None else None,
        }
    return {
        "route": "unstructured",
        "answer": None,
        "documents": retrieve(question, k, documents),
        "sql": None,
        "params": None,
    }


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
        here.parent / "eval-set" / "solutions",
        here.parent.parent / "eval-set" / "solutions",
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


def _flatten_queries(query_sets):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(query_sets, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [query for family in order for query in query_sets.get(family, [])]
    return list(query_sets)


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

def evaluate(structured_questions, corpus, query_sets=None, k=5):
    """Score the router's two halves honestly.

    ``structured_questions`` is a list of ``{"question", "expected"}`` items (``expected``
    is the value computed from the rows; an unsupported question has ``expected=None`` and
    is correct only when the router abstains). ``corpus`` is the shared eval set's
    ``generate_corpus(seed)`` and ``query_sets`` is ``queries.build_query_sets(corpus)`` or
    a flat query list. Returns the structured accuracy, the per-question records, the
    routing counts, and — when ``query_sets`` is given — the shared retrieval metrics over
    the questions the router sent to retrieval. The two halves are reported separately and
    neither is assumed to be perfect.
    """
    conn = load_tables(corpus)
    documents = corpus["documents"]
    records = []
    correct = 0
    for item in structured_questions:
        question = item["question"]
        expected = item.get("expected")
        got = answer_structured(question, conn)
        ok = _same(got, expected)
        correct += 1 if ok else 0
        records.append({
            "question": question, "expected": expected, "got": got,
            "correct": ok, "route": classify(question),
        })
    result = {
        "k": k,
        "structured_accuracy": (correct / len(structured_questions)
                                if structured_questions else 0.0),
        "structured": records,
        "routing": {"structured": 0, "unstructured": 0},
        "retrieval": None,
        "ranked": {},
    }
    if query_sets is None:
        conn.close()
        return result

    metrics = _import_metrics()
    queries = _flatten_queries(query_sets)
    ranked = {}
    for query in queries:
        tag = route_and_answer(query, conn, documents, k=k)
        result["routing"][tag["route"]] += 1
        ranked[query["qid"]] = tag["documents"]
    result["ranked"] = ranked
    result["retrieval"] = metrics.evaluate(ranked, queries, k=k)
    conn.close()
    return result


def _same(got, expected):
    """Structural equality with a float tolerance for AVG-style answers."""
    if isinstance(got, list) and isinstance(expected, (list, tuple)):
        if len(got) != len(expected):
            return False
        return all(_same(_as_tuple(a), _as_tuple(b))
                   for a, b in zip(got, expected))
    if isinstance(got, (int, float)) and isinstance(expected, (int, float)) \
            and not isinstance(got, bool) and not isinstance(expected, bool):
        return abs(float(got) - float(expected)) < 1e-9
    return got == expected


def _as_tuple(value):
    return tuple(value) if isinstance(value, (list, tuple)) else value


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def _demo_structured_questions(corpus, conn):
    """Hand-written structured questions with expected answers computed from the rows.

    The oracle is pure Python over ``corpus["tables"]``, independent of the SQL under
    test: a wrong aggregate or a wrong ORDER BY shows up as a mismatch.
    """
    revenue = corpus["tables"]["revenue_by_region"]
    headcount = corpus["tables"]["headcount_by_department"]
    vendors = corpus["tables"]["vendors"]
    rows = revenue["rows"]

    total_2025 = sum(row[3] for row in rows if row[1] == 2025)
    by_region = {}
    for row in rows:
        if row[1] == 2025:
            by_region[row[0]] = by_region.get(row[0], 0) + row[3]
    top_region = sorted(by_region, key=lambda name: (-by_region[name], name))[0]
    grouped = sorted((name, by_region[name]) for name in by_region)
    head_rows = headcount["rows"]
    average_head = sum(row[2] for row in head_rows) / len(head_rows)
    low_dept = sorted(head_rows, key=lambda row: (row[2], row[0]))[0][0]
    high_risk = sorted(row[1] for row in vendors["rows"]
                       if row[3] == "high")

    return [
        {"question": "What is the total revenue in 2025?", "expected": total_2025},
        {"question": "What is the average headcount in 2025?",
         "expected": average_head},
        {"question": "How many vendors are there?",
         "expected": len(vendors["rows"])},
        {"question": "How many vendors have high risk?",
         "expected": len(high_risk)},
        {"question": "List vendors with risk high",
         "expected": [(name,) for name in high_risk]},
        {"question": "Which region has the most revenue in 2025?",
         "expected": top_region},
        {"question": "Which department has the least headcount?",
         "expected": low_dept},
        {"question": "What is the total revenue by region in 2025?",
         "expected": grouped},
        {"question": "What is the total salary by region in 2025?", "expected": None},
    ]


def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print the measured router accuracy, retrieval recall and the limit cases."""
    sys.dont_write_bytecode = True
    eval_set = _eval_set_solutions()
    if str(eval_set) not in sys.path:
        sys.path.insert(0, str(eval_set))
    from corpus import generate_corpus
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(0)
    conn = load_tables(corpus)
    questions = _demo_structured_questions(corpus, conn)
    query_sets = build_query_sets(corpus)
    result = evaluate(questions, corpus, query_sets, k=5)

    print(f"corpus: {len(corpus['documents'])} documents, "
          f"{len(corpus['tables'])} tables "
          f"({', '.join(sorted(corpus['tables']))})")
    print(f"router: {len(SUPPORTED_SHAPES)} SQL shapes, deterministic keyword signals; "
          "no model, no network")
    print(f"structured accuracy: {result['structured_accuracy']:.3f} "
          f"({sum(1 for r in result['structured'] if r['correct'])}/"
          f"{len(result['structured'])})")
    for record in result["structured"]:
        mark = "ok " if record["correct"] else "MISS"
        print(f"  {mark} [{record['route']:>12}] {record['question']:<45} "
              f"got={record['got']!r} expected={record['expected']!r}")

    retrieval = result["retrieval"]
    print("\nunstructured families routed to retrieval:")
    families = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
    for family in families:
        stats = retrieval["by_type"].get(family, {})
        print(f"  {family:<11} n={len(query_sets.get(family, [])):>2} "
              f"recall@5={stats.get('recall@k', 0.0):.3f} "
              f"mrr={stats.get('mrr', 0.0):.3f}")
    total_queries = sum(len(query_sets.get(family, [])) for family in families)
    print(f"  {'overall':<11} n={total_queries:>2} "
          f"recall@5={retrieval['overall'].get('recall@k', 0.0):.3f} "
          f"mrr={retrieval['overall'].get('mrr', 0.0):.3f}")
    print(f"routing: {result['routing']}")

    print("\nlimit case 1a - a structured question phrased without a signal:")
    vague = "How did EMEA do in 2025?"
    tag = route_and_answer(vague, conn, corpus["documents"], k=5)
    print(f"  {vague!r} -> route={tag['route']}, answer={tag['answer']!r} "
          f"(retrieval, so the SQL answer is unreachable)")

    print("\nlimit case 1b - a prose question that happens to carry a signal:")
    prose = "Which document has the most detail about access control?"
    tag = route_and_answer(prose, conn, corpus["documents"], k=5)
    print(f"  {prose!r} -> route={tag['route']}, answer={tag['answer']!r} "
          f"(SQL, then abstains instead of retrieving)")

    print("\nlimit case 2 - a question naming a column that does not exist:")
    unknown = "What is the total salary by region in 2025?"
    tag = route_and_answer(unknown, conn, corpus["documents"], k=5)
    print(f"  {unknown!r} -> route={tag['route']}, answer={tag['answer']!r}, "
          "abstains rather than guessing")

    print("\nlimit case 3 - a hostile question carrying SQL is parameterised:")
    hostile = "What is the total revenue in 2025; DROP TABLE vendors; --"
    tag = route_and_answer(hostile, conn, corpus["documents"], k=5)
    alive = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    print(f"  {hostile!r}")
    print(f"  -> sql={tag['sql']!r} params={tag['params']!r} answer={tag['answer']!r}")
    print(f"  -> vendors table still has {alive} rows; the statement was not executed")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    demo()

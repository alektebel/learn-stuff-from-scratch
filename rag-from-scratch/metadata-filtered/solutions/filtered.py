"""Metadata-filtered RAG — project 2 of the RAG from-scratch track.

Project 2 is the *filter* stage: retrieval where the query carries structured
constraints (department, year, region, access level, author, superseded) and the
answer must be drawn only from documents that satisfy them. The corpus metadata
lives in SQLite (stdlib ``sqlite3``) with a secondary index per filterable column,
and the project contrasts three execution strategies on the very same shared
evaluation set the other stages use (``../eval-set``):

  * ``pre_filter``     — push the metadata predicate into SQL (using the indexes),
                         then rank only the surviving candidates.
  * ``post_filter``    — the anti-pattern: rank the whole corpus, then drop the
                         non-matching rows. Under a selective filter it silently
                         returns fewer than ``k`` results even though matching
                         documents exist.
  * ``filter_aware``   — keep the index navigable under a selective predicate by
                         driving the scan with the single most selective indexed
                         predicate and applying the remaining predicates over that
                         (much smaller) candidate set.

DESIGN DECISION - the metadata store is SQLite with one secondary index per
    filterable column.
    The point of the project is the *plan*: a filter is only cheap if an index can
    be chosen for it. ``build_db`` issues ``CREATE INDEX`` for department, date,
    author, region, access_level and superseded so that ``pre_filter``/``selectivity``
    can be answered by an index seek rather than a scan. Cost: six small extra
    indexes; at this scale the planner may still prefer a scan, which is itself part
    of what the project measures.

DESIGN DECISION - the lexical scorer is implemented here (BM25) rather than importing
    the sibling ``bm25`` module.
    The filter stage must be measurable on its own, in a tree where only
    ``{metadata-filtered,eval-set}`` exist, so it owns a small, self-contained Okapi
    BM25 (k1=1.5, b=0.75). The statistics (document frequencies, average length) are
    computed once over the *whole* corpus, so all three strategies rank with the same
    scoring function and differ only in which documents reach the scorer. Cost: a
    little duplication with ``bm25/``; kept minimal on purpose.

DESIGN DECISION - filters translate to SQL predicates, with ``year`` compared as the
    four-character date prefix ``substr(date,1,4)``.
    The eval set stores ``date`` as an ISO ``YYYY-MM-DD`` string and the query's
    ``year`` as an integer. Comparing the prefix is exact and rejects a wrong-year
    document outright; comparing a substring, or comparing fewer digits, would let
    neighbouring years through (that is the planted bug the checker looks for). Cost:
    ``substr`` cannot use the index on ``date``; a range predicate could, and is left
    as an optimisation exercise.

DESIGN DECISION - ``filter_aware`` chooses the driving predicate by its measured
    selectivity and re-checks the remaining predicates in Python.
    When several predicates are ANDed, the planner can only navigate one index, so
    driving on the rarest predicate shrinks the candidate set fastest; the other
    predicates are then cheap to test on that small set. It returns the same documents
    and the same order as ``pre_filter`` — the difference is the plan, not the answer.
    Cost: one extra ``COUNT(*)`` per predicate to estimate selectivity.

DESIGN DECISION - ties break by ``doc_id`` ascending and only positive scores are
    returned, so every strategy is deterministic and "no lexical match" is the empty
    list (the same abstention rule the other stages use).
    Reproducible output is required by the checks and the metrics. Cost: a full sort
    of the scored candidates.

Run the demo, which prints the honest per-strategy numbers on the shared eval set and
the selective-filter shortfall: ``python3 solutions/filtered.py``.
"""
from __future__ import annotations

import math
import os
import pathlib
import re
import sqlite3
import sys
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Columns that a query may filter on, and for which ``build_db`` indexes the table.
FILTERABLE = (
    "department",
    "date",
    "author",
    "region",
    "access_level",
    "superseded",
)

K1 = 1.5
B = 0.75


def tokenize(text):
    """Lower-cased alphanumeric tokens, in order, punctuation dropped.

    Identical to the sibling stages' tokeniser so the filter stage is measured on
    documents made of exactly the same tokens.
    """
    return TOKEN_RE.findall(text.lower())


# ---------------------------------------------------------------------------
# The eval set and the document shape
# ---------------------------------------------------------------------------

def _eval_set_solutions():
    """Locate the shared eval set's runnable fixture (its ``solutions/`` dir)."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent / "eval-set" / "solutions",          # .../metadata-filtered/solutions/
        here.parent.parent / "eval-set" / "solutions",   # .../metadata-filtered/
        pathlib.Path(os.environ["RAG_EVAL_SET"]) / "solutions"
        if os.environ.get("RAG_EVAL_SET") else None,
    ]
    for path in candidates:
        if path is not None and (path / "metrics.py").is_file():
            return path
    raise FileNotFoundError(
        "cannot find the shared eval set at ../eval-set/solutions relative to "
        f"{here}: run from inside rag-from-scratch/ or copy check.py next to the "
        "eval set.")


def load_documents(seed=0):
    """Load the eval set's documents (text + metadata) and return them as a list.

    Document shape: a dict with

      * ``doc_id``       stable string id
      * ``title``        short text
      * ``body``         longer text; the scorer reads ``title + " " + body``
      * ``date``         ISO ``YYYY-MM-DD`` string (``year`` filters read its prefix)
      * ``department``, ``author``, ``region``, ``access_level``   strings
      * ``superseded``   bool (stored as 0/1 in SQLite)

    Missing metadata keys become empty/zero so a heterogeneous corpus still loads.
    """
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import corpus

    data = corpus.generate_corpus(seed)
    docs = data["documents"] if isinstance(data, dict) else data
    out = []
    for doc in docs:
        normalized = dict(doc)
        if "superseded" not in normalized:
            normalized["superseded"] = normalized.get("superseded_by") is not None
        out.append(normalized)
    return out


def _doc_text(doc):
    return (doc.get("title") or "") + " " + (doc.get("body") or "")


def _row_values(doc):
    """The tuple stored in the ``documents`` table, in ``_COLUMNS`` order."""
    return (
        str(doc.get("doc_id", "")),
        str(doc.get("title", "")),
        str(doc.get("body", "")),
        str(doc.get("date", "")),
        str(doc.get("department", "")),
        str(doc.get("author", "")),
        str(doc.get("region", "")),
        str(doc.get("access_level", "")),
        1 if doc.get("superseded") else 0,
    )


_COLUMNS = ("doc_id", "title", "body", "date", "department", "author",
            "region", "access_level", "superseded")


def build_db(docs, path=":memory:"):
    """Create the SQLite document store and return the connection.

    The table mirrors ``_COLUMNS`` and carries a secondary index on every
    filterable metadata column (``FILTERABLE``), so a pre-filter can be answered by
    an index rather than a full scan. ``path`` defaults to an in-memory database;
    pass a filename to persist it.
    """
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE documents ("
        "doc_id TEXT PRIMARY KEY, title TEXT, body TEXT, date TEXT, "
        "department TEXT, author TEXT, region TEXT, access_level TEXT, "
        "superseded INTEGER)")
    conn.executemany(
        "INSERT INTO documents (doc_id, title, body, date, department, author, "
        "region, access_level, superseded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [_row_values(doc) for doc in docs])
    for column in FILTERABLE:
        conn.execute(
            f"CREATE INDEX idx_documents_{column} ON documents({column})")
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Filters -> SQL
# ---------------------------------------------------------------------------

def _where_clause(filters):
    """Return ``(sql, params)`` for a filter dict, or ``("1=1", [])`` when empty.

    ``year`` matches the four-character date prefix; ``superseded`` is stored as an
    integer; every other key is an equality on a whitelisted column.
    """
    clauses = []
    params = []
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if key == "year":
            clauses.append("substr(date, 1, 4) = ?")
            params.append(str(value))
        elif key == "superseded":
            clauses.append("superseded = ?")
            params.append(1 if value else 0)
        elif key in FILTERABLE:
            clauses.append(f"{key} = ?")
            params.append(value)
    if not clauses:
        return "1=1", []
    return " AND ".join(clauses), params


def selectivity(conn, filters):
    """Fraction of the corpus that ``filters`` matches (0.0 .. 1.0)."""
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    if not total:
        return 0.0
    where, params = _where_clause(filters)
    matched = conn.execute(
        f"SELECT COUNT(*) FROM documents WHERE {where}", params).fetchone()[0]
    return matched / total


# ---------------------------------------------------------------------------
# BM25 scoring (self-contained)
# ---------------------------------------------------------------------------

def _corpus_stats(docs):
    """Per-document term counts, lengths, document frequencies and averages."""
    doc_tokens = {}
    lengths = {}
    df = Counter()
    for doc in docs:
        counts = Counter(tokenize(_doc_text(doc)))
        doc_tokens[doc["doc_id"]] = counts
        lengths[doc["doc_id"]] = sum(counts.values())
        for term in counts:
            df[term] += 1
    n_docs = len(docs)
    avgdl = sum(lengths.values()) / n_docs if n_docs else 0.0
    return doc_tokens, lengths, df, n_docs, avgdl


def _bm25(terms, counts, length, df, n_docs, avgdl):
    """Okapi BM25 for one document against a query's token set."""
    if not terms or avgdl == 0.0:
        return 0.0
    score = 0.0
    for term in set(terms):
        frequency = counts.get(term, 0)
        if not frequency:
            continue
        idf = math.log(1.0 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
        score += idf * (frequency * (K1 + 1.0)) / (
            frequency + K1 * (1.0 - B + B * length / avgdl))
    return score


# ---------------------------------------------------------------------------
# The retriever
# ---------------------------------------------------------------------------

class FilteredRetriever:
    """Metadata-filtered lexical retrieval with three execution strategies.

    All three take ``(query, k=10, filters=None)`` and return a list of ``doc_id``
    strings, best first, containing only documents that satisfy ``filters``.
    ``query`` is either the eval set's query dict (``text`` and ``filters``) or a raw
    string; an explicit ``filters`` argument overrides the query's own.
    """

    def __init__(self, docs, conn=None):
        self.documents = list(docs)
        self.by_id = {doc["doc_id"]: doc for doc in self.documents}
        self.conn = conn if conn is not None else build_db(self.documents)
        (self.doc_tokens, self.lengths, self.df, self.n_docs,
         self.avgdl) = _corpus_stats(self.documents)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _split(query, filters):
        if isinstance(query, dict):
            text = query.get("text", "")
            if filters is None:
                filters = query.get("filters", {})
        else:
            text = query
        return text, (filters or {})

    def _passes(self, doc_id, filters):
        """Re-test a document against ``filters`` in Python (used by filter_aware)."""
        doc = self.by_id.get(doc_id)
        if doc is None:
            return False
        for key, value in (filters or {}).items():
            if value is None:
                continue
            if key == "year":
                if str(doc.get("date", ""))[:4] != str(value):
                    return False
            elif key == "superseded":
                if (1 if doc.get("superseded") else 0) != (1 if value else 0):
                    return False
            elif key in FILTERABLE:
                if doc.get(key) != value:
                    return False
        return True

    def _score(self, terms, doc_id):
        return _bm25(terms, self.doc_tokens[doc_id], self.lengths[doc_id],
                     self.df, self.n_docs, self.avgdl)

    def _rank(self, terms, doc_ids):
        scored = []
        for doc_id in doc_ids:
            score = self._score(terms, doc_id)
            if score > 0.0:
                scored.append((score, doc_id))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [doc_id for _score, doc_id in scored]

    @staticmethod
    def _top(ranked, k):
        return ranked if k is None or k < 0 else ranked[:k]

    # -- the three strategies ---------------------------------------------

    def pre_filter(self, query, k=10, filters=None):
        """Filter in SQL first (using the indexes), then rank the survivors."""
        text, filters = self._split(query, filters)
        terms = tokenize(text)
        if not terms:
            return self._top([], k)
        where, params = _where_clause(filters)
        rows = self.conn.execute(
            f"SELECT doc_id FROM documents WHERE {where}", params).fetchall()
        return self._top(self._rank(terms, [row[0] for row in rows]), k)

    def post_filter(self, query, k=10, filters=None):
        """Rank the whole corpus, take the top ``k``, then drop non-matching docs.

        This is the anti-pattern: a matching document that ranks below the global
        top-``k`` window is never seen, so under a selective filter the result can be
        shorter than ``k`` (even empty) although matching documents exist.
        """
        text, filters = self._split(query, filters)
        terms = tokenize(text)
        if not terms:
            return self._top([], k)
        ranked = self._rank(terms, [doc["doc_id"] for doc in self.documents])
        window = self._top(ranked, k)
        return [doc_id for doc_id in window if self._passes(doc_id, filters)]

    def filter_aware(self, query, k=10, filters=None):
        """Navigate the most selective indexed predicate, then rank the survivors.

        Unlike ``pre_filter`` (which ANDs every predicate and lets SQLite choose the
        plan), this drives the scan with the single predicate measured to match
        fewest rows and tests the remaining predicates over that small candidate set
        in Python. It returns the same documents and order as ``pre_filter``; only
        the plan differs.
        """
        text, filters = self._split(query, filters)
        terms = tokenize(text)
        if not terms:
            return self._top([], k)

        predicates = []
        for key, value in (filters or {}).items():
            if value is None:
                continue
            where, params = _where_clause({key: value})
            if where == "1=1":
                continue
            predicates.append((where, params,
                               self.conn.execute(
                                   f"SELECT COUNT(*) FROM documents WHERE {where}",
                                   params).fetchone()[0]))
        if not predicates:
            candidates = [doc["doc_id"] for doc in self.documents]
        else:
            where, params, _count = min(predicates, key=lambda item: item[2])
            candidates = [row[0] for row in self.conn.execute(
                f"SELECT doc_id FROM documents WHERE {where}", params).fetchall()]
            if len(predicates) > 1:
                candidates = [doc_id for doc_id in candidates
                              if self._passes(doc_id, filters)]
        return self._top(self._rank(terms, candidates), k)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _flatten_queries(queries):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(queries, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [q for family in order for q in queries.get(family, [])]
    return list(queries)


def _import_metrics():
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import metrics

    return metrics


def evaluate(corpus, queries, k=10):
    """Score every query with all three strategies on one retriever.

    ``corpus`` is ``corpus.generate_corpus(seed)`` (or a document list); ``queries``
    is the family dict or a flat list. Returns::

        {"pre_filter":  metrics_dict,
         "post_filter": metrics_dict,
         "filter_aware": metrics_dict,
         "mean_results": {"pre_filter": float, ...},
         "selectivity": {"filters": ..., "value": float, ...}}

    where each ``metrics_dict`` is exactly ``metrics.evaluate(...)`` (the same shape
    the sibling stages return: ``overall``, ``by_type``, ``per_query``,
    ``abstention``). ``mean_results`` is the mean number of results each strategy
    returned for the ``filtered`` family — the number that exposes the post-filter
    shortfall.
    """
    metrics = _import_metrics()
    docs = corpus["documents"] if isinstance(corpus, dict) else corpus
    flat = _flatten_queries(queries)
    retriever = FilteredRetriever(docs)

    strategies = ("pre_filter", "post_filter", "filter_aware")
    results = {}
    for name in strategies:
        ranked = {}
        for query in flat:
            ranked[query["qid"]] = getattr(retriever, name)(
                query, k=k, filters=query.get("filters", {}))
        results[name] = metrics.evaluate(ranked, flat, k=k)

    filtered = [q for q in flat if q.get("type") == "filtered"]
    mean_results = {}
    for name in strategies:
        counts = [len(getattr(retriever, name)(
            q, k=k, filters=q.get("filters", {}))) for q in filtered]
        mean_results[name] = sum(counts) / len(counts) if counts else 0.0

    return {
        "pre_filter": results["pre_filter"],
        "post_filter": results["post_filter"],
        "filter_aware": results["filter_aware"],
        "mean_results": mean_results,
        "n_filtered_queries": len(filtered),
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print the honest per-strategy numbers and the selective-filter shortfall."""
    docs = load_documents(0)
    conn = build_db(docs)
    retriever = FilteredRetriever(docs, conn=conn)

    # Import the eval set's generator/metrics directly for the demo.
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    from corpus import generate_corpus  # noqa: E402
    from queries import all_queries, build_query_sets  # noqa: E402
    import metrics  # noqa: E402

    corpus = generate_corpus(0)
    query_sets = build_query_sets(corpus)
    queries = all_queries(query_sets)

    strategies = ("pre_filter", "post_filter", "filter_aware")
    print(f"seed 0, {len(docs)} documents, {len(queries)} queries")
    print(f"{'strategy':<14}{'filtered r@10':>13}{'filtered MRR':>13}"
          f"{'filtered nDCG':>14}{'mean results':>14}")
    for name in strategies:
        ranked = {q["qid"]: getattr(retriever, name)(
            q, k=10, filters=q.get("filters", {})) for q in queries}
        result = metrics.evaluate(ranked, queries, k=10)
        fam = result["by_type"].get("filtered", {})
        filtered = [q for q in queries if q.get("type") == "filtered"]
        mean = (sum(len(ranked[q["qid"]]) for q in filtered) / len(filtered)
                if filtered else 0.0)
        print(f"{name:<14}{fam.get('recall@k', 0.0):>13.3f}"
              f"{fam.get('mrr', 0.0):>13.3f}{fam.get('ndcg@k', 0.0):>14.3f}"
              f"{mean:>14.2f}")

    print("\nselective-filter shortfall (a filter matching a tiny fraction):")
    best = None
    for doc in docs:
        candidate = {
            "department": doc.get("department"),
            "region": doc.get("region"),
            "access_level": doc.get("access_level"),
            "year": int(str(doc.get("date", "0000"))[:4]),
        }
        matches = [d for d in docs if retriever._passes(d["doc_id"], candidate)]
        if matches and (best is None or len(matches) < len(best[1])):
            best = (candidate, matches)
    if best is not None:
        filters, matches = best
        sel = selectivity(conn, filters)
        frequency = Counter()
        for doc in docs:
            frequency.update(tokenize(_doc_text(doc)))
        probes = [frequency.most_common(1)[0][0]] + tokenize(_doc_text(matches[0]))
        query_text = next(
            (term for term in probes
             if retriever.pre_filter(term, k=10, filters=filters)
             and len(retriever.post_filter(term, k=10, filters=filters))
             < len(retriever.pre_filter(term, k=10, filters=filters))),
            matches[0].get("title", ""))
        print(f"  filter {filters!r}: {len(matches)} of {len(docs)} documents "
              f"(selectivity {sel:.4f}), query {query_text!r}")
        for name in strategies:
            got = getattr(retriever, name)(query_text, k=10, filters=filters)
            print(f"  {name:<14} returned {len(got):>2}: {got}")
    else:
        print("  (no selective filter found in this corpus)")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    demo()

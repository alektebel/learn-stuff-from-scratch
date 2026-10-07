"""Okapi BM25 retrieval — the first stage of RAG project 1 (hybrid search).

Implements the ranking function of Robertson & Zaragoza, *The Probabilistic Relevance
Framework: BM25 and Beyond* (2009), section 3: a bag-of-words retriever whose term
frequency saturates through `k1` and whose score is length-normalised through `b`, over
the smoothed inverse document frequency

    idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5)).

The module is wired to the shared step-0 evaluation set (`../eval-set`): `evaluate_bm25`
and `demo` import its `corpus`, `queries`, `metrics` and `baseline` modules and report the
same metrics, so BM25 can be compared with the lexical floor it has to beat.

DESIGN DECISION - tokenisation is lowercase alphanumeric, with no stemming and no
    stopword list.
    Keep it simple and deterministic: `re.findall(r"[a-z0-9]+", text.lower())`. The
    baseline strips stopwords and one-character tokens; BM25 does not, which is exactly
    why BM25 answers some no-answer queries (a generic word like "policy" is a token
    here). That difference is honest and visible in the metrics, not hidden by a
    hand-tuned gate. Cost: the code tokens that make lexical queries easy are also split
    on hyphens ("POL-ENG-2023-001" -> pol/eng/2023/001), which is the price of a simple
    regex; it still separates the exact policy code from other documents.

DESIGN DECISION - the index is a term -> {doc_id: term_frequency} postings map plus per
    document lengths and their average.
    A term-keyed postings map is what makes scoring touch only the documents that match
    a query term instead of the whole corpus, and it is the structure the later inverted
    index (project 3) builds on. Cost: `bm25_score` must handle a document that matches
    none of the query terms by returning 0.0, and the index carries two side tables.

DESIGN DECISION - idf uses the smoothed BM25 form, never log(N / df).
    The +0.5 smoothing keeps the idf finite and positive for a term that occurs in every
    document (df = N), so a very common term contributes a small positive amount rather
    than dropping out or going negative. Cost: common terms still add a little noise; the
    saturation and the length normalisation are what suppress them.

DESIGN DECISION - metadata filters are applied before scoring, and abstention is "the
    result is empty".
    This mirrors the eval set's baseline: pre-filtering keeps the comparison honest when
    a region/year filter is selective, and an empty ranked list is the weakest defensible
    abstention rule (no matching term or no document passing the filter). Cost: like the
    baseline, it is not calibrated and will abstain on nothing answerable here; a learned
    threshold is project 7's subject.

DESIGN DECISION - ties break by doc_id ascending.
    Deterministic ordering is required for reproducible eval runs and for check.py. Cost:
    ties are broken without regard to relevance, which is what MRR is there to expose.

Run the demo to print a measurement: `python3 solutions/bm25.py`.
"""
from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")

_FILTER_KEYS = ("region", "year", "department", "access_level")


def tokenize(text):
    """Lower-cased alphanumeric tokens, in order, with punctuation dropped."""
    # TODO: Lower-case the text and return `TOKEN_RE.findall(...)`: [a-z0-9]+ tokens in order. No stemming, no stopword list — it must be deterministic.
    raise NotImplementedError("tokenize")


def build_inverted_index(docs):
    """Build the postings map for an iterable of documents.

    Returns a dict with three keys:
      * ``postings``   term -> {doc_id: term_frequency}
      * ``doc_lengths`` doc_id -> number of tokens in title + body
      * ``avg_length``  mean document length (0.0 for an empty corpus)
    """
    # TODO: For each doc, tokenize title + body, store its length, and for each term store its frequency under postings[term][doc_id]. Return the postings map, the doc_lengths map and the mean length.
    raise NotImplementedError("build_inverted_index")


def idf(index, term, n_docs):
    """Smoothed BM25 inverse document frequency of `term` over `n_docs` documents."""
    # TODO: df = number of documents containing the term; return math.log(1 + (n_docs - df + 0.5) / (df + 0.5)). The +0.5 smoothing keeps a term that occurs in every document from driving the score to zero or below.
    raise NotImplementedError("idf")


def bm25_score(index, query, doc_id, k1=1.5, b=0.75):
    """Okapi BM25 score of `doc_id` for the query text `query`.

    Sums over the query's tokens. A token the document does not contain contributes
    nothing (its tf is zero), so a document matching no token scores exactly 0.0 and is
    dropped by the retriever — that is the abstention rule.
    """
    # TODO: Sum over the query's tokens: skip a token the document does not contain; otherwise add idf * tf*(k1+1) / (tf + k1*(1 - b + b*dl/avg_dl)). Missing tokens contribute nothing, so a no-overlap document scores exactly 0.0.
    raise NotImplementedError("bm25_score")


class BM25Retriever:
    """BM25 retriever with pre-retrieval metadata filtering and empty-result abstention."""

    def __init__(self, docs):
        # Accept either the eval set's corpus dict or a plain list of documents.
        documents = docs["documents"] if isinstance(docs, dict) else docs
        self.documents = list(documents)
        self.index = build_inverted_index(self.documents)
        self._by_id = {doc["doc_id"]: doc for doc in self.documents}

    @staticmethod
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

    def retrieve(self, query, k=10, filters=None):
        """Return up to k doc_ids for `query`, best first; an empty list is "abstain".

        `query` is either the eval set's query dict (``text`` and ``filters``) or a raw
        string. An explicit `filters` argument overrides the query's own filters.
        """
        # TODO: Take the query text and its filters (an explicit `filters` argument wins); keep documents passing `_passes_filters`; score each with `bm25_score`; drop score 0 (that is the abstention); sort by (-score, doc_id) and return the top k.
        raise NotImplementedError("BM25Retriever.retrieve")


def _flatten_queries(queries):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(queries, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [q for family in order for q in queries.get(family, [])]
    return list(queries)


def _eval_set_path():
    """Locate the shared eval set's solutions directory."""
    import pathlib

    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent / "eval-set" / "solutions",
        here.parent.parent / "eval-set" / "solutions",
    ]
    for path in candidates:
        if (path / "metrics.py").is_file():
            return path
    raise FileNotFoundError(
        "cannot find the shared eval set at ../eval-set/solutions relative to "
        f"{here}: run the module from inside rag-from-scratch/ or copy check.py next "
        "to the eval set.")


def _import_metrics():
    import sys

    path = str(_eval_set_path())
    if path not in sys.path:
        sys.path.insert(0, path)
    import metrics

    return metrics


def evaluate_bm25(corpus, queries, k=10):
    """Score every query with BM25 and assemble the shared metrics.

    `corpus` is `corpus.generate_corpus(seed)`; `queries` is either
    `queries.build_query_sets(corpus)` or `queries.all_queries(...)`. Returns the dict
    assembled by `metrics.evaluate`.
    """
    # TODO: Flatten the query families, rank every query with BM25Retriever, then return `metrics.evaluate(ranked_by_qid, queries, k)` from the shared eval set.
    raise NotImplementedError("evaluate_bm25")


def main() -> None:
    import sys

    sys.dont_write_bytecode = True
    path = str(_eval_set_path())
    if path not in sys.path:
        sys.path.insert(0, path)

    from baseline import LexicalBaseline
    from corpus import generate_corpus
    from queries import all_queries, build_query_sets
    import metrics

    corpus = generate_corpus(0)
    query_sets = build_query_sets(corpus)
    queries = all_queries(query_sets)

    bm25 = BM25Retriever(corpus)
    bm25_ranked = {q["qid"]: bm25.retrieve(q, 10) for q in queries}
    bm25_result = metrics.evaluate(bm25_ranked, queries, k=10)

    baseline = LexicalBaseline(corpus)
    base_ranked = {q["qid"]: baseline.retrieve(q, 10) for q in queries}
    base_result = metrics.evaluate(base_ranked, queries, k=10)

    header = f"{'family':<12}{'BM25 r@10':>11}{'BM25 MRR':>10}{'base r@10':>11}{'base MRR':>10}"
    print(f"seed 0, {len(corpus['documents'])} documents, {len(queries)} queries")
    print(header)
    for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer", "overall"):
        if family == "overall":
            b = bm25_result["overall"]
            l = base_result["overall"]
        else:
            b = bm25_result["by_type"].get(family, {})
            l = base_result["by_type"].get(family, {})
        print(f"{family:<12}{b.get('recall@k', 0.0):>11.3f}{b.get('mrr', 0.0):>10.3f}"
              f"{l.get('recall@k', 0.0):>11.3f}{l.get('mrr', 0.0):>10.3f}")
    print(f"abstention  BM25: tp={bm25_result['abstention']['tp']} "
          f"fp={bm25_result['abstention']['fp']} "
          f"fn={bm25_result['abstention']['fn']} | baseline: "
          f"tp={base_result['abstention']['tp']} fp={base_result['abstention']['fp']} "
          f"fn={base_result['abstention']['fn']}")


if __name__ == "__main__":
    main()

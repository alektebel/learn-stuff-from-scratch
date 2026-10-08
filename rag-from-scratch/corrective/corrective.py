"""Corrective RAG, offline — RAG project 7 of the from-scratch track.

A single retrieval pass is happy to return *something* even when the corpus has no good
answer: the top-listed document may be a weak lexical coincidence. **Corrective RAG**
(CRAG) adds a small control loop around the retriever: judge the first-stage result, and
only when it looks weak, *correct* it — rewrite the query with pseudo-relevance feedback
and retry, then fall back to a second corpus. The point of this project is the loop and
its failure modes, measured honestly; it is **not** a new retriever.

DESIGN DECISION - the retrieval-quality gate is a deterministic score/consensus heuristic,
    not a trained evaluator.
    The CRAG paper trains a lightweight retrieval evaluator that labels the retrieved
    evidence *correct* / *incorrect* / *ambiguous*. Training one needs labels, a model and
    a network, none of which this repo has. ``quality_gate`` therefore reads two signals
    straight off the first-stage results: the **top score** (is anything matching at all?)
    and the **term consensus** among the top-k documents (do they agree, or is the
    ranking unstable?). It needs no corpus labels, so it cannot leak the test judgments.
    The gate is weak when *either* signal fires — the score is the primary signal, and a
    near-zero score (a generic word matching many documents) is exactly the weak partial
    match corrective RAG exists to catch. The alternative is a conjunction, which is more
    conservative but would skip those partial matches entirely; ``check.py``'s step 4
    reports the measured behaviour either way. Cost: it is still a heuristic. It will call
    some strong retrievals weak and some weak ones strong, and its rewrite can turn a weak
    partial match into a confident-looking wrong one. The trained evaluator is the
    explicitly deferred variant.

DESIGN DECISION - the correction is pseudo-relevance feedback (PRF), and the ``top_n`` and
    term-budget knobs are explicit.
    ``rewrite_prf`` assumes the top-n first-stage documents are relevant (that is the
    "pseudo" in PRF), extracts their most frequent discriminative content terms — the ones
    that recur across the top documents — and appends them to the query, excluding
    stopwords and terms already present. Cost: when the top-n are *not* relevant, PRF
    injects the wrong terms and can drag the ranking away from the answer. That query
    drift is a real CRAG failure mode and ``check.py`` constructs it.

DESIGN DECISION - the fallback is a tiny in-module second corpus, and the pipeline never
    invents documents.
    ``build_second_corpus`` generates a handful of deterministic "external" documents
    covering topics the primary corpus lacks, so a fallback has somewhere to go. Every
    document returned by any path is a real dictionary from one of the two corpora; an
    empty result stays empty. Cost: it is a toy stand-in for a real web/enterprise search;
    it exists so the fallback path is testable offline.

DESIGN DECISION - the gate is computed only from the results, never from the query
    judgments.
    This is what keeps the correction honest: ``check.py`` re-runs the evaluation with the
    relevance labels blanked and requires the path counts to be identical, so a gate that
    peeked at the labels is caught.

Run the demo with ``python3 solutions/corrective.py``: raw vs corrective recall@k, MRR and
nDCG@k per family, the path counts (raw / rewritten / fallback / abstention), and the two
limit cases (query drift; a weak query whose correction cannot help).
"""
from __future__ import annotations

import math
import os
import pathlib
import re
import sys
from collections import Counter

if not sys.dont_write_bytecode:
    sys.dont_write_bytecode = True

TOKEN_RE = re.compile(r"[a-z0-9]+")

#: The query families of the shared eval set, in report order.
FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")

#: English function words PRF must not promote into a query.
STOPWORDS = frozenset((
    "a an and are as at be been but by for from had has have he her his how i if in into "
    "is it its of on or our she that the their them then there these they this to up us "
    "was we were what when where which who whom why will with you your us our").split())

#: Gate defaults. A result is weak when the top score is low *and* the top-k documents
#: disagree (low consensus); see the module docstring's first design decision.
GATE_THRESHOLD = 1.0
GATE_OVERLAP = 0.5
GATE_TOPK = 3

#: PRF defaults.
PRF_TOP_N = 3
PRF_TERMS = 5

# BM25 constants, identical to the sibling lexical stage.
K1, B = 1.5, 0.75
_FILTER_KEYS = ("region", "year", "department", "access_level")

#: A small "external" corpus covering topics the primary eval set lacks. Deterministic and
#: in-module, so the fallback has somewhere to go with no network.
SECOND_CORPUS = [
    {"doc_id": "EXT-0001", "title": "surface code error correction",
     "body": "logical qubits survive noise with a surface code decoding threshold"},
    {"doc_id": "EXT-0002", "title": "mangrove restoration after storms",
     "body": "coastal mangrove replanting buffers storm surge and stores blue carbon"},
    {"doc_id": "EXT-0003", "title": "terracotta glaze chemistry",
     "body": "lead free terracotta glaze matures near cone six in an electric kiln"},
    {"doc_id": "EXT-0004", "title": "bicycle derailleur alignment",
     "body": "indexing a rear derailleur fixes ghost shifting on a worn cassette"},
    {"doc_id": "EXT-0005", "title": "sourdough starter hydration",
     "body": "a stiff sourdough starter ferments slower than a liquid levain"},
]


# ---------------------------------------------------------------------------
# small text helpers
# ---------------------------------------------------------------------------

def tokenize(text):
    """Lower-cased word/number tokens, in order."""
    return TOKEN_RE.findall(str(text).lower())


def _text(question):
    """The query text, whether a query dict, a string or a term list."""
    if isinstance(question, dict):
        return str(question.get("text", ""))
    if isinstance(question, (list, tuple)):
        return " ".join(str(item) for item in question)
    return str(question)


def _query_terms(question, terms=None):
    """The query as a list of lower-cased terms (an explicit ``terms`` wins)."""
    if terms is not None:
        return [str(term).lower() for term in terms]
    return tokenize(_text(question))


def _result_terms(result):
    """The content terms of one retrieved result (or of a raw document)."""
    if isinstance(result, dict):
        terms = result.get("terms")
        if terms:
            return [str(term) for term in terms]
        text = str(result.get("title", "")) + " " + str(result.get("body", ""))
        return sorted({tok for tok in tokenize(text) if tok not in STOPWORDS})
    return tokenize(str(result))


def _doc_terms(document):
    """The non-stopword content terms of a corpus document."""
    text = str(document.get("title", "")) + " " + str(document.get("body", ""))
    return {tok for tok in tokenize(text) if tok not in STOPWORDS}


def _passes_filters(document, filters):
    """The metadata predicate the lexical stage applies before scoring."""
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


# ---------------------------------------------------------------------------
# the lexical first stage (the sibling ../bm25, with a local BM25 fallback)
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


def _local_rank(terms, documents, filters=None):
    """A self-contained Okapi BM25 ranker returning scored result dicts.

    Each result is ``{"doc_id", "score", "terms"}``; ``terms`` are the document's own
    non-stopword content terms, which the gate reads for consensus. Only positive scores
    are returned, so no match abstains with ``[]``.
    """
    n_docs = len(documents)
    if n_docs == 0 or not terms:
        return []
    counts = []
    document_frequency = Counter()
    for document in documents:
        counter = Counter(tokenize(
            str(document.get("title", "")) + " " + str(document.get("body", ""))))
        counts.append(counter)
        for term in set(counter):
            document_frequency[term] += 1
    average = (sum(sum(counter.values()) for counter in counts) / n_docs) or 1.0
    scored = []
    for document, counter in zip(documents, counts):
        if not _passes_filters(document, filters or {}):
            continue
        length = sum(counter.values()) or 1
        score = 0.0
        for term in terms:
            frequency = counter.get(term, 0)
            if not frequency:
                continue
            idf = math.log(
                1.0 + (n_docs - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5))
            score += idf * (frequency * (K1 + 1.0)) / (
                frequency + K1 * (1.0 - B + B * length / average))
        if score > 0.0:
            scored.append({
                "doc_id": document["doc_id"],
                "score": score,
                "terms": sorted({tok for tok in counter if tok not in STOPWORDS}),
            })
    scored.sort(key=lambda item: (-item["score"], item["doc_id"]))
    return scored


def retrieve_primary(query, k, documents):
    """First-stage retrieval: up to ``k`` scored results, best first.

    Uses the sibling ``../bm25`` to decide *which* documents match (so the two stages
    share one tokenisation and one abstention rule); when the sibling is not in this tree
    it falls back to :func:`_local_rank`. Scores and content terms are always recomputed
    locally so the gate has a stable signal to read.
    """
    # TODO: Score the documents with ``_local_rank(terms, documents, filters)`` (filters come from a dict query). When the sibling ``../bm25`` imports, reorder those result dicts by its ranked doc_ids. Return at most ``k``; a document matching no query term scores 0 and is dropped.
    raise NotImplementedError("retrieve_primary")


# ---------------------------------------------------------------------------
# the quality gate
# ---------------------------------------------------------------------------

def _consensus(results):
    """Mean fraction of the top result's terms shared by each result (0 when empty)."""
    if not results:
        return 0.0
    base = set(results[0].get("terms") or [])
    if not base:
        return 0.0
    overlaps = [len(base & set(item.get("terms") or [])) / len(base)
                for item in results]
    return sum(overlaps) / len(overlaps)


def quality_gate(results, threshold=None):
    """Return ``"ok"`` or ``"weak"`` for a first-stage result list.

    ``results`` is the best-first list produced by :func:`retrieve_primary`. The gate is
    weak when there is nothing to show, when the top score is below ``threshold``, or when
    the top-:data:`GATE_TOPK` documents share too few terms. Both signals are computed
    from ``results`` alone — never from the query's relevance judgments — which is what
    step 4's leak check of ``check.py`` relies on. See the module docstring's first design
    decision for the cost of using a heuristic instead of CRAG's trained evaluator.
    """
    # TODO: Return "weak" when ``results`` is empty, when ``results[0]['score']`` is below ``threshold``, or when ``_consensus(results[:GATE_TOPK])`` is below ``GATE_OVERLAP``; otherwise "ok". Read only ``results`` — never the query's relevance judgments.
    raise NotImplementedError("quality_gate")


# ---------------------------------------------------------------------------
# pseudo-relevance feedback (query rewriting)
# ---------------------------------------------------------------------------

def rewrite_prf(query, results, top_n=PRF_TOP_N, terms=None, n_terms=PRF_TERMS):
    """Expand ``query`` with the most shared content terms of the top ``top_n`` results.

    Returns the expanded term list: the original query terms first, then up to ``n_terms``
    candidate terms ordered by how many of the top documents they appear in (ties broken
    alphabetically). Stopwords and terms already in the query are never added. The
    expansion is deterministic. See the module docstring's second design decision for the
    cost (query drift when the pseudo-relevant documents are off-topic).
    """
    # TODO: Start from the original query terms. For each of the top ``top_n`` results, count each non-stopword term once per document (a set per result). Sort the candidates by ``(-count, term)`` and append up to ``n_terms`` of them, skipping stopwords and terms already in the query. Return original + added.
    raise NotImplementedError("rewrite_prf")


# ---------------------------------------------------------------------------
# the second corpus and the corrective pipeline
# ---------------------------------------------------------------------------

def build_second_corpus():
    """The deterministic external corpus, a fresh list of documents."""
    # TODO: Return a fresh list of the module's ``SECOND_CORPUS`` documents, copying each dict so a caller cannot mutate the constant.
    raise NotImplementedError("build_second_corpus")


def retrieve_second(query, k, documents=None):
    """Retrieve up to ``k`` scored results from the second corpus (no metadata filters)."""
    # TODO: Return the first ``k`` results of ``_local_rank(_query_terms(query), documents or build_second_corpus(), {})`` — no metadata filters on the external corpus.
    raise NotImplementedError("retrieve_second")


def corrective_retrieve(query, k, documents=None, threshold=None, top_n=PRF_TOP_N,
                        n_terms=PRF_TERMS):
    """Run the corrective loop and return the chosen result tagged with the path taken.

    Steps: (1) retrieve from the primary corpus; (2) gate; (3) if weak, rewrite with PRF
    and retry the primary stage; (4) if still weak, consult the second corpus; (5) if
    nothing helps, return the best primary/rewrite result rather than an invention. The
    returned dict is ``{"documents", "results", "path", "gate", "expanded", "abstained"}``
    with ``path`` one of ``"raw"``, ``"rewritten"``, ``"fallback"`` or ``"abstain"``, so
    the caller can count how often each route was taken.
    """
    # TODO: Retrieve the primary and gate it. Keep it (path "raw") when the gate is ok. Otherwise rewrite with PRF and retry: if the retry gates ok use it (path "rewritten"). Otherwise try the second corpus (path "fallback"). If nothing helps, keep the retry or the primary — or abstain when empty. Tag the returned dict with the path and the abstained flag.
    raise NotImplementedError("corrective_retrieve")


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
        here.parent / "eval-set",
        here.parent.parent / "eval-set",
    ]
    for path in candidates:
        if path is not None and (path / "metrics.py").is_file() \
                and (path / "corpus.py").is_file():
            return path
    raise FileNotFoundError(
        "cannot find the shared eval set at ../eval-set/solutions relative to "
        f"{here}: run from inside rag-from-scratch/ or set RAG_EVAL_SET.")


def load_eval_set(seed=0):
    """Load the shared eval set: documents, queries/judgments and metrics.

    Returns ``{"corpus", "documents", "query_sets", "queries", "metrics"}`` where
    ``query_sets`` is the family dict and ``queries`` is its flattened list. Mirrors the
    sibling stages' discovery of ``../eval-set/solutions``.
    """
    # TODO: Locate the shared eval set's ``solutions/`` (pathlib, with an ``RAG_EVAL_SET`` override), add it to ``sys.path``, import ``corpus``/``metrics``/``queries``, generate ``corpus.generate_corpus(seed)``, build the query sets and return the documents, the family dict, the flattened query list and the metrics module.
    raise NotImplementedError("load_eval_set")


def _flatten_query_sets(query_sets):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(query_sets, dict):
        return [query for family in FAMILIES for query in query_sets.get(family, [])]
    return list(query_sets)


# ---------------------------------------------------------------------------
# local metrics (recall@k, MRR, nDCG@k), computed from the query judgments
# ---------------------------------------------------------------------------

def _relevance_map(query):
    """``{doc_id: grade}`` for the query, accepting dicts or id lists."""
    relevance = query.get("relevance") if isinstance(query, dict) else {}
    if isinstance(relevance, dict):
        return {str(doc_id): float(grade) for doc_id, grade in relevance.items()
                if float(grade) > 0.0}
    return {str(doc_id): 1.0 for doc_id in (relevance or [])}


def _recall_at_k(retrieved, relevant, k):
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)


def _mrr(retrieved, relevant):
    if not relevant:
        return 0.0
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def _gain(grade):
    """Exponential gain ``2**grade - 1``, matching the shared metrics module."""
    return 2.0 ** grade - 1.0


def _ndcg_at_k(retrieved, relevant, k):
    if not relevant:
        return 0.0
    dcg = sum(_gain(relevant.get(doc_id, 0.0)) / math.log2(rank + 1.0)
              for rank, doc_id in enumerate(retrieved[:k], start=1))
    ideal = sorted(relevant.values(), reverse=True)[:k]
    idcg = sum(_gain(grade) / math.log2(rank + 1.0)
               for rank, grade in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0


def _aggregate(groups, k):
    """Mean recall@k, MRR and nDCG@k for each family and overall."""
    out = {}
    for family, items in groups.items():
        count = len(items)
        out[family] = {
            "n": count,
            "recall@k": sum(_recall_at_k(r, rel, k) for r, rel in items) / count,
            "mrr": sum(_mrr(r, rel) for r, rel in items) / count,
            "ndcg@k": sum(_ndcg_at_k(r, rel, k) for r, rel in items) / count,
        }
    everything = [item for items in groups.values() for item in items]
    out["overall"] = {
        "n": len(everything),
        "recall@k": sum(_recall_at_k(r, rel, k) for r, rel in everything)
        / len(everything),
        "mrr": sum(_mrr(r, rel) for r, rel in everything) / len(everything),
        "ndcg@k": sum(_ndcg_at_k(r, rel, k) for r, rel in everything)
        / len(everything),
    }
    return out


def evaluate(query_sets, documents=None, k=5, threshold=None):
    """Compare the raw and corrective pipelines over the shared eval set, honestly.

    ``query_sets`` is the family dict (or a flat query list). ``documents`` defaults to the
    primary corpus of:func:`load_eval_set`. Returns the raw and corrective metrics per
    family and overall, the path counts (``raw`` / ``rewritten`` / ``fallback``), the
    abstention count, the per-query records, and the set of corpus doc ids. The corrective
    result is never asserted to beat the raw one; on an easy set they may tie.
    """
    # TODO: For every query, get both ``retrieve_primary`` and ``corrective_retrieve``, record the two ranked id lists against ``_relevance_map(query)``, count the corrective path or the abstention, and aggregate recall@k/MRR/nDCG@k per family and overall. The gate and the path decision must not read the judgments.
    raise NotImplementedError("evaluate")


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def _print_metrics(title, result, families):
    print(title)
    for family in families + ("overall",):
        stats = result["overall"] if family == "overall" else result["by_type"][family]
        print(f"  {family:<11} n={stats['n']:>2} "
              f"recall@{result['k']}={stats['recall@k']:.3f} "
              f"mrr={stats['mrr']:.3f} "
              f"ndcg@{result['k']}={stats['ndcg@k']:.3f}")


def demo():
    """Print the raw vs corrective numbers and the limit cases."""
    sys.dont_write_bytecode = True
    loaded = load_eval_set(0)
    documents = loaded["documents"]
    query_sets = loaded["query_sets"]
    result = evaluate(query_sets, documents, k=5)
    families = tuple(f for f in FAMILIES if query_sets.get(f))

    raw = {"k": result["k"], "overall": result["raw"]["overall"],
           "by_type": result["raw"]}
    corrective = {"k": result["k"], "overall": result["corrective"]["overall"],
                  "by_type": result["corrective"]}
    print(f"primary corpus: {len(documents)} documents; "
          f"second corpus: {len(SECOND_CORPUS)} documents")
    print(f"correction: heuristic gate (top score + top-{GATE_TOPK} consensus), "
          f"PRF rewrite (top_n={PRF_TOP_N}, +{PRF_TERMS} terms), second-corpus fallback")
    _print_metrics("raw retrieval:", raw, families)
    _print_metrics("corrective retrieval:", corrective, families)
    print(f"paths: raw={result['paths']['raw']} "
          f"rewritten={result['paths']['rewritten']} "
          f"fallback={result['paths']['fallback']} "
          f"abstained={result['abstained']} (n={result['n']})")
    valid = result["valid_ids"]
    invented = [record["qid"] for record in result["records"]
                if not set(record["corrective"]) <= valid]
    print(f"invented documents: {len(invented)} "
          "(every returned doc_id belongs to a corpus)")

    print("\nlimit case 1 - query drift: PRF adds off-topic terms")
    corpus = [
        {"doc_id": "R", "title": "widget", "body": "widget"},
        {"doc_id": "X", "title": "widget gadget sprocket", "body": "widget gadget sprocket"},
        {"doc_id": "Y", "title": "gadget sprocket", "body": "gadget sprocket"},
    ]
    raw_top = retrieve_primary("widget", 5, corpus)
    expanded = rewrite_prf("widget", raw_top, top_n=2, terms=["widget"])
    rewritten_top = retrieve_primary(expanded, 5, corpus)
    print(f"  raw 'widget'        -> {[r['doc_id'] for r in raw_top]}")
    print(f"  PRF expansion        -> {expanded}")
    print(f"  rewritten            -> {[r['doc_id'] for r in rewritten_top]} "
          "(the off-topic doc overtakes the relevant one)")

    print("\nlimit case 2 - a weak query the correction cannot help")
    weak = corrective_retrieve("zzzq nonexistent topic", 5, documents)
    print(f"  'zzzq nonexistent topic' -> path={weak['path']} "
          f"documents={weak['documents']} gate={weak['gate']} "
          "(empty, not a hallucination)")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    demo()

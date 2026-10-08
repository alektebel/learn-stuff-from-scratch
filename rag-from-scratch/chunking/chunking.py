"""Contextual chunking, offline — RAG project 4 of the from-scratch track.

Retrieval reads a *chunk*, not a whole document. Split a document into passages and a bare
passage can lose the one word that says what it is about: a chunk that reads "revenue grew
twelve percent" retrieves badly for a query about the annual report, because the words
"annual report" live in the document title, not in the passage. **Contextual retrieval**
(prepending the document title and the section each chunk came from before indexing) exists
to fix exactly that. This project builds chunking and the contextual prefix, then measures
plain chunks against contextual chunks on the shared eval set — honestly, including the
cases where the fix does nothing.

DESIGN DECISION - sentences are split by a deterministic punctuation rule, and the
    abbreviations it cannot know about are the documented cost.
    ``split_sentences`` ends a sentence after a run of ``.`` / ``!`` / ``?`` followed by
    whitespace or the end of the body. No model, no sentence tokeniser, no abbreviation
    list. Cost: it splits inside "Dr.", "etc.", "e.g.", "i.e.", "U.S.", "3.14" and other
    dotted tokens, producing short spurious sentences. That only makes chunks slightly
    smaller and the overlap more generous; it never loses text, and this repository has no
    label that would justify shipping an abbreviation dictionary. The real plan may use a
    proper sentence splitter; the deterministic rule is the testable stand-in.

DESIGN DECISION - chunks are sentence-aligned and overlapping, and the last partial chunk
    is always kept.
    ``chunk_document`` packs whole sentences until the next one would pass ``size``
    characters, then emits. The next chunk starts again at the last sentence(s) that fit in
    ``overlap``, so a fact spanning a boundary appears intact in at least one chunk once the
    overlap is wide enough. The trailing leftover is emitted even when it is far below
    ``size``: dropping it is the classic chunker bug, and dropping it is exactly what
    ``check.py`` mutates to catch. A body shorter than ``size`` therefore yields exactly one
    chunk. Cost: because the alignment is by sentence, a chunk whose last sentence carries
    an answer that continues into the next chunk is only repaired by overlap, not by
    splitting the sentence; ``check.py``'s step 5 constructs that boundary case.

DESIGN DECISION - ``section_path`` is a deterministic stand-in for the document's real
    heading path.
    The contextual-retrieval plan in the literature prepends the *actual* breadcrumb the
    document carries ("Annual report > Finance > Revenue"). This corpus has no heading tree:
    it has ``department`` and ``topics``. ``section_path`` therefore returns
    ``"<department>: <first topic>"`` — the same kind of short, discriminative label, built
    deterministically from metadata that exists. Cost: it is a coarse label, not the real
    path, so it can be wrong for a document whose first topic is not its section.

DESIGN DECISION - the comparison is reported as measured, never asserted to favour the fix.
    On this synthetic corpus many documents are short enough to be a single chunk, so the
    title and section prefix add no recall that the body did not already provide, and plain
    and contextual retrieval often tie. ``evaluate`` reports the numbers and only checks
    that the result is a valid retrieval (every returned id is in the corpus, no document
    is repeated). A test that forced contextual to win would be measuring the corpus, not
    the method.

Run the demo with ``python3 solutions/chunking.py``: plain vs contextual recall@k, MRR and
nDCG@k per family, the abstention counts, and the boundary limit case (a fact split across
a chunk boundary, repaired by more overlap).
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

#: Sentence end: a run of terminators followed by whitespace or end-of-text.
SENTENCE_END_RE = re.compile(r"[.!?]+(?=\s|$)")

#: The query families of the shared eval set, in report order.
FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")

#: English function words the local ranker does not count as content. Only used to decide
#: which terms a chunk is "about" in the fallback ranker; never to drop query terms.
STOPWORDS = frozenset((
    "a an and are as at be been but by for from had has have he her his how i if in into "
    "is it its of on or our she that the their them then there these they this to up us "
    "was we were what when where which who whom why will with you your us our").split())

#: Chunking defaults. ``size`` is a character budget, ``overlap`` a character budget for the
#: sentence tail carried into the next chunk. Both are explicit knobs; step 5 of ``check.py``
#: shows that overlap is what repairs a fact that straddles a boundary.
DEFAULT_SIZE = 240
DEFAULT_OVERLAP = 60

# BM25 constants, identical to the sibling lexical stage.
K1, B = 1.5, 0.75


class Chunk:
    """One sentence-aligned passage of a document body.

    ``start`` and ``end`` are character offsets into the *body* (not the title), so a chunk
    can always be sliced back out of the source: ``doc["body"][chunk.start:chunk.end]``.
    """

    __slots__ = ("chunk_id", "doc_id", "text", "start", "end")

    def __init__(self, chunk_id, doc_id, text, start, end):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.text = text
        self.start = start
        self.end = end

    def __repr__(self):
        return (f"Chunk({self.chunk_id!r}, {self.doc_id!r}, "
                f"{self.start}:{self.end}, {self.text!r})")

    def __eq__(self, other):
        if not isinstance(other, Chunk):
            return NotImplemented
        return (self.chunk_id, self.doc_id, self.text, self.start, self.end) == (
            other.chunk_id, other.doc_id, other.text, other.start, other.end)

    def __hash__(self):
        return hash((self.chunk_id, self.doc_id, self.text, self.start, self.end))


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


def _metadata_list(value):
    """``topics`` as a list of strings, accepting a single string too."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    return [str(item) for item in value]


# ---------------------------------------------------------------------------
# sentence splitting and chunking
# ---------------------------------------------------------------------------

def split_sentences(text):
    """Return ``(start, end)`` spans of the sentences in ``text``, in order.

    Rule: a sentence ends after a run of ``.`` / ``!`` / ``?`` that is followed by
    whitespace or the end of the text. A span starts at the sentence's first non-whitespace
    character and runs to the first character of the next sentence, so the separator
    whitespace belongs to the span before it and the spans *tile* the body: each span's
    ``end`` equals the next span's ``start``, and the last ``end`` is ``len(text)`` (for a
    body with no leading whitespace). That is what lets a chunk's ``start``/``end`` cover
    the body without a gap. ``check.py`` relies on the tiling.

    Abbreviations deliberately not handled — each is a *cost*, not a bug to file: dotted
    tokens such as ``Dr.`` ``Mr.`` ``etc.`` ``e.g.`` ``i.e.`` ``U.S.`` ``vs.`` and decimal
    numbers such as ``3.14`` end a sentence here. The split is deterministic and never
    drops text; it only makes chunks a little smaller. See the module docstring.
    """
    # TODO: Find each run of ``[.!?]+`` followed by whitespace or the end of the text with ``SENTENCE_END_RE``. A span starts at the sentence's first non-whitespace character and ends at the next sentence's first character (carry the separator whitespace), so the spans tile the body: each ``end`` equals the next ``start`` and the last ``end`` is ``len(text)``. Return the spans in order.
    raise NotImplementedError("split_sentences")


def _chunk_id(doc_id, index):
    """A stable, unique, sortable id for the ``index``-th chunk of ``doc_id``."""
    return f"{doc_id}#{index:04d}"


def chunk_document(doc, size=DEFAULT_SIZE, overlap=DEFAULT_OVERLAP):
    """Split ``doc["body"]`` into overlapping, sentence-aligned :class:`Chunk` objects.

    Packs whole sentences until the next would make the chunk longer than ``size``
    characters, emits it, and starts the next chunk at the last sentence(s) whose combined
    length fits in ``overlap``. The last chunk is always emitted, however small. A body
    with no printable text yields ``[]``; a body shorter than ``size`` yields exactly one
    chunk. Deterministic for a given body, ``size`` and ``overlap``.
    """
    # TODO: Split the body into sentence spans. Greedily pack whole sentences while the next keeps the chunk within ``size`` characters, then emit a ``Chunk`` with ``body[start:end]``. If sentences remain, start the next chunk at the last sentence(s) whose combined length fits in ``overlap`` (never at or before the chunk's first sentence, so progress is guaranteed). Always emit the trailing leftover, however small; a body with no printable text returns ``[]``.
    raise NotImplementedError("chunk_document")


# ---------------------------------------------------------------------------
# the context label and the contextual prefix
# ---------------------------------------------------------------------------

def section_path(doc):
    """A short deterministic section label for ``doc``, from its metadata.

    Returns ``"<department>: <first topic>"`` (falling back to ``"general"`` when either is
    missing), e.g. ``"finance: revenue"``. This is a *stand-in* for the document's real
    heading path ("Annual report > Finance > Revenue"), which this corpus does not carry;
    see the module docstring. The caller must not assume the label is a literal heading.
    """
    # TODO: Return ``'<department>: <first topic>'`` from the document's metadata, using ``_metadata_list`` for ``topics`` and ``'general'`` for a missing department or topic. Deterministic; this is the stand-in for the real heading path, not a literal heading.
    raise NotImplementedError("section_path")


def contextualise(chunk, doc):
    """The chunk text prefixed with ``<title>. <section_path>. `` — the context fix.

    The order is title, then section path, then the chunk's own text, so a search for the
    title, the label or the passage all hit the same indexed string. Plain chunking indexes
    :attr:`Chunk.text` alone; this function is only used when ``contextual=True``.
    """
    # TODO: Return ``f'{title}. {section_path(doc)}. {chunk.text}'`` — the title, then the section path, then the passage, in that order, so a search for any of the three hits the same indexed string.
    raise NotImplementedError("contextualise")


# ---------------------------------------------------------------------------
# the lexical ranker (the sibling ../bm25, with a local BM25 fallback)
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

            try:
                _BM25_CACHE[0] = importlib.import_module("bm25")
            except Exception:  # noqa: BLE001 - the sibling is a convenience
                _BM25_CACHE[0] = None
            break
    _BM25_CACHE[1] = True
    return _BM25_CACHE[0]


def _local_rank(terms, entries, filters=None):
    """A self-contained Okapi BM25 ranker over indexed entries.

    ``entries`` are ``{"doc_id", "title", "body"}`` dicts (here the chunk id and the chunk
    text). Returns scored ``{"doc_id", "score", "terms"}`` dicts, best first, only for
    positive scores — so no match abstains with ``[]``.
    """
    n_docs = len(entries)
    if n_docs == 0 or not terms:
        return []
    counts = []
    document_frequency = Counter()
    for entry in entries:
        counter = Counter(tokenize(
            str(entry.get("title", "")) + " " + str(entry.get("body", ""))))
        counts.append(counter)
        for term in set(counter):
            document_frequency[term] += 1
    average = (sum(sum(counter.values()) for counter in counts) / n_docs) or 1.0
    scored = []
    for entry, counter in zip(entries, counts):
        if filters and not _passes_filters(entry, filters):
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
                "doc_id": entry["doc_id"],
                "score": score,
                "terms": sorted({tok for tok in counter if tok not in STOPWORDS}),
            })
    scored.sort(key=lambda item: (-item["score"], str(item["doc_id"])))
    return scored


def _passes_filters(entry, filters):
    """The metadata predicate the lexical stage applies, kept for API parity."""
    for key, value in (filters or {}).items():
        if entry.get(key) != value:
            return False
    return True


# ---------------------------------------------------------------------------
# the chunk-level index and retrieval
# ---------------------------------------------------------------------------

def _doc_index(documents):
    return {str(document["doc_id"]): document for document in documents}


def build_index(documents, contextual=False, size=DEFAULT_SIZE, overlap=DEFAULT_OVERLAP):
    """Build a chunk-level index over ``documents``.

    Every document is chunked with :func:`chunk_document`; each chunk becomes one indexed
    entry whose ``doc_id`` is the chunk id and whose ``body`` is either the chunk text
    (plain) or :func:`contextualise` of it (contextual). The returned dict carries the
    chunks, the chunk -> document map, and the entries the ranker reads. The sibling
    ``../bm25`` consumes the entries directly when it is present.
    """
    # TODO: Chunk every document with ``chunk_document``. Build one indexed entry per chunk with ``doc_id`` = the chunk id and ``body`` = the chunk text, or ``contextualise(chunk, doc)`` when ``contextual`` is true. Return the chunks, the chunk -> document map, the entries the ranker reads, and the flags.
    raise NotImplementedError("build_index")


def _rank_chunks(query, k, chunk_index):
    """Rank the index's chunk entries for ``query``, best first, up to ``k``."""
    terms = tokenize(_text(query))
    if not terms or k <= 0:
        return []
    entries = chunk_index["entries"]
    local = _local_rank(terms, entries)
    if not local:
        return []
    bm25 = _try_import_bm25()
    if bm25 is not None:
        try:
            ranked = bm25.BM25Retriever(entries).retrieve(query, k=k)
        except Exception:  # noqa: BLE001 - the sibling is a convenience, not a contract
            ranked = None
        if ranked:
            by_id = {item["doc_id"]: item for item in local}
            ordered = []
            for item in ranked:
                chunk_id = item.get("doc_id") if isinstance(item, dict) else item
                if chunk_id in by_id:
                    ordered.append(by_id[chunk_id])
            if ordered:
                return ordered
    return local[:max(0, k)]


def retrieve(query, k, chunk_index):
    """Top-``k`` chunks for ``query``, reduced to the distinct ``doc_id``s, in rank order.

    A document answered by several chunks appears once, at the rank of its best chunk. A
    query that matches no chunk returns ``[]`` (abstention), never a sample of the index.
    """
    # TODO: Rank the index's chunk entries for the query with ``_rank_chunks`` (up to ``k``), then walk them best-first and append each chunk's ``doc_id`` once, skipping a document already seen. A query that matches no chunk returns ``[]`` — never a sample of the index.
    raise NotImplementedError("retrieve")


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
    """Load the shared eval set: documents, queries/judgments and the family dict.

    Returns ``{"corpus", "documents", "query_sets", "queries", "metrics"}`` where
    ``query_sets`` is the family dict and ``queries`` is its flattened list. Mirrors the
    sibling stages' discovery of ``../eval-set/solutions``.
    """
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import corpus
    import metrics
    import queries

    generated = corpus.generate_corpus(seed)
    query_sets = queries.build_query_sets(generated)
    return {
        "corpus": generated,
        "documents": generated["documents"],
        "query_sets": query_sets,
        "queries": _flatten_query_sets(query_sets),
        "metrics": metrics,
    }


def _flatten_query_sets(query_sets):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(query_sets, dict):
        return [query for family in FAMILIES for query in query_sets.get(family, [])]
    return list(query_sets)


# ---------------------------------------------------------------------------
# local metrics (doc-level recall@k, MRR, nDCG@k)
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
    """Mean recall@k, MRR, nDCG@k and abstention count for each family and overall."""
    out = {}
    for family, items in groups.items():
        count = len(items)
        out[family] = {
            "n": count,
            "recall@k": sum(_recall_at_k(r, rel, k) for r, rel in items) / count,
            "mrr": sum(_mrr(r, rel) for r, rel in items) / count,
            "ndcg@k": sum(_ndcg_at_k(r, rel, k) for r, rel in items) / count,
            "abstained": sum(1 for r, _rel in items if not r),
        }
    everything = [item for items in groups.values() for item in items]
    out["overall"] = {
        "n": len(everything),
        "recall@k": sum(_recall_at_k(r, rel, k) for r, rel in everything)
        / len(everything),
        "mrr": sum(_mrr(r, rel) for r, rel in everything) / len(everything),
        "ndcg@k": sum(_ndcg_at_k(r, rel, k) for r, rel in everything) / len(everything),
        "abstained": sum(1 for r, _rel in everything if not r),
    }
    return out


def evaluate(documents, query_sets, k=5, size=DEFAULT_SIZE, overlap=DEFAULT_OVERLAP):
    """Compare plain and contextual chunks on the shared eval set, at the document level.

    ``documents`` is the corpus, ``query_sets`` the family dict (or a flat query list). The
    same documents are chunked twice — once plain, once contextual — and both rankings are
    reduced to distinct doc ids and scored with recall@k, MRR and nDCG@k per family, plus an
    abstention count. Returns the two aggregates, the per-query records, and the corpus ids.
    Contextual is never asserted to beat plain; on this corpus it often ties. See the
    module docstring's last design decision.
    """
    # TODO: Build the plain and contextual indexes over the same documents. For every query, retrieve both doc-id rankings and record them against ``_relevance_map(query)``. Aggregate recall@k, MRR, nDCG@k and the abstention count per family and overall with ``_aggregate``. Report the two aggregates as measured; do not assume contextual wins.
    raise NotImplementedError("evaluate")


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def _print_metrics(title, result, families):
    print(title)
    for family in families + ("overall",):
        stats = result["overall"] if family == "overall" else result[family]
        print(f"  {family:<11} n={stats['n']:>2} "
              f"recall@{result['k'] if 'k' in result else 5}={stats['recall@k']:.3f} "
              f"mrr={stats['mrr']:.3f} "
              f"ndcg={stats['ndcg@k']:.3f} abstained={stats['abstained']}")


def demo():
    """Print the plain vs contextual numbers and the boundary limit case."""
    sys.dont_write_bytecode = True
    loaded = load_eval_set(0)
    documents = loaded["documents"]
    query_sets = loaded["query_sets"]
    result = evaluate(documents, query_sets, k=5)
    families = tuple(family for family in FAMILIES if query_sets.get(family))

    total_chunks = len(build_index(documents, contextual=False)["chunks"])
    print(f"corpus: {len(documents)} documents -> {total_chunks} plain chunks "
          f"(size={DEFAULT_SIZE}, overlap={DEFAULT_OVERLAP})")
    print("plain (no prefix):")
    _print_metrics("  plain chunks:", {"k": result["k"], **result["plain"]}, families)
    print("contextual (title + section path prefix):")
    _print_metrics("  contextual chunks:",
                   {"k": result["k"], **result["contextual"]}, families)
    print(f"abstentions: plain={result['abstained']['plain']} "
          f"contextual={result['abstained']['contextual']} (n={result['n']})")
    print("honest note: on this synthetic corpus most documents fit in one chunk, so the "
          "prefix often adds nothing and the two columns tie; the fix earns its keep only "
          "where a bare passage loses the title/section words.")

    print("\nlimit case - a fact straddling a chunk boundary, repaired by more overlap")
    documents = [
        {"doc_id": "A", "title": "summary", "department": "general", "topics": ["summary"],
         "body": "budget ledger report summary for the operations department."},
        {"doc_id": "I", "title": "review", "department": "general", "topics": ["review"],
         "body": "quarterly review. budget planning. ledger reconciliation."},
    ]
    for overlap in (0, 40):
        index = build_index(documents, contextual=False, size=40, overlap=overlap)
        ranking = retrieve("budget ledger", 5, index)
        print(f"  overlap={overlap:>2}: chunks of I = "
              f"{[chunk.text for chunk in index['chunks'] if chunk.doc_id == 'I']} "
              f"-> ranking {ranking}")
    index = build_index(documents, contextual=False, size=40, overlap=40)
    print(f"  with overlap=40 the combined chunk matches both query terms, so the intended "
          f"document I is first: {retrieve('budget ledger', 5, index)}")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    demo()

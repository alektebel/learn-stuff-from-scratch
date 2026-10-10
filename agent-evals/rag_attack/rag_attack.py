"""rag_attack: an adversarial harness for a retrieval system (agent-evals #5).

agent-evals #5. A retrieval system is happy to return *something* for any query. This
module probes one with deterministic adversarial inputs and reports where it fails: does a
small query perturbation push the true document out of the top-k, and does an injected
"poison" document (stuffed with the query's own terms) enter the result? It does not need a
model — retrieval is offline — only a *system under test* (SUT) and the shared evaluation
set.

LEARN-mode file: the SUT adapters, the eval-set loader and the token/metric helpers are
provided as test infrastructure and are implemented. The four attack entry points
(`perturb_text`, `poison_document`, `probe`, `evaluate_attacks`) are deliberately unwritten;
the tests in tests/test_rag_attack.py define what the learner must make true.

A SUT is a *factory* ``sut_factory(documents) -> retrieve``, so the attack can hand it an
augmented corpus; ``retrieve(query, k) -> [{"doc_id", "score"}, ...]`` ranks at most k
documents. Everything is deterministic under an explicit seed; standard library only.
"""

from __future__ import annotations

import os
import pathlib
import random
import re
import string
import sys

TOKEN_RE = re.compile(r"[a-z0-9]+")
_FILTER_KEYS = ("region", "year", "department", "access_level")

STOPWORDS = frozenset((
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "what", "when", "where", "which", "who",
    "why", "with",
))

__all__ = [
    "LocalRetriever",
    "local_sut_factory",
    "load_eval_set",
    "content_terms",
    "tokenize",
    "perturb_text",
    "poison_document",
    "probe",
    "evaluate_attacks",
]


# --------------------------------------------------------------------------
# Test infrastructure (implemented on purpose; its tests pass today)
# --------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def content_terms(text: str) -> list[str]:
    """Query/document content terms: tokens minus stopwords, order preserved."""
    return [t for t in tokenize(text) if t not in STOPWORDS]


def _document_text(document: dict) -> str:
    return f"{document.get('title', '')} {document.get('body', '')}".strip()


def _passes_filters(document: dict, filters: dict) -> bool:
    for key in _FILTER_KEYS:
        value = filters.get(key)
        if value is None:
            continue
        if key == "year":
            if str(document.get("date", ""))[:4] != str(value):
                return False
        elif document.get(key) != value:
            return False
    return True


class LocalRetriever:
    """A deterministic lexical SUT: rank by content-term overlap, tie-break by doc_id.

    A document matching no query term scores 0 and is dropped. This is the SUT the demo
    uses, and it is deliberately vulnerable to the term-stuffing poison.
    """

    def __init__(self, documents) -> None:
        self._documents = list(documents)

    def __call__(self, query, k: int = 5) -> list[dict]:
        text = query["text"] if isinstance(query, dict) else query
        filters = (query.get("filters") or {}) if isinstance(query, dict) else {}
        wanted = set(content_terms(text))
        ranked = []
        for document in self._documents:
            if not _passes_filters(document, filters):
                continue
            overlap = len(wanted & set(content_terms(_document_text(document))))
            if overlap:
                ranked.append({"doc_id": document["doc_id"], "score": float(overlap)})
        ranked.sort(key=lambda row: (-row["score"], row["doc_id"]))
        return ranked[:k]


def local_sut_factory(documents) -> LocalRetriever:
    """A SUT factory over a fixed document list (the shape the attacks consume)."""
    return LocalRetriever(documents)


def _eval_set_solutions():
    here = pathlib.Path(__file__).resolve().parent
    candidates = []
    env = os.environ.get("RAG_EVAL_SET")
    if env:
        candidates.append(pathlib.Path(env))
    repo = here.parent.parent
    candidates += [repo / "rag-from-scratch" / "eval-set",
                   repo / "rag-from-scratch" / "eval-set" / "solutions"]
    for base in candidates:
        for cand in (base, base / "solutions"):
            if (cand / "corpus.py").is_file() and (cand / "queries.py").is_file():
                return cand
    raise FileNotFoundError(
        "cannot find rag-from-scratch/eval-set; set RAG_EVAL_SET or run from the repo.")


def load_eval_set(seed: int = 0) -> dict:
    """Load the shared eval set: documents, query sets and the flattened queries."""
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import corpus
    import queries

    generated = corpus.generate_corpus(seed)
    query_sets = queries.build_query_sets(generated)
    families = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
    return {
        "documents": generated["documents"],
        "query_sets": query_sets,
        "queries": [q for family in families for q in query_sets.get(family, [])],
    }


def _recall(ids, relevant, k: int) -> float | None:
    """Fraction of the relevant docs present in the top k; None when there are none."""
    relevant = set(relevant)
    if not relevant:
        return None
    return len(relevant & set(list(ids)[:k])) / len(relevant)


# --------------------------------------------------------------------------
# The core (LEARN: not implemented yet; the tests define it)
# --------------------------------------------------------------------------


def perturb_text(text: str, *, seed: int, rate: float) -> str:
    """Return ``text`` with a deterministic character-level perturbation.

    One word in roughly ``rate`` of the words is altered by a single edit: swap two
    adjacent characters, delete, duplicate, or replace a character with the next letter.
    ``rate <= 0`` is the identity; the same seed gives the same output; a word shorter
    than two characters is left alone. Never uses the global RNG.

    LEARN: not implemented yet -- tests/test_rag_attack.py defines it.
    """
    raise NotImplementedError("perturb_text is the learner's core (agent-evals #5)")


def poison_document(query, *, seed: int = 0) -> dict:
    """A synthetic document stuffed with the query's own content terms.

    Returns a corpus-shaped dict whose ``doc_id`` is derived from the query's ``qid`` (so
    it never collides with a real document) and whose title/body repeat the query's content
    terms. It is not in any query's ground truth; the point is to see whether a term-count
    SUT ranks it above the true answer.

    LEARN: not implemented yet -- tests/test_rag_attack.py defines it.
    """
    raise NotImplementedError("poison_document is the learner's core (agent-evals #5)")


def probe(sut_factory, documents, query, *, k: int = 5, rate: float = 0.2, seed: int = 0) -> dict:
    """Run one attack against one query and report what changed.

    Builds the clean result, then the attacked result from the perturbed query over the
    corpus plus the poison document, and returns a dict with EXACTLY these keys:

        qid       -- the query's qid (or None)
        clean     -- list of doc_ids the SUT returned for the clean query
        attacked  -- list of doc_ids for the perturbed query over the poisoned corpus
        relevant  -- list of the query's relevant doc_ids
        dropped   -- True when a relevant doc was found clean and is gone after the attack
        poisoned  -- True when the poison document entered the attacked top-k
        abstained -- True when the attacked result is empty

    ``sut_factory(documents)`` returns a callable ``retrieve(query, k)``.

    LEARN: not implemented yet -- tests/test_rag_attack.py defines it.
    """
    raise NotImplementedError("probe is the learner's core (agent-evals #5)")


def evaluate_attacks(sut_factory, documents, query_sets, *, k: int = 5,
                     rate: float = 0.2, seed: int = 0) -> dict:
    """Attack every query and aggregate, per family and overall.

    Returns ``{"families": {family: report}, "overall": report}`` where each report has
    EXACTLY these keys: ``n``, ``answerable``, ``clean_recall``, ``attacked_recall``,
    ``attack_success`` (fraction of answerable probes where a doc was ``dropped`` or the
    result was ``poisoned``), ``drops``, ``poisons``, and ``abstention`` (fraction of
    no-answer probes that abstained, or None when the family has none). Recall is the mean
    of ``_recall`` over the answerable probes; ``n`` counts every query. The attack reads
    only the query text, never its judgments.

    LEARN: not implemented yet -- tests/test_rag_attack.py defines it.
    """
    raise NotImplementedError("evaluate_attacks is the learner's core (agent-evals #5)")

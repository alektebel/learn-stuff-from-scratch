"""RAG project 8 — Self-RAG: decide to retrieve, grade the evidence, check support.

The [RAG plan](../README.md) row 8. Self-RAG (Asai et al., 2023) is a model *trained* to
emit reflection tokens during decoding: whether to retrieve at all, whether each retrieved
passage is relevant, and whether the answer is supported by the evidence. This module builds
the part that does not need a trained model — the **control loop** around those reflection
decisions — and runs it against a deterministic, injected reflection model, so the whole
thing is offline, seeded and checkable. The prompted/trained model is the deferred variant.

Design decisions (full rationale in the docstrings of the functions):

- **Reflection is an injected interface, not a trained model.** A ``model`` passed to the
  loop answers three questions (retrieve? relevant? supported?). The offline stand-in
  ``OverlapReflectionModel`` answers them by term overlap; the checks script the answers to
  exercise every branch. Cost: the measured numbers are the loop's, not a real model's.
- **No parameterised answering.** When the reflection model says "do not retrieve", the
  loop abstains instead of answering from weights it does not have. Cost: the ``no_retrieve``
  path is always an abstention here; a real model would answer.
- **The answer is extractive.** ``_extractive_answer`` returns the evidence passage's most
  on-topic sentence, so support is checkable without generation. Cost: no fluent answering;
  the support check is about the evidence, not the prose.
- **The loop never sees the judgments.** ``self_rag_answer`` gets the query's text and
  filters, never its ``relevance``; ``evaluate`` scores afterwards. The checker blanks the
  labels and requires the path counts to be unchanged, which catches a peek that moves a
  decision.
- **Standard library only.** Tokenisation, the lexical retriever and the metrics are stdlib;
  the shared eval set is imported the way the sibling stages import it.
"""

from __future__ import annotations

import pathlib
import re
import sys
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")

FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")

STOPWORDS = frozenset((
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "what", "when", "where", "which", "who",
    "why", "with",
))

# --- knobs -----------------------------------------------------------------------
TOP_K = 5            # passages retrieved per attempt
MAX_ATTEMPTS = 2     # answers tried before the loop abstains
MIN_RELEVANT = 1     # relevant passages needed to attempt an answer

# --- provided scaffolding: tokenising and a tiny lexical retriever ----------------

def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def content_terms(text: str) -> list[str]:
    """Query/document content terms: tokens minus stopwords, order preserved."""
    return [t for t in tokenize(text) if t not in STOPWORDS]


def _document_text(document: dict) -> str:
    return f"{document.get('title', '')} {document.get('body', '')}".strip()


_FILTER_KEYS = ("region", "year", "department", "access_level")


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


def _local_rank(terms, documents, filters=None):
    """A deterministic lexical ranker: overlap, tie-broken by doc_id. A document that
    matches no term scores 0 and is dropped."""
    wanted = set(terms)
    ranked = []
    for document in documents:
        if not _passes_filters(document, filters or {}):
            continue
        doc_terms = set(content_terms(_document_text(document)))
        overlap = len(wanted & doc_terms)
        if overlap == 0:
            continue
        ranked.append({
            "doc_id": document["doc_id"],
            "text": _document_text(document),
            "score": overlap / (1.0 + len(doc_terms)),
        })
    ranked.sort(key=lambda row: (-row["score"], row["doc_id"]))
    return ranked


def make_retriever(documents):
    """A ``retriever(query, k) -> passages`` over a fixed document list."""
    def retrieve(query, k=TOP_K, filters=None):
        effective = dict(query.get("filters") or {}) if isinstance(query, dict) else {}
        if filters:
            effective.update(filters)
        terms = content_terms(query["text"] if isinstance(query, dict) else query)
        return _local_rank(terms, documents, effective)[:k]
    return retrieve


def _extractive_answer(query: str, passage: dict) -> str:
    """The passage sentence with the most query content terms (ties: earliest)."""
    wanted = set(content_terms(query))
    sentences = re.split(r"(?<=[.!?])\s+", passage["text"]) or [passage["text"]]
    best = max(sentences, key=lambda s: (len(wanted & set(content_terms(s))), -sentences.index(s)))
    return best.strip()


# --- the injected reflection model (offline stand-in) ----------------------------

class OverlapReflectionModel:
    """A deterministic stand-in for the trained reflection tokens.

    ``retrieve_decision`` always says yes; ``relevance`` says a passage is relevant when it
    shares a content term with the query; ``support`` says the answer is supported when all
    its content terms appear in the passage. Replace it with a real model and the loop is
    unchanged — that is the interface's point.
    """

    def __init__(self, *, threshold: int = 1) -> None:
        self.threshold = threshold

    def retrieve_decision(self, question: str):
        return True

    def relevance(self, question: str, passage: str):
        return len(set(content_terms(question)) & set(content_terms(passage))) >= self.threshold

    def support(self, question: str, answer: str, passage: str):
        answer_terms = set(content_terms(answer))
        return bool(answer_terms) and answer_terms <= set(content_terms(passage))


# --- the Self-RAG control loop (the learner implements the five below) -----------

def should_retrieve(question: str, model) -> bool:
    """Decide whether to retrieve at all.

    Fail-safe: no question content or no model means retrieve rather than guess; an unknown
    or missing decision from the model also means retrieve (retrieval can only add evidence;
    skipping it can only lose it)."""
    if not content_terms(question):
        return False
    if model is None:
        return True
    decision = model.retrieve_decision(question)
    return True if decision is None else bool(decision)


def grade_evidence(question: str, passages, model, *, min_relevant: int = MIN_RELEVANT):
    """Keep the passages the model marks relevant, in retrieval order.

    Nothing is invented and nothing is re-ranked: the list is a subsequence of ``passages``.
    """
    if model is None:
        return list(passages)
    relevant = [p for p in passages if model.relevance(question, p["text"])]
    return relevant if len(relevant) >= min_relevant else []


def check_support(question: str, answer: str, evidence, model) -> bool:
    """True when at least one evidence passage supports the answer.

    The relevance grade and the support grade are different questions: a passage can be
    relevant and still not support the sentence the loop extracted from it."""
    if not answer or not evidence:
        return False
    if model is None:
        return True
    return any(model.support(question, answer, passage["text"]) for passage in evidence)


def self_rag_answer(query, retriever, model, *, k: int = TOP_K,
                    max_attempts: int = MAX_ATTEMPTS) -> dict:
    """Answer one query, or abstain.

    Returns ``{"answer", "evidence", "path", "retrieved", "attempts", "supported"}`` with
    ``path`` one of ``no_retrieve``, ``answered``, ``abstain``. The query's judgments are
    never read here — only ``text`` and ``filters``.
    """
    question = query["text"] if isinstance(query, dict) else query
    result = {"answer": None, "evidence": [], "path": "abstain", "retrieved": [],
              "attempts": 0, "supported": False}

    if not should_retrieve(question, model):
        result["path"] = "no_retrieve"
        return result

    passages = retriever(query, k)
    result["retrieved"] = [p["doc_id"] for p in passages]

    for attempt in range(1, max_attempts + 1):
        result["attempts"] = attempt
        evidence = grade_evidence(question, passages, model)
        if not evidence:
            break
        answer = _extractive_answer(question, evidence[0])
        result["supported"] = check_support(question, answer, evidence[:1], model)
        if result["supported"]:
            result["answer"] = answer
            result["evidence"] = [evidence[0]["doc_id"]]
            result["path"] = "answered"
            return result
        # The draft was not supported: drop that passage and try the next relevant one.
        passages = [p for p in passages if p["doc_id"] != evidence[0]["doc_id"]]

    return result


# --- evaluation on the shared eval set -------------------------------------------

def _eval_set_solutions():
    """Locate ``../eval-set`` (or its solutions/) as a pathlib.Path."""
    import os

    here = pathlib.Path(__file__).resolve().parent
    candidates = []
    env = os.environ.get("RAG_EVAL_SET")
    if env:
        candidates.append(pathlib.Path(env))
    candidates += [here.parent / "eval-set", here / "eval-set",
                   here.parent.parent / "eval-set"]
    for base in candidates:
        for cand in (base / "solutions", base):
            if (cand / "metrics.py").is_file() and (cand / "corpus.py").is_file():
                return cand
    raise FileNotFoundError(
        "cannot find the shared eval set. Expected it at ../eval-set (or "
        "../eval-set/solutions), or set RAG_EVAL_SET.")


def load_eval_set(seed: int = 0) -> dict:
    """Load the shared eval set and a retriever over its corpus."""
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import corpus
    import queries

    generated = corpus.generate_corpus(seed)
    query_sets = queries.build_query_sets(generated)
    return {
        "corpus": generated,
        "documents": generated["documents"],
        "query_sets": query_sets,
        "queries": _flatten(query_sets),
        "retriever": make_retriever(generated["documents"]),
    }


def _flatten(query_sets):
    return [q for family in FAMILIES for q in query_sets.get(family, [])]


def evaluate(query_sets, retriever, model, *, k: int = TOP_K) -> dict:
    """Run the loop over every query and aggregate, per family and overall.

    A query with judgments is answered correctly when the evidence it returns is relevant;
    a ``no_answer`` query is correct when the loop abstains. The loop decides; this function
    only scores, so blanking the labels cannot change a path.
    """
    groups = {family: [] for family in FAMILIES}
    paths = Counter()
    predicted_abstain = {"tp": 0, "fp": 0, "fn": 0}
    for family in FAMILIES:
        for query in query_sets.get(family, []):
            outcome = self_rag_answer(query, retriever, model, k=k)
            paths[outcome["path"]] += 1
            relevant = set(query.get("relevance") or {})
            abstained = outcome["answer"] is None
            if abstained:
                predicted_abstain["tp" if not relevant else "fn"] += 1
            elif not relevant:
                predicted_abstain["fp"] += 1
            correct = (not relevant and abstained) or (bool(relevant) and
                                                       bool(relevant & set(outcome["evidence"])))
            groups[family].append(correct)
    answerable = [c for family in FAMILIES if family != "no_answer" for c in groups[family]]
    overall = (sum(answerable) / len(answerable)) if answerable else 0.0
    precision, recall = _abstention(precision_counts=predicted_abstain)
    return {
        "per_family": {family: (sum(v) / len(v) if v else 0.0) for family, v in groups.items()},
        "answer_accuracy": overall,
        "abstention_precision": precision,
        "abstention_recall": recall,
        "paths": dict(paths),
        "n": sum(len(v) for v in groups.values()),
    }


def _abstention(*, precision_counts):
    tp, fp, fn = precision_counts["tp"], precision_counts["fp"], precision_counts["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


# --- demo ------------------------------------------------------------------------

def demo() -> None:
    data = load_eval_set(0)
    model = OverlapReflectionModel()
    result = evaluate(data["query_sets"], data["retriever"], model)
    print("Self-RAG (offline, overlap reflection model), seed 0")
    print(f"  answer accuracy (answerable): {result['answer_accuracy']:.3f}")
    print(f"  abstention precision/recall:  {result['abstention_precision']:.3f} / "
          f"{result['abstention_recall']:.3f}")
    print(f"  paths: {result['paths']} (n={result['n']})")
    for family in FAMILIES:
        print(f"    {family:<9} correct {result['per_family'][family]:.3f}")
    sample = data["queries"][0]
    outcome = self_rag_answer(sample, data["retriever"], model)
    print(f"  sample {sample['qid']}: path={outcome['path']} "
          f"evidence={outcome['evidence']} answer={outcome['answer']!r}")


if __name__ == "__main__":
    demo()

"""Query sets with relevance judgments (step 0 of the RAG plan).

Five query families, matching `rag-from-scratch/README.md` step 0:

  lexical    - the query names an exact policy code; substring/BM25 should win.
  semantic   - a paraphrase of a topic; only an embedding method should win.
  filtered   - a topic plus metadata constraints ("access control", EMEA, 2025).
  multi_hop  - answers depend on a relation (a person's manager), not on one document.
  no_answer  - nothing in the corpus answers it; a good system returns nothing.

DESIGN DECISION - relevance is graded, not binary.
    nDCG needs grades. A document whose primary topic is the query topic scores 2.0;
    a document that only supports the answer scores 1.0. Cost: every query builder now
    has to say *how* relevant, which is more ground truth to keep honest.

DESIGN DECISION - superseded documents are never relevant.
    This is the single most fragile invariant of the set. The current version answers
    the question; the stale one must not be counted as a hit even though its text still
    matches. `_current()` is the one place that filter lives, and check.py asserts it.

DESIGN DECISION - no-answer queries are constructed, not sampled.
    They are questions about things the corpus genuinely does not contain, so the empty
    relevance is a fact, not a judgement. Cost: they are ungrammatical relative to the
    corpus vocabulary on purpose, and a lexical retriever will abstain for the trivial
    reason that no word matches.

DESIGN DECISION - queries are rebuilt from the corpus, never stored.
    If the generator changes, the judgments move with it. Cost: building the set is
    code, not a frozen file, so this module must stay deterministic.

Run the demo to print a measurement: `python3 solutions/queries.py`.
"""
from __future__ import annotations

from corpus import TOPICS, generate_corpus

# A paraphrase per topic. It deliberately keeps at least one topic word so that a
# lexical baseline never abstains on an answerable query (abstention is reserved for
# the no-answer family); the surrounding words differ from the corpus on purpose.
_SEMANTIC_PARAPHRASES = {
    "access control": "who is allowed into our systems and buildings",
    "data retention": "how long we keep records before deleting them",
    "expense policy": "what we may claim back for costs",
    "vendor onboarding": "the steps to bring a supplier on board",
    "incident response": "what to do when something goes badly wrong",
    "travel reimbursement": "getting money back for trips",
    "encryption standard": "which cipher we must use to protect files",
    "remote work": "the rules for working away from the office",
    "procurement": "how we buy goods and services",
    "audit logging": "the trail of who did what and when",
    "backup recovery": "restoring data after it is lost",
    "on-call rotation": "whose turn it is to be reachable out of hours",
    "customer data": "information we hold about the people we serve",
    "password rotation": "how often secrets must be changed",
    "third-party risk": "danger coming from an outside organisation",
}

_NO_ANSWER = (
    "What is our policy on interstellar freight insurance?",
    "How do I request a zero-gravity yoga allowance?",
    "What is the process for a lunar office relocation?",
    "Who approves submarine fleet purchases?",
    "What is the daily allowance for dragon taming?",
    "Explain the escrow rules for orbital debris cleanup.",
)


def _current(corpus):
    """Documents that are not superseded. The ground truth's single source of truth."""
    return [d for d in corpus["documents"] if not d.get("superseded_by")]


def _by(corpus, predicate):
    """Graded relevance: every current document matching `predicate`, at grade 2.0."""
    return {d["doc_id"]: 2.0 for d in _current(corpus) if predicate(d)}


def build_query_sets(corpus):
    """Return {"lexical": [...], "semantic": [...], "filtered": [...],
    "multi_hop": [...], "no_answer": [...]}; each query is a dict with `qid`, `text`,
    `type`, `filters` and `relevance` (doc_id -> grade)."""
    # TODO: Return the five families. Every answerable relevance must be built from _current() (superseded versions excluded) and every no_answer relevance must be {}; the filtered judgments must satisfy their own region/year filter.
    raise NotImplementedError("build_query_sets")


def all_queries(query_sets):
    """Flatten the dict of lists into one ordered list of queries."""
    out = []
    for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer"):
        out.extend(query_sets[family])
    return out


def main() -> None:
    corpus = generate_corpus(0)
    qs = build_query_sets(corpus)
    total = sum(len(v) for v in qs.values())
    print(f"query families: {{" + ", ".join(f"{k}: {len(v)}" for k, v in qs.items()) + "}")
    print(f"total queries: {total}, all have unique qids: "
          f"{len({q['qid'] for q in all_queries(qs)}) == total}")
    empty = [q["qid"] for q in qs["no_answer"] if q["relevance"]]
    print(f"no-answer queries with non-empty relevance: {empty}")


if __name__ == "__main__":
    main()

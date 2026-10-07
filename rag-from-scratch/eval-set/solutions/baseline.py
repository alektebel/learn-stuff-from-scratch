"""A trivial baseline retriever so the metrics are exercised and non-degenerate.

Deliberately not BM25 and not an embedding model (those are later projects): this scores
a document by how many distinct query tokens it contains and abstains when nothing
matches. It exists to prove the eval set *can* be scored, to give later retrievers a
floor to beat, and to make the no-answer family meaningful.

DESIGN DECISION - metadata filters are applied before scoring, not after.
    The baseline is a stand-in for project 2's metadata-filtered RAG. Post-filtering
    would return fewer than k results when the filter is selective; pre-filtering here
    keeps the comparison honest and mirrors the SQLite metadata store the project uses.
    Cost: filter-selective queries get the full k only if enough documents pass.

DESIGN DECISION - abstention is "no query token matched any candidate".
    That is the weakest defensible rule, and it is enough because the no-answer queries
    contain no corpus vocabulary. Any smarter gate (score threshold, calibration) is
    later project 7's subject. Cost: it abstains on nothing else, so abstention
    precision is high by construction on this set; that is the point of the floor.

DESIGN DECISION - ties break by doc_id ascending.
    Deterministic ordering is required for reproducible eval runs and for check.py.
    Cost: ties are broken arbitrarily with respect to relevance, which is exactly what
    MRR is meant to expose.
"""
from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")

# Grammar and question words only. Topic words ("work", "call", "data") are left in:
# removing them would make the baseline abstain on answerable queries.
STOPWORDS = frozenset("""
a an and are as at be been by can could did do does for from had has have how i if in
into is it its many may might much of on or our please shall should so than that the
their them there these this those to was we were what when which who whom whose why will
with would you your say says require requires explain request process policy policies
document documents
""".split())


def tokenize(text):
    """Lower-cased alphanumeric tokens with stopwords and single characters removed."""
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


class LexicalBaseline:
    """Token-overlap retriever with pre-retrieval metadata filtering and abstention."""

    def __init__(self, corpus):
        self.corpus = corpus
        self._tokens = {
            d["doc_id"]: set(tokenize(d["title"] + " " + d["body"]))
            for d in corpus["documents"]
        }
        self._docs = {d["doc_id"]: d for d in corpus["documents"]}

    def _passes_filters(self, doc, filters):
        if not filters:
            return True
        if "region" in filters and doc["region"] != filters["region"]:
            return False
        if "year" in filters and doc["date"][:4] != str(filters["year"]):
            return False
        if "department" in filters and doc["department"] != filters["department"]:
            return False
        if "access_level" in filters and doc["access_level"] != filters["access_level"]:
            return False
        return True

    def retrieve(self, query, k=10):
        """Return up to k doc_ids, best first. An empty list means "abstain"."""
        tokens = set(tokenize(query["text"]))
        scored = []
        for doc_id, doc_tokens in self._tokens.items():
            if not self._passes_filters(self._docs[doc_id], query.get("filters", {})):
                continue
            score = len(tokens & doc_tokens)
            if score > 0:
                scored.append((score, doc_id))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [doc_id for _score, doc_id in scored[:k]]


def main() -> None:
    from corpus import generate_corpus
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(0)
    queries = all_queries(build_query_sets(corpus))
    baseline = LexicalBaseline(corpus)
    answers = sum(1 for q in queries if baseline.retrieve(q))
    print(f"queries: {len(queries)}, answered by the baseline: {answers}, "
          f"abstained: {len(queries) - answers}")


if __name__ == "__main__":
    main()

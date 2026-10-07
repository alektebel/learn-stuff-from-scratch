"""Synthetic company-docs corpus generator (step 0 of the RAG plan).

Implements the corpus half of `rag-from-scratch/README.md` step 0: a deterministic,
seeded, standard-library-only "company docs" collection that carries the metadata,
version history, tables and knowledge-graph triples the later projects need
(metadata filtering, SQL + vector, graph + vector).

DESIGN DECISION - synthetic and seeded instead of a downloaded corpus.
    The environment has no network and no downloadable models. A synthetic corpus also
    lets the ground truth be *constructed* rather than guessed: we know which document
    is superseded, which topic a paraphrase points at, and which triples connect. Cost:
    the vocabulary is controlled and the text is repetitive, so the absolute scores here
    do not transfer to a real corpus; only the comparison between methods does.

DESIGN DECISION - superseded documents stay in the corpus.
    A real store cannot delete an old policy; audits and citations still need it, and
    retrieval must learn to rank the current version first. Deleting them would turn
    versioning into a non-problem. Cost: recall alone still looks fine when the stale
    version wins, which is exactly why MRR and nDCG are reported alongside it.

DESIGN DECISION - tables and triples live in the same generator.
    Later projects need the same entities and facts the documents describe, so a
    question answered by SQL and one answered by retrieval can be compared on one eval
    set. Cost: the generator is heavier than a text-only one, and any change to it moves
    every project's ground truth, so this file is frozen once step 0 is accepted.

Run the demo to print a measurement: `python3 solutions/corpus.py`.
"""
from __future__ import annotations

import random

DEPARTMENTS = ("Engineering", "Finance", "Legal", "Sales", "HR", "Security")
REGIONS = ("EMEA", "AMER", "APAC", "GLOBAL")
ACCESS_LEVELS = ("public", "internal", "confidential", "restricted")
AUTHORS = (
    "A. Rivera", "B. Okafor", "C. Lindqvist", "D. Haddad",
    "E. Nguyen", "F. Moreau", "G. Petrov", "H. Sato",
)
TOPICS = (
    "access control", "data retention", "expense policy", "vendor onboarding",
    "incident response", "travel reimbursement", "encryption standard",
    "remote work", "procurement", "audit logging", "backup recovery",
    "on-call rotation", "customer data", "password rotation", "third-party risk",
)
YEARS = (2023, 2024, 2025, 2026)
BASE_DOCS = 60
REVISION_EVERY = 10  # one superseding revision for every 10th base document


def generate_corpus(seed):
    """Return a fully deterministic corpus dict for `seed`.

    The same seed always yields the same structure and the same text: every random
    choice comes from `random.Random(seed)` and nothing iterates a set. Two calls with
    the same seed are equal under `json.dumps(..., sort_keys=True)`; a different seed
    changes the documents.
    """
    # TODO: Use random.Random(seed) only; build BASE_DOCS documents in index order, append a revision for every REVISION_EVERY-th document, then emit entities, typed relations and the tables. Never iterate a set: the output must be byte-identical for the same seed.
    raise NotImplementedError("generate_corpus")


def main() -> None:
    corpus = generate_corpus(0)
    current = [d for d in corpus["documents"] if not d.get("superseded_by")]
    superseded = [d for d in corpus["documents"] if d.get("superseded_by")]
    print(f"seed 0: {len(corpus['documents'])} documents "
          f"({len(superseded)} superseded, {len(current)} current)")
    print(f"entities: {len(corpus['entities'])}, relations: {len(corpus['relations'])}, "
          f"tables: {sorted(corpus['tables'])}")
    import json
    a = json.dumps(generate_corpus(7), sort_keys=True)
    b = json.dumps(generate_corpus(7), sort_keys=True)
    c = json.dumps(generate_corpus(8), sort_keys=True)
    print(f"determinism: same seed equal = {a == b}, different seed changes = {a != c}")


if __name__ == "__main__":
    main()

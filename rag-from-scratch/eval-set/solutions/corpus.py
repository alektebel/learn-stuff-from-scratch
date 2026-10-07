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
    rng = random.Random(seed)
    documents = []
    code_seq = {dept: 0 for dept in DEPARTMENTS}

    for i in range(BASE_DOCS):
        dept = DEPARTMENTS[i % len(DEPARTMENTS)]
        topic = TOPICS[i % len(TOPICS)]
        region = REGIONS[i % len(REGIONS)]
        access = ACCESS_LEVELS[i % len(ACCESS_LEVELS)]
        author = AUTHORS[i % len(AUTHORS)]
        year = YEARS[i % len(YEARS)]
        month = (i % 12) + 1
        day = (i % 27) + 1
        code_seq[dept] += 1
        code = f"POL-{dept[:3].upper()}-{year}-{code_seq[dept]:03d}"
        doc_id = f"DOC-{len(documents):04d}"
        title = f"{dept} {topic} standard {year}"
        documents.append({
            "doc_id": doc_id,
            "title": title,
            "body": (
                f"{title} (code {code}). {dept} document for {region}, effective "
                f"{year:04d}-{month:02d}-{day:02d}, owner {author}. Scope and controls "
                f"for {topic}. Access level {access}. Review every year; see {code}."
            ),
            "department": dept,
            "region": region,
            "author": author,
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "access_level": access,
            "version": 1,
            "supersedes": None,
            "superseded_by": None,
            "topics": [topic],
            "code": code,
        })

    # Version chains: the old document keeps its facts but is explicitly superseded.
    for i, old in enumerate(list(documents)):
        if i % REVISION_EVERY != 0:
            continue
        year = min(int(old["date"][:4]) + 1, YEARS[-1])
        month = (i % 12) + 1
        day = (i % 27) + 1
        new_id = f"DOC-{len(documents):04d}"
        new = {
            "doc_id": new_id,
            "title": old["title"] + " (revision 2)",
            "body": (
                f"Revision 2 of {old['doc_id']} ({old['code']}). {old['department']} "
                f"document for {old['region']}, effective {year:04d}-{month:02d}-{day:02d}, "
                f"owner {AUTHORS[(i + 3) % len(AUTHORS)]}. Scope and controls for "
                f"{old['topics'][0]}. This revision supersedes {old['doc_id']}."
            ),
            "department": old["department"],
            "region": old["region"],
            "author": AUTHORS[(i + 3) % len(AUTHORS)],
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "access_level": old["access_level"],
            "version": old["version"] + 1,
            "supersedes": old["doc_id"],
            "superseded_by": None,
            "topics": list(old["topics"]),
            "code": old["code"],
        }
        old["superseded_by"] = new["doc_id"]
        documents.append(new)

    # Knowledge graph: people, departments and topics as entities, plus typed triples.
    entities = []
    for idx, name in enumerate(AUTHORS):
        entities.append({"id": f"PER-{idx:02d}", "name": name, "type": "person"})
    for idx, dept in enumerate(DEPARTMENTS):
        entities.append({"id": f"DEP-{idx:02d}", "name": dept, "type": "department"})
    for idx, topic in enumerate(TOPICS):
        entities.append({"id": f"TOP-{idx:02d}", "name": topic, "type": "topic"})

    relations = []
    for idx in range(len(AUTHORS)):
        relations.append([f"PER-{idx:02d}", "works_in", f"DEP-{idx % len(DEPARTMENTS):02d}"])
    for idx in range(len(AUTHORS) - 1):
        relations.append([f"PER-{idx:02d}", "reports_to", f"PER-{idx + 1:02d}"])
    for idx, _topic in enumerate(TOPICS):
        relations.append([f"DEP-{idx % len(DEPARTMENTS):02d}", "owns", f"TOP-{idx:02d}"])
    relations.sort()

    # Structured facts for the SQL + vector project.
    tables = {
        "revenue_by_region": {
            "columns": ["region", "year", "quarter", "amount_usd"],
            "rows": [
                [region, year, quarter, rng.randrange(100, 900) * 1000]
                for region in REGIONS
                for year in (2024, 2025)
                for quarter in (1, 2, 3, 4)
            ],
        },
        "headcount_by_department": {
            "columns": ["department", "year", "headcount"],
            "rows": [[dept, 2025, rng.randrange(5, 200)] for dept in DEPARTMENTS],
        },
        "vendors": {
            "columns": ["vendor_id", "name", "region", "risk_level"],
            "rows": [
                ["VEN-001", "Northwind Logistics", "EMEA", "low"],
                ["VEN-002", "Acme Cloud", "AMER", "high"],
                ["VEN-003", "Sakura Components", "APAC", "medium"],
                ["VEN-004", "Globex Services", "GLOBAL", "high"],
            ],
        },
    }

    return {
        "seed": seed,
        "generated_by": "corpus.generate_corpus",
        "documents": documents,
        "entities": entities,
        "relations": relations,
        "tables": tables,
    }


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

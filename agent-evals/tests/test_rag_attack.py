"""Tests for agent-evals #5: the RAG adversarial harness.

LEARN mode: the four attack entry points (perturb_text, poison_document, probe,
evaluate_attacks) are not written yet; every test that needs them is decorated
``xfail(raises=NotImplementedError, reason="core not implemented")`` and turns into a real
check once the learner implements it. The SUT adapters, the eval-set loader and the
token/metric helpers are provided infrastructure and their tests pass today.

Map to SPEC.md:
    A1 -> test_perturb_*                       L1 -> test_perturb_identity_at_rate_zero
    A2 -> test_poison_document_shape           L2 -> test_perturb_short_words_no_crash
    A3 -> test_probe_*                         L3 -> test_evaluate_attacks_deterministic
    A4 -> test_evaluate_attacks_report_shape   L4 -> test_probe_oracle_never_drops
    A5 -> test_attack_has_teeth_on_lexical_sut L5 -> test_evaluate_attacks_counts_abstention
"""

import sys
from pathlib import Path

import pytest

# Make the agent-evals project importable no matter where pytest is rooted.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rag_attack  # noqa: E402

XFAIL_CORE = pytest.mark.xfail(
    raises=NotImplementedError, reason="core not implemented"
)

# --- hand-built corpus and queries (no eval set needed) -------------------------

DOCS = [
    {"doc_id": "D1", "title": "access control policy",
     "body": "access control policy requires manager approval",
     "region": "EMEA", "date": "2025-01-01", "department": "Security",
     "access_level": "internal"},
    {"doc_id": "D2", "title": "payroll calendar",
     "body": "payroll calendar year end schedule",
     "region": "AMER", "date": "2025-02-01", "department": "HR",
     "access_level": "internal"},
    {"doc_id": "D3", "title": "access control permissions",
     "body": "access control permissions matrix",
     "region": "EMEA", "date": "2024-06-01", "department": "Security",
     "access_level": "public"},
]

LEXICAL = {"qid": "Q1", "text": "access control policy", "type": "lexical",
           "filters": {}, "relevance": {"D1": 1}}
NO_ANSWER = {"qid": "Q2", "text": "zzz nowhere term", "type": "no_answer",
             "filters": {}, "relevance": {}}
QUERY_SETS = {"lexical": [LEXICAL], "no_answer": [NO_ANSWER]}


def fragile_factory(documents):
    """A SUT that only answers the exact clean query and collapses on any perturbation."""
    def retrieve(query, k=5):
        text = query["text"] if isinstance(query, dict) else query
        if text == "access control policy":
            return [{"doc_id": "D1", "score": 1.0}][:k]
        return []
    return retrieve


def first_doc_factory(documents):
    """A SUT unaffected by the text: always D1 first, then the rest. The oracle."""
    def retrieve(query, k=5):
        ids = [d["doc_id"] for d in documents]
        order = ["D1"] + [i for i in ids if i != "D1"]
        return [{"doc_id": i, "score": 1.0} for i in order][:k]
    return retrieve


# --- infrastructure: these must pass now ----------------------------------------

def test_tokenize_and_content_terms():
    assert rag_attack.tokenize("Access Control, 2025!") == ["access", "control", "2025"]
    assert rag_attack.content_terms("of the policy and control") == ["policy", "control"]


def test_local_retriever_ranks_by_overlap():
    sut = rag_attack.local_sut_factory(DOCS)
    ranked = [r["doc_id"] for r in sut(LEXICAL, 5)]
    assert ranked and ranked[0] in {"D1", "D3"}, "a lexical match must rank first"
    assert "D2" not in ranked, "an unrelated document must be dropped"
    assert sut(LEXICAL, 1) == sut(LEXICAL, 1), "the SUT must be deterministic"


@XFAIL_CORE
def test_load_eval_set_shape():
    try:
        data = rag_attack.load_eval_set(0)
    except FileNotFoundError:
        pytest.skip("rag-from-scratch/eval-set not available from this checkout")
    assert data["documents"]
    assert data["queries"]
    assert set(data["query_sets"]) >= {"lexical", "no_answer"}


# --- core: xfail until the learner implements -----------------------------------

@XFAIL_CORE
def test_perturb_identity_at_rate_zero():
    """L1/A1: rate 0 is the identity, so the attack is a no-op."""
    assert rag_attack.perturb_text("access control policy", seed=0, rate=0.0) == \
        "access control policy"


@XFAIL_CORE
def test_perturb_is_deterministic():
    """A1: the same seed gives the same perturbation, every call."""
    a = rag_attack.perturb_text("access control policy matrix", seed=3, rate=1.0)
    b = rag_attack.perturb_text("access control policy matrix", seed=3, rate=1.0)
    assert a == b


@XFAIL_CORE
def test_perturb_changes_the_text():
    """A1: at rate 1 every long word is altered, so the text is not the original."""
    text = "access control policy matrix"
    out = rag_attack.perturb_text(text, seed=1, rate=1.0)
    assert out != text
    assert len(out.split()) == len(text.split()), "word count must be preserved"


@XFAIL_CORE
def test_perturb_short_words_no_crash():
    """L2/A1: one-character words survive untouched and nothing raises."""
    out = rag_attack.perturb_text("a b c access", seed=0, rate=1.0)
    assert out.split()[:3] == ["a", "b", "c"]


@XFAIL_CORE
def test_poison_document_shape():
    """A2: the poison is a corpus-shaped, query-stuffed document outside the ground truth."""
    poison = rag_attack.poison_document(LEXICAL, seed=0)
    assert poison["doc_id"] not in LEXICAL["relevance"]
    assert poison["doc_id"].startswith("ADV-")
    text = f"{poison['title']} {poison['body']}"
    assert {"access", "control", "policy"} <= set(rag_attack.content_terms(text))


@XFAIL_CORE
def test_probe_reports_clean_and_attacked():
    """A3: probe returns the report keys and both result lists."""
    out = rag_attack.probe(first_doc_factory, DOCS, LEXICAL, k=3, rate=0.2, seed=0)
    assert set(out) == {"qid", "clean", "attacked", "relevant", "dropped",
                        "poisoned", "abstained"}
    assert out["clean"] and out["attacked"]
    assert out["relevant"] == ["D1"]


@XFAIL_CORE
def test_probe_flags_a_drop():
    """A3: a SUT that collapses on the perturbation reports dropped=True."""
    out = rag_attack.probe(fragile_factory, DOCS, LEXICAL, k=3, rate=1.0, seed=0)
    assert out["dropped"] is True, "the relevant doc left the top-k after the perturbation"
    assert out["abstained"] is True


@XFAIL_CORE
def test_probe_flags_poison():
    """A3: a term-count SUT ranks the stuffed poison first, without dropping D1."""
    out = rag_attack.probe(rag_attack.local_sut_factory, DOCS, LEXICAL, k=5,
                           rate=0.0, seed=0)
    assert out["poisoned"] is True
    assert out["dropped"] is False, "D1 is still in the top-k; the poisoning is the failure"


@XFAIL_CORE
def test_probe_oracle_never_drops():
    """L4: a SUT that returns the true doc first is never marked dropped."""
    out = rag_attack.probe(first_doc_factory, DOCS, LEXICAL, k=1, rate=1.0, seed=0)
    assert out["dropped"] is False
    assert out["poisoned"] is False


@XFAIL_CORE
def test_evaluate_attacks_report_shape():
    """A4: per-family and overall reports carry exactly the specified keys."""
    report = rag_attack.evaluate_attacks(rag_attack.local_sut_factory, DOCS, QUERY_SETS,
                                         k=5, rate=0.2, seed=0)
    keys = {"n", "answerable", "clean_recall", "attacked_recall", "attack_success",
            "drops", "poisons", "abstention"}
    assert set(report["families"]) == {"lexical", "no_answer"}
    assert set(report["overall"]) == keys
    assert set(report["families"]["lexical"]) == keys
    assert report["overall"]["n"] == 2
    assert report["overall"]["answerable"] == 1


@XFAIL_CORE
def test_evaluate_attacks_counts_abstention():
    """L5/A4: no-answer probes are scored by abstention, not recall."""
    report = rag_attack.evaluate_attacks(fragile_factory, DOCS, QUERY_SETS,
                                         k=5, rate=0.2, seed=0)
    assert report["families"]["no_answer"]["abstention"] == 1.0
    assert report["families"]["no_answer"]["answerable"] == 0
    assert report["families"]["no_answer"]["clean_recall"] is None or \
        report["families"]["no_answer"]["clean_recall"] == 0.0


@XFAIL_CORE
def test_evaluate_attacks_deterministic():
    """L3: the same seed gives the same report, every call."""
    a = rag_attack.evaluate_attacks(rag_attack.local_sut_factory, DOCS, QUERY_SETS, seed=5)
    b = rag_attack.evaluate_attacks(rag_attack.local_sut_factory, DOCS, QUERY_SETS, seed=5)
    assert a == b


@XFAIL_CORE
def test_attack_has_teeth_on_lexical_sut():
    """A5: recall stays 1.0 while the poison enters — the failure recall cannot see."""
    report = rag_attack.evaluate_attacks(rag_attack.local_sut_factory, DOCS, QUERY_SETS,
                                         k=5, rate=0.2, seed=0)
    lexical = report["families"]["lexical"]
    assert lexical["clean_recall"] == 1.0
    assert lexical["attack_success"] == 1.0, "the poison must be detected as a success"
    assert lexical["poisons"] >= 1

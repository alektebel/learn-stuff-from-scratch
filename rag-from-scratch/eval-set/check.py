"""
Progress checker for the RAG step-0 evaluation-set templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checks are deliberately adversarial: they hand-compute the metric values, they
construct the limit cases (empty relevance, duplicate hits, k > n, no-answer queries)
rather than hoping random data hits them, and they assert the two ground-truth
invariants a RAG eval set lives or dies by — superseded documents are never relevant,
and a no-answer query has empty relevance.
"""

import os
import pathlib
import shutil
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def tmpdir() -> str:
    return tempfile.mkdtemp(prefix="rag-evalset-check-")


# ---------------------------------------------------------------------------
# Steps 1-2: corpus.py
# ---------------------------------------------------------------------------

def check_corpus_determinism() -> None:
    import json

    from corpus import generate_corpus

    a = json.dumps(generate_corpus(123), sort_keys=True)
    b = json.dumps(generate_corpus(123), sort_keys=True)
    c = json.dumps(generate_corpus(124), sort_keys=True)
    assert a == b, (
        "the same seed produced two different corpora: the generator must use "
        "random.Random(seed), never the global random module or an unseeded source")
    assert a != c, (
        "two different seeds produced byte-identical corpora: the seed is not driving "
        "the choices (is it actually passed to random.Random?)")


def check_corpus_structure() -> None:
    from corpus import generate_corpus

    corpus = generate_corpus(7)
    docs = corpus["documents"]
    assert len(docs) >= 40, f"a company corpus of {len(docs)} documents is too small for k=10"
    required = {
        "doc_id", "title", "body", "department", "region", "author", "date",
        "access_level", "version", "supersedes", "superseded_by", "topics", "code",
    }
    for d in docs:
        missing = required - set(d)
        assert not missing, f"document {d.get('doc_id')} is missing metadata {sorted(missing)}"
        assert d["topics"], f"{d['doc_id']} has no topics; semantic queries need them"
        assert d["date"][4] == "-", f"{d['doc_id']} date {d['date']!r} is not ISO yyyy-mm-dd"

    ids = {d["doc_id"] for d in docs}
    assert len(ids) == len(docs), "duplicate doc_id: ground truth by id would be ambiguous"
    superseded = [d for d in docs if d["superseded_by"]]
    assert superseded, (
        "no document is marked superseded: the version chains were not built, so the "
        "hardest ground-truth invariant is never exercised")
    for old in superseded:
        assert old["superseded_by"] in ids, f"{old['doc_id']} points at a missing newer version"
        new = next(d for d in docs if d["doc_id"] == old["superseded_by"])
        assert new["supersedes"] == old["doc_id"], (
            f"{old['doc_id']} and {new['doc_id']} disagree about the version chain")
        assert new["superseded_by"] is None, f"{new['doc_id']} is both newest and superseded"
        assert new["date"] >= old["date"], (
            f"revision {new['doc_id']} predates the document it supersedes")
        assert new["version"] > old["version"], "a revision must increase the version number"

    assert len(corpus["tables"]) >= 2, "the SQL project needs more than one table"
    for name, table in corpus["tables"].items():
        assert table["rows"], f"table {name} is empty"
        width = len(table["columns"])
        assert all(len(row) == width for row in table["rows"]), (
            f"table {name} has rows of the wrong width")
        assert table["columns"], f"table {name} has no column names"

    entity_ids = {e["id"] for e in corpus["entities"]}
    assert len(entity_ids) == len(corpus["entities"]), "duplicate entity id"
    assert len(corpus["entities"]) >= 10, "the graph project needs a non-trivial entity set"
    for s, _p, o in corpus["relations"]:
        assert s in entity_ids and o in entity_ids, (
            f"relation ({s}, {_p}, {o}) references an unknown entity id")
    assert any(p == "reports_to" for _s, p, _o in corpus["relations"]), (
        "no reports_to relation: the multi-hop query family has nothing to traverse")


# ---------------------------------------------------------------------------
# Steps 3-4: queries.py
# ---------------------------------------------------------------------------

def check_query_families() -> None:
    from corpus import generate_corpus
    from queries import all_queries, build_query_sets

    query_sets = build_query_sets(generate_corpus(3))
    assert set(query_sets) == {"lexical", "semantic", "filtered", "multi_hop", "no_answer"}, (
        f"expected the five query families, got {sorted(query_sets)}")
    minimum = {"lexical": 4, "semantic": 3, "filtered": 2, "multi_hop": 1, "no_answer": 4}
    for family, low in minimum.items():
        assert len(query_sets[family]) >= low, (
            f"family {family!r} has {len(query_sets[family])} queries, want at least {low}")
    allq = all_queries(query_sets)
    qids = [q["qid"] for q in allq]
    assert len(set(qids)) == len(qids), "duplicate qids: per-query results would overwrite"
    for q in allq:
        missing = {"qid", "text", "type", "filters", "relevance"} - set(q)
        assert not missing, f"{q.get('qid')} is missing {sorted(missing)}"
        assert q["text"].strip(), f"{q['qid']} has empty query text"


def check_ground_truth_invariants() -> None:
    from corpus import generate_corpus
    from queries import build_query_sets

    corpus = generate_corpus(5)
    docs = {d["doc_id"]: d for d in corpus["documents"]}
    superseded = {d["doc_id"] for d in corpus["documents"] if d["superseded_by"]}
    assert superseded, "no superseded documents to test the exclusion invariant against"
    query_sets = build_query_sets(corpus)

    for family, queries in query_sets.items():
        for q in queries:
            for doc_id, grade in q["relevance"].items():
                assert doc_id in docs, f"{q['qid']} refers to unknown document {doc_id}"
                assert doc_id not in superseded, (
                    f"{q['qid']} marks superseded document {doc_id} as relevant: the "
                    "ground truth must exclude stale versions, or a retriever is rewarded "
                    "for returning the version it should replace")
                assert grade > 0, f"{q['qid']} gives {doc_id} a non-positive grade"
            if family == "no_answer":
                assert q["relevance"] == {}, (
                    f"{q['qid']} is a no-answer query but its relevance is non-empty: "
                    "abstention recall is then measured against the wrong answer")
            else:
                assert q["relevance"], f"{q['qid']} is answerable but has no relevant documents"

    for q in query_sets["filtered"]:
        assert q["filters"], f"{q['qid']} is a filtered query with no filters"
        for doc_id in q["relevance"]:
            doc = docs[doc_id]
            assert doc["region"] == q["filters"]["region"], (
                f"{q['qid']} relevance violates its own region filter")
            assert doc["date"][:4] == str(q["filters"]["year"]), (
                f"{q['qid']} relevance violates its own year filter")

    for q in query_sets["lexical"]:
        code = q["text"].split()[2]
        expected = {
            d["doc_id"]: 2.0
            for d in corpus["documents"]
            if d["code"] == code and d["doc_id"] not in superseded
        }
        assert q["relevance"] == expected, (
            f"{q['qid']} relevance does not match the current documents carrying {code}: "
            f"got {sorted(q['relevance'])}, expected {sorted(expected)}")


# ---------------------------------------------------------------------------
# Steps 5-10: metrics.py
# ---------------------------------------------------------------------------

def _close(got, want, what):
    assert abs(got - want) < 1e-12, f"{what}: got {got!r}, expected {want!r}"


def check_recall_and_mrr() -> None:
    from metrics import mrr, recall_at_k

    ranked = ["a", "b", "c", "d", "e"]
    relevance = {"b": 2.0, "d": 2.0, "x": 1.0}
    _close(recall_at_k(ranked, relevance, 2), 1 / 3, "recall@2")
    _close(recall_at_k(ranked, relevance, 5), 2 / 3, "recall@5")
    _close(recall_at_k(ranked, relevance, 0), 0.0, "recall@0")
    _close(mrr(ranked, relevance), 0.5, "MRR (first hit at rank 2)")
    _close(mrr(["x", "a"], {"a": 1.0}), 0.5, "MRR (first hit at rank 2)")
    _close(mrr(["a"], {"a": 1.0}), 1.0, "MRR (first hit at rank 1)")
    _close(mrr(["z"], {"a": 1.0}), 0.0, "MRR (no hit)")
    # A duplicated document in the top k must not be counted twice.
    _close(recall_at_k(["a", "a", "b"], {"a": 2.0}, 2), 1.0, "recall@2 with a duplicate")


def check_ndcg() -> None:
    import math

    from metrics import ndcg_at_k

    ranked = ["b", "a", "c"]
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    gain = lambda g: 2.0 ** g - 1.0
    discount = lambda rank: 1.0 / math.log2(rank + 1)
    dcg = sum(gain(relevance[d]) * discount(r) for r, d in enumerate(ranked, start=1))
    idcg = sum(gain(g) * discount(r)
               for r, g in enumerate(sorted(relevance.values(), reverse=True), start=1))
    _close(ndcg_at_k(ranked, relevance, 3), dcg / idcg, "nDCG@3 on a hand-computed ranking")
    _close(ndcg_at_k(["a", "b", "c"], relevance, 3), 1.0, "nDCG@3 of the ideal order")
    # The log discount must change the answer: without it this ranking scores 0.8.
    discounted = ndcg_at_k(["c", "a", "b"], relevance, 2)
    assert abs(discounted - 0.8) > 0.05, (
        f"nDCG@2 of a bad ranking came out {discounted:.4f}, indistinguishable from the "
        "no-discount value 0.8: apply 1/log2(rank + 1) per position")


def check_metric_edges() -> None:
    from metrics import mrr, ndcg_at_k, recall_at_k

    _close(recall_at_k([], {}, 10), 0.0, "recall with empty relevance")
    _close(mrr([], {}), 0.0, "MRR with empty relevance")
    _close(ndcg_at_k(["a"], {}, 10), 0.0, "nDCG with empty relevance")
    _close(ndcg_at_k(["a"], {"a": 1.0}, 0), 0.0, "nDCG@0")
    _close(recall_at_k(["a", "b", "c"], {"a": 1.0, "b": 1.0}, 100), 1.0, "recall with k > n")
    _close(ndcg_at_k(["a", "b"], {"a": 1.0, "b": 1.0}, 100), 1.0, "nDCG with k > n")
    # Ties: equal grades in either order must both be ideal.
    _close(ndcg_at_k(["a", "b"], {"a": 1.0, "b": 1.0}, 2), 1.0, "nDCG with tied grades (a,b)")
    _close(ndcg_at_k(["b", "a"], {"a": 1.0, "b": 1.0}, 2), 1.0, "nDCG with tied grades (b,a)")


def check_abstention() -> None:
    from metrics import abstention_metrics

    # Asymmetric on purpose: two no-answer queries answered, one no-answer abstained, and
    # one answerable query abstained. A symmetric input lets a bug that swaps "empty means
    # abstain" for "non-empty means abstain" cancel itself out.
    queries = [
        {"qid": "n1", "type": "no_answer", "relevance": {}},
        {"qid": "n2", "type": "no_answer", "relevance": {}},
        {"qid": "n3", "type": "no_answer", "relevance": {}},
        {"qid": "a1", "type": "lexical", "relevance": {"d1": 2.0}},
        {"qid": "a2", "type": "lexical", "relevance": {"d2": 2.0}},
        {"qid": "a3", "type": "semantic", "relevance": {"d3": 2.0}},
        {"qid": "a4", "type": "semantic", "relevance": {"d4": 2.0}},
    ]
    predictions = {"n1": [], "n2": ["d3"], "n3": ["d3"],
                   "a1": ["d1"], "a2": ["d2"], "a3": ["d3"], "a4": []}
    got = abstention_metrics(predictions, queries)
    assert (got["tp"], got["fp"], got["fn"], got["tn"], got["abstentions"]) == (1, 1, 2, 3, 2), (
        f"abstention counts wrong: got {got}. A returned document on a no-answer query is a "
        "false negative, not a correct abstention; abstaining on an answerable query is a "
        "false positive.")
    _close(got["precision"], 0.5, "abstention precision over chosen abstentions")
    _close(got["recall"], 1 / 3, "abstention recall over no-answer queries")


def check_latency() -> None:
    from metrics import latency_stats

    stats = latency_stats([float(i * 10) for i in range(1, 11)])
    assert stats["count"] == 10, f"count wrong: {stats['count']}"
    _close(stats["mean"], 55.0, "latency mean")
    _close(stats["median"], 50.0, "latency median")
    _close(stats["p95"], 100.0, "latency p95")
    _close(stats["max"], 100.0, "latency max")
    empty = latency_stats([])
    assert empty == {"count": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}, (
        f"latency_stats of an empty sample should be all zeros, got {empty}")


def check_paired_comparison() -> None:
    from metrics import mcnemar_exact, paired_bootstrap_ci, wilson_interval

    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0 and 0.0 < hi < 1.0, f"Wilson(0/10) should start at exactly 0: {(lo, hi)}"
    lo, hi = wilson_interval(10, 10)
    assert hi == 1.0 and 0.0 < lo < 1.0, f"Wilson(10/10) should end at exactly 1: {(lo, hi)}"
    _close(mcnemar_exact(5, 0), 2 * (1 / 2 ** 5), "exact McNemar(b=5, c=0)")
    _close(mcnemar_exact(0, 0), 1.0, "exact McNemar with no discordant pairs")

    a = [1.0, 1.0, 1.0, 0.0]
    b = [0.0, 0.0, 0.0, 0.0]
    first = paired_bootstrap_ci(a, b, seed=1)
    second = paired_bootstrap_ci(a, b, seed=1)
    assert first == second, "the same inputs and seed must give the same interval"
    _close(first[0], 0.75, "mean paired difference")
    assert first[1] <= first[0] <= first[2], f"the CI must bracket the mean: {first}"
    try:
        paired_bootstrap_ci([1.0], [1.0, 0.0])
        raise AssertionError(
            "paired_bootstrap_ci accepted two differently sized score lists: pairing "
            "requires one score per query for each variant")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Steps 11-12: baseline.py
# ---------------------------------------------------------------------------

def check_baseline_mechanics() -> None:
    from baseline import LexicalBaseline
    from corpus import generate_corpus
    from metrics import mrr, recall_at_k
    from queries import build_query_sets

    corpus = generate_corpus(11)
    query_sets = build_query_sets(corpus)
    baseline = LexicalBaseline(corpus)

    lexical = query_sets["lexical"][0]
    assert baseline.retrieve(lexical, 10) == baseline.retrieve(lexical, 10), (
        "the baseline is not deterministic: identical input gave different rankings")
    assert len(baseline.retrieve(lexical, 1)) <= 1, "retrieve ignored the k=1 limit"
    broad = {"qid": "X", "text": "access control EMEA 2025 policy", "filters": {},
             "relevance": {}}
    assert len(baseline.retrieve(broad, 1)) <= 1, "retrieve ignored the k=1 limit on a broad query"
    assert len(baseline.retrieve(broad, 3)) <= 3, "retrieve ignored the k=3 limit"

    for q in query_sets["filtered"]:
        for doc_id in baseline.retrieve(q, 10):
            doc = next(d for d in corpus["documents"] if d["doc_id"] == doc_id)
            assert doc["region"] == q["filters"]["region"] and doc["date"][:4] == str(
                q["filters"]["year"]), (
                f"baseline returned {doc_id} for {q['qid']}, violating the metadata filter: "
                "apply filters before scoring")

    recalls = [recall_at_k(baseline.retrieve(q, 10), q["relevance"], 10) for q in query_sets["lexical"]]
    mrrs = [mrr(baseline.retrieve(q, 10), q["relevance"]) for q in query_sets["lexical"]]
    mean_recall = sum(recalls) / len(recalls)
    mean_mrr = sum(mrrs) / len(mrrs)
    assert mean_recall >= 0.8, (
        f"baseline lexical recall@10 is {mean_recall:.2f}: an exact policy code should be "
        "easy to match, so the metrics are not being exercised")
    assert mean_mrr > 0.3, (
        f"baseline lexical MRR is {mean_mrr:.2f}: too low to show the metrics discriminate")


def check_baseline_abstention() -> None:
    from baseline import LexicalBaseline
    from corpus import generate_corpus
    from metrics import abstention_metrics
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(13)
    queries = all_queries(build_query_sets(corpus))
    baseline = LexicalBaseline(corpus)
    predictions = {q["qid"]: baseline.retrieve(q, 10) for q in queries}
    metrics = abstention_metrics(predictions, queries)
    assert metrics["fn"] == 0 and metrics["recall"] == 1.0, (
        f"the baseline answered a no-answer query (fn={metrics['fn']}): abstention must be "
        "decided when nothing matches, not left to the metric")
    assert metrics["precision"] >= 0.99, (
        f"the baseline abstained on answerable queries (fp={metrics['fp']}): the no-answer "
        "family is the only one an empty result should be correct for")


# ---------------------------------------------------------------------------
# Step 13: metrics.evaluate end to end
# ---------------------------------------------------------------------------

def check_evaluate_integration() -> None:
    from baseline import LexicalBaseline
    from corpus import generate_corpus
    from metrics import evaluate
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(2)
    queries = all_queries(build_query_sets(corpus))
    baseline = LexicalBaseline(corpus)
    predictions = {q["qid"]: baseline.retrieve(q, 10) for q in queries}
    result = evaluate(predictions, queries, k=10,
                      latencies=[float(i) for i in range(len(queries))])
    assert result["k"] == 10
    assert set(result["by_type"]) == {"lexical", "semantic", "filtered", "multi_hop", "no_answer"}, (
        f"evaluate() lost a query family: {sorted(result['by_type'])}")
    for family, scores in result["by_type"].items():
        for key, value in scores.items():
            assert 0.0 <= value <= 1.0, f"by_type[{family}][{key}] = {value} is outside [0, 1]"
    assert 0.0 <= result["overall"]["recall@k"] <= 1.0
    assert set(result["per_query"]) == {q["qid"] for q in queries}, "per_query is incomplete"
    assert result["abstention"]["recall"] == 1.0, (
        "evaluate() should report the same abstention recall as abstention_metrics()")
    assert result["latency"]["count"] == len(queries)


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("corpus.py", "same seed -> identical corpus, new seed -> new corpus", check_corpus_determinism),
    ("corpus.py", "document metadata, version chains, tables, triples", check_corpus_structure),
    ("queries.py", "all five query families, unique qids", check_query_families),
    ("queries.py", "no-answer empty; superseded never relevant; filtered consistent", check_ground_truth_invariants),
    ("metrics.py", "recall@k and MRR on hand-computed cases", check_recall_and_mrr),
    ("metrics.py", "nDCG@k with graded relevance and log discount", check_ndcg),
    ("metrics.py", "edge cases: empty relevance, k=0, k>n, ties", check_metric_edges),
    ("metrics.py", "abstention precision and recall", check_abstention),
    ("metrics.py", "latency stats: mean, median, p95, max", check_latency),
    ("metrics.py", "Wilson, exact McNemar, seeded paired bootstrap", check_paired_comparison),
    ("baseline.py", "filters, k limit, determinism, non-degenerate lexical scores", check_baseline_mechanics),
    ("baseline.py", "abstains on every no-answer query", check_baseline_abstention),
    ("metrics.py", "evaluate(): per-family and overall assembly", check_evaluate_integration),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}RAG from scratch, step 0 — evaluation set{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<11} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<11} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<11} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — the evaluation set is built.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

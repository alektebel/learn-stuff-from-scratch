"""
Progress checker for the RAG project-1 FUSION templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports this module's own solutions/; it
tests YOUR template. The sibling stages are different modules, and are imported from
`../bm25/solutions` and `../lsa/solutions` exactly the way the LSA checker reaches BM25.
The shared eval set lives in `../eval-set` (its modules are imported from its solutions/).

The checks are deliberately adversarial: the RRF scores in step 1 are recomputed by hand
including a document from a single ranking and a deliberate tie; step 2 holds min-max and
z-score to hand values; step 3 injects a lexical-only and a dense-only stage to prove
fusion recovers what one stage misses (a degenerate "BM25 only" fusion fails it); step 5
shows that weights tuned on one family do NOT transfer to another; and step 6 pins the
abstention contract (both stages empty -> empty, one stage empty -> the other's hits).
"""
import math
import os
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, Dict, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

MAX_STEP = 6


def _close(got, want, what, tol=1e-9):
    assert abs(got - want) < tol, f"{what}: got {got!r}, expected {want!r}"


def _find_eval_set():
    """Locate the shared evaluation set (the dir or its solutions/) as a pathlib.Path."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = []
    env = os.environ.get("RAG_EVAL_SET")
    if env:
        candidates.append(pathlib.Path(env))
    candidates += [
        here.parent / "eval-set",
        here / "eval-set",
        here.parent.parent / "eval-set",
    ]
    for base in candidates:
        for cand in (base / "solutions", base):
            if (cand / "metrics.py").is_file() and (cand / "corpus.py").is_file():
                return cand
    raise FileNotFoundError(
        "cannot find the shared eval set. Expected it at ../eval-set (or "
        "../eval-set/solutions) relative to check.py, or set RAG_EVAL_SET. "
        f"Looked from {here}.")


def _load_eval_set():
    """Import the eval set's modules, adding its directory to sys.path once."""
    path = str(_find_eval_set())
    if path not in sys.path:
        sys.path.insert(0, path)
    import baseline
    import corpus
    import metrics
    import queries

    return corpus, queries, metrics, baseline


def _stage_module(name):
    """Import a sibling stage's solution module (`bm25` or `lsa`), or return None."""
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here.parent / name / "solutions", here.parent.parent / name / "solutions"):
        if (cand / f"{name}.py").is_file():
            if str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
            import importlib

            return importlib.import_module(name)
    return None


# ---------------------------------------------------------------------------
# toy stages used by the hand-built steps (no sibling import needed)
# ---------------------------------------------------------------------------

TOY_DOCS = [
    {"doc_id": "lex", "title": "xylophone", "body": "maintenance manual"},
    {"doc_id": "litauto", "title": "auto", "body": "repair shop"},
    {"doc_id": "sem", "title": "automobile", "body": "engine service"},
    {"doc_id": "guitar", "title": "guitar", "body": "strings instrument"},
]


def _toy_query_text(query):
    return query.get("text", "") if isinstance(query, dict) else query


class _ToyLexicalStage:
    """Literal-token overlap only (the 'BM25' shape for the toy corpus)."""

    def scored(self, query, depth=100, filters=None):
        tokens = set(_toy_query_text(query).lower().split())
        out = []
        if "xylophone" in tokens:
            out.append(("lex", 9.0))
        if "auto" in tokens:
            out.append(("litauto", 5.0))
        return out[:depth]

    def retrieve(self, query, k=10, filters=None):
        return [key for key, _score in self.scored(query, depth=k, filters=filters)]


class _ToyDenseStage:
    """Concept overlap only: 'auto' ~ 'automobile', 'xylophone' ~ 'guitar'."""

    def scored(self, query, depth=100, filters=None):
        tokens = set(_toy_query_text(query).lower().split())
        if "xylophone" in tokens:
            return [("guitar", 9.0)][:depth]
        if "auto" in tokens:
            return [("sem", 9.0)][:depth]
        return []

    def retrieve(self, query, k=10, filters=None):
        return [key for key, _score in self.scored(query, depth=k, filters=filters)]


def _toy_hybrid():
    import fusion

    stages = {"bm25": _ToyLexicalStage(), "lsa": _ToyDenseStage()}
    return fusion, fusion.HybridRetriever(TOY_DOCS, stages=stages)


# ---------------------------------------------------------------------------
# Step 1: reciprocal rank fusion against hand-computed scores
# ---------------------------------------------------------------------------

def check_rrf() -> None:
    import fusion

    rankings = [["a", "b", "c"], ["b", "a", "c", "d"]]
    k = 60
    fused = fusion.rrf(rankings, k=k)
    scores = dict(fused)
    assert len(fused) == 4, f"four distinct keys, got {len(fused)}"

    # a and b are each #1 in one list and #2 in the other: a genuine tie.
    _close(scores["a"], 1 / 61 + 1 / 62, "rrf(a)")
    _close(scores["b"], 1 / 62 + 1 / 61, "rrf(b)")
    assert abs(scores["a"] - scores["b"]) < 1e-15, "a and b must be exactly tied"
    # c is rank 3 in both; d only appears in the second ranking (rank 4).
    _close(scores["c"], 1 / 63 + 1 / 63, "rrf(c) — a key shared by both rankings")
    _close(scores["d"], 1 / 64, "rrf(d) — a key present in only one ranking")

    order = [key for key, _score in fused]
    assert order == ["a", "b", "c", "d"], (
        f"RRF order wrong: {order}. Ungrouped rank terms must use 1/(k+rank), not rank; "
        "ties must break by key ascending (a before b)")

    # A tie on rank with a single-list key must break by key ascending too.
    fused2 = fusion.rrf([["c"], ["e"]], k=k)
    order2 = [key for key, _score in fused2]
    assert order2 == ["c", "e"], f"tied single-list keys must break by key, got {order2}"

    # weights and the (key, score) input form.
    weighted = fusion.rrf([["a", "b"], ["b", "a"]], k=k, weights=[3, 1])
    wscores = dict(weighted)
    _close(wscores["a"], 3 / 61 + 1 / 62, "rrf weighted a")
    _close(wscores["b"], 3 / 62 + 1 / 61, "rrf weighted b")
    assert [key for key, _ in weighted] == ["a", "b"], "weights must change the order"

    paired_form = fusion.rrf([[("a", 9.0), ("b", 1.0)], [("a", 0.1)]], k=k)
    assert [key for key, _ in paired_form] == ["a", "b"], (
        "rrf must accept (key, score) pairs and ignore the scores")


# ---------------------------------------------------------------------------
# Step 2: score normalisation and weighted fusion against hand values
# ---------------------------------------------------------------------------

def check_normalization() -> None:
    import fusion

    # min-max on [3, 5, 10] -> [0, 2/7, 1].
    assert fusion.normalize_scores([3, 5, 10], "minmax") == [0.0, 2 / 7, 1.0], (
        f"minmax got {fusion.normalize_scores([3, 5, 10], 'minmax')}")
    # a constant collection must map to 0.0 (never divide by zero).
    assert fusion.normalize_scores([4, 4, 4], "minmax") == [0.0, 0.0, 0.0], (
        "minmax on a constant score list must be 0.0, not a ZeroDivisionError")

    # z-score on [1, 2, 3, 4]: mean 2.5, population std sqrt(1.25).
    std = math.sqrt(1.25)
    expected = [(-1.5) / std, (-0.5) / std, (0.5) / std, (1.5) / std]
    got = fusion.normalize_scores([1, 2, 3, 4], "zscore")
    for g, w in zip(got, expected):
        _close(g, w, "zscore value")
    assert fusion.normalize_scores([7, 7], "zscore") == [0.0, 0.0], (
        "zscore on a zero-variance list must be 0.0")

    # keyed forms: mapping in, mapping out; pairs in, mapping out.
    normalised = fusion.normalize_scores({"a": 10, "b": 5, "c": 0}, "minmax")
    assert normalised == {"a": 1.0, "b": 0.5, "c": 0.0}, f"keyed minmax got {normalised}"
    normalised_pairs = fusion.normalize_scores([("a", 10), ("b", 5), ("c", 0)], "minmax")
    assert normalised_pairs == {"a": 1.0, "b": 0.5, "c": 0.0}, (
        f"pair minmax got {normalised_pairs}")

    # weighted_fusion: min-max each stage per query, then weight-sum.
    # stage 1 {a:10,b:5,c:0} -> {a:1,b:0.5,c:0}; stage 2 {b:4,a:0} -> {b:1,a:0}.
    fused = fusion.weighted_fusion([{"a": 10, "b": 5, "c": 0}, {"b": 4, "a": 0}], [1, 1])
    scores = dict(fused)
    _close(scores["b"], 1.5, "weighted b")
    _close(scores["a"], 1.0, "weighted a")
    _close(scores["c"], 0.0, "weighted c")
    assert [key for key, _ in fused] == ["b", "a", "c"], (
        f"weighted order wrong: {[key for key, _ in fused]}")

    fused_w = fusion.weighted_fusion([{"a": 10, "b": 5, "c": 0}, {"b": 4, "a": 0}], [1, 2])
    _close(dict(fused_w)["b"], 0.5 + 2.0, "weighted b with weight 2")

    # z-score weighting: stage 1 {a:10,b:0} -> {+1,-1}; stage 2 {a:0} -> {0}.
    fused_z = fusion.weighted_fusion([{"a": 10, "b": 0}, {"a": 0}], [1, 1], norm="zscore")
    _close(dict(fused_z)["a"], 1.0, "weighted zscore a")


# ---------------------------------------------------------------------------
# Step 3: fusion recovers what ONE stage misses
# ---------------------------------------------------------------------------

def check_fusion_recovers_missing() -> None:
    fusion, hybrid = _toy_hybrid()
    lexical = _ToyLexicalStage()
    dense = _ToyDenseStage()

    # LSA-only (semantic) case: "auto" misses the literal tokens and must be bridged to
    # the "automobile" document by the dense stage.
    lex_rank = [key for key, _ in lexical.scored("auto")]
    dense_rank = [key for key, _ in dense.scored("auto")]
    assert "sem" not in lex_rank, f"the toy lexical stage must miss 'sem', got {lex_rank}"
    assert "sem" in dense_rank, f"the toy dense stage must find 'sem', got {dense_rank}"
    for method in ("rrf", "weighted"):
        fused = hybrid.retrieve("auto", k=3, method=method)
        assert "sem" in fused[:2], (
            f"fusion ({method}) failed to recover the dense-only document 'sem': got {fused}. "
            "A hybrid that drops the dense stage degenerates to BM25 and fails here.")

    # BM25-only (lexical) case: "xylophone" has no synonym in the dense stage.
    lex_rank = [key for key, _ in lexical.scored("xylophone")]
    dense_rank = [key for key, _ in dense.scored("xylophone")]
    assert "lex" not in dense_rank, f"the toy dense stage must miss 'lex', got {dense_rank}"
    assert "lex" in lex_rank, f"the toy lexical stage must find 'lex', got {lex_rank}"
    for method in ("rrf", "weighted"):
        fused = hybrid.retrieve("xylophone", k=3, method=method)
        assert "lex" in fused[:2], (
            f"fusion ({method}) failed to recover the lexical-only document 'lex': got {fused}")


# ---------------------------------------------------------------------------
# Step 4: end to end on the shared evaluation set, per family, with paired counts
# ---------------------------------------------------------------------------

FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")


def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def check_eval_set_end_to_end() -> None:
    import fusion

    corpus_mod, queries_mod, metrics, _baseline = _load_eval_set()
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)

    result = fusion.evaluate(corpus, query_sets, k=10)
    for family in FAMILIES:
        assert family in result["by_type"], (
            f"evaluate dropped the {family!r} family; every family must be reported")
    assert "overall" in result and "abstention" in result, (
        "evaluate must return the shared metrics shape (overall, by_type, abstention)")
    assert set(result["methods"]) == {"rrf", "weighted", "bm25", "lsa"}, (
        f"evaluate must report rrf/weighted/bm25/lsa, got {sorted(result['methods'])}")

    # The single-stage numbers must be reproducible from the sibling stages themselves:
    # a fusion module that silently invents its own BM25/LSA is caught here.
    bm = _stage_module("bm25")
    lsa = _stage_module("lsa")
    assert bm is not None and lsa is not None, (
        "step 4 needs the sibling ../bm25 and ../lsa solutions beside the eval set")
    bm25_ref = bm.evaluate_bm25(corpus, query_sets, k=10)
    lsa_ref = lsa.evaluate(corpus, query_sets, k=10)
    for metric in ("recall@k", "mrr", "ndcg@k"):
        _close(result["methods"]["bm25"]["overall"][metric],
               bm25_ref["overall"][metric],
               f"fusion's BM25 stage vs the sibling BM25 ({metric})")
        _close(result["methods"]["lsa"]["overall"][metric],
               lsa_ref["overall"][metric],
               f"fusion's LSA stage vs the sibling LSA ({metric})")

    # Paired comparisons are per query and must account for every query exactly once.
    n_queries = len(queries)
    for method in ("rrf", "weighted"):
        for stage in ("bm25", "lsa"):
            stats = result["paired"][method][stage]
            assert stats["wins"] + stats["losses"] + stats["ties"] == n_queries, (
                f"paired {method} vs {stage} did not count every query: {stats}")
            assert 0.0 <= stats["win_rate"] <= 1.0
    assert 0.0 <= result["overall"]["recall@k"] <= 1.0

    print(f"      seed 0, {len(corpus['documents'])} documents, {n_queries} queries")
    header = (f"      {'family':<11}{'BM25 r@10':>11}{'LSA r@10':>10}"
              f"{'RRF r@10':>10}{'WT r@10':>9}")
    print(header)
    for family in FAMILIES + ("overall",):
        line = f"      {family:<11}"
        for method, width in (("bm25", 11), ("lsa", 10), ("rrf", 10), ("weighted", 9)):
            value = _row(result["methods"][method], family).get("recall@k", 0.0)
            line += f"{value:>{width}.3f}"
        print(line)
    print("      paired per-query (W/L/T = fusion better / worse / equal), metric recall@10:")
    for method in ("rrf", "weighted"):
        for stage in ("bm25", "lsa"):
            stats = result["paired"][method][stage]
            print(f"        {method:>8} vs {stage:<4}  {stats['wins']}/{stats['losses']}/"
                  f"{stats['ties']}  win_rate={stats['win_rate']:.3f} "
                  f"mean_diff={stats['mean_diff']:+.3f} p={stats['p_value']:.3f}")
    print("      reported as measured: fusion is not assumed to beat either single stage.")


# ---------------------------------------------------------------------------
# Step 5: weights tuned on one family do not transfer to another
# ---------------------------------------------------------------------------

# Controlled two-family corpus for step 5: the shared eval set is too easy here (its
# semantic queries carry the topic word, so BM25 alone already scores 1.0), so the
# non-transfer limit is shown on a constructed pair of stages and families where the
# weight is the only thing deciding the ranking.
_TRANSFER_DOCS = [
    {"doc_id": "lex1", "title": "x", "body": "y"},
    {"doc_id": "sem1", "title": "x", "body": "y"},
]
_TRANSFER_QUERIES = {
    "lexical": [{"qid": "TLEX-01", "text": "lexquery", "type": "lexical",
                 "filters": {}, "relevance": {"lex1": 2.0}}],
    "semantic": [{"qid": "TSEM-01", "text": "semquery", "type": "semantic",
                  "filters": {}, "relevance": {"sem1": 2.0}}],
}


class _TransferLexicalStage:
    """Wins the lexical family (key 'lex1'), but its semantic hit 'zz_litauto' is a
    non-relevant distractor whose id sorts after the dense winner 'sem1'."""

    def scored(self, query, depth=100, filters=None):
        text = _toy_query_text(query)
        if text == "lexquery":
            return [("lex1", 9.0), ("aaa_guitar", 5.0)][:depth]
        if text == "semquery":
            return [("zz_litauto", 9.0)][:depth]
        return []


class _TransferDenseStage:
    """Wins the semantic family (key 'sem1'), but its lexical hit 'aaa_guitar' is a
    non-relevant distractor whose id sorts before the lexical winner 'lex1'."""

    def scored(self, query, depth=100, filters=None):
        text = _toy_query_text(query)
        if text == "lexquery":
            return [("aaa_guitar", 9.0)][:depth]
        if text == "semquery":
            return [("sem1", 9.0)][:depth]
        return []


def check_weights_do_not_transfer() -> None:
    import fusion

    hybrid = fusion.HybridRetriever(
        _TRANSFER_DOCS,
        stages={"bm25": _TransferLexicalStage(), "lsa": _TransferDenseStage()})

    def family_recall(family, weights, method="rrf"):
        total = 0.0
        for query in _TRANSFER_QUERIES[family]:
            ranked = hybrid.retrieve(query, k=1, method=method, weights=weights)
            if ranked and ranked[0] in query["relevance"]:
                total += 1.0
        return total / len(_TRANSFER_QUERIES[family])

    # Tune the BM25/LSA weight on the lexical family only. Equal weights let the dense
    # stage's distractor win on the id tie-break, so the lexical-heavy end is best.
    grid = [[w, 1.0 - w] for w in (0.0, 0.5, 1.0)]
    lexical_scores = {tuple(w): family_recall("lexical", w) for w in grid}
    best = max(lexical_scores.values())
    tuned = list(next(w for w in grid if lexical_scores[tuple(w)] == best))
    default = [0.5, 0.5]

    lexical_default = family_recall("lexical", default)
    lexical_tuned = family_recall("lexical", tuned)
    semantic_default = family_recall("semantic", default)
    semantic_tuned = family_recall("semantic", tuned)

    print(f"      weights tuned on lexical: default {default} -> lexical recall@1 "
          f"{lexical_default:.3f}; tuned {tuned} -> lexical recall@1 {lexical_tuned:.3f}")
    print(f"      the SAME tuned weights applied to semantic: default recall@1 "
          f"{semantic_default:.3f} -> tuned {semantic_tuned:.3f}")

    # The tuning must actually help the family it was tuned on...
    assert lexical_tuned >= lexical_default, (
        f"the weights {tuned} tuned on lexical (recall@1 {lexical_tuned:.3f}) are worse "
        f"than the default (recall@1 {lexical_default:.3f}); the search is not tuning")
    # ... and must not transfer: lexical-heavy weights hurt the semantic family.
    assert semantic_tuned < semantic_default, (
        f"weights {tuned} tuned on lexical did NOT degrade semantic retrieval "
        f"(default recall@1 {semantic_default:.3f}, tuned recall@1 {semantic_tuned:.3f}); "
        "weights are supposed to not transfer across families")
    # A weight search that only ever returns the default would pass the first assertion
    # vacuously; make sure the tuned weights are genuinely lexical-heavy.
    assert tuned[0] > tuned[1], (
        f"tuning on the lexical family should pick a lexical-heavy weighting, got {tuned}")


# ---------------------------------------------------------------------------
# Step 6: limits — abstention and the one-stage-only case
# ---------------------------------------------------------------------------

def _passes(doc, filters):
    """Minimal metadata-filter predicate for the toy stage in step 6."""
    if not filters:
        return True
    for key, value in filters.items():
        if key == "year":
            if doc.get("date", "")[:4] != str(value):
                return False
        elif doc.get(key) != value:
            return False
    return True


def check_abstention() -> None:
    import fusion

    docs = [
        {"doc_id": "x", "title": "xylophone", "body": "music"},
        {"doc_id": "y", "title": "banana", "body": "fruit"},
    ]

    class _LiteralStage:
        """A lexical stage that honours metadata filters (the 'BM25' shape)."""

        def scored(self, query, depth=100, filters=None):
            text = _toy_query_text(query)
            if filters is None and isinstance(query, dict):
                filters = query.get("filters", {})
            tokens = set(text.lower().split())
            out = []
            for doc in docs:
                if not _passes(doc, filters):
                    continue
                if tokens & set((doc["title"] + " " + doc["body"]).lower().split()):
                    out.append((doc["doc_id"], 1.0))
            return out[:depth]

    class _EmptyStage:
        def scored(self, query, depth=100, filters=None):
            return []

    hybrid = fusion.HybridRetriever(docs, stages={"bm25": _LiteralStage(), "lsa": _EmptyStage()})

    # Both stages have no candidate: the hybrid must abstain, not return the corpus.
    assert hybrid.retrieve("zzzq nonexistentterm", k=10) == [], (
        "a query with no candidate in either stage must abstain (return [])")
    assert hybrid.retrieve({"text": "zzzq nonexistentterm", "filters": {}}, k=10) == [], (
        "a no-match query dict must abstain too")
    assert hybrid.retrieve({"text": "xylophone", "filters": {"region": "NOWHERE"}}, k=10) == [], (
        "a metadata filter that empties the only matching stage must abstain")

    # Only one stage has candidates: the other stage's silence must not erase the hits.
    assert hybrid.retrieve("xylophone", k=10) == ["x"], (
        "when only the lexical stage has candidates, fusion must still return them")
    assert hybrid.retrieve("banana", k=10) == ["y"], (
        "the other single-stage candidate must also survive fusion")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("fusion.py", "reciprocal rank fusion matches hand-computed scores and ties", check_rrf),
    ("fusion.py", "min-max/z-score normalisation and weighted fusion match hand values", check_normalization),
    ("fusion.py", "fusion recovers a document that one stage misses", check_fusion_recovers_missing),
    ("fusion.py", "end to end on the shared eval set, per family, with paired counts", check_eval_set_end_to_end),
    ("fusion.py", "weights tuned on one family degrade another (they do not transfer)", check_weights_do_not_transfer),
    ("fusion.py", "limits: both-empty abstains, one-empty keeps the other's hits", check_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 1 — FUSION (the hybrid stage){RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<9} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<9} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<9} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — FUSION (the hybrid stage) is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

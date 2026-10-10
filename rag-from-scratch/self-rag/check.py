"""
Progress checker for the RAG project-8 Self-RAG templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is the
next thing to write. Nothing here imports this module's own ``solutions/``; it tests YOUR
template. Steps 1, 2, 3 and 5 run on hand-built passages and scripted reflection models and
never touch the shared eval set, so the mutation harness works in a bare temporary
directory; only step 4 needs ``../eval-set``.

The checks are deliberately adversarial:

* step 1 pins the retrieve decision: a model that says no, one with no decision, and no
  model at all, and a query with no content terms;
* step 2 pins evidence grading: it keeps exactly the passages the model marks relevant, in
  retrieval order, and returns nothing below ``min_relevant``;
* step 3 pins every branch of the loop: no-retrieve abstains, a supported draft is answered,
  no relevant evidence abstains, and an unsupported draft is retried and then abandoned;
* step 4 runs the loop on the shared eval set: every returned doc comes from the retrieved
  set (nothing is invented), and blanking the relevance labels leaves the path counts
  unchanged (the loop never reads the judgments);
* step 5 pins the limit cases: a query nothing matches abstains, and an over-eager model
  that marks everything relevant still cannot answer without support.
"""
import os
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")


# --- shared eval set (step 4 only) ----------------------------------------------

def _find_eval_set():
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
    raise FileNotFoundError(f"cannot find the shared eval set from {here}.")


# --- hand-built passages and scripted reflection models --------------------------

def _passage(doc_id: str, text: str) -> dict:
    return {"doc_id": doc_id, "text": text, "score": 1.0}


def _retriever(passages):
    def retrieve(query, k=5, filters=None):
        return list(passages)[:k]
    return retrieve


class ScriptModel:
    """A reflection model with hand-picked answers, so a branch can be forced."""

    def __init__(self, *, retrieve=True, relevant=None, supported=None):
        # relevant/supported: a set of passage texts, or None for a constant rule
        self._retrieve = retrieve
        self._relevant = relevant
        self._supported = supported

    def retrieve_decision(self, question):
        return self._retrieve

    def relevance(self, question, passage):
        if self._relevant == "all":
            return True
        if self._relevant == "none":
            return False
        return passage in (self._relevant or ())

    def support(self, question, answer, passage):
        if self._supported == "all":
            return True
        if self._supported == "none":
            return False
        return passage in (self._supported or ())


# ---------------------------------------------------------------------------
# Step 1: the retrieve decision
# ---------------------------------------------------------------------------

def check_retrieve_decision() -> None:
    import self_rag

    assert self_rag.should_retrieve("What does POL-ENG require?", ScriptModel(retrieve=True)) is True
    assert self_rag.should_retrieve("What does POL-ENG require?", ScriptModel(retrieve=False)) is False
    assert self_rag.should_retrieve("What does POL-ENG require?", ScriptModel(retrieve=None)) is True, \
        "an unclear decision must fail safe to retrieving"
    assert self_rag.should_retrieve("What does POL-ENG require?", None) is True, \
        "no model must still retrieve"
    assert self_rag.should_retrieve("the and of to", ScriptModel(retrieve=True)) is False, \
        "a query with no content terms cannot retrieve"


# ---------------------------------------------------------------------------
# Step 2: evidence grading
# ---------------------------------------------------------------------------

def check_grade_evidence() -> None:
    import self_rag

    p1 = _passage("D1", "access control policy alpha")
    p2 = _passage("D2", "payroll calendar year end")
    p3 = _passage("D3", "access control permissions matrix")
    model = ScriptModel(relevant={p1["text"], p3["text"]})

    kept = self_rag.grade_evidence("access control", [p1, p2, p3], model)
    assert [p["doc_id"] for p in kept] == ["D1", "D3"], \
        "grading must keep the relevant passages in retrieval order"
    assert self_rag.grade_evidence("access control", [p2], model) == [], \
        "nothing relevant must grade to nothing"
    assert self_rag.grade_evidence("access control", [p1, p2, p3], model, min_relevant=3) == [], \
        "fewer than min_relevant passages must grade to nothing"


# ---------------------------------------------------------------------------
# Step 3: the answer loop's branches
# ---------------------------------------------------------------------------

def check_loop_branches() -> None:
    import self_rag

    good = _passage("D1", "access control policy requires manager approval")

    # no-retrieve: the offline loop abstains rather than answer from nothing
    out = self_rag.self_rag_answer({"text": "access control", "filters": {}},
                                   _retriever([good]), ScriptModel(retrieve=False))
    assert out["path"] == "no_retrieve" and out["answer"] is None, \
        "a no-retrieve decision must abstain, not answer"

    # relevant and supported: answered from the retrieved document
    out = self_rag.self_rag_answer({"text": "access control", "filters": {}},
                                   _retriever([good]),
                                   ScriptModel(relevant={good["text"]}, supported="all"))
    assert out["path"] == "answered" and out["evidence"] == ["D1"] and out["answer"], \
        "a supported draft must be answered with its evidence"
    assert out["supported"] is True

    # nothing relevant: abstain with no evidence
    out = self_rag.self_rag_answer({"text": "access control", "filters": {}},
                                   _retriever([good]),
                                   ScriptModel(relevant="none", supported="all"))
    assert out["path"] == "abstain" and out["answer"] is None and out["evidence"] == []

    # unsupported draft: the loop retries the next relevant passage
    second = _passage("D2", "access control policy alpha beta")
    model = ScriptModel(relevant={good["text"], second["text"]},
                        supported={second["text"]})
    out = self_rag.self_rag_answer({"text": "access control", "filters": {}},
                                   _retriever([good, second]), model)
    assert out["path"] == "answered" and out["evidence"] == ["D2"], \
        "an unsupported draft must be dropped and the next passage tried"
    assert out["attempts"] >= 2

    # unsupported everywhere: abstain after the attempts are spent
    out = self_rag.self_rag_answer({"text": "access control", "filters": {}},
                                   _retriever([good, second]),
                                   ScriptModel(relevant="all", supported="none"))
    assert out["path"] == "abstain" and out["answer"] is None
    assert out["attempts"] == self_rag.MAX_ATTEMPTS, \
        "the loop must stop after MAX_ATTEMPTS, not spin"


# ---------------------------------------------------------------------------
# Step 4: end to end on the shared eval set
# ---------------------------------------------------------------------------

def _blanked(query_sets):
    return {family: [dict(q, relevance={}) for q in qs]
            for family, qs in query_sets.items()}


def _self_contained_sets():
    """An answerable query and a no-answer one, over a hand-built retriever."""
    good = _passage("D1", "access control policy requires approval")
    query_sets = {
        "lexical": [{"qid": "X1", "text": "access control", "type": "lexical",
                     "filters": {}, "relevance": {"D1": 1}}],
        "semantic": [], "filtered": [], "multi_hop": [],
        "no_answer": [{"qid": "X2", "text": "zzz nowhere", "type": "no_answer",
                       "filters": {}, "relevance": {}}],
    }
    return query_sets, _retriever([good])


def check_end_to_end() -> None:
    import self_rag

    # (a) self-contained: the path counts must not move when the labels are blanked
    self_contained, retriever0 = _self_contained_sets()
    model0 = self_rag.OverlapReflectionModel()
    with_labels = self_rag.evaluate(self_contained, retriever0, model0)
    without = self_rag.evaluate(_blanked(self_contained), retriever0, model0)
    assert without["paths"] == with_labels["paths"], \
        "blanking the relevance labels must not change the path counts (the loop leaked a judgment)"

    # (b) on the shared eval set: no invention, and the same leak check at scale
    path = str(_find_eval_set())
    if path not in sys.path:
        sys.path.insert(0, path)
    import corpus
    import queries

    generated = corpus.generate_corpus(0)
    documents = generated["documents"]
    query_sets = queries.build_query_sets(generated)
    retriever = self_rag.make_retriever(documents)
    model = self_rag.OverlapReflectionModel()

    all_queries = [q for family in FAMILIES for q in query_sets.get(family, [])]
    for query in all_queries:
        out = self_rag.self_rag_answer(query, retriever, model)
        assert set(out["evidence"]) <= set(out["retrieved"]), \
            f"{query['qid']}: evidence must come from the retrieved set (no invention)"

    result = self_rag.evaluate(query_sets, retriever, model)
    assert result["n"] == len(all_queries), "every query must be scored exactly once"
    assert sum(result["paths"].values()) == len(all_queries), "path counts must sum to n"

    blanked = self_rag.evaluate(_blanked(query_sets), retriever, model)
    assert blanked["paths"] == result["paths"], \
        "blanking the relevance labels must not change the path counts (the loop leaked a judgment)"

    print(f"      answer accuracy: {result['answer_accuracy']:.3f}  "
          f"abstention p/r: {result['abstention_precision']:.3f}/{result['abstention_recall']:.3f}  "
          f"paths: {result['paths']}")


# ---------------------------------------------------------------------------
# Step 5: limit cases
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    import self_rag

    # a query nothing matches: the retriever is empty, so the loop abstains
    out = self_rag.self_rag_answer({"text": "zzz nowhere term", "filters": {}},
                                   _retriever([]), self_rag.OverlapReflectionModel())
    assert out["path"] == "abstain" and out["answer"] is None and out["retrieved"] == [], \
        "a query with no retrieved passages must abstain"

    # an over-eager model marks everything relevant but supports nothing: no answer escapes
    passages = [_passage("D1", "access control policy alpha"),
                _passage("D2", "access control policy beta")]
    out = self_rag.self_rag_answer({"text": "access control", "filters": {}},
                                   _retriever(passages),
                                   ScriptModel(relevant="all", supported="none"))
    assert out["answer"] is None and out["path"] == "abstain", \
        "relevance alone must never produce an answer without support"
    assert set(out["evidence"]) <= set(out["retrieved"]) and out["evidence"] == []


# ---------------------------------------------------------------------------
CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("self_rag.py", "the retrieve decision, fail-safe, on scripted models", check_retrieve_decision),
    ("self_rag.py", "evidence grading keeps exactly the relevant passages", check_grade_evidence),
    ("self_rag.py", "every branch of the answer loop", check_loop_branches),
    ("self_rag.py", "end to end on the shared eval set; no invention, no label leak", check_end_to_end),
    ("self_rag.py", "the limit cases: nothing matches, relevance without support", check_limit_cases),
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
    print(f"\n{BOLD}RAG from scratch, project 8 — Self-RAG (offline){RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — Self-RAG is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the RAG project-3 RERANKING templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports this module's own solutions/; it
tests YOUR template. The sibling stages are different modules and are imported from
``../bm25/solutions`` and ``../lsa/solutions``; the shared eval set lives in
``../eval-set`` and is imported from its solutions/ (all three resolved exactly the way
the FUSION checker reaches them).

The checks are deliberately adversarial:

* step 1 builds nine documents against an injected toy context and requires EVERY
  feature to vary across them (a dropped or constant feature is caught, not hidden by
  the others varying);
* step 2 uses a hand-built example whose first-stage feature ranks the distractor
  first, and requires training to reverse it while the loss falls (a zero-weight model
  and a no-op reranker both fail);
* step 3 hands the reranker a strict subset and requires it to return only those
  candidates (re-scoring the whole corpus fails);
* step 4 checks the train/eval split is disjoint *before* touching the shared eval set,
  then reports base vs reranked honestly and asserts the first-stage recall@100 ceiling;
* step 5 makes the ceiling bind by enlarging the index past the candidate budget, and
  shows the reranker can reach an injected document but not an excluded one;
* step 6 pins abstention: an empty first stage stays empty through the reranker.
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
FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")


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


def _answerable_recall(metrics_result, queries):
    """Mean recall@k over the queries that actually have a relevant document."""
    total = 0.0
    count = 0
    for query in queries:
        if query["relevance"]:
            total += metrics_result["per_query"][query["qid"]]["recall@k"]
            count += 1
    return (total / count) if count else 0.0


# ---------------------------------------------------------------------------
# Step 1: the documented feature vector, finite and with no dead feature
# ---------------------------------------------------------------------------

_TOY_FEATURE_DOCS = [
    {"doc_id": "a", "title": "alpha beta", "body": "alpha beta gamma"},
    {"doc_id": "b", "title": "alpha", "body": "gamma beta gamma"},
    {"doc_id": "c", "title": "delta", "body": "delta delta", "superseded_by": "b"},
]


class _ToyContext:
    """A context whose stage/dense/idf values differ per document on purpose."""

    avg_length = 5.0
    _STAGE = {"a": 0.2, "b": 0.5, "c": 0.9}
    _DENSE = {"a": 0.9, "b": 0.5, "c": 0.1}
    _IDF = {"alpha": 2.0, "beta": 1.0}

    def stage_score(self, query_text, doc):
        return self._STAGE[doc["doc_id"]]

    def dense_cosine(self, query_text, doc):
        return self._DENSE[doc["doc_id"]]

    def idf(self, term):
        return self._IDF.get(term, 0.5)


def check_features() -> None:
    import rerank

    names = list(rerank.FEATURE_NAMES)
    assert len(names) >= 6, (
        f"expected at least six documented features, got {len(names)}: {names}")
    assert len(set(names)) == len(names), f"feature names must be unique: {names}"

    query = {"text": "alpha beta"}
    context = _ToyContext()
    vectors = []
    for doc in _TOY_FEATURE_DOCS:
        vector = list(rerank.features(query, doc, context))
        assert len(vector) == len(names), (
            f"features() returned {len(vector)} values for {len(names)} names")
        for value in vector:
            assert math.isfinite(value), (
                f"feature vector for {doc['doc_id']!r} has a non-finite value: {vector}")
        vectors.append(vector)

    # The text-only features must also be finite with no context at all.
    for doc in _TOY_FEATURE_DOCS:
        vector = list(rerank.features(query, doc))
        assert len(vector) == len(names)
        assert all(math.isfinite(value) for value in vector), (
            "features() without a context must still return finite values")

    for index, name in enumerate(names):
        column = {round(vectors[row][index], 12) for row in range(len(_TOY_FEATURE_DOCS))}
        assert len(column) > 1, (
            f"feature {name!r} is constant across the toy documents; a dropped or dead "
            "feature cannot help the reranker. Compute it from the query and document.")


# ---------------------------------------------------------------------------
# Step 2: training learns, the loss falls, and a wrong base order is reversed
# ---------------------------------------------------------------------------

def check_training() -> None:
    import rerank

    docs = [
        {"doc_id": "rel", "title": "alpha", "body": "alpha alpha"},
        {"doc_id": "dist", "title": "omega", "body": "omega"},
    ]

    def stage_scorer(query_text, doc):
        return 0.1 if doc["doc_id"] == "rel" else 0.9

    context = rerank.FeatureContext(
        docs, stage_scorer=stage_scorer, dense_scorer=lambda _q, _d: 0.0,
        idf=lambda _term: 1.0, avg_length=2.0)
    query = {"text": "alpha"}
    relevant = list(rerank.features(query, docs[0], context))
    distractor = list(rerank.features(query, docs[1], context))

    stage_index = list(rerank.FEATURE_NAMES).index("stage_score")
    assert distractor[stage_index] > relevant[stage_index], (
        "the toy first-stage feature must rank the distractor first, so that reversing "
        "the order proves the model learned rather than copied the base ranking")

    model = rerank.Reranker(context=context)
    model.fit([(distractor, 0.0), (relevant, 1.0)])

    assert all(math.isfinite(weight) for weight in model.weights), (
        f"trained weights must be finite, got {model.weights}")
    assert math.isfinite(model.bias), "the trained bias must be finite"
    assert len(model.loss_history) >= 2, (
        "fit must record the loss on each iteration (see Reranker.loss_history)")
    assert model.loss_history[-1] < model.loss_history[0], (
        f"the training loss must fall: {model.loss_history[0]:.4f} -> "
        f"{model.loss_history[-1]:.4f}. A model left at zero weights has a flat loss.")
    assert model.score_vector(relevant) > model.score_vector(distractor), (
        "after training the relevant document must score higher than the distractor")

    order = model.rerank(query, ["dist", "rel"], k=2)
    assert order == ["rel", "dist"], (
        f"rerank must return the relevant document first, got {order}. A no-op reranker "
        "that echoes the candidate order fails here.")

    # A model whose weights are fixed (or that only ever learns the bias) passes the
    # loss and ordering assertions above on this separable example. Training on the
    # swapped labels must flip the ordering, which only an example-dependent `fit` can
    # do.
    flipped = rerank.Reranker(context=context)
    flipped.fit([(distractor, 1.0), (relevant, 0.0)])
    assert flipped.score_vector(distractor) > flipped.score_vector(relevant), (
        "training on the swapped labels must rank the distractor first. `fit` has to "
        "depend on the examples: a hard-coded weight vector (one that only learns the "
        "bias, say) passes the checks above and fails here.")


# ---------------------------------------------------------------------------
# Step 3: rerank only reorders the candidates it was given
# ---------------------------------------------------------------------------

def check_rerank_is_a_subset() -> None:
    import rerank

    docs = [
        {"doc_id": "d0", "title": "alpha", "body": "alpha beta"},
        {"doc_id": "d1", "title": "beta", "body": "beta gamma"},
        {"doc_id": "d2", "title": "gamma", "body": "gamma delta"},
        {"doc_id": "d3", "title": "delta", "body": "delta alpha"},
        {"doc_id": "d4", "title": "epsilon", "body": "epsilon zeta"},
        {"doc_id": "d5", "title": "zeta", "body": "zeta eta"},
    ]
    context = rerank.FeatureContext(docs)
    model = rerank.Reranker(context=context, iterations=1)
    all_ids = [doc["doc_id"] for doc in docs]

    for query in ({"text": "alpha"}, {"text": "beta gamma"}):
        candidates = all_ids[2:]
        assert set(candidates) < set(all_ids), "the candidate list must be a strict subset"
        for k in (1, 3, 5):
            order = model.rerank(query, candidates, k=k)
            assert set(order) <= set(candidates), (
                f"rerank returned documents outside the candidate list: {order} vs "
                f"{candidates}. It must never score the whole corpus.")
            assert len(order) <= k, f"rerank returned more than k={k}: {len(order)}"
            assert len(order) == min(k, len(candidates))
        pairs = [(doc_id, float(index)) for index, doc_id in enumerate(candidates)]
        order = model.rerank(query, pairs, k=2)
        assert set(order) <= set(candidates), "rerank must accept (doc_id, score) pairs"

    assert model.rerank({"text": "nothing"}, [], k=5) == [], (
        "an empty candidate list must produce an empty result")


# ---------------------------------------------------------------------------
# Step 4: end to end on the shared eval set, disjoint split, honest numbers
# ---------------------------------------------------------------------------

def check_eval_set_end_to_end() -> None:
    import rerank

    # (a) The split contract, checked on a tiny self-contained query set so it is
    # verified even when the shared eval set is not beside this copy of check.py.
    toy_queries = [
        {"qid": f"TOY-{index:02d}", "type": "lexical", "text": "x",
         "filters": {}, "relevance": {"d": 2.0}}
        for index in range(6)
    ]
    train, evaluation = list(rerank.choose_split(toy_queries))
    assert train and evaluation, "choose_split must put queries on both sides"
    assert set(train).isdisjoint(evaluation), (
        "choose_split leaked: the training and evaluation queries must be disjoint, or "
        "the reported metric is training accuracy in disguise")

    # (b) The shared evaluation set.
    try:
        corpus_mod, queries_mod, metrics, _baseline = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; "
              "checked the split contract only")
        return

    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)
    by_qid = {query["qid"]: query for query in queries}

    result = rerank.train_and_evaluate(corpus, query_sets, k=5)
    assert set(result["train_qids"]).isdisjoint(result["eval_qids"]), (
        "the training and evaluation qids returned by train_and_evaluate overlap")

    for family in FAMILIES:
        assert family in result["reranked"]["by_type"], (
            f"the {family!r} family is missing from the reranked metrics")

    ceiling = result["first_stage_recall@100"]
    eval_queries = [by_qid[qid] for qid in result["eval_qids"]]
    answerable_recall = _answerable_recall(result["reranked"], eval_queries)
    assert answerable_recall <= ceiling + 1e-9, (
        f"reranked recall@5 over answerable queries ({answerable_recall:.3f}) exceeds the "
        f"first-stage recall@100 ({ceiling:.3f}); a reranker cannot recover a document "
        "the first stage never returned")

    base = result["base"]
    reranked = result["reranked"]
    print(f"      seed 0, {len(corpus['documents'])} documents, {len(queries)} queries; "
          f"train {len(result['train_qids'])}, eval {len(result['eval_qids'])} "
          f"(disjoint: {set(result['train_qids']).isdisjoint(result['eval_qids'])})")
    print(f"      first-stage recall@100 (the ceiling): {ceiling:.3f}")
    print(f"      {'family':<11}{'base r@5':>9}{'rerank r@5':>12}{'base MRR':>10}"
          f"{'rerank MRR':>12}{'base nDCG':>10}{'rerank nDCG':>13}")
    for family in FAMILIES + ("overall",):
        if family == "overall":
            b, r = base["overall"], reranked["overall"]
        else:
            b = base["by_type"].get(family, {})
            r = reranked["by_type"].get(family, {})
        print(f"      {family:<11}{b.get('recall@k', 0.0):>9.3f}{r.get('recall@k', 0.0):>12.3f}"
              f"{b.get('mrr', 0.0):>10.3f}{r.get('mrr', 0.0):>12.3f}"
              f"{b.get('ndcg@k', 0.0):>10.3f}{r.get('ndcg@k', 0.0):>13.3f}")
    print("      reported as measured: the reranker is not assumed to beat the base ranking.")


# ---------------------------------------------------------------------------
# Step 5: the ceiling — the first stage decides what can be reranked
# ---------------------------------------------------------------------------

def check_ceiling() -> None:
    import rerank

    corpus_mod, queries_mod, _metrics, _baseline = _load_eval_set()
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)

    case = rerank.find_ceiling_case(corpus, query_sets)
    assert case is not None, (
        "expected find_ceiling_case to find a query whose relevant document is not in "
        "the first-stage top-100 (the index is enlarged past the candidate budget)")
    query = case["query"]
    doc_id = case["doc_id"]
    candidates = case["candidates"]
    assert doc_id not in set(candidates), (
        "find_ceiling_case returned a query whose relevant document IS a candidate")

    augmented = {"documents": case["documents"]}
    model = rerank.train_and_evaluate(augmented, query_sets, k=5)["model"]

    reranked = model.rerank(query, candidates, k=5)
    assert doc_id not in reranked, (
        f"the reranker returned {doc_id!r}, which was not among its candidates; that is "
        "impossible without scoring documents outside the candidate list")

    injected = model.rerank(query, list(candidates) + [doc_id], k=1)
    assert injected == [doc_id], (
        f"when the relevant document {doc_id!r} is injected as a candidate the reranker "
        f"should rank it first, got {injected}. The reranker works; it is the first "
        "stage's candidate list that is the ceiling.")

    print(f"      ceiling query {query['qid']}: relevant {doc_id} is outside the "
          f"first-stage top-100 (index grown to {len(case['documents'])} documents)")
    print(f"      from the candidates the reranker cannot return it: {reranked}")
    print(f"      injected as a candidate it is ranked first: {injected}")


# ---------------------------------------------------------------------------
# Step 6: abstention — the reranker does not invent results
# ---------------------------------------------------------------------------

class _EmptyRetriever:
    """A first stage that returns nothing."""

    def retrieve(self, query, k=10, filters=None):
        return []


def check_abstention() -> None:
    import rerank

    docs = [
        {"doc_id": "x", "title": "xylophone", "body": "music"},
        {"doc_id": "y", "title": "banana", "body": "fruit"},
    ]
    context = rerank.FeatureContext(docs)
    model = rerank.Reranker(context=context)

    base = rerank.first_stage("zzzq nonexistentterm", k=100, retriever=_EmptyRetriever())
    assert base == [], "the toy first stage must abstain (return [])"
    assert model.rerank("zzzq nonexistentterm", base, k=5) == [], (
        "reranking an abstention must stay empty, not return the corpus")
    assert model.rerank({"text": "zzzq", "filters": {}}, [], k=5) == [], (
        "an explicit empty candidate list must rerank to []")

    # The shared eval set has real no-answer queries; at least one must abstain at the
    # first stage, and the reranker must preserve that abstention.
    try:
        corpus_mod, queries_mod, _metrics, _baseline = _load_eval_set()
    except FileNotFoundError:
        return
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    abstaining = [q for q in query_sets["no_answer"]
                  if not rerank.first_stage(q, k=100)]
    assert abstaining, (
        "expected at least one no-answer query the first stage abstains on; if this "
        "fails the shared corpus changed and this check needs updating")
    query = abstaining[0]
    real_model = rerank.Reranker(context=rerank.build_context(corpus))
    assert real_model.rerank(query, rerank.first_stage(query, k=100), k=5) == [], (
        f"the no-answer query {query['qid']} must stay empty after reranking")
    print(f"      {len(abstaining)} no-answer queries abstain at the first stage and "
          "stay empty through the reranker")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("rerank.py", "features are finite, the documented length, and none is dead", check_features),
    ("rerank.py", "training lowers the loss and reverses a wrong base order", check_training),
    ("rerank.py", "rerank only reorders the candidates it was given", check_rerank_is_a_subset),
    ("rerank.py", "end to end on the shared eval set with a disjoint split and the ceiling", check_eval_set_end_to_end),
    ("rerank.py", "the first stage is the ceiling; the reranker cannot invent a document", check_ceiling),
    ("rerank.py", "abstention survives reranking", check_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 3 — RERANKING (retrieve 100, rerank to 5){RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<10} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<10} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<10} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — RERANKING (retrieve 100, rerank to 5) is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

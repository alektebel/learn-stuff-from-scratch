"""
Progress checker for the RAG project-1 BM25 templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The eval set lives in `../eval-set` as its own graded module. Its top-level files are
templates, so the checks import the modules from `../eval-set/solutions` (the graded
reference) and only add that directory to `sys.path` lazily, inside the one check that
needs it. The hand-computed steps (1-4, 6) do not need the eval set at all.

The checks are deliberately adversarial: the idf and BM25 values are recomputed by hand,
the tf-saturation and length-normalisation limit cases are constructed rather than
sampled, and the abstention cases (a term in no document, a filter matching no document)
are made explicit instead of hoping a random query hits them.
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

MAX_STEP = 6


def _close(got, want, what):
    assert abs(got - want) < 1e-9, f"{what}: got {got!r}, expected {want!r}"


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


# ---------------------------------------------------------------------------
# Step 1: tokenize + inverted index
# ---------------------------------------------------------------------------

def check_tokenize_and_index() -> None:
    import bm25

    assert bm25.tokenize("Hello, World! 42") == ["hello", "world", "42"], (
        "tokenize must lower-case and keep alphanumeric tokens only "
        "([a-z0-9]+), dropping punctuation")
    assert bm25.tokenize("POL-ENG-2023-001") == ["pol", "eng", "2023", "001"], (
        "tokenize must be deterministic and split on non-alphanumerics; the hyphenated "
        "policy code becomes separate tokens")
    assert bm25.tokenize("Aa aA AA") == ["aa", "aa", "aa"], (
        "tokenize must not case-fold inconsistently")

    docs = [
        {"doc_id": "d1", "title": "Cat cat", "body": "dog"},
        {"doc_id": "d2", "title": "Cat", "body": "bird bird"},
    ]
    index = bm25.build_inverted_index(docs)
    postings = index["postings"]
    assert postings["cat"] == {"d1": 2, "d2": 1}, (
        f"posting list for 'cat' is {postings.get('cat')!r}: the index must be keyed by "
        "term, mapping each term to its per-document frequencies")
    assert postings["bird"] == {"d2": 2}, f"posting list for 'bird' is {postings.get('bird')!r}"
    assert postings["dog"] == {"d1": 1}, f"posting list for 'dog' is {postings.get('dog')!r}"
    assert index["doc_lengths"] == {"d1": 3, "d2": 3}, (
        f"doc lengths are {index['doc_lengths']!r}: length counts title + body tokens")
    _close(index["avg_length"], 3.0, "average document length")


# ---------------------------------------------------------------------------
# Step 2: idf and the BM25 score against a hand-computed value
# ---------------------------------------------------------------------------

def check_idf_and_score() -> None:
    import math

    import bm25

    docs = [
        {"doc_id": "a", "title": "alpha", "body": "alpha beta"},
        {"doc_id": "b", "title": "beta", "body": "gamma delta epsilon"},
    ]
    index = bm25.build_inverted_index(docs)  # N = 2, lengths a=3, b=4, avg=3.5

    rare = bm25.idf(index, "alpha", 2)   # df = 1
    common = bm25.idf(index, "beta", 2)  # df = 2
    assert rare > common > 0.0, (
        f"idf must decrease as a term gets more common and stay positive: "
        f"idf(df=1)={rare!r}, idf(df=2)={common!r}")
    _close(rare, math.log(1 + (2 - 1 + 0.5) / (1 + 0.5)), "idf(alpha, N=2, df=1)")
    _close(common, math.log(1 + (2 - 2 + 0.5) / (2 + 0.5)), "idf(beta, N=2, df=2)")

    wide = [
        {"doc_id": "x", "title": "common", "body": ""},
        {"doc_id": "y", "title": "common", "body": ""},
        {"doc_id": "z", "title": "common rare", "body": ""},
    ]
    wide_index = bm25.build_inverted_index(wide)
    assert bm25.idf(wide_index, "common", 3) < bm25.idf(wide_index, "rare", 3), (
        "a term in all 3 documents must have a smaller idf than a term in 1")

    # Hand-computed BM25 for doc 'a' and the single-term query "beta".
    idf_beta = math.log(1 + (2 - 2 + 0.5) / (2 + 0.5))
    dl, avg = 3, 3.5
    expected = idf_beta * (1 * (1.5 + 1)) / (1 + 1.5 * (1 - 0.75 + 0.75 * dl / avg))
    got = bm25.bm25_score(index, "beta", "a", k1=1.5, b=0.75)
    _close(got, expected, "bm25_score('beta', doc 'a') on the hand example")


# ---------------------------------------------------------------------------
# Step 3: tf saturation and length normalisation
# ---------------------------------------------------------------------------

def check_tf_saturation_and_length() -> None:
    import bm25

    docs = [
        {"doc_id": "t1", "title": "alpha", "body": ""},
        {"doc_id": "t2", "title": "alpha alpha", "body": ""},
        {"doc_id": "t3", "title": "alpha alpha alpha", "body": ""},
    ]
    index = bm25.build_inverted_index(docs)
    s1 = bm25.bm25_score(index, "alpha", "t1")
    s2 = bm25.bm25_score(index, "alpha", "t2")
    s3 = bm25.bm25_score(index, "alpha", "t3")
    assert s1 < s2 < s3, (
        f"more occurrences of a query term must increase the score: "
        f"tf=1 -> {s1!r}, tf=2 -> {s2!r}, tf=3 -> {s3!r}")
    assert (s2 - s1) > (s3 - s2), (
        f"term frequency must saturate: the gain from tf=1 to 2 ({s2 - s1!r}) should "
        f"exceed the gain from tf=2 to 3 ({s3 - s2!r}); check the k1 saturation term")

    docs2 = [
        {"doc_id": "short", "title": "alpha", "body": ""},
        {"doc_id": "long", "title": "alpha", "body": "filler filler filler filler"},
    ]
    index2 = bm25.build_inverted_index(docs2)
    short = bm25.bm25_score(index2, "alpha", "short")
    long = bm25.bm25_score(index2, "alpha", "long")
    assert short > long > 0.0, (
        f"for the same tf, a shorter document must score higher: short={short!r}, "
        f"long={long!r}; the b length-normalisation term is missing from the denominator")


# ---------------------------------------------------------------------------
# Step 4: retrieval returns a ranked list
# ---------------------------------------------------------------------------

def check_retriever_ranking() -> None:
    import bm25

    # The strongly-matching document d1 is deliberately LAST in corpus order, so a
    # retriever that returns candidates without ranking cannot pass.
    docs = [
        {"doc_id": "d2", "title": "Beta", "body": "zx9"},
        {"doc_id": "d3", "title": "Gamma", "body": "misc"},
        {"doc_id": "d1", "title": "Alpha", "body": "zx9 zx9 zx9"},
    ]
    retriever = bm25.BM25Retriever({"documents": docs})
    ranked = retriever.retrieve({"text": "zx9", "filters": {}}, k=10)
    assert isinstance(ranked, list), f"retrieve must return a list, got {type(ranked)}"
    assert ranked and ranked[0] == "d1", (
        f"the known-relevant document for 'zx9' is not ranked first: got {ranked}. "
        "retrieve must sort candidates by (-score, doc_id), not return corpus order")
    assert "d3" not in ranked, f"a document with no query-term match must be dropped: {ranked}"
    assert retriever.retrieve({"text": "zx9", "filters": {}}, k=10) == ranked, (
        "retrieve is not deterministic: identical input gave different rankings")
    assert retriever.retrieve({"text": "zx9", "filters": {}}, k=1) == ["d1"], (
        "retrieve must honour the k limit")
    assert retriever.retrieve("zx9", k=1) == ["d1"], (
        "retrieve must accept a raw query string as well as the eval-set query dict")


# ---------------------------------------------------------------------------
# Step 5: end to end on the shared evaluation set
# ---------------------------------------------------------------------------

def check_eval_set_end_to_end() -> None:
    import bm25

    corpus_mod, queries_mod, metrics, baseline_mod = _load_eval_set()
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)

    bm25_result = bm25.evaluate_bm25(corpus, query_sets, k=10)
    bm25_lexical = bm25_result["by_type"]["lexical"]["recall@k"]

    baseline = baseline_mod.LexicalBaseline(corpus)
    base_ranked = {q["qid"]: baseline.retrieve(q, 10) for q in queries}
    base_result = metrics.evaluate(base_ranked, queries, k=10)
    base_lexical = base_result["by_type"]["lexical"]["recall@k"]

    assert bm25_lexical >= base_lexical - 1e-12, (
        f"BM25 lexical recall@10 ({bm25_lexical:.3f}) is below the lexical baseline "
        f"({base_lexical:.3f}): an exact policy code must be at least as easy to find "
        "with BM25 as with token overlap")

    retriever = bm25.BM25Retriever(corpus)
    predictions = {q["qid"]: retriever.retrieve(q, 10) for q in queries}
    answered_no_answer = [q["qid"] for q in query_sets["no_answer"] if predictions[q["qid"]]]
    if answered_no_answer:
        # BM25 has no stopword list, so it may return documents for a no-answer query on
        # a generic token. That is allowed only if it is reported honestly: the family is
        # still present, scores 0 on retrieval, and the answered queries count as
        # false negatives for abstention.
        assert "no_answer" in bm25_result["by_type"], (
            "evaluate_bm25 dropped the no_answer family, hiding the queries it answered")
        _close(bm25_result["by_type"]["no_answer"]["recall@k"], 0.0,
               "no_answer retrieval recall (empty relevance)")
        assert bm25_result["abstention"]["fn"] >= len(answered_no_answer), (
            f"BM25 answered {len(answered_no_answer)} no-answer queries but abstention "
            f"counts only {bm25_result['abstention']['fn']} false negatives: the "
            "abstention metrics must be computed over every query, not a subset")
    else:
        assert bm25_result["abstention"]["recall"] == 1.0, (
            "BM25 abstained on every no-answer query but abstention recall is not 1.0")


# ---------------------------------------------------------------------------
# Step 6: limit cases (abstention)
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    import bm25

    docs = [
        {"doc_id": "d1", "title": "Alpha", "body": "zx9", "region": "EMEA",
         "date": "2025-03-01", "department": "Legal", "access_level": "internal"},
        {"doc_id": "d2", "title": "Beta", "body": "zx9", "region": "AMER",
         "date": "2024-05-01", "department": "Sales", "access_level": "public"},
    ]
    retriever = bm25.BM25Retriever({"documents": docs})
    assert retriever.retrieve({"text": "nonexistentterm", "filters": {}}) == [], (
        "a query whose terms occur in no document must return an empty list (abstain), "
        "not the whole corpus")
    assert retriever.retrieve({"text": "nonexistentterm elsewhere", "filters": {}}) == [], (
        "a multi-term query with no matching term must also abstain")
    assert retriever.retrieve({"text": "zx9", "filters": {"region": "NOWHERE"}}) == [], (
        "a metadata filter matching no document must return an empty list")
    assert retriever.retrieve({"text": "zx9", "filters": {"year": 1999}}) == [], (
        "a year filter matching no document must return an empty list")
    assert retriever.retrieve({"text": "zx9", "filters": {"department": "Finance"}}) == [], (
        "a department filter matching no document must return an empty list")
    # A query whose only matching document is excluded by the filter abstains too.
    assert retriever.retrieve({"text": "zx9", "filters": {"access_level": "restricted"}}) == [], (
        "when the only matching documents are filtered out, the result must be empty")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("bm25.py", "tokenize and the inverted index posting lists", check_tokenize_and_index),
    ("bm25.py", "idf monotone in df and bm25_score on a hand example", check_idf_and_score),
    ("bm25.py", "tf saturation and length normalisation", check_tf_saturation_and_length),
    ("bm25.py", "retrieve returns a ranked list, relevant document first", check_retriever_ranking),
    ("bm25.py", "end to end on the shared eval set (lexical vs the baseline)", check_eval_set_end_to_end),
    ("bm25.py", "limit cases: no matching term and empty filters abstain", check_limit_cases),
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
    print(f"\n{BOLD}RAG from scratch, project 1 — BM25 (stage 1 of hybrid search){RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — BM25 (stage 1) is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

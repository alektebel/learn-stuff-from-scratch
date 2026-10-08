"""
Progress checker for the RAG project-1 LSA templates.

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

The checks are deliberately adversarial: the tf-idf values are recomputed by hand, the
truncated SVD is held to the full Gram spectrum and to the reconstruction identity
||A - A_k||_F^2 = sum of the discarded singular values squared, the semantic step is a
constructed synonym case rather than a sampled one, and the D > N (more terms than
documents) limit is built so the document-space Gram matrix is the only correct route.
"""
import math
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


def _bm25_module():
    """Import the sibling BM25 solution if it is present, else return None.

    Step 5 compares against BM25 when the sibling stage is next to this one; the module
    must still check correctly when only LSA is copied beside the eval set.
    """
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here.parent / "bm25" / "solutions", here.parent.parent / "bm25" / "solutions"):
        if (cand / "bm25.py").is_file():
            if str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
            import bm25

            return bm25
    return None


# ---------------------------------------------------------------------------
# Step 1: tokenise + the term-document count matrix
# ---------------------------------------------------------------------------

def check_tokenize_and_term_document() -> None:
    import lsa

    assert lsa.tokenize("Hello, World! 42") == ["hello", "world", "42"], (
        "tokenize must lower-case and keep alphanumeric tokens only "
        "([a-z0-9]+), dropping punctuation")
    assert lsa.tokenize("POL-ENG-2023-001") == ["pol", "eng", "2023", "001"], (
        "tokenize must be deterministic and split on non-alphanumerics; the hyphenated "
        "policy code becomes separate tokens")
    assert lsa.tokenize("Aa aA AA") == ["aa", "aa", "aa"], (
        "tokenize must not case-fold inconsistently")

    bm = _bm25_module()
    if bm is not None:
        for text in ("Hello, World! 42", "POL-ENG-2023-001", "Aa aA AA", "one 2 three"):
            assert lsa.tokenize(text) == bm.tokenize(text), (
                f"LSA and BM25 must use the SAME tokeniser so the two stages are "
                f"comparable; disagreed on {text!r}")

    docs = [
        {"doc_id": "d1", "title": "Cat cat", "body": "dog"},
        {"doc_id": "d2", "title": "Cat", "body": "bird bird"},
    ]
    terms, matrix = lsa.build_term_document(docs)
    assert terms == ["bird", "cat", "dog"], (
        f"the vocabulary must be the sorted set of tokens, got {terms!r}")
    assert matrix == [[0, 2, 1], [2, 1, 0]], (
        f"the term-document matrix must be N x D raw counts, row-major; got {matrix!r}. "
        "d1 has cat x2 and dog x1, d2 has bird x2 and cat x1")


# ---------------------------------------------------------------------------
# Step 2: tf-idf against hand-computed values
# ---------------------------------------------------------------------------

def check_tf_idf() -> None:
    import lsa

    docs = [
        {"doc_id": "d1", "title": "cat", "body": "cat dog"},
        {"doc_id": "d2", "title": "dog", "body": "dog"},
        {"doc_id": "d3", "title": "bird", "body": "cat"},
    ]
    terms, matrix = lsa.build_term_document(docs)
    assert terms == ["bird", "cat", "dog"], f"vocabulary is {terms!r}"

    # N = 3: bird df=1, cat df=2, dog df=2, smoothed idf as in BM25.
    idf_bird = math.log(1 + (3 - 1 + 0.5) / (1 + 0.5))
    idf_cat = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
    idf_dog = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))

    weighted = lsa.tf_idf(matrix)
    assert len(weighted) == 3 and all(abs(len(row) - 3) < 1e-12 for row in weighted), (
        f"tf_idf must preserve the N x D shape, got {weighted!r}")

    # d1: 0*bird + 2*cat + 1*dog, then L2-normalised.
    norm = math.sqrt((2 * idf_cat) ** 2 + idf_dog ** 2)
    _close(weighted[0][0], 0.0, "tf-idf(d1, bird)")
    _close(weighted[0][1], 2 * idf_cat / norm, "tf-idf(d1, cat)")
    _close(weighted[0][2], idf_dog / norm, "tf-idf(d1, dog)")
    # d2: 2*dog only -> [0, 0, 1].
    _close(weighted[1][0], 0.0, "tf-idf(d2, bird)")
    _close(weighted[1][1], 0.0, "tf-idf(d2, cat)")
    _close(weighted[1][2], 1.0, "tf-idf(d2, dog)")
    # d3: 1*bird + 1*cat.
    norm3 = math.sqrt(idf_bird ** 2 + idf_cat ** 2)
    _close(weighted[2][0], idf_bird / norm3, "tf-idf(d3, bird)")
    _close(weighted[2][1], idf_cat / norm3, "tf-idf(d3, cat)")
    _close(weighted[2][2], 0.0, "tf-idf(d3, dog)")

    assert idf_bird > idf_cat, (
        "a term in 1 document must have a larger idf than a term in 2: tf_idf is not "
        "using a document-frequency idf at all")
    for row in weighted:
        length = math.sqrt(sum(value * value for value in row))
        _close(length, 1.0, "row length; tf_idf must L2-normalise for cosine")


# ---------------------------------------------------------------------------
# Step 3: the truncated SVD, the Gram routes and the reconstruction identity
# ---------------------------------------------------------------------------

def _gram(matrix, left_vectors):
    if left_vectors:
        n = len(matrix)
        return [[sum(matrix[i][j] * matrix[l][j] for j in range(len(matrix[i])))
                 for l in range(n)] for i in range(n)]
    t = len(matrix[0]) if matrix else 0
    return [[sum(matrix[d][i] * matrix[d][j] for d in range(len(matrix)))
             for j in range(t)] for i in range(t)]


def check_jacobi_and_svd() -> None:
    import lsa

    docs = [
        {"doc_id": "d1", "title": "a b", "body": "b c"},
        {"doc_id": "d2", "title": "c d", "body": "d e"},
        {"doc_id": "d3", "title": "a e", "body": "a c"},
        {"doc_id": "d4", "title": "b d", "body": "b e"},
    ]
    terms, matrix = lsa.build_term_document(docs)  # N = 4 docs, D = 5 terms
    n_docs, n_terms = len(matrix), len(terms)
    assert n_docs == 4 and n_terms == 5, "the hand example must be 4 docs x 5 terms"

    k = 2
    model = lsa.fit_lsa(docs, k)
    assert len(model["components"]) == k, (
        f"fit_lsa(docs, {k}) must return exactly {k} components, got "
        f"{len(model['components'])}; it must not silently fit more (or fewer)")
    assert len(model["singular_values"]) == k, (
        f"expected {k} singular values, got {len(model['singular_values'])}")
    assert model["singular_values"][0] >= model["singular_values"][1] >= 0.0, (
        f"singular values must be returned largest-first: {model['singular_values']!r}; "
        "if jacobi's unsorted eigenpairs leak through, the top-k are the wrong ones")
    assert model["gram_size"] == n_docs, (
        f"with {n_docs} documents and {n_terms} terms the smaller Gram matrix is the "
        f"N x N document-space one ({n_docs} x {n_docs}), but the model reports "
        f"gram_size={model['gram_size']}")

    weighted = lsa.tf_idf(matrix)
    mean = [sum(weighted[i][j] for i in range(n_docs)) / n_docs for j in range(n_terms)]
    for j in range(n_terms):
        _close(model["mean"][j], mean[j], f"mean[term {terms[j]}]")
    centred = [[weighted[i][j] - mean[j] for j in range(n_terms)] for i in range(n_docs)]

    # The full spectrum from both Gram matrices: the two routes must agree.
    vals_doc, _ = lsa.eig_sorted(_gram(centred, True))
    vals_term, _ = lsa.eig_sorted(_gram(centred, False))
    sv_doc = sorted((math.sqrt(max(v, 0.0)) for v in vals_doc), reverse=True)
    sv_term = sorted((math.sqrt(max(v, 0.0)) for v in vals_term), reverse=True)
    for i in range(min(n_docs, n_terms)):
        _close(sv_doc[i], sv_term[i], f"singular value {i} from the two Gram routes", tol=1e-6)
    for i in range(k):
        _close(model["singular_values"][i], sv_doc[i],
               f"singular value {i} vs the document-space Gram spectrum")

    # A_k = (X_centred V_k) V_k^T is the best rank-k approximation; its residual must
    # equal the sum of the discarded singular values squared (a hand identity).
    components = model["components"]
    residual = 0.0
    for i in range(n_docs):
        coords = [sum(centred[i][t] * components[c][t] for t in range(n_terms))
                  for c in range(k)]
        for j in range(n_terms):
            approx = sum(coords[c] * components[c][j] for c in range(k))
            residual += (centred[i][j] - approx) ** 2
    discarded = sum(sv_doc[i] ** 2 for i in range(k, len(sv_doc)))
    assert discarded > 0.0, "the example must have discarded singular values to test"
    assert abs(residual - discarded) < 1e-9, (
        f"||A - A_k||_F^2 is {residual!r} but the discarded singular values squared sum "
        f"to {discarded!r}: the truncation or the centring is wrong")


# ---------------------------------------------------------------------------
# Step 4: a controlled semantic case (LSA, not raw term overlap)
# ---------------------------------------------------------------------------

def _overlap_baseline(docs, query, k=10):
    """The raw term-overlap floor: count shared tokens, drop zero, best first."""
    import lsa

    query_tokens = set(lsa.tokenize(query))
    scored = []
    for doc in docs:
        tokens = set(lsa.tokenize(doc["title"] + " " + doc["body"]))
        score = len(query_tokens & tokens)
        if score > 0:
            scored.append((score, doc["doc_id"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [doc_id for _score, doc_id in scored[:k]], query_tokens


def check_semantic_retrieval() -> None:
    import lsa

    # "auto" and "automobile" are synonyms in the sense LSA can learn: they occupy
    # almost the same documents, so their latent directions are close. b1/b2/b3 use
    # "automobile" and never "auto", so a term-overlap retriever cannot reach them.
    docs = [
        {"doc_id": "a1", "title": "auto repair shop", "body": "auto repair shop services"},
        {"doc_id": "a2", "title": "auto engine repair", "body": "auto engine repair workshop"},
        {"doc_id": "a3", "title": "auto shop", "body": "auto shop maintenance"},
        {"doc_id": "b1", "title": "automobile repair shop", "body": "automobile repair shop services"},
        {"doc_id": "b2", "title": "automobile engine repair", "body": "automobile engine repair workshop"},
        {"doc_id": "b3", "title": "automobile shop", "body": "automobile shop maintenance"},
        {"doc_id": "n1", "title": "banana fruit", "body": "banana fruit apple orange"},
        {"doc_id": "n2", "title": "weather rain", "body": "weather rain cloud wind"},
    ]
    retriever = lsa.LsaRetriever(docs, n_components=2)
    ranked = retriever.retrieve("auto", k=10)
    baseline, query_tokens = _overlap_baseline(docs, "auto", k=10)

    assert ranked, "LSA returned nothing for an answerable query"
    assert "b1" in ranked and "b1" not in baseline, (
        f"the semantic bridge failed: 'b1' (automobile, no 'auto') must be retrieved by "
        f"LSA but not by raw term overlap. LSA={ranked}, overlap={baseline}")
    assert not (query_tokens & set(lsa.tokenize(docs[3]["title"] + " " + docs[3]["body"]))), (
        "the example is wrong: 'b1' must share no literal token with the query")
    assert any(doc_id in ranked for doc_id in ("a1", "a3") ), (
        "the literal 'auto' documents must still be retrieved")

    embedding = lsa.embed_query("auto", retriever.model)
    norm = math.sqrt(sum(value * value for value in embedding))
    _close(norm, 1.0, "embed_query must return an L2-normalised vector (cosine, not dot)")


# ---------------------------------------------------------------------------
# Step 5: end to end on the shared evaluation set
# ---------------------------------------------------------------------------

def check_eval_set_end_to_end() -> None:
    import lsa

    corpus_mod, queries_mod, metrics, baseline_mod = _load_eval_set()
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)

    lsa_result = lsa.evaluate(corpus, query_sets, k=10)
    for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer"):
        assert family in lsa_result["by_type"], (
            f"evaluate dropped the {family!r} family; every family must be reported")
    assert "overall" in lsa_result and "abstention" in lsa_result, (
        "evaluate must return the shared metrics shape (overall, by_type, abstention)")

    # Recompute from the retriever to prove the reported number is not fabricated.
    retriever = lsa.LsaRetriever(corpus)
    predictions = {q["qid"]: retriever.retrieve(q, 10) for q in queries}
    recomputed = metrics.evaluate(predictions, queries, k=10)
    sem_qids = [q["qid"] for q in queries if q["type"] == "semantic"]
    sem_recall = sum(lsa_result["per_query"][qid]["recall@k"] for qid in sem_qids) / len(sem_qids)
    assert sem_qids, "the eval set must contain semantic queries for this step to mean anything"
    _close(lsa_result["by_type"]["semantic"]["recall@k"], sem_recall,
           "semantic recall@k vs the per-query recomputation")
    _close(recomputed["by_type"]["semantic"]["recall@k"],
           lsa_result["by_type"]["semantic"]["recall@k"],
           "evaluate is not reproducible from its own retriever")
    assert 0.0 <= lsa_result["by_type"]["semantic"]["recall@k"] <= 1.0

    baseline = baseline_mod.LexicalBaseline(corpus)
    base_result = metrics.evaluate({q["qid"]: baseline.retrieve(q, 10) for q in queries},
                                   queries, k=10)

    bm25_result = None
    bm = _bm25_module()
    if bm is not None:
        bm25_result = bm.evaluate_bm25(corpus, query_sets, k=10)
        assert set(bm25_result["by_type"]) >= set(lsa_result["by_type"]), (
            "BM25 and LSA must return the same family keys when measured on one set")

    def show(result, family):
        if family == "overall":
            return result["overall"]
        return result["by_type"].get(family, {})

    print(f"      seed 0, {len(corpus['documents'])} documents, {len(queries)} queries, "
          f"LSA rank {len(retriever.model['singular_values'])}")
    header = f"      {'family':<11}{'LSA r@10':>10}{'LSA MRR':>9}{'base r@10':>11}{'base MRR':>10}"
    if bm25_result is not None:
        header += f"{'BM25 r@10':>11}{'BM25 MRR':>10}"
    print(header)
    for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer", "overall"):
        l = show(lsa_result, family)
        b = show(base_result, family)
        line = (f"      {family:<11}{l.get('recall@k', 0.0):>10.3f}{l.get('mrr', 0.0):>9.3f}"
                f"{b.get('recall@k', 0.0):>11.3f}{b.get('mrr', 0.0):>10.3f}")
        if bm25_result is not None:
            m = show(bm25_result, family)
            line += f"{m.get('recall@k', 0.0):>11.3f}{m.get('mrr', 0.0):>10.3f}"
        print(line)
    print("      the semantic numbers above are reported as measured: dense retrieval is "
          "not assumed to win")


# ---------------------------------------------------------------------------
# Step 6: limits — more terms than documents, and abstention
# ---------------------------------------------------------------------------

def check_gram_and_abstention() -> None:
    import lsa

    # D > N: 15 distinct terms over 3 documents. The T x T term-space Gram matrix would
    # be large; the N x N document-space one is the correct route.
    docs = [
        {"doc_id": "n1", "title": "alpha beta gamma", "body": "delta epsilon"},
        {"doc_id": "n2", "title": "zeta eta theta", "body": "iota kappa"},
        {"doc_id": "n3", "title": "lambda mu nu", "body": "xi omicron"},
    ]
    terms, matrix = lsa.build_term_document(docs)
    assert len(terms) > len(matrix), (
        f"the limit case needs more terms than documents, got {len(terms)} terms and "
        f"{len(matrix)} documents")
    model = lsa.fit_lsa(docs, 2)
    assert model["gram_size"] == len(docs), (
        f"with D={len(terms)} terms and N={len(docs)} documents the model decomposed a "
        f"Gram matrix of size {model['gram_size']}; it must use the N x N document-space "
        "matrix (the D x D one is the large one and is the bug)")
    assert len(model["components"]) == 2, (
        f"the D > N route returned {len(model['components'])} components, not 2")
    assert all(len(component) == len(terms) for component in model["components"]), (
        "each right singular vector must live in term space, length D")
    assert len(model["doc_embeddings"]) == len(docs) and all(
        len(vector) == 2 for vector in model["doc_embeddings"]), (
        "the document embeddings must be N x k")
    assert model["singular_values"][0] >= model["singular_values"][1] >= 0.0

    retriever = lsa.LsaRetriever(docs)
    assert retriever.retrieve("alpha") != [], (
        "a real term must still retrieve something; otherwise the abstention test is vacuous")

    assert retriever.retrieve({"text": "zzzq nonexistentterm", "filters": {}}) == [], (
        "a query whose tokens are in no document must abstain (return []), not return "
        "the whole corpus")
    assert retriever.retrieve({"text": "zzzq nonexistentterm elsewhere", "filters": {}}) == [], (
        "a multi-token query with no known token must abstain too")
    assert retriever.retrieve("zzzq nonexistentterm") == [], (
        "a raw string no-match query must abstain as well")
    assert retriever.retrieve({"text": "alpha", "filters": {"region": "NOWHERE"}}) == [], (
        "a metadata filter matching no document must return an empty list")
    assert retriever.retrieve({"text": "alpha", "filters": {"year": 1999}}) == [], (
        "a year filter matching no document must return an empty list")
    assert retriever.retrieve({"text": "alpha", "filters": {"department": "Finance"}}) == [], (
        "a department filter matching no document must return an empty list")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("lsa.py", "tokenize and the term-document count matrix", check_tokenize_and_term_document),
    ("lsa.py", "tf-idf matches hand-computed values and is row-normalised", check_tf_idf),
    ("lsa.py", "jacobi/eig_sorted, the two Gram routes and the reconstruction identity", check_jacobi_and_svd),
    ("lsa.py", "a semantic query is retrieved by LSA but not by term overlap", check_semantic_retrieval),
    ("lsa.py", "end to end on the shared eval set (LSA vs baseline and BM25)", check_eval_set_end_to_end),
    ("lsa.py", "limits: D > N uses the N x N Gram matrix; no-match abstains", check_gram_and_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 1 — LSA (the dense stage){RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — LSA (the dense stage) is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

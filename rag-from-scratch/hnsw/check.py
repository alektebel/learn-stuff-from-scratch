"""
Progress checker for the RAG project-1 HNSW templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The eval set lives in `../eval-set` as its own graded module. Its top-level files are
templates, so step 4 imports the modules from `../eval-set/solutions` (the graded
reference) and only adds that directory to `sys.path` lazily, inside the one check that
needs it. The hand-built steps (1-3, 5, 6) do not need the eval set at all, which is
what lets the mutation suite run them from a bare temporary directory.

The checks are deliberately adversarial: the distance helpers are pinned to hand cases
so the squared-distance bug cannot hide; the tiny index must reproduce brute force
exactly and prove the graph is genuinely layered (higher layers smaller, links
symmetric); the recall/work trade-off is measured as ef grows; step 4 holds the index to
exact search on the real LSA embeddings; step 5 constructs a query at tiny ef and
asserts the miss rather than hiding the approximation; and step 6 asserts that a very
selective metadata filter applied AFTER the ANN returns fewer than k results (possibly
zero) instead of pretending the filter is free.
"""
import math
import os
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

MAX_STEP = 6


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
# Step 1: the distance helpers
# ---------------------------------------------------------------------------

def check_distance_helpers() -> None:
    import hnsw

    assert abs(hnsw.l2([0.0, 0.0], [3.0, 4.0]) - 5.0) < 1e-12, (
        "l2([0,0],[3,4]) must be 5.0 — the Euclidean distance, not its square (25.0)")
    assert abs(hnsw.l2([1.0, 2.0], [1.0, 2.0])) < 1e-12, (
        "l2 of a point with itself must be 0.0")
    assert abs(hnsw.l2([0.0, 0.0], [3.0, 4.0])
               - hnsw.l2([3.0, 4.0], [0.0, 0.0])) < 1e-12, "l2 must be symmetric"
    assert hnsw.l2([0.0, 0.0], [3.0, 4.0]) < 6.0, (
        "a distance of 25.0 is the squared distance; the metric must be the root")

    assert abs(hnsw.cosine([1.0, 0.0], [1.0, 0.0])) < 1e-12, (
        "identical directions have cosine distance 0.0")
    assert abs(hnsw.cosine([1.0, 0.0], [2.0, 0.0])) < 1e-12, (
        "cosine distance must ignore magnitude: [1,0] and [2,0] are the same direction")
    assert abs(hnsw.cosine([1.0, 0.0], [0.0, 1.0]) - 1.0) < 1e-12, (
        "orthogonal vectors have cosine distance 1.0")
    assert abs(hnsw.cosine([1.0, 0.0], [-1.0, 0.0]) - 2.0) < 1e-12, (
        "opposite directions have cosine distance 2.0")
    assert abs(hnsw.cosine([1.0, 2.0], [3.0, 4.0])
               - hnsw.cosine([3.0, 4.0], [1.0, 2.0])) < 1e-12, "cosine must be symmetric"
    assert abs(hnsw.cosine([0.0, 0.0], [1.0, 1.0])) < 1e-12, (
        "the zero vector has no direction: cosine must return 0.0 by convention")
    value = hnsw.cosine([1.0, 2.0], [-3.0, 0.5])
    assert 0.0 <= value <= 2.0, f"cosine distance must lie in [0, 2], got {value}"


# ---------------------------------------------------------------------------
# Step 2: a tiny index reproduces brute force, and is genuinely layered
# ---------------------------------------------------------------------------

def check_tiny_index_and_layers() -> None:
    import hnsw

    rng = random.Random(20240501)
    centres = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0), (10.0, 10.0),
               (5.0, 5.0), (20.0, 3.0)]
    points = []
    for cluster, (cx, cy) in enumerate(centres):
        for j in range(7):
            points.append((f"c{cluster}-{j:02d}",
                           [cx + rng.uniform(-0.4, 0.4), cy + rng.uniform(-0.4, 0.4)]))
    keys = [key for key, _vector in points]
    vectors = [vector for _key, vector in points]

    index = hnsw.HnswIndex(2, M=8, ef_construction=64, seed=7)
    for key, vector in points:
        index.insert(vector, key)

    query = [0.3, -0.1]
    exact = hnsw.exact_search(vectors, keys, query, 5)
    approximate = index.search({"key": "probe", "vector": query}, 5, ef=256)
    got = [key for key, _distance in approximate]
    assert "probe" not in got, (
        "the query's own key must never be fabricated into the result (self-match bug)")
    assert got == [key for key, _distance in exact], (
        f"at a large ef on a small set HNSW must return exactly the brute-force "
        f"neighbours; got {got}, brute force says {[k for k, _ in exact]}")

    counts = [len(layer) for layer in index.layers]
    assert counts[0] == len(points), (
        f"layer 0 must contain every node: {counts[0]} of {len(points)}")
    assert counts == sorted(counts, reverse=True), (
        f"higher layers must be subsets of lower ones (fewer nodes): {counts}")
    assert len(index.layers) >= 2, (
        "the geometric level assignment must actually create upper layers")
    assert counts[-1] < counts[0], "the top layer must be strictly smaller than layer 0"
    assert index.max_level == len(index.layers) - 1, (
        "max_level must match the number of layers")

    upper_edges = 0
    for layer in range(1, len(index.layers)):
        for a, neighbours in index.layers[layer].items():
            for b in neighbours:
                assert a in index.layers[layer][b], (
                    f"upper-layer links must be bidirectional: {a!r} -> {b!r} but not back")
                upper_edges += 1
    assert upper_edges > 0, (
        "upper layers must carry links; an index that never links them is only a "
        "layer-0 graph")


# ---------------------------------------------------------------------------
# Step 3: recall rises (never falls) with ef — the recall/work trade-off
# ---------------------------------------------------------------------------

def check_recall_work_trade_off() -> None:
    import hnsw

    assert abs(hnsw.recall_at_k(["a"], ["a", "b", "c", "d"]) - 0.25) < 1e-12, (
        "recall_at_k must divide by the size of the EXACT set, not the returned count")

    rng = random.Random(99)
    dim = 8
    vectors, keys = [], []
    for cluster in range(12):
        centre = [rng.uniform(-5.0, 5.0) for _ in range(dim)]
        for j in range(15):
            vectors.append([centre[d] + rng.gauss(0.0, 0.35) for d in range(dim)])
            keys.append(f"p{cluster:02d}-{j:03d}")
    index = hnsw.HnswIndex(dim, M=16, ef_construction=200, seed=3)
    for key, vector in zip(keys, vectors):
        index.insert(vector, key)

    probes = [vectors[rng.randrange(len(vectors))] for _ in range(12)]
    efs = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128)
    recalls, calls = [], []
    for ef in efs:
        total_recall = 0.0
        total_calls = 0.0
        for query in probes:
            exact = hnsw.exact_search(vectors, keys, query, 10)
            approximate = index.search({"key": "probe", "vector": query}, 10, ef=ef)
            total_recall += hnsw.recall_at_k([k for k, _d in approximate],
                                             [k for k, _d in exact])
            total_calls += index.distance_calls
        recalls.append(total_recall / len(probes))
        calls.append(total_calls / len(probes))

    assert recalls[0] < 1.0, (
        "at ef=1 the search must miss true neighbours: recall below 1.0 is the "
        "approximation being real, not a bug to paper over")
    assert recalls[-1] == 1.0, (
        f"at ef=128 on 180 points the index must recover the exact top-10, got "
        f"recall {recalls[-1]:.3f}")
    for i in range(len(efs) - 1):
        assert recalls[i + 1] + 1e-9 >= recalls[i], (
            f"recall must not fall as ef grows: ef={efs[i]} -> {recalls[i]:.3f}, "
            f"ef={efs[i + 1]} -> {recalls[i + 1]:.3f}")
    assert calls[-1] > calls[0], "larger ef must cost at least as many distance calls"
    assert calls[0] < len(vectors), (
        f"even the greedy ef=1 search must not touch the whole corpus: "
        f"{calls[0]:.1f} calls for {len(vectors)} vectors")

    print(f"      ef 1..128: mean recall@10 {recalls[0]:.2f} -> {recalls[-1]:.2f}, "
          f"distance calls/query {calls[0]:.1f} -> {calls[-1]:.1f} of {len(vectors)}")


# ---------------------------------------------------------------------------
# Step 4: on the eval-set LSA embeddings, HNSW reproduces exact search
# ---------------------------------------------------------------------------

def check_eval_set_ann_matches_exact() -> None:
    import hnsw

    corpus_mod, queries_mod, _metrics, _baseline = _load_eval_set()
    corpus = corpus_mod.generate_corpus(0)
    documents = corpus["documents"]
    n_components = max(1, min(100, len(documents) // 4))

    keys, vectors, model = hnsw.build_lsa_index(documents, n_components, 0)
    assert len(keys) == len(documents), (
        f"build_lsa_index must return one embedding per document: {len(keys)} vs "
        f"{len(documents)}")
    dim = len(vectors[0])
    index = hnsw.HnswIndex(dim, M=16, ef_construction=200, seed=0)
    for key, vector in zip(keys, vectors):
        index.insert(vector, key)

    query_sets = queries_mod.build_query_sets(corpus)
    recalls, calls = [], []
    for query in queries_mod.all_queries(query_sets):
        embedding = hnsw.embed_query(query["text"], model)
        if not any(embedding):
            continue
        exact = hnsw.exact_search(vectors, keys, embedding, 10)
        approximate = index.search({"key": query["qid"], "vector": embedding}, 10, ef=512)
        recalls.append(hnsw.recall_at_k([k for k, _d in approximate],
                                        [k for k, _d in exact]))
        calls.append(index.distance_calls)

    assert recalls, "the eval set produced no embeddable queries"
    mean_recall = sum(recalls) / len(recalls)
    assert mean_recall == 1.0, (
        f"with ef=512 over {len(vectors)} embeddings the index must reproduce exact "
        f"search; mean recall@10 was {mean_recall:.3f}")
    print(f"      HNSW vs exact on {len(vectors)} LSA embeddings (rank {n_components}) "
          f"at ef=512: mean recall@10={mean_recall:.3f}, "
          f"distance calls/query={sum(calls) / len(calls):.1f} (a scan is {len(vectors)}, "
          f"the large ef that buys exactness costs more)")


# ---------------------------------------------------------------------------
# Step 5: a controlled adversarial query that tiny ef genuinely misses
# ---------------------------------------------------------------------------

def check_adversarial_miss() -> None:
    import hnsw

    rng = random.Random(5)
    dim = 6
    vectors, keys = [], []
    centres = [[0.0] * dim, [30.0] + [0.0] * (dim - 1)]
    for cluster, centre in enumerate(centres):
        for j in range(20):
            vectors.append([centre[d] + rng.gauss(0.0, 0.5) for d in range(dim)])
            keys.append(f"cl{cluster}-{j:02d}")

    index = hnsw.HnswIndex(dim, M=4, ef_construction=8, seed=11)
    for key, vector in zip(keys, vectors):
        index.insert(vector, key)

    query = [0.2] + [0.0] * (dim - 1)  # deep inside cluster 0
    exact = hnsw.exact_search(vectors, keys, query, 5)
    exact_keys = [key for key, _distance in exact]
    approximate = index.search({"key": "probe", "vector": query}, 5, ef=2)
    approx_keys = [key for key, _distance in approximate]

    assert len(approximate) < 5, (
        f"a tiny ef must not return the full k here; got {len(approximate)} results")
    missed = set(exact_keys) - set(approx_keys)
    assert missed, "the adversarial query must expose a miss at small ef"
    assert hnsw.recall_at_k(approx_keys, exact_keys) < 1.0, (
        "the miss must show up in recall; the approximation is not to be hidden")

    recovered = index.search({"key": "probe", "vector": query}, 5, ef=256)
    assert [key for key, _d in recovered][:5] == exact_keys, (
        "a large ef must recover the true top-5; the graph has to be navigable")
    print(f"      small ef=2 missed {len(missed)} of the true top-5 "
          f"(recall {hnsw.recall_at_k(approx_keys, exact_keys):.2f}); "
          f"ef=256 recovers all five")


# ---------------------------------------------------------------------------
# Step 6: limit — a selective metadata filter after the ANN returns fewer than k
# ---------------------------------------------------------------------------

def check_selective_filter_shortfall() -> None:
    import hnsw

    documents = []
    for i in range(12):
        documents.append({
            "doc_id": f"d{i:02d}",
            "title": f"access control policy {i}",
            "body": f"access control policy number {i} for company systems",
            "department": "Finance" if i == 0 else "Engineering",
            "region": ("EMEA", "AMER", "APAC")[i % 3],
            "date": f"202{3 + i % 3}-0{i % 9 + 1}-01",
            "access_level": "public",
            "topics": ["access control"],
        })

    keys, vectors, model = hnsw.build_lsa_index(documents, 2, 0)
    index = hnsw.HnswIndex(len(vectors[0]), M=8, ef_construction=64, seed=0)
    for key, vector in zip(keys, vectors):
        index.insert(vector, key)

    embedding = hnsw.embed_query("access control policy", model)
    hits = index.search({"key": "probe", "vector": embedding}, 10, ef=256)
    top = [key for key, _distance in hits]
    assert len(top) == 10, f"the ANN must return the requested k=10, got {len(top)}"

    everything = hnsw.metadata_filter(top, {}, documents)
    assert everything == top, "an empty filter must pass every ANN candidate through"

    nothing = hnsw.metadata_filter(top, {"region": "MARS"}, documents)
    assert nothing == [], (
        "a metadata filter matching no document must yield zero results, not the corpus")

    selective = hnsw.metadata_filter(top, {"department": "Finance"}, documents)
    assert len(selective) < 10, (
        f"a very selective filter applied AFTER the ANN must return fewer than k "
        f"results; got {len(selective)} (did the filter get skipped?)")
    assert set(selective) <= {d["doc_id"] for d in documents if d["department"] == "Finance"}

    annual = hnsw.metadata_filter(top, {"year": 1999}, documents)
    assert len(annual) < 10, (
        "a year matching nothing after the ANN must leave fewer than k results")
    print(f"      post-ANN filter counts out of k=10: none=0, "
          f"{{department=Finance}}={len(selective)}, {{year=1999}}={len(annual)} "
          f"(the filter is not free)")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("hnsw.py", "l2 and cosine distances on hand cases", check_distance_helpers),
    ("hnsw.py", "a tiny index matches brute force and is genuinely layered", check_tiny_index_and_layers),
    ("hnsw.py", "recall rises with ef and small ef stays cheap", check_recall_work_trade_off),
    ("hnsw.py", "on the eval-set LSA embeddings HNSW reproduces exact search", check_eval_set_ann_matches_exact),
    ("hnsw.py", "a controlled adversarial query is missed at small ef", check_adversarial_miss),
    ("hnsw.py", "a selective post-ANN metadata filter returns fewer than k", check_selective_filter_shortfall),
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
    print(f"\n{BOLD}RAG from scratch, project 1 — HNSW (the ANN stage){RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<8} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<8} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<8} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — HNSW (the ANN stage) is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

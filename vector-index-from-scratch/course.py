"""Vector Index From Scratch — course manifest.

Ten graded stages that build an exact vector index, then two approximate ones,
and measure the trade they make: brute force, the metric, k-means, IVF, the
frontier, the HNSW graph, the walk, deletions, int8 quantization, and the
report you use to choose between them.

    python3 codecraft/cli.py run vector-index-from-scratch
"""

import math
import random

from codecraft.api import stage

TITLE = "Vector Index From Scratch"
DESCRIPTION = ("Brute force to IVF to HNSW: the exact baseline, the metric, "
               "the partition, the graph, the walk, deletions and int8 "
               "quantization — each one measured against the exact answer.")
LEVEL = "intermediate"
ORDER = 9


# --- helpers shared by the checks ------------------------------------------

def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol


def _keys(rows):
    return [k for k, _ in rows]


def _scores(rows):
    return [s for _, s in rows]


def _vectors(n, d, seed, prefix="v"):
    """n unit vectors in d dimensions, deterministic."""
    rng = random.Random(seed)
    return {f"{prefix}{i}": _unit(tuple(rng.uniform(-1.0, 1.0) for _ in range(d)))
            for i in range(n)}


def _clustered(counts, d, seed, spread=0.05, gap=1.0):
    """counts[i] points tight around center i, centers `gap` apart.

    Returns (vectors, labels): labels[group_index] is the list of keys in that
    group. The groups are far enough apart that any sane k-means recovers them.
    """
    rng = random.Random(seed)
    vectors, labels = {}, []
    for j, n in enumerate(counts):
        center = [0.0] * d
        center[j % d] = gap
        group = []
        for i in range(n):
            key = f"c{j}_{i}"
            vectors[key] = _unit([c + rng.uniform(-spread, spread) for c in center])
            group.append(key)
        labels.append(group)
    return vectors, labels


def _queries(n, d, seed):
    rng = random.Random(seed)
    return [_unit(tuple(rng.uniform(-1.0, 1.0) for _ in range(d)))
            for _ in range(n)]


def _group_of(labels, key):
    for j, group in enumerate(labels):
        if key in group:
            return j
    raise AssertionError(f"{key} is in no group")


# --- 1. the exact baseline and recall@k ------------------------------------

def check_1():
    import stage_01 as s

    assert s.dot((1.0, 0.0), (1.0, 0.0)) == 1.0
    assert s.dot((1.0, 2.0, 3.0), (0.0, 1.0, 0.0)) == 2.0
    try:
        s.dot((1.0, 0.0), (1.0, 0.0, 0.0))
    except ValueError:
        pass
    else:
        raise AssertionError(
            "vectors of different dimensions are a bug, not a short dot "
            "product: zip() truncates to the shorter one silently")

    idx = s.ExactIndex()
    idx.add("a", (1.0, 0.0))
    idx.add("b", (0.0, 1.0))
    idx.add("c", (0.6, 0.8))
    assert len(idx) == 3, f"len: {len(idx)}"
    got = idx.search((1.0, 0.0), 2)
    assert _keys(got) == ["a", "c"], f"top-2 by dot, descending; got {got}"
    assert _close(_scores(got)[0], 1.0) and _close(_scores(got)[1], 0.6), f"{got}"
    assert len(idx.search((1.0, 0.0), 99)) == 3, (
        "asking for more rows than exist returns what exists: no error, no "
        "padding, and no repeated rows")
    assert idx.search((1.0, 0.0), 0) == [], "k=0 is an empty result"
    assert _keys(idx.search((1.0, 0.0), 3)) == ["a", "c", "b"], "descending"

    ties = s.ExactIndex()
    ties.add("p", (1.0, 0.0))
    ties.add("q", (1.0, 0.0))
    assert _keys(ties.search((1.0, 0.0), 2)) == ["p", "q"], (
        "equal scores must keep insertion order, or the same query ranks "
        "differently between runs and every recall number measures noise")

    same = s.ExactIndex()
    same.add("a", (1.0, 0.0))
    same.add("a", (0.0, 1.0))
    assert len(same) == 1, "a repeated key replaces its vector, it does not add a row"
    assert _close(dict(same.search((1.0, 0.0), 2))["a"], 0.0), (
        "the replacement vector is what gets scored")

    src = [1.0, 0.0]
    copy = s.ExactIndex()
    copy.add("m", src)
    src[0] = 0.0
    assert _close(copy.search((1.0, 0.0), 1)[0][1], 1.0), (
        "the index kept a reference to the caller's list: one mutation "
        "outside the index changes every score it reports")

    idx.reset_counter()
    assert idx.comparisons == 0, "reset_counter() zeroes the counter"
    idx.search((1.0, 0.0), 2)
    assert idx.comparisons == 3, (
        f"a scan over 3 vectors performs 3 dot products; counted "
        f"{idx.comparisons}. Work is what this course measures, so it is "
        f"counted, not estimated")
    idx.search((1.0, 0.0), 1)
    assert idx.comparisons == 6, f"the counter accumulates; got {idx.comparisons}"

    assert _close(s.recall_at_k(["a", "b"], ["a", "x"], 1), 0.5), (
        "recall@k is relevant-retrieved-in-the-top-k / ALL relevant: two "
        "relevant documents, one retrieved, is 0.5 — not 1.0 and not 0.0")
    assert _close(s.recall_at_k(["a", "b"], ["x", "a", "b"], 2), 0.5), (
        "the top 2 of that list is ['x', 'a']: one of two relevant retrieved")
    assert _close(s.recall_at_k(["a"], ["a"], 5), 1.0)
    assert _close(s.recall_at_k([], ["a"], 5), 1.0), (
        "nothing relevant in the corpus means nothing was missed")


# --- 2. the metric, and the norm cache -------------------------------------

def check_2():
    import stage_02 as s

    assert _close(s.norm((3.0, 4.0)), 5.0), f"got {s.norm((3.0, 4.0))}"
    assert _close(s.l2((0.0, 0.0), (3.0, 4.0)), 5.0), (
        f"got {s.l2((0.0, 0.0), (3.0, 4.0))}. The squared distance ranks "
        f"identically and is not the distance — which is why forgetting the "
        f"sqrt survives review and only shows up in a reported number")
    assert _close(s.l2((1.0, 1.0), (1.0, 2.0)), 1.0)

    assert _close(s.cosine((1.0, 0.0), (1.0, 0.0)), 1.0)
    assert _close(s.cosine((1.0, 0.0), (-1.0, 0.0)), -1.0)
    assert _close(s.cosine((1.0, 0.0), (0.0, 1.0)), 0.0)
    assert s.cosine((0.0, 0.0), (1.0, 0.0)) == 0.0, (
        "a zero vector has no direction: return 0.0, not nan. NaN compares "
        "False to everything including itself, so it poisons every sort it "
        "enters — silently")
    try:
        s.l2((1.0,), (1.0, 2.0))
    except ValueError:
        pass
    else:
        raise AssertionError("l2 must refuse mismatched dimensions exactly as dot does")

    idx = s.CosineIndex()
    idx.add("long", (10.0, 0.0))
    idx.add("short", (0.5, 0.0))
    idx.add("diag", (0.6, 0.8))
    got = idx.search((1.0, 0.0), 3)
    assert _keys(got) == ["long", "short", "diag"], (
        f"got {_keys(got)}: cosine divides the magnitudes out, so the 10-long "
        f"vector and the 0.5-long one point the same way and TIE. Dot would "
        f"rank 'diag' above 'short' — two metrics, two answers, same data")
    assert _close(_scores(got)[0], 1.0) and _close(_scores(got)[1], 1.0), f"{got}"
    assert _close(_scores(got)[2], 0.6), f"scores: {_scores(got)}"

    zero = s.CosineIndex()
    zero.add("z", (0.0, 0.0))
    zero.add("x", (1.0, 0.0))
    got = zero.search((1.0, 0.0), 2)
    assert _keys(got) == ["x", "z"] and _close(_scores(got)[1], 0.0), (
        f"a zero vector scores 0.0 against everything rather than nan; got {got}")

    cached = s.CosineIndex()
    for i in range(10):
        cached.add(f"v{i}", (1.0, 0.0))
    assert cached.norm_evaluations == 10, (
        f"adding 10 vectors derives 10 norms; counted {cached.norm_evaluations}")
    cached.search((1.0, 0.0), 3)
    cached.search((1.0, 0.0), 3)
    assert cached.norm_evaluations == 12, (
        f"counted {cached.norm_evaluations}: the stored vectors' norms are "
        f"being recomputed inside the comparison loop, so a scan costs O(n) "
        f"square roots instead of O(n) dot products. Cache each stored norm "
        f"at add time — only the query's own norm is per search")


# --- 3. k-means ------------------------------------------------------------

def check_3():
    import stage_03 as s

    assert _close(s.squared_l2((0.0, 0.0), (3.0, 4.0)), 25.0)
    assert s.assign([(1.0, 0.0), (0.99, 0.01), (0.0, 1.0), (0.01, 0.99)],
                    [(1.0, 0.0), (0.0, 1.0)]) == [0, 0, 1, 1]
    assert s.assign([(1.0, 0.0)], [(1.0, 0.0), (1.0, 0.0)]) == [0], (
        "equidistant centroids tie to the LOWEST index, or the partition is "
        "not reproducible and neither is anything measured on it")
    assert s.assign([], [(1.0, 0.0)]) == [], "no vectors, no assignments"

    vectors, labels = _clustered([3, 3, 3], 4, seed=2, spread=0.03)
    flat = [vectors[k] for k in vectors]
    keys = list(vectors)
    centroids, assignments = s.kmeans(flat, 3, seed=0)
    assert len(centroids) == 3, f"one centroid per cluster; got {len(centroids)}"
    assert len(assignments) == len(flat), "one assignment per vector"
    assert len(set(assignments)) == 3, (
        f"three separated groups and three clusters must not leave one empty: "
        f"{assignments}")
    assert len({_group_of(labels, keys[i]) for i in range(len(keys))}) == 3

    for i, (v, a) in enumerate(zip(flat, assignments)):
        assert s.assign([v], centroids)[0] == a, (
            f"vector {keys[i]} is assigned to cluster {a}, but {centroids} "
            f"says another centroid is nearer. Assignment and centroids must "
            f"agree when the iteration stops")
    for j, c in enumerate(centroids):
        members = [v for v, a in zip(flat, assignments) if a == j]
        assert len(c) == len(flat[0]), "a centroid lives in the same space as the data"
        assert all(x == x for x in c), (
            f"NaN centroid: {c}. NaN spreads through every distance computed "
            f"against it and compares False to everything")
        for dim in range(len(c)):
            mean = sum(v[dim] for v in members) / len(members)
            assert _close(c[dim], mean, 1e-9), (
                f"centroid {j} is not the mean of its {len(members)} members "
                f"({c[dim]} vs {mean}): a drifted centroid is a silent recall "
                f"loss, and the iteration's fixed point is the definition")

    again_c, again_a = s.kmeans(flat, 3, seed=0)
    assert again_c == centroids and again_a == assignments, (
        "the same seed must produce the same partition, or the frontier in "
        "stage 5 moves between runs and nothing you measure is comparable")
    other_c, other_a = s.kmeans(flat, 3, seed=7)
    assert len(other_c) == 3 and len(other_a) == len(flat), "any seed is a valid partition"

    for bad in (0, -1, len(flat) + 1):
        try:
            s.kmeans(flat, bad, seed=0)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"nlist={bad} is impossible — empty clusters by construction; "
                f"refuse it instead of returning a partition with holes")


# --- 4. IVF ----------------------------------------------------------------

def _ivf_case(seed=11):
    import stage_01 as s1
    import stage_04 as s4

    vectors, labels = _clustered([20, 20, 20, 20], 8, seed=seed)
    index = s4.IVFIndex(vectors, 4, seed=0)
    exact = s1.ExactIndex()
    for k, v in vectors.items():
        exact.add(k, v)
    return index, exact, vectors, labels


def check_4():
    idx, exact, vectors, labels = _ivf_case()

    assert idx.nlist == 4, f"nlist: {idx.nlist}"
    assert sum(idx.sizes) == len(vectors), (
        f"the partition covers the corpus once: sizes {idx.sizes}, "
        f"{len(vectors)} vectors")
    assert all(n > 0 for n in idx.sizes), f"an empty cluster hides a bug: {idx.sizes}"
    for group in labels:
        members = {idx.assignment(k) for k in group}
        assert len(members) == 1, (
            f"these {len(group)} vectors sit 1.0 apart from every other group "
            f"and 0.05 apart from each other; a partition that splits them, or "
            f"merges two groups, is not the one k-means converges to ({members})")

    q = _unit((0.6, 0.8) + (0.0,) * 6)
    n = len(vectors)

    full = idx.search(q, n, nprobe=4)
    assert full == exact.search(q, n), (
        f"nprobe == nlist visits every vector, so the answer must equal the "
        f"exact index row for row — same rows, same scores, same order")
    assert _scores(full) == sorted(_scores(full), reverse=True)

    one = idx.search(q, 5, nprobe=1)
    clusters = {idx.assignment(k) for k, _ in one}
    assert len(clusters) == 1, (
        f"nprobe=1 opens ONE list, so every returned key comes from one "
        f"cluster; got {clusters}. Scanning more than you were asked to open "
        f"is how an 'approximate' index quietly becomes an exact one with the "
        f"approximate index's memory")
    assert idx.visited == idx.sizes[clusters.pop()], (
        f"a one-list probe scores that list's members and no others: visited "
        f"{idx.visited}, sizes {idx.sizes}")

    two = idx.search(q, 5, nprobe=2)
    assert len({idx.assignment(k) for k, _ in two}) <= 2

    # the probe is by DISTANCE to the query: a corpus member's own cluster is
    # its nearest centroid — that is what an assignment is — so a one-list
    # probe on a member must open that list. Probing the first nprobe lists by
    # index is invisible until a query lands outside them.
    for group in labels:
        member = group[0]
        rows = idx.search(vectors[member], 3, nprobe=1)
        assert rows and rows[0][0] == member, (
            f"{member} is in the corpus, so it is its own nearest neighbour "
            f"and its own cluster is the nearest centroid; nprobe=1 must "
            f"return it first. Got {_keys(rows)}")
        assert {idx.assignment(k) for k, _ in rows} == {idx.assignment(member)}, (
            f"query {member} lives in cluster {idx.assignment(member)}, so "
            f"one probe lands there; got "
            f"{ {idx.assignment(k) for k, _ in rows} }")
    assert _scores(two) == sorted(_scores(two), reverse=True), (
        "descending by score across the probed lists: emitting each list's "
        "best rows in list order produces a list that is only accidentally "
        "sorted, and it is wrong exactly when two lists interleave")
    assert idx.visited == sum(idx.sizes[c] for c in
                             {idx.assignment(k) for k, _ in two} |
                             {idx.assignment(two[-1][0])}) or idx.visited > 0

    idx.search(q, 5, nprobe=99)
    assert idx.visited == n, (
        f"nprobe above nlist clamps to nlist; visited {idx.visited} of {n}")
    try:
        idx.search(q, 5, nprobe=0)
    except ValueError:
        pass
    else:
        raise AssertionError("nprobe=0 probes nothing at all: raise ValueError")

    # a tight cluster near the query is not always the cluster holding the
    # query's nearest neighbour — that is the miss nprobe=1 is allowed to make
    missed = 0
    for query in _queries(30, 8, seed=5):
        if _keys(idx.search(query, 1, nprobe=1)) != _keys(exact.search(query, 1)):
            missed += 1
    assert missed > 0, (
        "a one-list probe found the exact top-1 for all 30 queries: this "
        "index is not restricting its scan, or its 'approximation' is the "
        "exact answer with different bookkeeping")


# --- 5. the frontier, and the set you must not tune on ----------------------

def _bench_corpus(seed=11):
    idx, exact, vectors, labels = _ivf_case(seed=seed)

    rng = random.Random(5)
    tune = [vectors[rng.choice(labels[0])] for _ in range(8)]
    # held-out queries sit between two clusters: near a boundary, so the
    # nearest centroid is not guaranteed to hold their top-k
    held = []
    for a in range(len(labels)):
        for b in range(a + 1, len(labels)):
            for _ in range(2):
                va = vectors[rng.choice(labels[a])]
                vb = vectors[rng.choice(labels[b])]
                held.append(_unit([x + y for x, y in zip(va, vb)]))
    return idx, exact, tune, held


def check_5():
    import stage_05 as s

    idx, exact, tune, held = _bench_corpus()
    k, nprobes = 5, [1, 2, 4]

    rows = s.sweep(idx, exact, tune + held, k, nprobes)
    assert [r["nprobe"] for r in rows] == nprobes, (
        f"one row per nprobe, in the order asked; got "
        f"{[r.get('nprobe') for r in rows]}")
    recalls = [r["recall"] for r in rows]
    visited = [r["visited"] for r in rows]
    assert recalls == sorted(recalls), (
        f"recall cannot fall as you probe more lists — the candidate set only "
        f"grows. Got {recalls}")
    assert visited == sorted(visited) and visited[0] < visited[-1], (
        f"work rises with nprobe; got {visited}. If visited never changes you "
        f"are scanning everything and calling it approximate")
    assert _close(recalls[-1], 1.0), (
        f"nprobe == nlist returns exactly the exact rows, so recall@k is "
        f"exactly 1.0; got {recalls[-1]}. A gold set taken from your own "
        f"approximate answer measures nothing")
    assert 0.0 < recalls[0] < 1.0, (
        f"one list out of four should find some of the gold and miss some; "
        f"got {recalls[0]}")
    assert all(set(r) == {"nprobe", "recall", "visited"} for r in rows), f"rows: {rows}"

    one_only = s.sweep(idx, exact, held, k, [1])[0]["recall"]
    assert 0.0 < one_only < 1.0, (
        f"the boundary queries must defeat a single probe; got {one_only}. "
        f"These queries are built between clusters precisely so that the "
        f"nearest centroid is not enough")

    chosen = s.tune_nprobe(idx, exact, tune, k, 0.9, nprobes)
    recs = {r["nprobe"]: r["recall"] for r in s.sweep(idx, exact, tune, k, nprobes)}
    assert recs[chosen] >= 0.9, f"tuned nprobe {chosen} scores {recs[chosen]}"
    assert all(recs[n] < 0.9 for n in nprobes if n < chosen), (
        f"{chosen} is not the SMALLEST nprobe that reaches the target: "
        f"{recs}")
    assert chosen < nprobes[-1], (
        "the tune queries are corpus members inside cluster 0, so a single "
        "probe reaches its own cluster: the tune set must not need a full scan")

    chosen_held = s.tune_nprobe(idx, exact, held, k, 0.99, nprobes)
    recs_held = {r["nprobe"]: r["recall"] for r in s.sweep(idx, exact, held, k, nprobes)}
    assert recs_held[chosen_held] >= 0.99
    assert all(recs_held[n] < 0.99 for n in nprobes if n < chosen_held)
    assert chosen_held > 1, (
        f"on boundary queries one probe must not reach 0.99; got {recs_held}")
    for bad_target, bad_probes in ((1.01, nprobes), (0.99, [1])):
        try:
            s.tune_nprobe(idx, exact, held, k, bad_target, bad_probes)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"no nprobe in {bad_probes} reaches a recall of {bad_target}: "
                f"returning the largest anyway reports a parameter that does "
                f"not do what it says")

    out = s.report(idx, exact, tune, held, k, 0.9)
    assert set(out) == {"nprobe", "tune_recall", "held_out_recall"}, f"keys: {out}"
    assert out["nprobe"] == chosen, f"report tunes on the tune set; got {out}"
    assert out["tune_recall"] >= 0.9, f"{out}"
    assert out["held_out_recall"] < out["tune_recall"], (
        f"the same nprobe scores worse on queries it never saw — that gap is "
        f"the whole lesson of this stage. Got {out}. Equal numbers mean the "
        f"held-out set is not held out")


# --- 6. the HNSW graph -----------------------------------------------------

def check_6():
    import stage_06 as s

    vectors = _vectors(120, 8, seed=4)
    n = len(vectors)

    try:
        s.build(vectors, 1, seed=0)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "M=1 gives mL = 1/ln(1): there is no such level distribution. "
            "Raise ValueError instead of dividing by zero")

    flat = s.build(vectors, 8, seed=0, mL=0.0)
    assert s.layers(flat) == [0], f"mL=0 is a flat graph; got {s.layers(flat)}"
    assert all(s.level(flat, k) == 0 for k in vectors), "mL=0 puts every node at layer 0"

    g = s.build(vectors, 8, seed=0)
    levels = {k: s.level(g, k) for k in vectors}
    assert s.layers(g) == sorted(set(levels.values())), (
        f"layers() is the set of levels that exist: {s.layers(g)} vs "
        f"{sorted(set(levels.values()))}")
    assert 0 in s.layers(g)
    top = max(levels.values())
    assert top >= 1, (
        "every node sitting at layer 0 is a flat graph — with 120 vectors, "
        "the chance that no node rose above layer 0 is negligible, so the "
        "level draw is not geometric")
    assert levels[g["entry"]] == top, (
        f"the entry point is a highest-level node: {g['entry']} sits at "
        f"layer {levels[g['entry']]}, the top is {top}")
    raised = sum(1 for lv in levels.values() if lv >= 1)
    assert 0 < raised < n / 2, (
        f"{raised} of {n} nodes at layer >= 1. Levels thin out geometrically "
        f"(P(level >= 1) = 1/M); a hierarchy everyone is in is a flat graph "
        f"with extra steps")

    for k in vectors:
        assert g["vectors"][k] == vectors[k], "the graph carries the vectors it built"
    src = {k: tuple(v) for k, v in vectors.items()}
    built = s.build(src, 8, seed=0)
    src["v0"] = (0.0,) * 8
    del src["v1"]
    assert built["vectors"]["v0"] != (0.0,) * 8 and "v1" in built["vectors"], (
        "the graph keeps a reference to the caller's dict: one edit outside "
        "the index invalidates every score it reports")

    links = 0
    for k in vectors:
        for layer in range(levels[k] + 1):
            ns = s.neighbors(g, k, layer)
            assert ns == sorted(ns), f"neighbours of {k} at layer {layer} are sorted"
            assert k not in ns, f"{k} is its own neighbour at layer {layer}"
            cap = 2 * 8 if layer == 0 else 8
            assert len(ns) <= cap, (
                f"{k} has {len(ns)} neighbours at layer {layer}; the cap is "
                f"{cap}. Unbounded degree makes each hop a scan")
            for j in ns:
                assert j in vectors, f"unknown key {j} in the graph"
                assert k in s.neighbors(g, j, layer), (
                    f"{j} is a neighbour of {k} at layer {layer} and not the "
                    f"other way round: a one-way link lets the walk in and "
                    f"not out, so behaviour depends on where it entered")
                links += 1
    assert links > 0, "a graph with no edges is not a graph"

    seen, stack = {g["entry"]}, [g["entry"]]
    while stack:
        for j in s.neighbors(g, stack.pop(), 0):
            if j not in seen:
                seen.add(j)
                stack.append(j)
    assert len(seen) == n, (
        f"layer 0 came out in {len(seen)} pieces: {n - len(seen)} nodes are "
        f"unreachable from the entry point. No query tells you — it just "
        f"returns a worse neighbour, forever")

    again = s.build(vectors, 8, seed=0)
    assert {k: s.level(again, k) for k in vectors} == levels, (
        "the same seed draws the same levels")
    for k in vectors:
        for layer in range(levels[k] + 1):
            assert s.neighbors(again, k, layer) == s.neighbors(g, k, layer), (
                f"the same seed links {k} the same way at layer {layer}")
    other = s.build(vectors, 8, seed=99)
    assert {k: s.level(other, k) for k in vectors} != levels, (
        "a different seed must give a different draw; if it does not, the "
        "seed is ignored and every run is the same graph")

    try:
        s.level(g, "not-a-key")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown key has no level: KeyError")
    assert s.neighbors(g, g["entry"], top + 5) == [], (
        "a layer above every node is empty, not an error")


# --- 7. the walk, and ef ---------------------------------------------------

def check_7():
    import stage_01 as s1
    import stage_06 as s6
    import stage_07 as s

    tiny = {"a": (1.0, 0.0), "b": (0.0, 1.0), "c": (0.7, 0.7)}
    tg = s6.build(tiny, 4, seed=0)
    got = s.search(tg, (1.0, 0.0), 2, ef=10)
    assert _keys(got) == ["a", "c"], (
        f"a pool wider than the corpus is exhaustive; got {_keys(got)}")
    assert _scores(got) == sorted(_scores(got), reverse=True)
    assert len(s.search(tg, (1.0, 0.0), 9, ef=10)) == 3, (
        "k above the corpus size returns everything there is, once each")

    ties = s6.build({"b": (1.0, 0.0), "a": (1.0, 0.0)}, 4, seed=0)
    tie_rows = s.search(ties, (1.0, 0.0), 2, ef=10)
    assert _keys(tie_rows) == ["a", "b"], (
        f"equal scores order by key ascending, the one factor every caller "
        f"agrees on; got {_keys(tie_rows)}")
    assert _close(_scores(tie_rows)[0], _scores(tie_rows)[1]), "and they are a tie"

    try:
        s.search(tg, (1.0, 0.0), 5, ef=3)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "ef is the pool width and k is the answer size: a pool narrower "
            "than the answer cannot return k rows. Refuse it")

    vectors = _vectors(300, 32, seed=3)
    graph = s6.build(vectors, 16, seed=3)
    exact = s1.ExactIndex()
    for k, v in vectors.items():
        exact.add(k, v)
    queries = _queries(25, 32, seed=21)
    k = 10

    for q in queries[:5]:
        assert s.search(graph, q, k, ef=len(vectors)) == exact.search(q, k), (
            "a pool as wide as the corpus is an exhaustive scan: the rows "
            "must equal the exact index, in the same order")

    wide = s.search(graph, queries[0], k, ef=96)
    assert wide == s.search(graph, queries[0], k, ef=96), "search is deterministic"
    assert len(wide) == k and _scores(wide) == sorted(_scores(wide), reverse=True)

    def mean_recall(ef):
        total = 0.0
        for q in queries:
            gold = set(_keys(exact.search(q, k)))
            got_keys = _keys(s.search(graph, q, k, ef=ef))
            total += len(gold & set(got_keys)) / k
        return total / len(queries)

    narrow, wide_r = mean_recall(k), mean_recall(96)
    assert narrow < wide_r, (
        f"recall@10 at ef=10 ({narrow:.3f}) must be below ef=96 ({wide_r:.3f}): "
        f"ef is the dial this stage exists to turn. Equal numbers mean ef is "
        f"being used as the result count and not as the pool width")
    assert wide_r >= 0.98, (
        f"with ef=96 over 300 nodes the walk should be within a hair of "
        f"exhaustive; got {wide_r:.3f}. That number is low when the walk "
        f"returns where it stopped instead of the best rows it saw")

    hits = 0.0
    for q in queries:
        if _keys(s.search(graph, q, 1, ef=64)) == _keys(exact.search(q, 1)):
            hits += 1.0
    assert hits / len(queries) >= 0.95, (
        f"top-1 found {hits / len(queries):.2f} of the time with ef=64: the "
        f"graph is not navigable, or the descent through the upper layers "
        f"starts the layer-0 walk somewhere useless")

    before = {k: s6.neighbors(graph, k, 0) for k in vectors}
    s.search(graph, queries[1], k, ef=32)
    assert {k: s6.neighbors(graph, k, 0) for k in vectors} == before, (
        "search must not mutate the graph")


# --- 8. deletions ----------------------------------------------------------

def check_8():
    import stage_01 as s1
    import stage_08 as s

    vectors = _vectors(60, 8, seed=2)
    idx = s.DeletableIndex(vectors, 8, seed=2)
    exact = s1.ExactIndex()
    for k, v in vectors.items():
        exact.add(k, v)

    assert len(idx) == 60, f"len before any delete: {len(idx)}"
    assert not idx.deleted("v7")

    query = vectors["v7"]
    assert _keys(idx.search(query, 5, ef=200))[0] == "v7", (
        "an exact corpus point is its own nearest neighbour; if that is not "
        "the top row, the index under the deletions is already wrong")

    idx.delete("v7")
    assert idx.deleted("v7") and len(idx) == 59, f"len: {len(idx)}"
    idx.delete("v7")
    assert len(idx) == 59 and idx.deleted("v7"), (
        "deleting a deleted key is a no-op, not a second deletion")
    idx.delete("never-existed")
    assert not idx.deleted("never-existed"), (
        "deleting a key the index never saw must not invent it")

    rows = _keys(idx.search(query, 5, ef=200))
    assert "v7" not in rows, (
        "the tombstone is the true nearest neighbour of this query and must "
        "still not be returned — not even as a filler")
    live_gold = [k for k in _keys(exact.search(query, 10)) if k != "v7"][:5]
    assert rows == live_gold, (
        f"the k best LIVE vectors, which is not the same as the k best "
        f"vectors with the dead one dropped at the end: got {rows} vs "
        f"{live_gold}")

    for k in [k for k in vectors if k != "v7"][:20]:
        idx.delete(k)
    live = [k for k in vectors if not idx.deleted(k)]
    assert len(live) == 39 and len(idx) == len(live), f"{len(idx)} live of {len(live)}"

    whole = idx.search(query, len(live), ef=400)
    assert len(whole) == len(live), (
        f"a pool wide enough for every live node returns all {len(live)} of "
        f"them; got {len(whole)}. A tombstone occupies a candidate slot, so "
        f"filtering only the final rows silently shortens the answer — the "
        f"hallmark of a delete that is 'working'")
    assert not (set(_keys(whole)) & {k for k in vectors if idx.deleted(k)}), (
        "a deleted key came back through the pool")

    live_exact = s1.ExactIndex()
    for k in live:
        live_exact.add(k, vectors[k])
    total = 0.0
    for q in _queries(15, 8, seed=17):
        gold = _keys(live_exact.search(q, 10))
        got = _keys(idx.search(q, 10, ef=400))
        assert not (set(got) - set(live)), f"a deleted key came back: {got}"
        total += len(set(gold) & set(got)) / 10
    assert total / 15 >= 0.95, (
        f"recall over the live corpus fell to {total / 15:.2f} after deleting "
        f"a third of it. If the deleted nodes were unlinked to remove them, "
        f"the paths the remaining ones need went with them — tombstone them "
        f"instead and pay the filtering cost where the walk can see it")

    fresh = _unit((1.0,) + (0.0,) * 7)
    idx.add("v7", fresh)
    assert not idx.deleted("v7") and len(idx) == len(live) + 1, f"len: {len(idx)}"
    rows = dict(idx.search(fresh, len(live) + 1, ef=400))
    assert "v7" in rows and _close(rows["v7"], 1.0), (
        f"a re-admitted key is scored with its NEW vector; got {rows.get('v7')}")


# --- 9. int8 quantization --------------------------------------------------

def check_9():
    import stage_01 as s1
    import stage_09 as s

    vectors = _vectors(200, 8, seed=0)
    q = s.ScalarQuantizer()
    q.fit(vectors.values())
    assert q.bytes_per_vector == 8, (
        f"one byte per dimension: 8 dimensions cost 8 bytes against 32 for "
        f"float32; got {q.bytes_per_vector}")

    span = max(max(col) - min(col) for col in zip(*vectors.values()))
    v = vectors["v3"]
    for x, y in zip(v, q.dequantize(q.quantize(v))):
        assert abs(x - y) <= span / 510 + 1e-12, (
            f"{x} came back as {y}: half of a 255-wide bucket over a span of "
            f"{span} is the most a round trip can lose")

    flat = s.ScalarQuantizer()
    flat.fit([(0.0, 0.0), (1.0, 1.0)])
    codes = flat.quantize((1000.0, -5.0))
    assert codes == [255, 0], (
        f"out-of-range values clamp to the ends of the fitted range; got "
        f"{codes}. An integer cast wraps instead, turning a far-away vector "
        f"into a plausibly close one")
    assert flat.dequantize([255, 0]) == [1.0, 0.0], (
        f"got {flat.dequantize([255, 0])}: the code carries the fitted "
        f"minimum and it has to be added back, or every distance is offset")
    mid = flat.quantize((0.5, 0.5))
    assert mid in ([128, 128], [127, 127]), f"the middle of the range: {mid}"

    idx = s.QuantizedIndex(vectors)
    assert len(idx) == 200
    assert len(idx.code("v3")) == 8

    query = _unit((0.6, 0.8) + (0.0,) * 6)
    got = idx.search(query, 4)
    assert len(got) == 4 and _scores(got) == sorted(_scores(got), reverse=True)

    expected = []
    for key, vec in vectors.items():
        restored = q.dequantize(idx.code(key))
        expected.append((key, sum(a * b for a, b in zip(query, restored))))
    expected.sort(key=lambda kv: -kv[1])
    assert _keys(got)[0] == expected[0][0], (
        f"top row {_keys(got)[0]} vs {expected[0][0]}: the score is the EXACT "
        f"query against the DEQUANTIZED stored vector. Quantizing the query "
        f"too — symmetric distance — adds its error for nothing")
    assert _close(_scores(got)[0], expected[0][1]), (
        f"score {_scores(got)[0]} against the recomputed {expected[0][1]}")

    exact = s1.ExactIndex()
    for key, vec in vectors.items():
        exact.add(key, vec)
    total = 0.0
    for query in _queries(10, 8, seed=6):
        gold = set(_keys(exact.search(query, 10)))
        got_keys = _keys(idx.search(query, 10))
        total += len(gold & set(got_keys)) / 10
    assert total / 10 >= 0.9, (
        f"int8 recall@10 came out at {total / 10:.2f}. One byte per dimension "
        f"is lossy, not broken — this corpus tolerates 0.9. A much lower "
        f"number is usually the offset (lo) left out, or a wrapped cast")


# --- 10. the frontier, and choosing a point on it ---------------------------

def _frontier_case(seed=13):
    import stage_01 as s1
    import stage_04 as s4
    import stage_09 as s9

    vectors, labels = _clustered([25, 25, 25, 25], 8, seed=seed, spread=0.01)
    ivf = s4.IVFIndex(vectors, 4, seed=0)
    quant = s9.QuantizedIndex(vectors)
    exact = s1.ExactIndex()
    for k, v in vectors.items():
        exact.add(k, v)
    dim = 8

    def exact_search(query, k):
        exact.reset_counter()
        rows = exact.search(query, k)
        return rows, exact.comparisons

    def ivf_search(query, k):
        return ivf.search(query, k, nprobe=2), ivf.visited

    def quant_search(query, k):
        return quant.search(query, k), len(vectors)

    entries = [
        {"name": "exact", "search": exact_search, "bytes_per_vector": dim * 4},
        {"name": "ivf-nprobe2", "search": ivf_search, "bytes_per_vector": dim * 4},
        {"name": "int8", "search": quant_search, "bytes_per_vector": dim},
    ]
    return entries, exact, vectors, labels


def check_10():
    import stage_01 as s1
    import stage_10 as s

    entries, exact, vectors, labels = _frontier_case()
    rng = random.Random(3)
    queries = [vectors[rng.choice(labels[0])] for _ in range(6)]
    queries += _queries(6, 8, seed=8)
    k = 10

    rows = s.compare(entries, exact, queries, k)
    assert [r["name"] for r in rows] == ["int8", "exact", "ivf-nprobe2"], (
        f"the frontier comes back cheapest bytes first, ties by name; got "
        f"{[r.get('name') for r in rows]}")
    assert all(set(r) == {"name", "bytes_per_vector", "recall", "visited"} for r in rows), (
        f"one row per index with those four fields: {rows}")

    by_name = {r["name"]: r for r in rows}
    assert _close(by_name["exact"]["recall"], 1.0), (
        f"the exact index is the gold, so its recall is 1.0 by construction; "
        f"got {by_name['exact']['recall']}")
    assert 0.0 < by_name["int8"]["recall"] < 1.0, (
        f"int8 loses some recall; got {by_name['int8']['recall']}. If it is "
        f"1.0 the quantizer is not quantizing, and the bytes do not shrink")
    assert by_name["int8"]["visited"] == len(vectors), (
        "a flat scan visits the whole corpus, that is its cost")
    assert by_name["ivf-nprobe2"]["visited"] < len(vectors), (
        f"probing 2 of 4 lists visits about half the corpus; got "
        f"{by_name['ivf-nprobe2']['visited']}. The IVF's win is work, not "
        f"bytes — its row carries the same bytes_per_vector as the exact one")

    # the reported numbers must be measurements, not decorations
    for row in rows:
        total_r, total_v = 0.0, 0.0
        entry = next(e for e in entries if e["name"] == row["name"])
        for q in queries:
            got_keys = set(_keys(entry["search"](q, k)[0]))
            gold = set(_keys(exact.search(q, k)))
            total_r += len(gold & got_keys) / k
            total_v += entry["search"](q, k)[1]
        assert _close(row["recall"], total_r / len(queries), 1e-9), (
            f"{row['name']}: reported recall {row['recall']} against a "
            f"recomputed {total_r / len(queries)}")
        assert _close(row["visited"], total_v / len(queries), 1e-9), (
            f"{row['name']}: reported visited {row['visited']} against a "
            f"recomputed {total_v / len(queries)}")

    assert s.choose(rows, 1.0) == "exact", (
        "only the exact index reaches a recall floor of 1.0: the cheapest "
        "index that satisfies the requirement is the one to pick, and int8 "
        "does not satisfy it")
    assert s.choose(rows, 0.0) == "int8", (
        f"with no recall requirement the cheapest representation wins; got "
        f"{s.choose(rows, 0.0)}")
    assert s.choose(rows, by_name["int8"]["recall"]) == "int8", (
        "at exactly the floor an index qualifies — >= is not >")
    assert s.choose(rows, min(1.0, by_name["int8"]["recall"] + 0.01)) == "exact", (
        "just above int8's recall the choice becomes the exact index")

    crafted = [
        {"name": "fast-but-wrong", "bytes_per_vector": 4, "recall": 0.5,
         "visited": 10},
        {"name": "balanced", "bytes_per_vector": 8, "recall": 0.93, "visited": 200},
        {"name": "exact", "bytes_per_vector": 32, "recall": 1.0, "visited": 200},
    ]
    assert s.choose(crafted, 0.9) == "balanced", (
        f"got {s.choose(crafted, 0.9)}: the fewest-bytes row that MEETS the "
        f"floor. Sorting by bytes and taking the first is how a recall floor "
        f"quietly becomes a bytes-per-vector award")
    assert s.choose(crafted, 1.0) == "exact"
    for rows_in, floor in ((crafted, 1.01), ([], 0.5)):
        try:
            s.choose(rows_in, floor)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"nothing in {rows_in} reaches {floor}: a fallback that "
                f"returns something anyway is how the floor stops meaning "
                f"anything")


STAGES = [
    stage(
        1, file="stage_01.py", title="the exact baseline and recall@k",
        tags=["retrieval", "measurement"],
        action=("Implement dot, ExactIndex (stable ties, a work counter, copies "
                "of the vectors) and recall_at_k."),
        predict="Two relevant documents, one of them in the top 1: recall@1?",
        hints=["the denominator is the number of relevant documents, not k",
               "sort by (-score, insertion index); ties are the whole reason "
               "the stage exists"],
        check=check_1, solution="solutions/stage_01.py: ExactIndex"),
    stage(
        2, file="stage_02.py", title="the metric, and the norm cache",
        tags=["metric", "caching"],
        action=("Implement norm, l2, cosine (0.0 for a zero vector) and "
                "CosineIndex with each stored vector's norm cached at add time."),
        predict="Cosine of a long vector and a short one in the same direction?",
        hints=["NaN compares False to everything, including itself",
               "cache the stored norms; the query's norm is not storable"],
        check=check_2, solution="solutions/stage_02.py: CosineIndex"),
    stage(
        3, file="stage_03.py", title="k-means, the partition IVF scans",
        tags=["clustering", "reproducibility"],
        action=("Implement squared_l2, assign and kmeans with k-means++ init "
                "from random.Random(seed), stopping when assignments stop "
                "changing."),
        predict="Which point does k-means++ pick as the second centroid?",
        hints=["weight the draw by the squared distance to the nearest chosen "
               "centroid",
               "an empty cluster keeps its previous centroid; never a NaN"],
        check=check_3, solution="solutions/stage_03.py: kmeans"),
    stage(
        4, file="stage_04.py", title="IVF: probing and ranking across lists",
        tags=["retrieval", "ordering"],
        action=("Implement IVFIndex: partition with k-means, probe the nprobe "
                "nearest centroids, score only their members, rank the union."),
        predict="With nprobe=nlist, how does the answer compare to the exact one?",
        hints=["probe by distance to the query, not by list index",
               "one heap across all probed lists; never emit list by list"],
        check=check_4, solution="solutions/stage_04.py: IVFIndex"),
    stage(
        5, file="stage_05.py", title="the frontier, and the query set",
        tags=["measurement", "overfitting"],
        action=("Implement sweep, tune_nprobe and report: recall against the "
                "exact index, tuned on one query set and measured on another."),
        predict="Tuned on one set, measured on another: which number is bigger?",
        hints=["gold is the exact index's top-k, per query",
               "report both recalls, or the gap stays invisible"],
        check=check_5, solution="solutions/stage_05.py: report"),
    stage(
        6, file="stage_06.py", title="the HNSW graph, built not searched",
        tags=["graph", "invariants"],
        action=("Implement build, neighbors, level and layers: geometric "
                "levels, mutual links, degree caps at layer 0 and above."),
        predict="What fraction of 120 nodes ends up above layer 0?",
        hints=["prune symmetrically, or the walk can enter and not leave",
               "level = floor(-ln(u) * mL), mL = 1/ln(M)"],
        check=check_6, solution="solutions/stage_06.py: build"),
    stage(
        7, file="stage_07.py", title="the walk, and ef",
        tags=["graph", "tuning"],
        action=("Implement search: greedy descent above layer 0, a best-first "
                "walk with a pool of ef at layer 0, the k best rows seen."),
        predict="Mean recall@10 at ef=8 and ef=96 over 25 queries?",
        hints=["what the walk stopped at is not the answer — the best rows "
               "seen are",
               "ef >= the corpus size is an exhaustive scan: use it to check "
               "yourself"],
        check=check_7, solution="solutions/stage_07.py: search"),
    stage(
        8, file="stage_08.py", title="deletions without unlink",
        tags=["deletion", "invariants"],
        action=("Implement DeletableIndex: tombstone on delete, filter during "
                "the walk so the pool still fills, re-admit on add."),
        predict="Delete 25 of 60 nodes: how many rows does k=35 return?",
        hints=["a pool slot taken by a dead node is a slot the walk cannot use",
               "unlinking the node removes the edges its neighbours still need"],
        check=check_8, solution="solutions/stage_08.py: DeletableIndex"),
    stage(
        9, file="stage_09.py", title="int8 quantization",
        tags=["compression", "numerical-stability"],
        action=("Implement ScalarQuantizer (per-dimension fit, clamp, "
                "dequantize) and QuantizedIndex scoring the exact query "
                "against the reconstructed vector."),
        predict="Codes for a corpus spanning [0,1], given a query at 1000?",
        hints=["clamp at 255; a wrap turns far away into plausibly close",
               "keep the query exact — asymmetric distance is free accuracy"],
        check=check_9, solution="solutions/stage_09.py: QuantizedIndex"),
    stage(
        10, file="stage_10.py", title="the frontier, and choosing a point on it",
        tags=["measurement", "decision"],
        action=("Implement compare (recall, bytes, work per index, tuned by "
                "the caller) and choose: the fewest bytes that meet the floor."),
        predict="Recall floor 0.9 and a 4-bytes-per-vector index at recall "
                "0.5: which index is chosen?",
        hints=["compare at equal recall, never at equal parameters",
               "the floor is a >= test, and nothing meeting it is an error, "
               "not a fallback"],
        check=check_10, solution="solutions/stage_10.py: choose"),
]

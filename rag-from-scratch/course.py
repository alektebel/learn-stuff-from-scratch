"""RAG From Scratch — course manifest.

A retrieval-augmented generation stack, built from the parts up in pure
standard-library Python: chunking, term-weighting embeddings, a vector index,
BM25, rank fusion, reranking, citations, tenant isolation, and an end-to-end
recall@k capstone.

The checks are the course. Each one targets a mistake that is easy to make and
hard to notice — off-by-one chunk offsets, an idf that goes negative, a fusion
that compares incomparable scores, a retrieval call that can cross tenants.

Python standard library only. Run it with:

    python3 codecraft/cli.py run rag-from-scratch
"""

from codecraft.api import stage

TITLE = "RAG From Scratch"
DESCRIPTION = ("Retrieval-augmented generation from the parts up: chunking, "
               "TF-IDF, a vector index, BM25, hybrid fusion, reranking, "
               "citations and tenant isolation.")
LEVEL = "intermediate"
ORDER = 8


# --- 1. chunking -----------------------------------------------------------

def check_1():
    from stage_01 import chunk

    c = chunk("abcdefghij", 4, 1)
    assert [h["start"] for h in c] == [0, 3, 6], f"starts: {c}"
    assert [h["end"] for h in c] == [4, 7, 10], f"ends: {c}"
    for h in c:
        assert h["text"] == "abcdefghij"[h["start"]:h["end"]], (
            f"offset/text mismatch: {h}. If they disagree your citations point "
            "at the wrong bytes.")

    single = chunk("abc", 10, 0)
    assert len(single) == 1 and single[0]["text"] == "abc", (
        f"a document shorter than the window is one chunk; got {single}")

    assert [h["text"] for h in chunk("abcdef", 4, 0)] == ["abcd", "ef"], (
        "overlap 0 must produce contiguous, non-overlapping chunks")

    try:
        chunk("abc", 2, 2)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "overlap >= size would never advance (or would loop forever); "
            "raise ValueError")


# --- 2. TF-IDF -------------------------------------------------------------

def check_2():
    from stage_02 import Tfidf, cosine, tokenize

    assert tokenize("Hello, World! 42") == ["hello", "world", "42"], \
        f"tokenize must lowercase and split on non-alphanumerics: " \
        f"{tokenize('Hello, World! 42')}"

    m = Tfidf().fit(["the cat sat", "the dog sat", "quantum physics"])
    v = m.transform("the cat sat")
    assert abs(cosine(v, v) - 1.0) < 1e-9, (
        "a vector must be perfectly similar to itself; if this is off, your "
        "normalisation is wrong or the vectors carry unequal scales")
    assert cosine(v, m.transform("quantum physics")) < 0.5, (
        "unrelated documents must not look similar")
    assert m.idf["quantum"] > m.idf["the"], (
        "a rare term must outweigh a common one. If idf is negative you used "
        "log(df/N) without smoothing; use ln((N+1)/(df+1)) + 1")
    assert cosine({}, v) == 0.0, "an empty vector has zero similarity, not nan"


# --- 3. vector index -------------------------------------------------------

def check_3():
    from stage_03 import VectorIndex

    idx = VectorIndex()
    idx.add("a", {"x": 1.0})
    idx.add("b", {"y": 1.0})
    idx.add("c", {"x": 0.5})
    assert len(idx) == 3, f"len: {len(idx)}"
    assert idx.search({"x": 1.0}, 2) == [("a", 1.0), ("c", 0.5)], (
        f"dot products with sorted output expected; got {idx.search({'x': 1.0}, 2)}")

    ties = VectorIndex()
    ties.add("p", {"x": 1.0})
    ties.add("q", {"x": 1.0})
    assert [k for k, _ in ties.search({"x": 1.0}, 2)] == ["p", "q"], (
        "equal scores must keep insertion order, or results are unstable "
        "between runs and your evals measure noise")
    assert ties.search({"absent": 1.0}, 5) == [("p", 0.0), ("q", 0.0)]


# --- 4. BM25 ---------------------------------------------------------------

def check_4():
    from stage_04 import bm25_scores

    docs = [["cat", "sat"], ["dog", "sat"], ["quantum", "physics"]]
    s = bm25_scores(["quantum"], docs)
    assert len(s) == 3, f"one score per document; got {s}"
    assert s[2] == max(s) and s[2] > 0, (
        f"the only document containing the query term must rank first; got {s}")
    assert bm25_scores(["missing"], docs) == [0.0, 0.0, 0.0], (
        "a query term in no document contributes nothing")
    assert all(x >= 0 for x in s), (
        "BM25 scores must be non-negative; a negative idf means you used the "
        "un-smoothed log((N-df+0.5)/(df+0.5))")
    assert s[2] > bm25_scores(["sat"], docs)[0], \
        "a term in every other document must be worth less than a rare one"


# --- 5. hybrid fusion ------------------------------------------------------

def check_5():
    from stage_05 import reciprocal_rank_fusion

    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=60)
    ids = [i for i, _ in fused]
    assert ids[0] == "a", (
        f"a is #1 in dense and #2 in lexical, so it must win; got {fused}. "
        "Did you sum raw scores instead of reciprocal ranks?")
    assert set(ids) == {"a", "b", "c", "d"}, f"missing or invented ids: {ids}"
    assert len(ids) == len(set(ids)), "an id must appear once in the fusion"
    assert reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=1)[0][0] == "a"


# --- 6. reranking ----------------------------------------------------------

def check_6():
    from stage_06 import mrr, overlap_score, rerank

    assert overlap_score(["alpha"], ["alpha", "beta"]) == 1.0
    assert overlap_score(["alpha", "gamma"], ["alpha"]) == 0.5, (
        "coverage is over the QUERY, not the document")
    assert overlap_score([], ["alpha"]) == 0.0

    candidates = [("B", ["beta"]), ("A", ["alpha"])]
    before = ["B", "A"]
    after = [cid for cid, _ in rerank(["alpha"], candidates)]
    assert after[0] == "A", f"rerank must move the overlapping doc up; got {after}"
    assert mrr(before, {"A"}) == 0.5 and mrr(after, {"A"}) == 1.0, (
        "MRR is 1/rank of the first relevant id; this is the number the stage "
        "exists to move")


# --- 7. citations ----------------------------------------------------------

def check_7():
    from stage_07 import find_support, unsupported

    chunks = [["the", "cat", "sat"], ["quantum", "physics", "is", "hard"]]
    assert find_support(["cat", "sat"], chunks) == [0], \
        f"got {find_support(['cat', 'sat'], chunks)}"
    assert unsupported(["dogs", "fly"], chunks), (
        "a claim no chunk covers must be reported unsupported, never printed "
        "as if it were grounded")
    assert find_support(["cat", "sat", "down"], chunks) == [0], (
        "2/3 coverage is above the 0.6 threshold; near-misses must still cite")


# --- 8. tenant isolation ---------------------------------------------------

def check_8():
    from stage_08 import TenantIndex

    idx = TenantIndex()
    idx.add("A", "a1", {"x": 1.0})
    idx.add("A", "a2", {"y": 1.0})
    idx.add("B", "b1", {"x": 1.0})

    res_a = idx.search("A", {"x": 1.0}, 10)
    assert res_a and res_a[0][0] == "a1", f"tenant A must find its own doc: {res_a}"
    assert not any(k.startswith("b") for k, _ in res_a), (
        f"tenant A retrieved tenant B's doc: {res_a}")
    res_b = idx.search("B", {"x": 1.0}, 10)
    assert res_b and res_b[0][0] == "b1" and not any(k.startswith("a") for k, _ in res_b)
    assert idx.search("C", {"x": 1.0}, 10) == [], \
        "an unknown tenant retrieves nothing, it does not error"

    for i in range(50):
        idx.add("A", f"secretA{i}", {"z": 1.0})
        idx.add("B", f"secretB{i}", {"z": 1.0})
    for _ in range(50):
        got = idx.search("A", {"z": 1.0}, 1000)
        assert not any(k.startswith("secretB") for k, _ in got), (
            "cross-tenant leak. Isolation must be structural: search scopes "
            "to the tenant before scoring, in a way no caller can forget.")


# --- 9. end-to-end recall --------------------------------------------------

def check_9():
    from stage_09 import build, recall_at_k, retrieve

    docs = ["the cat sat on the mat", "quantum physics is hard",
            "dogs and cats are pets"]
    model, index = build(docs)
    top = [i for i, _ in retrieve("quantum physics", model, index, 1)]
    assert top == [1], (
        f"the only doc containing both query terms must rank first; got {top}")

    questions = ["quantum physics", "cat", "pets"]
    gold = [1, 0, 2]
    assert recall_at_k(model, index, questions, gold, 1) == 1.0, (
        "every question should find its gold chunk at k=1 on this corpus")
    assert recall_at_k(model, index, questions, gold, 3) == 1.0


STAGES = [
    stage(
        1, file="stage_01.py", title="chunking with exact offsets",
        tags=["chunking", "boundary"],
        action=("Implement chunk(): stride = size - overlap, emit "
                "{start, end, text} until the text is covered, keep the last "
                "chunk short and the offsets exact."),
        predict="How many chunks for a 10-char text, size 4, overlap 1?",
        hints=["stride is size - overlap, not size",
               "break when end == len(text), or the loop runs one chunk too far"],
        check=check_1),
    stage(
        2, file="stage_02.py", title="TF-IDF on sparse dicts",
        tags=["embeddings", "numerical-stability"],
        action=("Implement tokenize, Tfidf.fit/transform (smoothed idf, L2 "
                "normalise) and cosine over sparse dicts."),
        predict="What is cosine(v, v) for a TF-IDF vector, and why not exactly 1?",
        hints=["idf = ln((N + 1) / (df + 1)) + 1, which is never zero or negative",
               "normalise before indexing so dot product is cosine"],
        check=check_2),
    stage(
        3, file="stage_03.py", title="exact brute-force vector index",
        tags=["retrieval", "data-structure"],
        action=("Implement VectorIndex with insertion order preserved and a "
                "stable tie-break, so equal scores are deterministic."),
        predict="With two docs scoring 1.0 and 0.5, what does search(q, 2) return?",
        hints=["store the insertion index and sort by (-score, order)",
               "copy the vector on add; sharing it lets a caller mutate your index"],
        check=check_3),
    stage(
        4, file="stage_04.py", title="BM25",
        tags=["retrieval", "boundary"],
        action=("Implement bm25_scores: smoothed non-negative idf, "
                "length-normalised tf, one score per document."),
        predict="For a term absent from every document, what is its contribution?",
        hints=["idf = ln(1 + (N - df + 0.5) / (df + 0.5)) keeps scores >= 0",
               "average document length uses the corpus you were given"],
        check=check_4),
    stage(
        5, file="stage_05.py", title="reciprocal rank fusion",
        tags=["retrieval", "ordering"],
        action=("Implement RRF over rank lists: score += 1/(k + rank), "
                "deduped, sorted by score with a stable tie-break."),
        predict="Which doc wins: #1 dense + #2 lexical, or #3 dense + #1 lexical?",
        hints=["rk is 1-based; 1/(k+0) would let rank 0 dominate",
               "fuse ranks, not scores — the two retrievers have no common scale"],
        check=check_5),
    stage(
        6, file="stage_06.py", title="reranking and MRR",
        tags=["reranking", "regression"],
        action=("Implement query-coverage scoring, rerank the candidate list, "
                "and mrr() to measure the move."),
        predict="MRR of relevant doc at rank 2 before, and rank 1 after rerank?",
        hints=["coverage is |query ∩ doc| / |query|, not over the doc",
               "MRR is 1/rank of the FIRST relevant id, not the count"],
        check=check_6),
    stage(
        7, file="stage_07.py", title="citations and unsupported claims",
        tags=["attribution", "regression"],
        action=("Implement find_support and unsupported with a coverage "
                "threshold, so ungrounded claims are flagged not printed."),
        predict="A claim matching 2 of 3 tokens: supported at threshold 0.6?",
        hints=["coverage is over the claim tokens",
               ">= threshold, or a claim that exactly covers half is dropped"],
        check=check_7),
    stage(
        8, file="stage_08.py", title="tenant isolation",
        tags=["authorization", "aliasing"],
        action=("Implement TenantIndex so search scopes to the tenant before "
                "scoring; an unknown tenant returns []."),
        predict="Can a search for tenant A ever return a tenant-B key?",
        hints=["partition on add; never filter after scoring across all tenants",
               "unknown tenant returns an empty list, not an error"],
        check=check_8),
    stage(
        9, file="stage_09.py", title="end-to-end retrieval and recall@k",
        tags=["plumbing", "regression"],
        action=("Wire stages 1-3 into build/retrieve and measure recall@k "
                "against a tiny labelled set."),
        predict="Recall@1 for three questions whose gold docs are unambiguous?",
        hints=["key the index by the document's position in docs",
               "recall@k asks whether the gold id is in the top k at all"],
        check=check_9),
]

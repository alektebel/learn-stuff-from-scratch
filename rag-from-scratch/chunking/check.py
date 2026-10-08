"""
Progress checker for the RAG project-4 contextual-chunking templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports this module's own ``solutions/``; it
tests YOUR template. The shared eval set lives in ``../eval-set`` and is imported from its
``solutions/`` exactly the way the sibling stages reach it, in step 4 only. Steps 1, 2, 3,
5 and 6 and step 4's first half run on hand-built corpora, so the mutation harness can run
them in a bare temporary directory without the eval set or the sibling ``../bm25``.

The checks are deliberately adversarial:

* step 1 pins chunking by hand: a single-sentence body is one chunk, a long body is several
  with the *last partial chunk kept*, the character offsets cover the body exactly, and the
  result is deterministic — dropping the tail fails here;
* step 2 pins the context prefix: the contextual text must contain the title, the section
  path and the chunk text in that order, and a plain chunk must contain none of the first
  two;
* step 3 builds a query term that appears in many chunks of different documents but whose
  intended document carries it only in its *section label*, so plain chunking excludes or
  ranks that document away while contextual chunking ranks it first — a constant label or a
  missing prefix fails here;
* step 4 runs end to end on the shared eval set: plain vs contextual doc-level recall@k,
  MRR and nDCG@k per family plus abstention. It asserts only that the contextual ranking is
  a valid document set (no id outside the corpus, no document twice) and reports honestly —
  it never asserts contextual wins;
* step 5 constructs the limit cases: a fact straddling a chunk boundary that neither plain
  nor contextual ranks first until the overlap is widened, and a short body that must stay
  one chunk;
* step 6 pins abstention: a no-answer query returns no chunks and no documents for both
  plain and contextual chunking, and none through ``evaluate``.
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
    import corpus
    import metrics
    import queries

    return corpus, queries, metrics


# ---------------------------------------------------------------------------
# Hand-built corpora (every step except 4b needs no eval set)
# ---------------------------------------------------------------------------

def _self_contained():
    """A tiny corpus with two chunks for ``A``, plus one answerable and one no-answer query.

    The multi-chunk document is what catches a ``retrieve`` that forgets to reduce the
    chunk ranking to distinct documents: ``A`` matches the query in both of its chunks.
    """
    documents = [
        {"doc_id": "A", "title": "alpha report", "department": "eng",
         "topics": ["alpha"],
         "body": "alpha access policy. alpha access review. alpha access audit. "
                 "alpha access controls."},
        {"doc_id": "B", "title": "beta report", "department": "fin",
         "topics": ["beta"],
         "body": "beta retention schedule. beta retention review. beta retention audit."},
        {"doc_id": "C", "title": "gamma report", "department": "sec",
         "topics": ["gamma"], "body": "gamma encryption standard. gamma key rotation."},
    ]
    query_sets = {
        "lexical": [
            {"qid": "L1", "text": "alpha access", "type": "lexical", "filters": {},
             "relevance": {"A": 2.0}},
        ],
        "no_answer": [
            {"qid": "N1", "text": "zzzq nonexistent topic", "type": "no_answer",
             "filters": {}, "relevance": {}},
        ],
    }
    return documents, query_sets


def _disambiguation_corpus():
    """Four documents whose bare passages all contain "zebra" except the intended one.

    ``D`` is the intended document: its query term lives only in its *section label*
    (``"biology: zebra"``), never in its bare body, so plain chunking drops it while
    contextual chunking recovers it. The other three carry "zebra" in a longer body, so
    they are the many-chunk lexical noise the context must outrank.
    """
    return [
        {"doc_id": "D", "title": "field notes", "department": "biology",
         "topics": ["zebra"], "body": "coats vary"},
        {"doc_id": "E", "title": "savanna", "department": "ecology",
         "topics": ["habitat"],
         "body": "the zebra moves across the wide savanna plains at dawn"},
        {"doc_id": "F", "title": "riverbank", "department": "ecology",
         "topics": ["water"],
         "body": "a zebra grazes near the winding river every calm morning"},
        {"doc_id": "G", "title": "herd", "department": "ecology", "topics": ["social"],
         "body": "young zebra follow the herd through tall dry grass"},
    ]


def _boundary_corpus():
    """A fact split across two chunks: "budget" in one, "ledger" in the next.

    ``I`` is the intended document. With no overlap its two terms never share a chunk,
    while ``A`` has both in one chunk, so ``A`` ranks first. With a wide enough overlap
    ``I`` gains a chunk carrying both terms and takes the top rank.
    """
    return [
        {"doc_id": "A", "title": "summary", "department": "general",
         "topics": ["summary"],
         "body": "budget ledger report summary for the operations department."},
        {"doc_id": "I", "title": "review", "department": "general",
         "topics": ["review"],
         "body": "quarterly review. budget planning. ledger reconciliation."},
    ]


# ---------------------------------------------------------------------------
# Step 1: sentence splitting and chunking
# ---------------------------------------------------------------------------

def check_chunking() -> None:
    import chunking

    body = "Alpha one. Beta two! Gamma three?"
    spans = chunking.split_sentences(body)
    assert len(spans) == 3, (
        f"a three-sentence body must split into 3 spans, got {len(spans)}: {spans}")
    for start, end in spans:
        assert 0 <= start < end <= len(body), (
            f"a sentence span must be a valid (start, end) pair, got {(start, end)}")
        assert body[start:end].strip(), (
            f"a span must contain a sentence, got {body[start:end]!r}")
        assert not body[start].isspace(), (
            f"a span must start at the sentence's first character: {body[start:end]!r}")
    assert spans[0][0] == 0, "the first span must start at the body's first character"
    assert spans[-1][1] == len(body), "the last span must end at the body's last character"
    for left, right in zip(spans, spans[1:]):
        assert right[0] == left[1], (
            f"the spans must tile the body with no gap: {left} then {right}")

    short = {"doc_id": "D1", "title": "short", "body": "One short sentence."}
    chunks = chunking.chunk_document(short, size=1000, overlap=100)
    assert len(chunks) == 1, (
        f"a body shorter than size must be exactly one chunk, got {len(chunks)}")
    assert chunks[0].start == 0 and chunks[0].end == len(short["body"]), (
        f"the single chunk must cover the whole body, got "
        f"{chunks[0].start}:{chunks[0].end}")
    assert chunks[0].text == short["body"], (
        "the single chunk's text must be the body itself")

    long_body = ("Alpha carries the first fact we care about. "
                 "Beta carries the second fact we care about. "
                 "Gamma carries the third fact we care about. "
                 "Delta carries the fourth fact we care about. "
                 "Epsilon carries the final leftover fact.")
    long = {"doc_id": "D2", "title": "long", "body": long_body}
    chunks = chunking.chunk_document(long, size=70, overlap=15)
    assert len(chunks) >= 3, (
        f"a body much longer than size must yield several chunks, got {len(chunks)}")
    assert chunks[0].start == 0, (
        "the first chunk must start at the first character of the body")
    assert chunks[-1].end == len(long_body), (
        f"the LAST partial chunk must be kept: the final chunk ends at "
        f"{chunks[-1].end}, the body ends at {len(long_body)} — dropping the tail is the "
        "classic chunker bug")
    assert len(chunks[-1].text) < len(long_body), (
        "the last chunk must be a partial passage, not the whole body")
    for chunk in chunks:
        assert 0 <= chunk.start < chunk.end <= len(long_body), (
            f"chunk offsets out of range: {chunk.start}:{chunk.end}")
        assert chunk.text == long_body[chunk.start:chunk.end], (
            f"chunk text does not equal body[start:end]: {chunk.text!r}")
        assert chunk.doc_id == "D2", "a chunk must carry its document's id"
        assert chunk.chunk_id, "a chunk must have a non-empty chunk_id"
    for left, right in zip(chunks, chunks[1:]):
        assert right.start <= left.end, (
            f"chunks must be contiguous or overlapping, never gapped: "
            f"{left.start}:{left.end} then {right.start}:{right.end}")
        assert right.end > left.end, "chunks must make forward progress"
    ids = [chunk.chunk_id for chunk in chunks]
    assert len(set(ids)) == len(ids), f"chunk ids must be unique, got {ids}"
    again = chunking.chunk_document(long, size=70, overlap=15)
    assert again == chunks, "chunking must be deterministic for the same inputs"
    print(f"      split {len(spans)} sentences; short body -> 1 chunk; long body -> "
          f"{len(chunks)} chunks, last ends at {chunks[-1].end} (body {len(long_body)})")


# ---------------------------------------------------------------------------
# Step 2: the section label and the contextual prefix
# ---------------------------------------------------------------------------

def check_context() -> None:
    import chunking

    document = {
        "doc_id": "D1", "title": "Alpha retention standard", "department": "Finance",
        "topics": ["data retention"], "body": "keep records for seven years.",
    }
    chunks = chunking.chunk_document(document)
    assert chunks, "the document must produce at least one chunk"
    chunk = chunks[0]

    label = chunking.section_path(document)
    assert label == "Finance: data retention", (
        f"section_path must be '<department>: <first topic>', got {label!r}")
    assert chunking.section_path(document) == label, "section_path must be deterministic"

    contextual = chunking.contextualise(chunk, document)
    i_title = contextual.find(document["title"])
    i_label = contextual.find(label)
    i_chunk = contextual.find(chunk.text)
    assert i_title != -1, f"the contextual text must contain the title: {contextual!r}"
    assert i_label != -1, f"the contextual text must contain the section path: {contextual!r}"
    assert i_chunk != -1, f"the contextual text must contain the chunk text: {contextual!r}"
    assert i_title < i_label < i_chunk, (
        f"title, section path and chunk text must appear in that order, got "
        f"positions {(i_title, i_label, i_chunk)} in {contextual!r}")

    plain = chunk.text
    assert document["title"] not in plain, (
        "a plain chunk must be the passage alone, with no title prefix")
    assert label not in plain, (
        "a plain chunk must be the passage alone, with no section-path prefix")
    print(f"      section_path {label!r}; contextual text = {contextual!r}")


# ---------------------------------------------------------------------------
# Step 3: context disambiguates a bare passage
# ---------------------------------------------------------------------------

def check_retrieval() -> None:
    import chunking

    documents = _disambiguation_corpus()
    plain_index = chunking.build_index(documents, contextual=False)
    context_index = chunking.build_index(documents, contextual=True)
    plain_rank = chunking.retrieve("zebra", 5, plain_index)
    context_rank = chunking.retrieve("zebra", 5, context_index)

    matching = [chunk for chunk in plain_index["chunks"]
                if "zebra" in chunk.text.lower()]
    assert len(matching) >= 3, (
        f"the query term must appear in many chunks, got {len(matching)}")

    assert plain_rank, "plain chunking must return the documents whose passages match"
    assert plain_rank[0] != "D", (
        f"the intended document D has no query term in its bare passage, so plain "
        f"chunking must not rank it first; got {plain_rank}")
    assert "D" not in plain_rank, (
        f"plain chunking cannot see D at all (its body lacks the term); got {plain_rank}")

    assert context_rank and context_rank[0] == "D", (
        f"the section path puts the query term on D's chunk, so contextual chunking "
        f"must rank D first; got {context_rank}")

    intended = next(doc for doc in documents if doc["doc_id"] == "D")
    chunk = chunking.chunk_document(intended)[0]
    assert "zebra" not in chunk.text.lower(), (
        "the hand-built case is not testing the context fix: D's body already matches")
    assert "zebra" in chunking.contextualise(chunk, intended).lower(), (
        "the contextual text must carry the section-path term the body lacks")
    print(f"      plain {plain_rank} (D absent) -> contextual {context_rank} (D first)")


# ---------------------------------------------------------------------------
# Step 4: end to end on the shared eval set; the ranking must be valid
# ---------------------------------------------------------------------------

def _assert_valid_ranking(records, valid_ids, label):
    for record in records:
        for variant in ("plain", "contextual"):
            ids = record[variant]
            assert set(ids) <= valid_ids, (
                f"{label}: query {record['qid']} returned a document from no corpus in "
                f"its {variant} ranking: {ids}")
            assert len(set(ids)) == len(ids), (
                f"{label}: query {record['qid']} repeated a document in its {variant} "
                f"ranking (the chunk ranking was not reduced to distinct docs): {ids}")


def check_end_to_end() -> None:
    import chunking

    # (a) Self-contained: the ranking must be valid, and the no-answer query stays empty.
    documents, query_sets = _self_contained()
    result = chunking.evaluate(documents, query_sets, k=5, size=60, overlap=10)
    valid = {document["doc_id"] for document in documents}
    assert result["n"] == 2, f"evaluate scored {result['n']} queries, expected 2"
    _assert_valid_ranking(result["records"], valid, "self-contained")
    for variant in ("plain", "contextual"):
        assert "overall" in result[variant], f"missing overall metrics for {variant}"
        for family in ("lexical", "no_answer"):
            assert family in result[variant], (
                f"missing {family} metrics for {variant}")
    assert result["abstained"] == {"plain": 1, "contextual": 1}, (
        f"the no-answer query must abstain for both variants, got {result['abstained']}")
    print("      self-contained: distinct doc ids, valid corpus, no-answer abstains")

    # (b) The shared evaluation set.
    try:
        corpus_mod, queries_mod, metrics = _load_eval_set()
    except FileNotFoundError:
        print("      shared eval set not available in this tree; checked the "
              "self-contained half only")
        return

    corpus = corpus_mod.generate_corpus(0)
    documents = corpus["documents"]
    query_sets = queries_mod.build_query_sets(corpus)
    queries = queries_mod.all_queries(query_sets)
    result = chunking.evaluate(documents, query_sets, k=5)
    assert result["n"] == len(queries), (
        f"evaluate scored {result['n']} queries, the set has {len(queries)}")
    valid_ids = {document["doc_id"] for document in documents}
    _assert_valid_ranking(result["records"], valid_ids, "eval set")

    ranked = {record["qid"]: record["plain"] for record in result["records"]}
    shared = metrics.evaluate(ranked, queries, k=5)
    assert abs(shared["overall"]["recall@k"]
               - result["plain"]["overall"]["recall@k"]) < 1e-9, (
        "the local plain recall does not match the shared metrics module, so the two "
        "reports disagree on the same rankings")

    print(f"      seed 0: {len(documents)} documents, {result['n']} queries, "
          f"k=5 (reported as measured; contextual is NOT assumed to win)")
    header = (f"      {'family':<11}{'n':>3}{'plain r@5':>11}{'ctx r@5':>9}"
              f"{'plain mrr':>11}{'ctx mrr':>9}{'plain ndcg':>12}{'ctx ndcg':>10}")
    print(header)
    for family in FAMILIES:
        plain = result["plain"].get(family)
        context = result["contextual"].get(family)
        if not plain:
            continue
        print(f"      {family:<11}{plain['n']:>3}"
              f"{plain['recall@k']:>11.3f}{context['recall@k']:>9.3f}"
              f"{plain['mrr']:>11.3f}{context['mrr']:>9.3f}"
              f"{plain['ndcg@k']:>12.3f}{context['ndcg@k']:>10.3f}")
    print(f"      {'overall':<11}{result['plain']['overall']['n']:>3}"
          f"{result['plain']['overall']['recall@k']:>11.3f}"
          f"{result['contextual']['overall']['recall@k']:>9.3f}"
          f"{result['plain']['overall']['mrr']:>11.3f}"
          f"{result['contextual']['overall']['mrr']:>9.3f}"
          f"{result['plain']['overall']['ndcg@k']:>12.3f}"
          f"{result['contextual']['overall']['ndcg@k']:>10.3f}")
    print(f"      abstentions: plain={result['abstained']['plain']} "
          f"contextual={result['abstained']['contextual']} "
          "(most corpus documents are a single chunk, so the prefix often adds nothing "
          "and the columns tie — the same caveat as the demo)")


# ---------------------------------------------------------------------------
# Step 5: the limit cases — a boundary and a short body
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    import chunking

    # (a) A fact straddling a chunk boundary: no overlap puts "budget" and "ledger" in
    # different chunks, so the document with both in one passage wins; overlap repairs it.
    documents = _boundary_corpus()
    for contextual in (False, True):
        narrow = chunking.build_index(documents, contextual=contextual, size=40, overlap=0)
        narrow_rank = chunking.retrieve("budget ledger", 5, narrow)
        assert narrow_rank and narrow_rank[0] != "I", (
            f"with no overlap the two query terms sit in different I chunks, so I must "
            f"not rank first ({'contextual' if contextual else 'plain'}); got "
            f"{narrow_rank}")
        wide = chunking.build_index(documents, contextual=contextual, size=40, overlap=40)
        wide_rank = chunking.retrieve("budget ledger", 5, wide)
        assert wide_rank and wide_rank[0] == "I", (
            f"with a wide overlap I gains a chunk carrying both terms, so I must rank "
            f"first ({'contextual' if contextual else 'plain'}); got {wide_rank}")
    print("      boundary: overlap=0 -> A first (I's terms split); overlap=40 -> I first")

    # (b) A short body must not be fragmented into tiny chunks.
    document = {"doc_id": "S", "title": "tiny", "body": "one very short body."}
    chunks = chunking.chunk_document(document, size=1000, overlap=200)
    assert len(chunks) == 1, (
        f"a body shorter than size must stay one chunk, got {len(chunks)}")
    assert chunks[0].text == document["body"], (
        "the single chunk must be the body, not a fragment")
    assert len(chunking.chunk_document(document)) == 1, (
        "a short body must stay one chunk at the default size too")
    print("      short body: 1 chunk, not fragmented")


# ---------------------------------------------------------------------------
# Step 6: abstention — no chunk, no document, for both variants
# ---------------------------------------------------------------------------

def check_abstention() -> None:
    import chunking

    documents = _disambiguation_corpus()
    for contextual in (False, True):
        index = chunking.build_index(documents, contextual=contextual)
        for query in ("zzzq nonexistent topic", "qqqq wwww vvvv"):
            ranked = chunking.retrieve(query, 5, index)
            assert ranked == [], (
                f"the no-answer query {query!r} must return no documents "
                f"({'contextual' if contextual else 'plain'}), got {ranked}")

    # Through ``evaluate`` too: the no-answer family stays empty for both variants.
    docs, query_sets = _self_contained()
    result = chunking.evaluate(docs, query_sets, k=5, size=60, overlap=10)
    empty = [record for record in result["records"] if record["family"] == "no_answer"]
    assert empty, "the self-contained set must contain a no-answer query"
    for record in empty:
        assert record["plain"] == [] and record["contextual"] == [], (
            f"no-answer query {record['qid']} must stay empty through evaluate, got "
            f"plain={record['plain']} contextual={record['contextual']}")
    print("      no-answer queries return no chunks and no documents for both variants")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("chunking.py", "chunking keeps the last partial chunk and its offsets cover the body", check_chunking),
    ("chunking.py", "the contextual prefix is title + section path + chunk text, in order", check_context),
    ("chunking.py", "the section label lets contextual chunking find a bare passage", check_retrieval),
    ("chunking.py", "end to end on the shared eval set; the ranking is a valid doc set", check_end_to_end),
    ("chunking.py", "the limit cases: a chunk boundary, and a short body", check_limit_cases),
    ("chunking.py", "abstention holds for both plain and contextual chunks", check_abstention),
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
    print(f"\n{BOLD}RAG from scratch, project 4 — contextual chunking (offline){RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
            if detail:
                print(f"{detail}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — contextual chunking is built.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

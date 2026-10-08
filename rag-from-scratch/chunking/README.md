# RAG project 4 — contextual chunking

Chunking and *contextual retrieval*: split a document into passages, then prepend the
document's title and section path before indexing so a passage that would otherwise be a
bare fragment ("revenue grew twelve percent") still retrieves for a query that named the
report. The deterministic title-and-section variant is the baseline the later LLM-written
context has to beat (see the root `rag-from-scratch/README.md`, project 4).

The stage sits at the chunk level: it reuses the shared [evaluation set](../eval-set/) for
documents and judgments (which are at the **document** level) and the sibling lexical stage
[`../bm25`](../bm25/) over the chunk texts, with a self-contained Okapi BM25 fallback.

This is a graded module in the repo's `graded-module` format. Fill in the template
`chunking.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/chunking
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/chunking.py   # the demo: plain vs contextual chunks on seed 0
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network).
`check.py` adds `../eval-set/solutions` to `sys.path` lazily, in step 4 only.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | chunking.py | `split_sentences` tiles the body; `chunk_document` keeps the last partial chunk, covers the body and is deterministic |
| 2 | chunking.py | `section_path` reads the metadata; `contextualise` is title + section path + chunk text, in order |
| 3 | chunking.py | a query term carried only by the section label ranks the intended document first with context, and away without it |
| 4 | chunking.py | end to end on the eval set (seed 0): plain vs contextual recall@k/MRR/nDCG@k per family plus abstention; the contextual ranking is a valid distinct document set |
| 5 | chunking.py | limit cases: a fact straddling a chunk boundary (repaired by overlap); a short body stays one chunk |
| 6 | chunking.py | a no-answer query returns no chunks and no documents for both variants |

## Design decisions

Summarised; the full rationale is in the `solutions/chunking.py` docstring.

- **Deterministic punctuation sentence splitting.** A sentence ends after a run of
  `.`/`!`/`?` followed by whitespace or end-of-text. Spans tile the body, so chunk offsets
  leave no gaps. Cost: `Dr.`, `etc.`, `e.g.`, `U.S.`, `3.14` end a sentence early — the
  split is a little finer, never lossy.
- **Sentence-aligned, overlapping chunks; the last partial chunk is always kept.** Carry
  the last sentence(s) that fit in `overlap` into the next chunk; emit the trailing
  leftover however small. Dropping the tail is the classic chunker bug and step 1 mutates
  it. Cost: a fact split across a boundary is repaired by overlap, not by splitting a
  sentence (step 5 constructs it).
- **`section_path` is a deterministic stand-in for the heading path.** The corpus has
  `department` and `topics`, not a heading tree, so the label is
  `"<department>: <first topic>"`, the same kind of short discriminative context. Cost: a
  coarse label that can be wrong when the first topic is not the section.
- **Contextual retrieval is the title + section path prefix; plain chunking is the bare
  passage.** The two are indexed and scored side by side.
- **The comparison is reported as measured, never asserted to favour the fix.** On this
  synthetic corpus most documents are short enough to be one chunk (and the body already
  repeats the title), so plain and contextual tie or trade small amounts. A test that
  forced contextual to win would measure the corpus, not the method.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/chunking rag-from-scratch/chunking/_build/mutations.py`
— every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | `chunk_document` drops the last partial chunk | the last chunk's `end` must equal `len(body)` |
| 3 | `contextualise` omits the title/section prefix | the intended document's label-only term disappears |
| 3 | `section_path` returns a constant label | no chunk carries the discriminative label |
| 4 | `retrieve` does not reduce the chunk ranking to distinct docs | a document answered by two chunks is listed twice |
| 4 | `retrieve` returns a document outside the corpus | the ranking must be a subset of the corpus |
| 6 | the no-match case returns the whole index | a no-answer query must stay empty |

## Questions to answer (no answers here)

1. Step 4's honest result is that contextual and plain chunks **tie** on this corpus. Name
   the corpus property that hides the benefit and describe a document set where it would
   not be hidden.
2. Sentence splitting is by punctuation only, so `Dr.` and `3.14` end a sentence. Which
   chunks get *worse* because of that, and which query would expose it?
3. `overlap` is a character budget, not a sentence count. Construct a body where the
   overlap fits one sentence but the answer needs two, and say whether more overlap or a
   different unit is the right fix.
4. The section label is `department: first_topic`. Give a corpus where the first topic is
   the wrong breadcrumb and the prefix therefore *hurts* recall.
5. The LLM-written context variant (root README, project 4) costs one model call per chunk
   at indexing time. Against this deterministic baseline, what is the smallest measurable
   gain that would justify it?

## Limits

- The corpus is synthetic and repetitive and its document bodies already repeat the title,
  so the contextual prefix rarely adds recall here; the comparison is honest but weak.
- No LLM-written context (deferred): `contextualise` is the deterministic title + section
  path only.
- Sentence splitting ignores abbreviations and decimals; sentence "alignment" is therefore
  approximate.
- Chunking is by characters with no field weights and no positional information; the
  metadata filters of the lexical stage are not applied at the chunk level (chunks carry no
  region/date).
- Metadata judgments stay at the **document** level; a chunk is only ever credited through
  its document, so chunk-level ranking quality (which chunk of a relevant document is on
  top) is not measured here.

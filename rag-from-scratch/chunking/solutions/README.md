# Solutions — RAG project 4 (contextual chunking)

The complete implementation and the measurement it produces. Read
[`chunking.py`](chunking.py); its docstring names each design decision and the cost of the
choice, and `check.py` in the parent directory grades the template against the same
behaviour.

## What it builds

- `Chunk(chunk_id, doc_id, text, start, end)` — one sentence-aligned passage, with character
  offsets into the body so `doc["body"][start:end]` is the chunk.
- `split_sentences(text)` — the deterministic punctuation rule; returns `(start, end)` spans
  that tile the body. Documents the abbreviations it deliberately does not handle.
- `chunk_document(doc, size, overlap)` — packs whole sentences up to `size`, carries the
  last sentence(s) that fit in `overlap` into the next chunk, and always emits the last
  partial chunk. A body shorter than `size` is exactly one chunk.
- `section_path(doc)` — `"<department>: <first topic>"`, the deterministic stand-in for the
  document's real heading path.
- `contextualise(chunk, doc)` — the chunk text prefixed with the title and the section path.
- `build_index(documents, contextual, size, overlap)` — a chunk-level index (sibling
  `../bm25` over the chunk texts, local Okapi BM25 fallback) mapping each chunk to its
  `doc_id`.
- `retrieve(query, k, chunk_index)` — the top-`k` chunks reduced to the distinct `doc_id`s
  in rank order; a document answered by several chunks appears once, at its best rank.
- `evaluate(documents, query_sets, k, size, overlap)` — doc-level recall@k, MRR and nDCG@k
  for plain vs contextual chunks, per family and overall, plus the abstention counts and the
  per-query records.
- `load_eval_set(seed=0)` — locates `../eval-set/solutions` and imports its `corpus`,
  `queries` and `metrics`.

## Expected output

`python3 solutions/chunking.py` (from `rag-from-scratch/chunking/`, seed 0):

```
corpus: 66 documents -> 75 plain chunks (size=240, overlap=60)
plain (no prefix):
  plain chunks:
  lexical     n= 6 recall@5=1.000 mrr=0.889 ndcg=0.917 abstained=0
  semantic    n= 5 recall@5=0.950 mrr=0.867 ndcg=0.903 abstained=0
  filtered    n= 4 recall@5=1.000 mrr=1.000 ndcg=1.000 abstained=0
  multi_hop   n= 3 recall@5=0.282 mrr=1.000 ndcg=0.900 abstained=0
  no_answer   n= 6 recall@5=0.000 mrr=0.000 ndcg=0.000 abstained=1
  overall     n=24 recall@5=0.650 mrr=0.694 ndcg=0.696 abstained=1
contextual (title + section path prefix):
  contextual chunks:
  lexical     n= 6 recall@5=1.000 mrr=0.917 ndcg=0.938 abstained=0
  semantic    n= 5 recall@5=0.900 mrr=0.867 ndcg=0.873 abstained=0
  filtered    n= 4 recall@5=1.000 mrr=1.000 ndcg=1.000 abstained=0
  multi_hop   n= 3 recall@5=0.282 mrr=1.000 ndcg=0.900 abstained=0
  no_answer   n= 6 recall@5=0.000 mrr=0.000 ndcg=0.000 abstained=1
  overall     n=24 recall@5=0.639 mrr=0.701 ndcg=0.696 abstained=1
abstentions: plain=1 contextual=1 (n=24)
honest note: on this synthetic corpus most documents fit in one chunk, so the prefix often adds nothing and the two columns tie; the fix earns its keep only where a bare passage loses the title/section words.

limit case - a fact straddling a chunk boundary, repaired by more overlap
  overlap= 0: chunks of I = ['quarterly review. budget planning. ', 'ledger reconciliation.'] -> ranking ['A', 'I']
  overlap=40: chunks of I = ['quarterly review. budget planning. ', 'budget planning. ledger reconciliation.'] -> ranking ['I', 'A']
  with overlap=40 the combined chunk matches both query terms, so the intended document I is first: ['I', 'A']
```

The numbers are reported as measured. Plain and contextual **tie** on this corpus (recall
0.650 vs 0.639, MRR 0.694 vs 0.701) because the corpus's short document bodies already
repeat the title and most documents are a single chunk, so the prefix adds little. The
value of the module is the chunker (the last partial chunk, the tiling offsets, the
overlap), the boundary limit case, and the honest "it does not help here" measurement, not a
recall gain.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. Against the template
it reports six TODOs and no failures or errors. The mutation suite
(`_build/mutations.py`) plants six bugs and each is CAUGHT by the named step: step 1 (the
last partial chunk dropped), step 3 (the context prefix omitted, and a constant section
label), step 4 (no distinct documents, and a document outside the corpus), step 6
(abstention returning the whole index). Run it with:

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/chunking rag-from-scratch/chunking/_build/mutations.py
```

## Notes on the eval set and the sibling imports

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. `solutions/chunking.py` and `check.py` therefore import its `corpus`, `queries`
and `metrics` from `../eval-set/solutions` (adding that directory to `sys.path` lazily).
`evaluate` accepts an explicit document list, so the self-contained half of step 4 and every
hand-built step run in a bare temporary directory without the eval set. Chunk retrieval
imports `../bm25/solutions` over the chunk entries and falls back to a self-contained Okapi
BM25 when the sibling is absent, so the mutation harness (which copies only the solutions
and `check.py`) still runs. nDCG uses the exponential gain `2**grade - 1` with the `log2`
discount, exactly the shared `metrics.ndcg_at_k`, and step 4 cross-checks the plain recall
against that module.

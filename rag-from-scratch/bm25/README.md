# RAG project 1, stage 1 — BM25 and the evaluation wiring

The first stage of [hybrid search]: an Okapi BM25 retriever wired to the shared
[evaluation set](../eval-set/), so the next stages (LSA, HNSW, fusion) have a scored
lexical floor and a harness to compare against. BM25 is the "sparse" half of hybrid
search; the dense half (LSA / embeddings) and the fusion layer are later passes.

This is a graded module in the repo's `graded-module` format. Fill in the template
`bm25.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/bm25
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/bm25.py   # the demo: BM25 vs the lexical baseline on seed 0
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network).
`check.py` adds `../eval-set/solutions` to `sys.path` lazily, in step 5 only.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | bm25.py | `tokenize` is lowercase alphanumeric; the index is term -> {doc_id: tf} with lengths |
| 2 | bm25.py | `idf` is monotone decreasing in df and the smoothed BM25 formula; `bm25_score` matches a hand-computed value |
| 3 | bm25.py | term frequency saturates (`k1`) and a shorter document scores higher for the same tf (`b`) |
| 4 | bm25.py | `retrieve` returns a ranked list, relevant document first, honours k and requires no eval set |
| 5 | bm25.py | end to end on the eval set (seed 0): BM25's lexical recall@10 is at least the lexical baseline's, and the no-answer family is either abstained on or reported honestly |
| 6 | bm25.py | limit cases: a term in no document abstains; a filter matching no document returns empty |

## Design decisions

Summarised; the full rationale is in the `solutions/bm25.py` docstring.

- **Lowercase alphanumeric tokenisation, no stopwords, no stemming.** Simple and
  deterministic. The hyphenated policy code splits into tokens, which is fine for the
  lexical family. Cost: BM25 answers 5 of the 6 no-answer queries because a generic
  token matches (function words like "a"/"for"/"on", and "policy" on one); the eval
  set's baseline strips stopwords and abstains on all 6.
  Step 5 accepts this as long as the abstention metrics report it, rather than hiding it.
- **Term-keyed postings map + average length.** `{term: {doc_id: tf}}` plus `doc_lengths`
  and `avg_length`. This is the structure the later inverted index builds on.
- **Smoothed BM25 idf**, `log(1 + (N - df + 0.5)/(df + 0.5))`, never `log(N/df)`, so a
  term in every document stays small and positive.
- **`k1 = 1.5`, `b = 0.75`,** the standard defaults; no tuning on 24 queries.
- **Pre-retrieval metadata filtering**, matching the eval set's baseline, so a selective
  filter still returns the full k when enough documents pass.
- **Empty result means abstain**, the weakest defensible rule; a calibrated threshold is
  project 7.
- **Ties break by doc_id ascending** for reproducible evaluation.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/bm25 rag-from-scratch/bm25/_build/mutations.py`
— every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | the inverted index keys by document instead of term | term-keyed posting-list assertions |
| 2 | idf uses `log(N/df)` instead of the smoothed form | hand-computed idf and score |
| 3 | `bm25_score` drops the length normalisation (`b`) | short-vs-long document comparison |
| 4 | `retrieve` returns documents in corpus order (no sort) | relevant document is last in corpus order |
| 6 | the no-match path returns the whole corpus | no-matching-term abstention case |

## Questions to answer (no answers here)

1. BM25 matches the token-overlap baseline exactly on this corpus (lexical 1.000, MRR
   0.917; semantic 1.000, MRR 0.900). The synthetic vocabulary is deliberately clean.
   Which failure mode of real text makes a saturation-and-length model pull away from
   counting shared tokens, and can this eval set see it?
2. BM25 answers 5 of 6 no-answer queries on generic function words ("a"/"for"/"on",
   and "policy" on one). Is the mistake in BM25 (no stopword list) or in the
   abstention rule (empty result), and what would a learned gate change?
3. `idf` uses document frequency, not collection frequency. Construct a case where the
   two orderings disagree and say which a retriever should prefer.
4. Step 6 requires a filtered retriever to return empty when the only matching document
   is filtered out. What does that forbid about post-filtering, and how does a very
   selective filter (say 0.1% of the corpus) break it?
5. `k1` and `b` are fixed at the defaults. With 24 queries, how would you tune them
   without turning the eval set into a training set?

## Limits

- Title and body are concatenated into one field; field weights are not modelled.
- No stemming, no stopwords, no positional or phrase information.
- No score normalisation or calibration, so BM25 cannot abstain on a low-but-nonzero
  score.
- The eval set is synthetic and repetitive; the absolute scores do not transfer to real
  corpora (only the comparison between stages does). See the eval set's own limits.
- `k1` and `b` are not tuned; the point of this stage is a correct, measured floor.

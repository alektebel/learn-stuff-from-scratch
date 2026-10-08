# RAG project 1, stage 2 — LSA (latent semantic analysis)

The dense half of [hybrid search]: a latent semantic analysis retriever wired to the same
shared [evaluation set](../eval-set/) as [BM25](../bm25/), so the two stages are measured
on identical documents and queries. LSA builds a tf-idf term-document matrix, truncates
its singular value decomposition, and retrieves by cosine similarity in the latent
"concept" space — so a query can reach a document that shares no literal token with it.
The fusion layer, HNSW and trained embeddings are later passes.

This is a graded module in the repo's `graded-module` format. Fill in the template
`lsa.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/lsa
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/lsa.py    # the demo: LSA vs lexical baseline vs BM25 on seed 0
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network). The
solver is a hand-written cyclic Jacobi eigen-decomposition; the tokeniser is the same
`re.findall(r"[a-z0-9]+", text.lower())` BM25 uses. `check.py` adds
`../eval-set/solutions` to `sys.path` lazily, in step 5 only.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | lsa.py | `tokenize` matches BM25; `build_term_document` returns the sorted vocabulary and the N x D count matrix |
| 2 | lsa.py | `tf_idf` matches hand-computed values on 3 documents, uses a document-frequency idf and is row-normalised |
| 3 | lsa.py | `jacobi`/`eig_sorted`; the truncated SVD agrees with **both** Gram routes, is centred, keeps exactly k components, and `‖A − A_k‖_F²` equals the discarded singular values squared (to 1e-9) |
| 4 | lsa.py | a controlled semantic case: a query sharing no token with the relevant document is retrieved by LSA and not by raw term overlap |
| 5 | lsa.py | end to end on the eval set (seed 0): the per-family table is reported honestly next to the baseline and BM25, whichever way it goes |
| 6 | lsa.py | limits: the D > N case (more terms than documents) uses the N x N document-space Gram matrix; no-token and no-match queries abstain |

## Design decisions

Summarised; the full rationale is in the `solutions/lsa.py` docstring.

- **The tokeniser is identical to BM25's.** The two stages must disagree only about
  weighting, never about what a document is; otherwise the comparison is confounded.
  Cost: no stemming, no stopwords, so LSA answers some no-answer queries on a generic
  token, exactly as BM25 does (reported in the metrics, not hidden).
- **tf-idf uses the smoothed BM25 idf and L2-normalises every row.** Cosine similarity
  becomes a dot product, and the two stages agree on how rare a term is. Cost: the idf
  must be stored on the model separately, since it cannot be recovered from the
  normalised rows.
- **The term-document matrix is centred before the SVD.** Removing the per-term mean
  stops the leading directions describing the common vocabulary; the SVD then models
  contrast between documents. Cost: the centred matrix is dense, and the centring must
  be applied to the query too, so a no-token query is special-cased to zeros.
- **The SVD is taken from the smaller Gram matrix** (N x N when there are at most N
  documents, else D x D). This is what makes the D > N case tractable: the D x D
  term-space matrix is never built when D is large. Cost: writing and testing both
  routes; the model records `gram_size` so the route is auditable.
- **A query is folded in as a pseudo-document:** same idf, same normalisation, same
  centring, projected onto V_k and re-normalised. Cost: folding-in is not the same as
  recomputing the SVD with the query included, so a query that would move the axes is
  approximated.
- **The rank is a coarse default, `max(1, min(100, N // 4))`.** At full rank the
  embedding is the tf-idf matrix again and nothing is smoothed; a quarter actually
  truncates on these small corpora. A scree plot / explained-variance threshold is the
  principled alternative and is left as an exercise.
- **Pre-retrieval metadata filtering, empty result means abstain, ties break by
  doc_id ascending.** Identical candidate handling to BM25, so a difference in the
  table is a difference in ranking, not in filtering. Cost: the zero-cosine threshold
  is not calibrated (project 7), and LSA answers most no-answer queries.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py rag-from-scratch/lsa rag-from-scratch/lsa/_build/mutations.py`
— every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 2 | `tf_idf` forgets the idf factor | hand-computed tf-idf values |
| 3 | `eig_sorted` returns jacobi's eigenpairs unsorted | largest-first singular values + reconstruction identity |
| 3 | `fit_lsa` uses more components than requested | exactly-k components assertion |
| 3 | `fit_lsa` drops the centring | stored mean and the two Gram spectra |
| 4 | `embed_query` forgets to normalise | unit-norm contract (cosine vs dot product) |
| 6 | the no-match path returns the whole corpus | no-token abstention case |
| 6 | D > N uses the large term-space Gram matrix | `gram_size` must be the N x N document-space matrix |

## Questions to answer (no answers here)

1. At rank 16 LSA beats the baseline on semantic MRR (1.000 vs 0.900) but loses on
   lexical MRR (0.549 vs 0.917). Which part of the pipeline is smoothing the exact
   policy code away, and would field weights (title vs body) recover it?
2. The centre-then-SVD step makes a no-token query special. What would happen to
   abstention if the model did not centre the query the same way as the documents?
3. `‖A − A_k‖_F² = Σ_{i>k} s_i²` is exact for the full SVD. What does it not tell you
   about retrieval quality, and why is explained variance a poor rank selector here?
4. The D > N route decomposes N x N; the D < N route decomposes D x D. Show (or refute)
   that the two give the same singular values, and say why the smaller one exists.
5. BM25 and cosine live on different scales. What does project 1's fusion layer have to
   do besides adding the scores, and how would you know fusion beat both stages?
6. LSA is a linear, global method. Give a query in the eval set's families it cannot
   represent, and the document property that leaks into the embedding anyway.

## Limits

- Bag of words: no word order, no phrases, no negation, no stemming.
- One global linear subspace; polysemy and synonymy share the same axes.
- The absolute numbers do not transfer to real corpora (the corpus is synthetic and
  repetitive); only the comparison between stages does.
- No score calibration, so the zero-cosine abstention rule is weak: LSA answers 5 of 6
  no-answer queries on generic tokens.
- The rank is a heuristic, not tuned or validated; no scree plot or cross-validation.
- Title and body are concatenated into one field; field weights are not modelled.

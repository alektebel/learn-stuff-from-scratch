# solutions — LSA (RAG project 1, dense stage)

The complete implementation. `lsa.py` is pure standard library (`math`, `re`,
`collections`): no numpy, no pip, no network. It writes its own cyclic Jacobi symmetric
eigen-solver and reuses BM25's tokeniser so the two stages are measured on the same
documents.

Run the demo from the module directory:

```
cd rag-from-scratch/lsa
python3 solutions/lsa.py
```

## Expected demo output (seed 0)

```
seed 0, 66 documents, 24 queries
family        LSA r@10  LSA MRR  base r@10  base MRR  BM25 r@10  BM25 MRR
lexical          1.000    0.549      1.000     0.917      1.000     0.917
semantic         1.000    1.000      1.000     0.900      1.000     0.900
filtered         1.000    1.000      1.000     1.000      1.000     1.000
multi_hop        0.433    0.833      0.542     1.000      0.542     1.000
no_answer        0.000    0.000      0.000     0.000      0.000     0.000
overall          0.679    0.616      0.693     0.708      0.693     0.708
abstention (tp/fp/fn)  LSA: 1/0/5  baseline: 6/0/0
```

The extra BM25 columns come from the sibling `../bm25/solutions/bm25.py` when it is
present; the demo runs without it too.

## How to read these numbers honestly

- **The result is mixed, and it is reported as measured.** LSA wins semantic MRR
  (1.000 vs the baseline's 0.900) — the point of the dense stage — but loses lexical MRR
  (0.549 vs 0.917) and multi-hop recall (0.433 vs 0.542), and the overall figures are
  below the lexical baseline (0.679 / 0.616 vs 0.693 / 0.708). The checks do **not**
  hard-code a win; step 5 only asserts the numbers are reproducible.
- Why lexical MRR drops: on the synthetic corpus the exact policy code is the best
  signal, and truncating the SVD to rank 16 smooths that sparse signal into a dense
  neighbourhood, so the current version is no longer always ranked first (the code also
  matches its superseded predecessor, which is irrelevant).
- Why the semantic family looks easy: the eval-set paraphrases deliberately keep one
  topic word, so the lexical baseline already scores 1.000 recall. The constructed case
  in check step 4 (a query sharing *no* token with the relevant document) is where LSA
  beats term overlap, not this family.
- `no_answer`: LSA answers 5 of 6 because a generic token ("policy", "what", ...) is in
  the vocabulary and has a small positive cosine. Only the query with no in-vocabulary
  token abstains. The metrics report this (abstention recall 1/6); it is not hidden.

`check.py` on the solutions is the executable version of this page:

```
cd rag-from-scratch/lsa
cp solutions/lsa.py lsa.py        # or work in a temporary copy beside ../eval-set
python3 check.py --all
```

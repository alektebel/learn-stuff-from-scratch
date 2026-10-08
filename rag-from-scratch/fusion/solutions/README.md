# solutions — FUSION (RAG project 1, hybrid stage)

The complete implementation. `fusion.py` is pure standard library (`math`, `pathlib`,
`sys`, `collections`): no numpy, no pip, no network. It imports the two sibling stages
from `../bm25/solutions/bm25.py` and `../lsa/solutions/lsa.py`, and the shared eval set
from `../eval-set/solutions/`, so all four methods are measured on the same documents
and queries.

Run the demo from the module directory:

```
cd rag-from-scratch/fusion
python3 solutions/fusion.py
```

## Expected demo output (seed 0)

```
seed 0, 66 documents, 24 queries
family        BM25 r@10  LSA r@10  RRF r@10  WT r@10
lexical           1.000     1.000     1.000    1.000
semantic          1.000     1.000     1.000    1.000
filtered          1.000     1.000     1.000    1.000
multi_hop         0.542     0.433     0.542    0.542
no_answer         0.000     0.000     0.000    0.000
overall           0.693     0.679     0.693    0.693

paired per-query, RRF vs each single stage (metric recall@10):
  family           vs BM25 W/L/T    vs LSA W/L/T
  lexical                  0/0/6           0/0/6
  semantic                 0/0/5           0/0/5
  filtered                 0/0/4           0/0/4
  multi_hop                0/0/3           3/0/0
  no_answer                0/0/6           0/0/6
  overall                 0/0/24          3/0/21
  W/L/T = fusion better / worse / equal on that query; ties are queries where both retrieve the same documents.
  the numbers are reported as measured: fusion is not assumed to win.
```

## How to read these numbers honestly

- **On this eval set fusion does not beat BM25 overall, and that is reported as
  measured.** RRF and weighted fusion tie BM25 on every query (0/0/24) and beat LSA on
  three multi-hop queries (3/0/21), giving the same overall recall (0.693). The checks do
  **not** hard-code a fusion win; step 4 only asserts the numbers are reproducible and the
  paired counts cover every query.
- Why the set is saturated: its lexical, semantic and filtered families are all at 1.000
  for **both** single stages. The semantic paraphrases deliberately keep a topic word (so
  BM25 already scores 1.000), and the corpus is small (66 documents). There is simply no
  headroom left for fusion to show a gain on those families. The only signal is
  `multi_hop`, where LSA loses three queries that BM25 answers and fusion recovers them.
- Why weighted fusion equals RRF here: min-max maps each stage's best candidate to 1.0,
  and the two stages mostly rank the same documents first, so the two methods coincide on
  this data. A corpus where the stages' top ranks disagree is where they would diverge.
- The point of hybrid search is shown where the single stages differ, not by a headline
  number: check step 3 constructs a dense-only document (a synonym) and a lexical-only
  document (a rare literal) and requires fusion to surface each in the top two.
- Weights do not transfer: check step 5 tunes the BM25/LSA weight on a lexical family,
  gets `[1.0, 0.0]`, and shows that applying it to a semantic family drops recall@1 from
  1.000 to 0.000.

`check.py` on the solutions is the executable version of this page:

```
cd rag-from-scratch/fusion
cp solutions/fusion.py fusion.py        # or work in a temporary copy beside ../eval-set
python3 check.py --all
```

`check.py` adds `../eval-set/solutions`, `../bm25/solutions` and `../lsa/solutions` to
`sys.path` lazily, in the steps that need them (1–3 and 6 are hand-built and need no
siblings).

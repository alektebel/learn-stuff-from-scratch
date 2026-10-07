# Solutions — RAG step 0, the evaluation set

Complete implementations of the four templates. Each file opens with the design
decisions it makes; this is the expected output of the demos and the checks.

```
python3 check.py --all          # from a copy holding these files + check.py
```

## Expected demo output

`python3 corpus.py`:

```
seed 0: 66 documents (6 superseded, 60 current)
entities: 29, relations: 30, tables: ['headcount_by_department', 'revenue_by_region', 'vendors']
determinism: same seed equal = True, different seed changes = True
```

`python3 queries.py`:

```
query families: {lexical: 6, semantic: 5, filtered: 4, multi_hop: 3, no_answer: 6}
total queries: 24, all have unique qids: True
no-answer queries with non-empty relevance: []
```

`python3 metrics.py`:

```
ranked=['b', 'a', 'c'] relevance={'a': 3.0, 'b': 2.0, 'c': 1.0}
recall@2=0.6667 mrr=1.0000 ndcg@3=0.8428
paired diff a-b = (0.5, 0.125, 0.875)
```

`python3 baseline.py`:

```
queries: 24, answered by the baseline: 18, abstained: 6
```

Baseline scores (`evaluate`, seed 0, k=10):

```
overall: recall@10=0.6927 mrr=0.7083 ndcg@10=0.7132
  lexical    recall@10=1.000 MRR=0.917 nDCG@10=0.938
  semantic   recall@10=1.000 MRR=0.900 nDCG@10=0.941
  filtered   recall@10=1.000 MRR=1.000 nDCG@10=1.000
  multi_hop  recall@10=0.542 MRR=1.000 nDCG@10=0.927
  no_answer  recall@10=0.000 MRR=0.000 nDCG@10=0.000
abstention: tp=6 fp=0 fn=0 tn=18 precision=1.0 recall=1.0
```

`check.py --all`:

```
13/13 passing
All checks pass — the evaluation set is built.
```

## Files

- `corpus.py` — `generate_corpus(seed)`; deterministic seeded generator.
- `queries.py` — `build_query_sets(corpus)`, `all_queries(query_sets)`, `_current`,
  `_by`, and the paraphrase map.
- `metrics.py` — the five retrieval/abstention/latency metrics, `evaluate`, and the
  three paired-comparison helpers.
- `baseline.py` — `LexicalBaseline` and its `tokenize`/`STOPWORDS`/filter helpers.

## Why the numbers are what they are

- Lexical recall@10 is exactly 1.0 because an exact policy code appears in the current
  and the superseded document; the current one is always in the top 10. MRR is 0.917
  rather than 1.0 because on one query the superseded version outranks the current one
  (both carry the same code) — the phenomenon the version chains exist to expose.
- `multi_hop` recall@10 is 0.542: the baseline finds the manager's documents by name but
  cannot traverse the relation to the reporting author's documents.
- `no_answer` is 0.0 on every retrieval metric because there is nothing to recall; the
  baseline abstains on all six, which is why abstention precision and recall are both
  1.0. A system that abstained on everything would score recall 1.0 and precision ~0.

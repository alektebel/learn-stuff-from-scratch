# Solutions — RAG project 5 (SQL + vector)

The complete implementation and the measurement it produces. Read
[`router.py`](router.py); its docstring names each design decision and the cost of the
choice, and `check.py` in the parent directory grades the template against the same
behaviour.

## What it builds

- `load_tables(corpus, path=":memory:")` — creates one SQLite table per
  `corpus["tables"]` entry, in sorted name order, with no declared affinity, inserts the
  rows, commits and returns the connection. Deterministic and self-contained (a corpus
  dict needs no eval set).
- `classify(question)` — the deterministic router: `"structured"` on an
  aggregation/superlative signal, a list/risk phrase on a known table word, or a
  vendor-risk phrase; `"unstructured"` otherwise.
- `SUPPORTED_SHAPES` / `to_sql(question, conn)` — the seven templated forms
  (`count_rows`, `count_filter`, `total`, `average`, `group_max`, `group_min`,
  `list_filter`). Returns `(sql, params)` with every value bound; `None` for an unknown
  column/entity or an unsupported shape.
- `answer_structured(question, conn)` — runs the SQL; returns a scalar, a list of row
  tuples, or `None` to abstain (a genuine `COUNT` of 0 stays `0`).
- `route_and_answer(question, conn, documents, k)` — the tagged router result:
  `{"route", "answer", "documents", "sql", "params"}`.
- `retrieve(question, k, documents)` — the lexical stage (sibling `../bm25`, with a local
  BM25 fallback).
- `evaluate(structured_questions, corpus, query_sets=None, k=5)` — the structured
  accuracy (answers checked against an independent pure-Python oracle), the routing
  counts, and the shared `metrics.evaluate` result over the questions routed to retrieval.

## Expected output

`python3 solutions/router.py` (from `rag-from-scratch/sql-vector/`, seed 0):

```
corpus: 66 documents, 3 tables (headcount_by_department, revenue_by_region, vendors)
router: 7 SQL shapes, deterministic keyword signals; no model, no network
structured accuracy: 1.000 (9/9)
  ok  [  structured] What is the total revenue in 2025?            got=8203000 expected=8203000
  ok  [  structured] What is the average headcount in 2025?        got=105.83333333333333 expected=105.83333333333333
  ok  [  structured] How many vendors are there?                   got=4 expected=4
  ok  [  structured] How many vendors have high risk?              got=2 expected=2
  ok  [  structured] List vendors with risk high                   got=[('Acme Cloud',), ('Globex Services',)] expected=[('Acme Cloud',), ('Globex Services',)]
  ok  [  structured] Which region has the most revenue in 2025?    got='APAC' expected='APAC'
  ok  [  structured] Which department has the least headcount?     got='Finance' expected='Finance'
  ok  [  structured] What is the total revenue by region in 2025?  got=[('AMER', 1569000), ('APAC', 2539000), ('EMEA', 2099000), ('GLOBAL', 1996000)] expected=[('AMER', 1569000), ('APAC', 2539000), ('EMEA', 2099000), ('GLOBAL', 1996000)]
  ok  [  structured] What is the total salary by region in 2025?   got=None expected=None

unstructured families routed to retrieval:
  lexical     n= 6 recall@5=1.000 mrr=0.917
  semantic    n= 5 recall@5=0.950 mrr=0.900
  filtered    n= 4 recall@5=1.000 mrr=1.000
  multi_hop   n= 3 recall@5=0.304 mrr=1.000
  no_answer   n= 6 recall@5=0.000 mrr=0.000
  overall     n=24 recall@5=0.653 mrr=0.708
routing: {'structured': 0, 'unstructured': 24}

limit case 1a - a structured question phrased without a signal:
  'How did EMEA do in 2025?' -> route=unstructured, answer=None (retrieval, so the SQL answer is unreachable)

limit case 1b - a prose question that happens to carry a signal:
  'Which document has the most detail about access control?' -> route=structured, answer=None (SQL, then abstains instead of retrieving)

limit case 2 - a question naming a column that does not exist:
  'What is the total salary by region in 2025?' -> route=structured, answer=None, abstains rather than guessing

limit case 3 - a hostile question carrying SQL is parameterised:
  'What is the total revenue in 2025; DROP TABLE vendors; --'
  -> sql='SELECT SUM("amount_usd") FROM "revenue_by_region" WHERE "year" = ?' params=(2025,) answer=8203000
  -> vendors table still has 4 rows; the statement was not executed
```

The numbers are reported as measured. The router happens to route all 24 unstructured and
all 9 structured questions correctly on this synthetic corpus; the honest statement is the
held-out **0.90 floor** stated in the parent README before the checker was run, not a
claim that the keyword router generalises. `multi_hop` is capped by k=5 against ~15
relevant documents, and `no_answer` recall is zero by construction. The SQL examples show
the mechanism: the statement is a fixed template and the question's only surviving
influence is a bound parameter.

## Expected checker output

`python3 check.py --all` against these solutions reports `6/6 passing`. Against the
template it reports six TODOs and no failures or errors. The mutation suite
(`_build/mutations.py`) plants six bugs and each is CAUGHT by the named step: step 1
(dropped table), step 2 (always-unstructured router), step 3 (ascending superlative and
`0`-instead-of-`None`), step 4 (everything to retrieval), step 5 (interpolated year).

## Notes on the eval-set and sibling imports

The eval set at `../eval-set` is itself a graded module, so its top-level files are
templates. Both `solutions/router.py` and `check.py` therefore import its `corpus`,
`queries` and `metrics` from `../eval-set/solutions` (adding that directory to `sys.path`
lazily). `load_tables` accepts an explicit corpus so the hand-built checks and the
mutation harness never need it: every mutated step runs on the toy corpus in a bare
temporary directory. The lexical stage imports `../bm25/solutions` and falls back to a
self-contained Okapi BM25 when the sibling is absent.

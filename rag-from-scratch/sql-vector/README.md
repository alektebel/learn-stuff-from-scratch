# RAG project 5 — SQL + vector

The [RAG plan](../README.md) row 5: **a router that sends structured questions to SQLite
and the rest to retrieval**. Half of a real question set is not prose — "which region had
the most revenue in 2025?", "how many high-risk vendors are there?" — and a document
retriever answers those badly. This stage builds a standard-library **router**, a
deterministic **text-to-SQL template** over the shared eval set's `tables`, and a tagged
`route_and_answer` that sends the structured half to SQLite and the rest to the lexical
stage (the sibling [`../bm25`](../bm25/) retriever). The text-to-SQL is fixed templates;
the LLM / classifier variant is explicitly deferred.

This is a graded module in the repo's `graded-module` format. Fill in the template
`router.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/sql-vector
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/router.py # the demo: measured router accuracy, retrieval recall, and the limit cases
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network; `sqlite3`
is stdlib). `check.py` adds `../eval-set/solutions` to `sys.path` in the end-to-end step
only; `router.py` reuses `../bm25/solutions` and carries a small in-module BM25 fallback so
the hand-built checks run in a tree without the sibling.

## The tables

The eval-set corpus carries, beside the documents, one `tables` dict per structured
domain. `load_tables` creates and populates a SQLite table for each:

| Table | Columns | Rows |
|---|---|---|
| `revenue_by_region` | `region, year, quarter, amount_usd` | every region × 2024/2025 × Q1–Q4 |
| `headcount_by_department` | `department, year, headcount` | one row per department, 2025 |
| `vendors` | `vendor_id, name, region, risk_level` | four fixed vendors |

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | router.py | every corpus table exists in SQLite with the corpus's columns, row count and cells, on a hand-built corpus and on seed 0 |
| 2 | router.py | the router classifies clear structured and unstructured questions, and its accuracy on a held-out list meets the **0.90 floor predicted below before the result was known** |
| 3 | router.py | each `SUPPORTED_SHAPES` form produces SQL whose result matches a hand-computed value, and an unknown column returns `None` |
| 4 | router.py | structured questions answer through the SQL route, unstructured ones go to retrieval; the shared recall@k is printed and the router is not assumed perfect |
| 5 | router.py | the limit cases: an ambiguous question misrouted each way, a question naming a missing column abstaining, and a hostile question carrying SQL being parameterised |
| 6 | router.py | an unsupported structured question returns `None`, and a no-answer unstructured query stays empty through the router |

## The predicted floor

Stated here **before** the checker was run, not tuned afterwards: on a held-out list of
ten questions the keyword router is expected to classify at least **90 %** correctly
(`ROUTER_FLOOR = 0.90` in `check.py`). The router is a brittle template — that is its
documented cost — so a floor below 1.0 is the honest prediction, not a perfect score.

## Design decisions

Summarised; the full rationale is in `solutions/router.py`.

- **A deterministic keyword router; the LLM variant is deferred.** Structured means an
  aggregation/superlative signal (`how many`, `total`, `average`, `most`, `least`…), or a
  list/risk phrase on a known table word, or a vendor-risk phrase. No model, no training
  data, no network. Cost: brittle — "How did EMEA do in 2025?" is routed to retrieval,
  and a prose question containing "most" is routed to SQL.
- **Text-to-SQL is a fixed set of shapes, never an interpolation.** `SUPPORTED_SHAPES`
  names `count_rows`, `count_filter`, `total`, `average`, `group_max`, `group_min` and
  `list_filter`; every value is bound as a `?` parameter. A hostile question such as
  `"total revenue in 2025; DROP TABLE vendors; --"` can only change the bound year. Cost:
  a question outside the shapes abstains.
- **An unknown column or entity abstains with `None`, it does not guess or fall back to
  retrieval.** This keeps the two stages measurable: the checker can see the router drop
  the ball. Cost: an end-to-end system would prefer a fallback; that is a documented
  future step.
- **No declared affinity in SQLite, so integers stay integers.** `SUM(amount_usd)` is
  integer arithmetic and two runs are identical. Cost: no schema typing beyond what the
  generator wrote.
- **The unstructured half is the sibling `../bm25`, with a self-contained fallback.**
  Reuse keeps the comparison to the other stages honest; the fallback lets the hand
  checks and the mutation harness run without the sibling.

## What the measurement actually says

Seed 0, 66 documents, 24 unstructured queries, 9 structured questions, k=5 (from
`python3 solutions/router.py`):

```
structured accuracy: 1.000 (9/9)

unstructured families routed to retrieval:
  lexical     n= 6 recall@5=1.000 mrr=0.917
  semantic    n= 5 recall@5=0.950 mrr=0.900
  filtered    n= 4 recall@5=1.000 mrr=1.000
  multi_hop   n= 3 recall@5=0.304 mrr=1.000
  no_answer   n= 6 recall@5=0.000 mrr=0.000
  overall     n=24 recall@5=0.653 mrr=0.708
routing: {'structured': 0, 'unstructured': 24}
```

On this corpus the router happens to classify all nine structured questions and all 24
unstructured ones correctly, so the two halves are clean. That is a property of the
synthetic eval set, not a claim the router generalises: the held-out floor (0.90) is the
honest statement. `multi_hop` recall is low because ~15 documents are relevant and k=5
caps it; `no_answer` recall is zero because relevance is empty by construction, not because
the queries abstain: the raw lexical stage returns documents for five of the six (only
`NON-04` abstains), so abstention recall is 1/6 at precision 1.0 — the same limit the
sibling `../bm25` reports rather than hides. The checker asserts the structured accuracy
floor, the routed abstention, and the limit cases, never that the router is perfect.

## Mutation table

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/sql-vector rag-from-scratch/sql-vector/_build/mutations.py
```

Every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 2 | the router always returns `unstructured` | the structured hand-built list must classify correctly |
| 3 | the superlative orders ascending (`MIN` for `MAX`) | the hand-computed top region must be `EMEA` |
| 5 | `to_sql` interpolates the question's year into the SQL string | the hostile question's SQL must not contain the year |
| 1 | `load_tables` drops the `vendors` table | the set of created tables must equal the corpus's |
| 3/6 | `answer_structured` returns `0` instead of `None` for an unsupported question | the unknown-column question must abstain |
| 4 | `route_and_answer` sends every question to retrieval | the self-contained structured route must answer through SQL |

## Questions to answer (no answers here)

1. The router routes a question about "vendor onboarding" to retrieval but "list vendors
   with risk high" to SQL. Is the keyword signal the right boundary, or should the
   decision depend on whether a shape can be templated at all?
2. A structured question misrouted to retrieval returns documents, not `None`. Should
   `route_and_answer` fall back to retrieval when `to_sql` abstains, and what would that do
   to the honesty of the per-route accuracy?
3. `"total revenue in 2025; DROP TABLE vendors; --"` is parameterised. Which shapes are
   *not* covered by the templates, and what is the risk of an LLM writing those SQL
   strings instead?
4. `load_tables` creates integers without affinity. What breaks first when a table mixes
   integers and floats, and where would the checker notice?
5. `revenue_by_region` and `headcount_by_department` have different dimensions and grains
   (region×year×quarter vs department×year). The templates treat them uniformly with
   `SUM`. Which question would that answer wrongly?
6. `evaluate` reports the structured accuracy and the retrieval recall separately. If the
   router sends a question to the wrong half, which number moves, and why is a single
   "accuracy" misleading?

## Limits

- The router is a keyword template with no learning and no schema awareness beyond the
  hard-coded tables; it does not generalise to a new table.
- `to_sql` supports seven shapes and no joins, no `GROUP BY` beyond the fixed dimension,
  no `ORDER BY` other than the superlative, and no `HAVING`.
- The retrieved half is exactly the sibling BM25 stage (with the in-module fallback); its
  limits are that project's limits.
- The eval-set corpus is synthetic and regular, so the measured router accuracy is not a
  transferable estimate; only the floor and the structural checks are.

# RAG project 2 — metadata-filtered RAG

The filter stage of the [RAG plan](../README.md): retrieval where the query carries
structured constraints — department, year, region, access level, author, `superseded` —
and the answer must be drawn only from documents that satisfy them. The metadata lives
in a standard-library SQLite store with a secondary index per filterable column, and the
project contrasts three execution strategies on the same [shared evaluation
set](../eval-set/) the other stages use.

This is a graded module in the repo's `graded-module` format. Fill in the template
`filtered.py`, run `check.py`, compare with `solutions/`.

## Run it

```
cd rag-from-scratch/metadata-filtered
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # run everything
python3 solutions/filtered.py   # the demo: per-strategy numbers and the shortfall
```

Everything is standard-library only (Python 3.14, no numpy, no pip, no network);
SQLite comes from `sqlite3`. `check.py` adds `../eval-set/solutions` to `sys.path`
lazily, in step 4 only.

## The three strategies

| Strategy | Plan | When it fails |
|---|---|---|
| `pre_filter` | `SELECT … WHERE <filter>` (index), then rank the survivors | nothing structural; the planner picks the plan |
| `post_filter` | rank the whole corpus, take top k, then drop non-matching | a matching document below rank k is lost: fewer than k (even 0) results |
| `filter_aware` | count each predicate, drive the scan with the most selective index, re-check the rest in Python | nothing structural; same answer as `pre_filter`, better plan under selective ANDs |

`pre_filter` and `filter_aware` return the same documents and order; they differ in how
the candidate set is produced. `post_filter` is the anti-pattern the project is built to
expose.

## Steps

| # | File | What it proves |
|---|---|---|
| 1 | filtered.py | `build_db` creates the table and a secondary index on every filterable column (`PRAGMA index_list`/`index_info`) |
| 2 | filtered.py | on a tiny corpus `pre_filter` returns exactly the matching documents, in BM25 order, and a wrong-year document does not leak in |
| 3 | filtered.py | on a moderate filter the three strategies agree and every result satisfies the filter |
| 4 | filtered.py | end to end on the eval set's `filtered` family: recall@k, MRR, nDCG@k and mean results are reported per strategy, reproducibly and honestly (no strategy asserted to win) |
| 5 | filtered.py | a very selective filter (≤ 1/66 of the corpus) makes `post_filter` return fewer than k while `pre_filter`/`filter_aware` still find the match; the selectivity is printed |
| 6 | filtered.py | a filter matching nothing returns `[]` from every strategy, and a query with no lexical match abstains |

## Design decisions

Summarised; the full rationale is in the `solutions/filtered.py` docstring.

- **SQLite + one index per filterable column.** The project is about the *plan*: a filter
  is cheap only if an index can be chosen for it. Cost: six small indexes; on a tiny
  corpus the planner may still scan, which the project measures rather than hides.
- **A self-contained BM25 scorer** (k1=1.5, b=0.75) instead of importing the sibling
  `bm25` module, so the filter stage is measurable in a tree that holds only
  `{metadata-filtered, eval-set}`. Statistics are corpus-wide, so all strategies rank
  identically and differ only in which documents reach the scorer.
- **`year` is the four-character date prefix** (`substr(date, 1, 4) = ?`). Exact and
  rejects a wrong-year document; comparing a substring or fewer digits would admit
  neighbouring years. Cost: `substr` cannot use the `date` index (a range predicate
  could; left as an exercise).
- **`filter_aware` re-checks the full filter in Python** after driving on one predicate.
  Same answer as `pre_filter`, but the candidate set is produced by the rarest index.
- **Ties break by `doc_id` ascending; only positive scores are returned.**
  Deterministic output, and "no lexical match" is the empty list, matching the other
  stages' abstention rule.
- **Post-filter shortfall is the point.** `post_filter` takes the global top k *then*
  drops non-matching rows and never refills, so a selective filter can return nothing
  although matching documents exist. Step 5 constructs that case rather than hoping to
  sample it.

## Mutation table

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    rag-from-scratch/metadata-filtered rag-from-scratch/metadata-filtered/_build/mutations.py
```

Every row is CAUGHT.

| Step | Planted bug | Caught by |
|---|---|---|
| 1 | `build_db` never creates the secondary indexes | `PRAGMA` index coverage assertion |
| 2 | `pre_filter` forgets the SQL WHERE clause | a non-matching document (same query term) appears in the tiny result |
| 2 | `year` compared as a substring instead of the date prefix | the 2024 document leaks into a `year=2023` result |
| 2 | `pre_filter` ignores the `access_level` filter | the `access_level='internal'` case returns the whole corpus |
| 2 | the `superseded` predicate is inverted | `superseded=False` misses the fresh documents and `True` returns them |
| 5 | `post_filter` pads back up to k with non-matching docs | every result of the selective case must satisfy the filter |
| 5 | `post_filter` filters the whole ranking instead of the top-k window | the selective case must return `[]`, not the matching document |
| 5 | `filter_aware` degenerates to `post_filter` | `filter_aware` must equal `pre_filter` on the selective case |
| 6 | the no-match path returns the whole corpus | the no-matching-term abstention case |

## Questions to answer (no answers here)

1. `pre_filter` and `filter_aware` return the same list here. When would they differ in
   *plan* but not in answer, and how would you observe the difference without changing
   the result (timing, `EXPLAIN QUERY PLAN`, rows scanned)?
2. `post_filter` returns 4.75 of 10 results on the eval set's `filtered` family while
   keeping the same recall. Which metric hides that failure, and why is `mean results` the
   honest companion to it?
3. The `filtered` family uses `region` + `year`. In the generated corpus, `region`
   determines `year` (both cycle with the same period). How does that make the combined
   filter less selective than it looks, and how would you choose a genuinely selective
   predicate?
4. `year` is compared with `substr(date, 1, 4)`, which cannot use the index on `date`. A
   range predicate (`date >= ? AND date < ?`) can. Rewrite `_where_clause` accordingly and
   check that the answers are byte-identical.
5. Superseded documents share the text of their revision, and the eval set's relevance
   marks them as not relevant. Should a metadata filter for "current only" be expressed as
   `superseded = 0`, or should the ranker learn it? What does each choice cost?
6. `filter_aware` picks the driving predicate by `COUNT(*)` then re-checks the rest in
   Python. For a disjunction of filters (OR) rather than a conjunction, what breaks?

## Limits

- The store has no query planner hints and no composite indexes; a multi-column filter
  drives on one index and scans the rest.
- `selectivity` is a full `COUNT(*)` per predicate; at this scale that is fine and is the
  cost the `filter_aware` plan pays to order its predicates.
- BM25 is not tuned; the point is a correct, measured filter stage on a clean corpus.
- The eval set is synthetic and repetitive; absolute scores do not transfer (only the
  comparison between strategies does). See the eval set's own limits.

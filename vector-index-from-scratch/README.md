# Vector Index From Scratch

Build the exact answer, then two approximations of it, and measure what each
one gives up. In pure standard-library Python — no numpy, no FAISS, no GPU.

An approximate index is a trade, and a trade is only meaningful if both sides
are measured. The side everyone builds is the fast one; the side everyone
skips is the exact answer it is being compared against, which is why "12x
faster than brute force" survives review while the recall it cost does not
appear anywhere. This course builds the exact index first, keeps it as the gold
standard for every later stage, and makes each approximation pay for its
speed in a number.

## The stages

Ten graded stages. Each one targets a mistake that is easy to make and hard to
notice.

| # | File | The mechanism | The thing people get wrong |
|---|---|---|---|
| 1 | `stage_01.py` | Exact scan, recall@k, a work counter | Recall divided by `k` instead of by the relevant documents |
| 2 | `stage_02.py` | dot / L2 / cosine, the norm cache | Recomputing stored norms per comparison: `O(n)` square roots a scan |
| 3 | `stage_03.py` | k-means with k-means++ init | An unseeded partition, so every recall number moves between runs |
| 4 | `stage_04.py` | IVF: probe the nearest lists | Emitting each list's rows in list order — off by a swap, invisible |
| 5 | `stage_05.py` | The recall/latency frontier | Tuning `nprobe` on the same queries you then report |
| 6 | `stage_06.py` | The HNSW graph: levels, links | One-way links and a flat hierarchy; nothing fails loudly |
| 7 | `stage_07.py` | The walk, and `ef` | Treating `ef` as the result count, and returning where the walk stopped |
| 8 | `stage_08.py` | Deletions by tombstone | Unlinking the deleted node and cutting the paths the rest still need |
| 9 | `stage_09.py` | int8 scalar quantization | Clamping vs. the wrap of an integer cast; quantizing the query too |
| 10 | `stage_10.py` | The frontier report, and choosing | Choosing the fastest index without holding recall at the target |

Four of the ten are measurement stages, and that is the ratio the subject has.
The indexing half is a page of code per family; the half that decides whether
any of it works is the eval.

## How to use this directory

```bash
python3 codecraft/cli.py run vector-index-from-scratch   # what to build next, and why
python3 codecraft/cli.py hint vector-index-from-scratch  # when a nudge is not enough
```

Or without codecraft:

```bash
python3 -c "import course; [print(i, s.title) for i, s in enumerate(course.STAGES, 1)]"
```

Implement the templates at the top level; finished versions are in `solutions/`.
Each stage's checks exercise the stages before it (stage 4 measures against the
exact index of stage 1), so they are meant to be done in order.

## Prerequisites

`rag-from-scratch` stage 3 is the same exact index, written once already; this
course assumes you have built one and starts measuring it. Everything else is
self-contained Python: `math`, `random`, `heapq`. No embedding model, no vector
database, no network, no GPU.

## Design decisions

- **Count work, do not time it.** Every speed number is a count of dot products
  (`comparisons`, `visited`), not a wall-clock reading. A laptop's cache and the
  scheduler make milliseconds useless as a check, and a counter makes every
  claim in this course reproducible — the checks assert numbers.
- **Exact before approximate.** Stage 1 is the gold standard for all ten
  stages: recall is measured against the exact top-k for the very same query,
  never against a hand-labelled set (which can only speak about what a human
  thought to label) and never against the approximate answer itself.
- **Same seed, same partition, same graph.** k-means, the level draws and every
  tie-break are seeded and total (score, then insertion order or key). Without
  that, the frontier moves between runs and you cannot tell a better parameter
  from a luckier draw.
- **The graph is undirected on purpose.** Pruning a neighbour removes the
  reverse link too. A one-way link lets the walk in and not out, so behaviour
  depends on where it entered — and it is the kind of thing that shows up only
  as slightly worse recall.
- **Tune on one set of queries, report on another.** `report` returns both
  recalls, because that gap is the cheapest overfitting in the field and it is
  invisible in a table of results.
- **Compare at equal recall.** Indexes are tuned first (a dial is bound into a
  closure), then measured: bytes per vector, recall, work per query. A
  parameter value that does not share a scale with another parameter value
  cannot decide anything.
- **Deletion is a tombstone, and its cost is visible.** Unlinking is what
  everyone writes first and what quietly destroys recall; the stage makes you
  keep the node as a stepping stone and pay the filtering cost instead.

## Verification

The solutions pass all ten checks, and every check is mutation-tested: sixteen
plausible wrong implementations (recall divided by `k`, probe by list index,
per-cluster emit, one-way links, `ef` as the result count, unlink-on-delete,
symmetric distance, a wrap instead of a clamp, a floor that is not enforced)
are each planted into a solution and the stage's check must fail. `git log` and
the course's checks are the record; the mutations were applied privately, and
the assertions that catch them name the mistake in their message.

## Where this stops

Deliberately left out, so you know the boundary:

- **Scalar quantization only.** Product quantization (subvectors, a codebook per
  chunk) is the next compression step; int8 is where the asymmetry and the
  clamping lesson lives.
- **No heuristic neighbour selection.** Real HNSW adds a diversity heuristic
  when linking (a neighbour that is only reachable through another is skipped),
  which builds a better graph; the plain "M nearest, pruned symmetrically"
  graph is what these checks pin, and it is enough to measure `ef` against.
- **One thread, no SIMD, no persistence.** The indexes live in memory and count
  their own work; serving them, batching queries and storing them are the
  subjects of the inference and database courses.
- **No billion-scale claims.** At 60–300 vectors the numbers here are honest
  about the mechanism and silent about memory hierarchy — which is exactly the
  mistake the work counter exists to avoid.

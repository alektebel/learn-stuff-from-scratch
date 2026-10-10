# RAG From Scratch

Build a retrieval-augmented generation stack from the parts up, in pure
standard-library Python — and see the number each part produces.

RAG is usually introduced as a pipeline diagram: *embed, store, retrieve,
generate*. The diagram hides every decision that matters. This directory makes
you build the pieces and measure them, so the diagram becomes something you
could have drawn yourself.

## The stages

Nine graded stages. Each one targets a mistake that is easy to make and hard to
notice.

| # | File | The mechanism | The thing people get wrong |
|---|---|---|---|
| 1 | `stage_01.py` | Chunking with exact offsets | Overlap that shifts the offsets, so citations point at the wrong bytes |
| 2 | `stage_02.py` | TF-IDF embeddings | An un-smoothed idf that goes negative and reshuffles the ranking |
| 3 | `stage_03.py` | Exact vector index | Unstable ties — the same query ranks differently between runs |
| 4 | `stage_04.py` | BM25 | A term that occurs in every document scored as if it were informative |
| 5 | `stage_05.py` | Reciprocal rank fusion | Summing raw scores from two retrievers that do not share a scale |
| 6 | `stage_06.py` | Reranking and MRR | Measuring the wrong thing — ranking quality, not whether the fix helped |
| 7 | `stage_07.py` | Citations | An ungrounded claim printed as if a chunk supported it |
| 8 | `stage_08.py` | Tenant isolation | A retrieval call that *can* cross tenants, waiting for one forgotten filter |
| 9 | `stage_09.py` | End-to-end recall@k | No number at all — "it seems to work" |

## How to use this directory

```bash
python3 codecraft/cli.py run rag-from-scratch   # what to build next, and why
python3 codecraft/cli.py hint rag-from-scratch  # when a nudge is not enough
```

Or without codecraft:

```bash
python3 -c "import course; [print(i, s.title) for i, s in enumerate(course.STAGES, 1)]"
```

Implement the templates at the top level; finished versions are in `solutions/`.

**Prerequisites.** The LLM courses (`llm-from-scratch`) give you the tokenizer
mindset; everything here is self-contained Python. No embedding model, no vector
database, no network.

## Design decisions

- **TF-IDF, not a neural embedding.** The point of stage 2 is to see that an
  "embedding" is a weighting scheme you can write. A real model changes the
  numbers, not the shape of the pipeline — and stage 3's exact index is the
  ground truth every approximate index is measured against.
- **Brute force before ANN.** Approximate nearest-neighbour search is only
  meaningful relative to the exact answer. Stage 3 is that answer.
- **Isolation as a required argument.** `search(tenant, ...)` makes a
  cross-tenant read unrepresentable rather than merely discouraged. The
  enterprise RAG guide's warning is the reason: an embedding is the document,
  lightly encoded, so every argument that holds for documents must hold for
  vectors.

## Where this stops

Deliberately left out, so you know the boundary:

- **No generation.** This is the retrieval half. Wiring a model on top belongs
  with the agents and harness courses, not here.
- **No approximate index (HNSW/IVF).** That is the separate vector-index course;
  this one is the exact baseline it is measured against.
- **No persistence.** Indexes live in memory; a database-backed store is a
  different lesson (see `dynamo-paper` and `aws-from-scratch`'s DynamoDB).
- **TF-IDF is not semantic.** Synonyms will not match. That gap is *why* dense
  embeddings exist, and it is worth feeling before you replace them.

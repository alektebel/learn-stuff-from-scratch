# RAG from scratch

Ten retrieval-augmented generation projects, from hybrid search to agentic RAG, built as one
pipeline whose every stage has to earn its place on a shared evaluation set.

**Status: planned.** Nothing is built yet. This file is the plan; a project gets code only
when it is chosen, through the `graded-module` skill.

## Why this directory is first among the RAG-shaped plans

It is the most-cited gap in the repo: interview questions 1 and 11
([interview-prep](../interview-prep/ai-engineering.md)), agent-evals #5 and reliability #3
and #5 ([agent-evals](../agent-evals/README.md#the-rag-dependency)) all need a RAG system to
exist before they can be built.

## Constraints that shape the plan

- **No downloadable models.** huggingface.co is blocked in this environment, so there are no
  Sentence Transformers, no cross-encoder weights. Embeddings and rerankers are therefore
  built and trained here: latent semantic analysis (SVD of a term-document matrix, see
  `skill-tree` node foundations-03) and a small bi-encoder and reranker trained with
  [ml-systems/framework](../ml-systems/framework/). Weaker than pretrained models, and
  completely inspectable.
- **No LLM API key is configured.** Every stage up to generation runs offline. Generation,
  answer grading, Self-RAG and agentic RAG need a model; they come last, behind a
  budget, once a key exists.
- **No frameworks.** The source list's stacks (LangGraph, Elasticsearch, pgvector, Neo4j) are
  replaced by the pieces themselves: an inverted index with BM25, HNSW, SQLite (stdlib)
  for structured data and metadata, a small triple store. Same rule as `harness-lab/`:
  frameworks do the interesting half silently.

## Step 0: the evaluation set (built before any retriever)

A synthetic "company docs" corpus generated deterministically, with ground truth:
- documents with metadata (department, date, author, region, access level), some
  superseded by newer versions;
- tables (for the SQL + vector project), entities and relations (for the graph project);
- query sets with relevance judgments: lexical (exact codes, names), semantic
  (paraphrases), filtered ("policies from 2025, EMEA"), multi-hop, and **no-answer
  queries that must return nothing**;
- metrics: recall@k, MRR, nDCG@k, abstention precision and recall, latency; comparisons
  are paired per query (the statistics in `harness-lab/eval/stats.py`).

## The ten projects, mapped

| # | Project | Built here as | Needs | Already in the repo |
|---|---|---|---|---|
| 1 | Hybrid search (BM25 + dense) | inverted index + BM25; LSA and trained embeddings; HNSW; fusion by reciprocal rank and by weighted scores | CPU | [context-caching/semantic_cache.py](../context-caching/semantic_cache.py) (embeddings + cosine) |
| 2 | Metadata-filtered RAG | metadata in SQLite; pre-filter vs post-filter vs filter-aware graph search | CPU | [enterprise-ai-projects/02](../enterprise-ai-projects/02-multitenant-rag.md): tenant isolation as a filter that must not be bypassable; [database-from-scratch](../database-from-scratch/) secondary indexes |
| 3 | Reranking | retrieve 100, rerank to 5 with a reranker trained here | CPU | [ml-systems/framework](../ml-systems/framework/) to train it |
| 4 | Contextual chunking | chunk with the document's title and section path attached; the LLM-written context variant later | CPU, then LLM | — |
| 5 | SQL + vector | a router that sends structured questions to SQLite and the rest to retrieval; text-to-SQL later | CPU, then LLM | [rl-posttraining-llm](../rl-posttraining-llm/) (text-to-SQL environment and rewards) |
| 6 | Knowledge graph + vector | triple store, entity linking, multi-hop traversal combined with retrieval | CPU | — |
| 7 | Corrective RAG | a retrieval-quality gate; query rewriting (pseudo-relevance feedback first); fallback to a second corpus | CPU (offline fallback), web later | — |
| 8 | Self-RAG | decide whether to retrieve, grade evidence, check support of the answer | LLM | [contextcite/](../contextcite/) (attributing an answer to sources) |
| 9 | Multimodal RAG | tables and page images as first-class documents | vision model | — |
| 10 | Agentic RAG | an agent choosing sources and iterating retrieval | LLM | [harness-lab/](../harness-lab/) (loop, budgets, loop detection) |

## Corrections to the source list

The list is a good syllabus. Some of its framing would mislead if built literally:

- **"These can all be combined into one production pipeline."** They can; whether they
  should is an ablation question. Each stage adds latency, cost and failure modes. The
  deliverable of the combined pipeline is a table of the marginal gain of each stage, per
  query type, with paired confidence intervals. Expect one or two stages to carry most of
  the gain on any given corpus.
- **Hybrid search "finds both".** On some query sets dense alone matches or beats hybrid,
  and fusion weights tuned on one query set do not transfer. Measure per query type.
- **Metadata filtering** hides the hard part. Post-filtering an approximate top-k returns
  fewer than k results, or none, when the filter is selective; pre-filtering can disconnect
  an HNSW graph. The limit case is a filter matching 0.1% of the corpus.
- **Reranking** cannot recover what the first stage missed: recall@100 of retrieval is the
  ceiling of the reranked result. Measure both.
- **Contextual chunking with an LLM** costs one model call per chunk at indexing time
  (prompt caching reduces it). The deterministic variant (title + section path) is the
  baseline it has to beat.
- **Self-RAG** in the paper (Asai et al., 2023) is a model *trained* to emit reflection
  tokens; a prompted imitation is a different, cheaper system. **Corrective RAG** (Yan et
  al., 2024) uses a trained lightweight retrieval evaluator. (Both attributions from
  memory: verify before citing.)
- **Knowledge-graph RAG** pays for entity and relation extraction at indexing time; on
  questions that are not multi-hop it often adds nothing. The query set separates them.
- **Agentic RAG** inherits every agent failure: loops, cost blow-ups, tool misuse. It is the
  last project for a reason; its controls live in `harness-lab`.

## Recommended order

0 evaluation set → 1 (BM25, then LSA, then HNSW, then fusion) → 2 → 3 → 4 → 7 (offline
version) → 5 → 6 → then, with an LLM: 8 → 4 (LLM context) → 5 (text-to-SQL) → 10 → 9.

## Questions to answer before building (no answers here)

1. Your filter matches 0.1% of the corpus and you post-filter the top 10 of an ANN search.
   How many results do you expect to return?
2. BM25 and cosine scores live on different scales. What goes wrong if you add them, and what
   does reciprocal rank fusion do instead?
3. A no-answer query still returns k documents. Where in the pipeline does "I don't know"
   get decided, and what metric tells you whether it is decided well?
4. Why is recall@100 of the first stage more important than nDCG@5 when you plan to rerank?
5. Embeddings of your documents leak through the index even if the text is protected. What
   does enterprise-ai-projects/02 cite about inverting embeddings, and what does it change
   for project 2?

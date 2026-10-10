# LLM Engineering — a course map

Source: [ed-donner/llm_engineering](https://github.com/ed-donner/llm_engineering) (MIT,
© 2024 Ed Donner), read at commit `75c7b50` (2026-10-08). It is an eight-week applied-LLM
course: a notebook per day, ending in an autonomous multi-agent capstone.

This directory holds **no course code and no copied text**. It maps the course onto what
this repo already builds, so the course contributes a reading order, a comparison of what
is shallow versus deep, and a few task ideas — not a new track. The course is also listed
in [RESOURCES.md](../RESOURCES.md), "LLM agents".

## Verdict

Almost everything the course teaches is already built here, from scratch and with
checks. The one thing it teaches that this repo defers is **supervised fine-tuning of an
open model (LoRA / QLoRA)** — which needs a GPU — and the **paid hosted fine-tuning API**.
So the useful output of this intake is a map and two task ideas, not a module.

## Week-by-week map

| Wk | Course topic | Where it lands here | Status |
|---|---|---|---|
| 1 | Chat API, tokens and messages, statelessness ("illusion of memory"), structured JSON output, local models | [llm-from-scratch/](../llm-from-scratch/) (`tokenizer.py`, `sampling.py`), [sgl-lang/](../sgl-lang/) (JSON-schema/grammar constrained decoding), [harness-lab/](../harness-lab/) (transport) | covered |
| 2 | Frontier APIs, providers / abstraction layers, prompt caching, a chat UI, chatbots, **tool calling**, multimodality | [context-caching/](../context-caching/) (prompt caching), harness-lab [typed tool layer](../harness-lab/docs/phase2.md) (tool calling), [diffusion-models/](../diffusion-models/) (images), [agent-evals/](../agent-evals/) | partial — no app/UI layer |
| 3 | Colab/GPU, Hugging Face pipelines, tokenizers, open models, audio → minutes | [llm-from-scratch/](../llm-from-scratch/) (tokenizer); HF pipelines and speech-to-text need models/network | blocked — `huggingface.co` is not reachable here |
| 4 | Code generator: models write C++/Rust that is compiled and run, then compared | [agent-evals/](../agent-evals/) (#2 shadow, #10 Pareto, #3 judge), harness-lab bench | covered — could donate a task family |
| 5 | RAG week: chunking, embeddings, vector store, a framework, RAG evaluation, advanced RAG | [rag-from-scratch/](../rag-from-scratch/) (projects 1-8: chunking, HNSW/vector search, SQL+vector, graph+vector, reranking, corrective, Self-RAG, plus the shared eval set) | covered |
| 6 | Capstone: data curation, pre-processing, baselines (random forest, boosting), neural nets, frontier LLM, **fine-tune a hosted frontier model** | [ml-systems/framework/](../ml-systems/framework/) (NN, cost model), [quantitative-trading/](../quantitative-trading/) (boosting), rag data pipelines | partial — the frontier fine-tune is a paid API call |
| 7 | **Fine-tune open models: LoRA / QLoRA / PEFT / TRL**, experiment tracking, deploy | — ([rl-posttraining-llm/](../rl-posttraining-llm/) has TRL templates and [agent-evals/](../agent-evals/) #6 is deferred on GPU) | **gap — GPU** |
| 8 | Autonomous multi-agent capstone: planning / scanner / ensemble agents, RAG over a large product corpus, embeddings, deployment, notifications | [agent-evals/](../agent-evals/) + harness-lab phases 2-3 (tools, loop, subsystems), [ml-in-production/](../ml-in-production/), [mlops/](../mlops/) (deploy), rag-from-scratch (retrieval) | covered / extends |

## Gaps, grouped by what this environment can actually do

- **CPU-real or simulated.** A **code-generation task family** for harness-lab (a model
  writes code that must compile and pass hidden tests, then models are compared on pass
  rate), distilled from week 4; a **tool-calling scenario** (week 2's assistant) as an
  external check on the typed tool layer; an **audio → minutes** pipeline only as a
  simulated one, since there are no speech-to-text weights here.
- **GPU-required.** **LoRA / QLoRA supervised fine-tuning** of a small open model (week 7)
  is the largest genuine gap. It is already tracked by the deferred projects
  ([agent-evals/](../agent-evals/) #6, the GPU half of [inference-lab/](../inference-lab/)),
  so this course does not change the plan — it confirms it.
- **Paid API.** Fine-tuning a hosted frontier model (week 6) is a cost question, not a
  buildability one.
- **Out of this repo's shape.** A Gradio-style application layer: this repo builds
  protocols, harnesses and tools, not UI widgets. Recorded here, not planned as a module.

## What is worth taking

1. **The week-4 comparison design.** Code that must compile and pass hidden tests is a
   verifier, and comparing models on pass rate is exactly the shape of harness-lab's
   evaluation. Mine it for *task ideas* (no code is copied).
2. **The week-2 tool-calling assistant.** The smallest realistic tool-calling scenario; a
   good outside test for harness-lab's typed tool layer.
3. **Weeks 5-6 as reading order** for [rag-from-scratch/](../rag-from-scratch/) and
   [ml-systems/](../ml-systems/).

## Corrections (marketing versus engineering)

- The course sells "eight weeks to proficiency"; per topic it is one notebook deep. The
  from-scratch modules in this repo are the depth the course leaves out.
- "Fine-tune a frontier model" (week 6) is a **hosted API call** — upload a JSONL file and
  poll a job. The training happens at the provider; nothing is learned about training by
  doing it.
- The model-comparison "results" (weeks 4, 6) are single-run anecdotes until repeated over
  seeds with a significance test — see [harness-lab/eval/stats.py](../harness-lab/eval/stats.py).

## If a piece is taken on

Any of these is a real slice with its own contract; none is started. In rough order of
value per unit of environment cost:

1. **harness-lab: a code-generation task family** (generate → compile → run hidden tests →
   score). CPU-real, deterministic, no endpoint needed for the verifier; it also feeds the
   red-team and contamination projects.
2. **harness-lab: an external tool-calling scenario** on the typed tools.
3. **A PEFT/LoRA SFT module** — only if GPU access is decided yes (see [TODO.md](../TODO.md)).

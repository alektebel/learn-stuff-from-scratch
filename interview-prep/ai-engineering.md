# AI engineering interview questions

Twenty system-design and judgement questions for AI/LLM engineering roles. **No answers
here, on purpose.** For each question this file gives:

- **Practise with:** what in this repository you have built (or will build) that lets you
  answer from your own measurements instead of from blog posts;
- **Follow-up:** the probe an interviewer uses to tell a rehearsed answer from real
  experience. If you cannot answer the follow-up, the first answer was recited.

Status: **built** = code with graded checks exists here; **planned** = a plan exists, no
code yet; **gap** = nothing in the repo yet.

How to use it: answer out loud (or in writing) first, then open the "practise with" link
and check your answer against what the code and its measurements actually show.

| # | Question | Practise with | Status | Follow-up |
|---|---|---|---|---|
| 1 | Design a RAG system for company docs | [rag-from-scratch/](../rag-from-scratch/) (10 projects, shared eval set); multi-tenant isolation in [enterprise-ai-projects/02](../enterprise-ai-projects/02-multitenant-rag.md) | planned | A document is updated: how long until answers reflect it, and how do you know? |
| 2 | How do you stop hallucinations in production? | [contextcite/](../contextcite/) (attributing an answer to its sources by ablation); RAG adversarial harness (agent-evals #5) | built (attribution) / planned (harness) | "Stop" or "detect"? What is your measured faithfulness rate today, and on which sample? |
| 3 | When would you fine-tune vs prompt vs RAG? | [rl-posttraining-llm/](../rl-posttraining-llm/), post-training section of [llm-from-scratch/RESOURCES.md](../llm-from-scratch/RESOURCES.md) | built (RL course) | The knowledge changes weekly and the format never changes: which one, and why not the others? |
| 4 | Design an AI customer support agent | [harness-lab/](../harness-lab/) (loop, tools, budgets); [agent-evals/redteam](../agent-evals/redteam/) | partly built | When must it hand off to a human, and how do you measure that the hand-off happens? |
| 5 | How do you evaluate an LLM app? | [harness-lab/eval/](../harness-lab/eval/) (null/oracle controls, hardened verifiers), [ADR 0004](../harness-lab/docs/adr/0004-statistics.md) | built | Your eval set has 50 items. What is the smallest regression it can detect? |
| 6 | Explain embeddings like I'm hiring you | [context-caching/semantic_cache.py](../context-caching/semantic_cache.py); [ml-systems/framework](../ml-systems/framework/) part 2 (embeddings) | partly built | Two sentences with opposite meaning have cosine similarity 0.92. Why, and what do you do? |
| 7 | How do you cut inference cost by 10x? | [context-caching/](../context-caching/) (prefix and radix caching), [inference-lab/](../inference-lab/), [ml-systems/framework/costs.py](../ml-systems/framework/) | partly built | Which 10x: per token, per request, or per resolved task? Which of your levers moves each? |
| 8 | Design a multi-agent system that doesn't loop forever | harness-lab phase 3 (loop detection, stuck detector, iteration budgets), task [t18](../harness-lab/eval/tasks/t18-oscillating-fix/); [Hermes iteration budget](../harness-lab/docs/variants/sources-openclaw-hermes.md) | planned (task built) | Subagents each have a budget: can the total still exceed the parent's? (Hermes: yes. Why?) |
| 9 | How do you handle prompt injection from user docs? | [agent-evals/redteam](../agent-evals/redteam/) (r01-r04: README, code comment, tool output, quoted ticket) | built | Your detector checks final state. Which injection does it miss entirely? (Its README lists them.) |
| 10 | Build a semantic cache. When does it fail? | [context-caching/semantic_cache.py](../context-caching/semantic_cache.py) | built | Give a pair of prompts above your similarity threshold that need different answers. |
| 11 | How do you choose chunk size for RAG? | [rag-from-scratch/](../rag-from-scratch/) project 4 | planned | What did recall@k do when you halved the chunk size, on what queries? |
| 12 | Design observability for every LLM call | harness-lab run records ([contract.py](../harness-lab/eval/contract.py)); LLM tracing (agent-evals reliability #12) | partly built | You log every prompt: what about PII, retention and cost of the logs themselves? |
| 13 | How do you A/B test two models safely? | [ADR 0004](../harness-lab/docs/adr/0004-statistics.md) (paired McNemar, power); canaries in [deploy-and-debug/](../deploy-and-debug/); shadow comparator (agent-evals #2) | partly built | Outputs are non-deterministic. Is your difference the models or the sampling? How do you tell? |
| 14 | What's your fallback when the model provider is down? | [system-design/circuit_breaker.py](../system-design/circuit_breaker.py); AI gateway ([inference-lab](../inference-lab/) #13) | partly built | The fallback model is worse. How do you know it is still good enough, before the outage? |
| 15 | Design memory for a long-running personal agent | harness-lab phase 7 (write, correct, forget, associate); [prompt-cache constraint](../harness-lab/docs/variants/sources-openclaw-hermes.md) | planned | The user corrects a fact. How does the agent stop using the old one without a cache miss? |
| 16 | How do you grade tool-calling, not just final text? | trajectory grading (agent-evals #1); the `complicit` control in [redteam](../agent-evals/redteam/) | planned / built (the argument) | Two valid trajectories reach the same result. How does your grader not penalise one? |
| 17 | Rate-limit, retry, and timeout strategy for agents | [system-design/](../system-design/) (rate limiter, backoff with jitter, circuit breaker); harness-lab wall-clock budget in a killable process ([ADR 0003](../harness-lab/docs/adr/0003-run-record.md)) | built | A retry after a timeout: what if the first call actually succeeded? (idempotency) |
| 18 | How do you keep PII out of the context window? | [enterprise-ai-projects/03](../enterprise-ai-projects/03-pii-proxy.md) (guide); the `no_leak` detector in [redteam](../agent-evals/redteam/detectors.py) | planned | Redaction before the model: what breaks when the model needs the value to do the task? |
| 19 | Design a coding agent that can edit a real repo | [harness-lab/](../harness-lab/) (sandbox, verifier, phases 1-5) | partly built | How do you stop it passing the tests by editing the tests? (Phase 0's verifier isolation is one answer.) |
| 20 | Walk me through an AI system you shipped end to end | see below | — | What broke after launch that you had not predicted? |

## About question 20

Nothing in this repository has been *shipped* to users. These are learning projects that were
built and measured. Present them that way. An interviewer who hears "shipped" will ask
about users, incidents and on-call, and the answer falls apart. What you can honestly walk
through end to end, with numbers:

- **harness-lab phase 0:** a sandboxed evaluation bench. The null and oracle controls
  bracket 20 tasks; three verifier attacks fooled a naive verifier and not this one; the
  power analysis shows what 20 tasks cannot detect.
- **agent-evals red-team v1:** 18 runs that pass every final-answer test and still did the
  harmful thing.
- **database-from-scratch:** crash recovery verified at 120 truncation points, with a
  mutation-tested checker.

## Gaps this list exposes

Questions 1, 11 and 18 have no code behind them. RAG (1, 11) is the larger gap and unblocks
three planned eval projects; PII handling (18) has only a detector, no prevention.

# Roadmap

The order to build this repository in, and the review it is based on.
`python3 codecraft/cli.py path` renders this with your live progress.

The order is the one you set: **AWS → LLM internals → RAG → evals + agents → MCP
→ harness → benchmark → eval → the machine stack (GPU, CPU, OS) → the rest.**

---

## The review: every project, by what it needs to be usable

### Ready now — checker-driven, pure Python, `codecraft` runs them as-is

Seven courses, 102 graded checks between them, no dependencies.

| Course | Checks | What it teaches |
|---|---|---|
| `aws-from-scratch` | 18 | IAM, S3, SQS, DynamoDB, Lambda, SNS, KMS, VPC + capstone |
| `dynamo-paper` | 17 | Consistent hashing, vector clocks, quorums, hinted handoff, Merkle, gossip |
| `context-caching` | 16 | KV cache, prefix/radix caching, paged KV + copy-on-write, routing |
| `contextcite` | 14 | Context attribution by ablation + LASSO; the eval-flavoured one |
| `llm-from-scratch` | 13 | BPE, attention, sampling, KV cache, RoPE |
| `compiler-and-vgpu` | 12 | ISA, assembler, front end, register allocation, SIMT divergence |
| `deploy-and-debug` | 12 | Capacity math, percentiles, SLOs, fault diagnosis, rollout |

### Legacy — templates and solutions, but no checker (needs a `course.py`)

These are real and mostly substantial; they cannot join `codecraft` until they
have graded checks. An authored `course.py` can wrap a C/CUDA/Haskell project
just as well as a Python one — its check functions may shell out to `make`.

| Project | Notes |
|---|---|
| `system-design` | 6,000 lines, pure Python, 528 TODO markers. The big one. |
| `quantitative-trading` | 5,400 lines; numpy / pandas / scipy / sklearn |
| `world-models` | 10,500 lines of PyTorch across five papers |
| `lean-proofs` | 6,400 lines, 658 `sorry`s — the deepest single project here |
| `haskell-projects` | 3,600 lines |
| `c-compiler` | C; lexer, parser, semantic, codegen, optimizer + tests |
| `bash-from-scratch`, `http-server`, `dns-server`, `firewall-from-scratch`, `toralizer` | C systems projects |
| `communication-protocols`, `cryptographic-library`, `quantum-computing-lang` | C |
| `cuda-from-scratch` | 14 `.cu` files; needs a GPU |
| `diffusion-models`, `deepfake-creation`, `deepfake-detection` | PyTorch |
| `distributed-training`, `ml-in-production`, `ml-inference` | Thin (~210–280 lines) |
| `mlops` | 268 lines, and no `solutions/` at all |
| `spectral-graphs` | 473 lines; numpy |
| `sas-lineage-tool` | Python + SAS fixtures |
| `web-scraping` | **Complete** — zero TODO markers; use it as a reference, not a course |

### Docs-only — a README and nothing to build

`vllm-engine`, `tensorrt-inference`, `sgl-lang`. These need a course authored
from scratch, not just a checker.

### Missing entirely — the half of your list the repo does not have yet

A vector index, evals, agents, MCP, an agent harness, a benchmark, and an eval
framework. Also no `CPU` or `OS`. `rag-from-scratch/` now exists (phase B1).

---

## Do you need anything before AWS?

**No.** `aws-from-scratch` is self-contained: pure Python, no dependencies, and
its first section (`iam.py`) is the intended entry point — everything else gates
on it. Start there.

Three adjacent courses deepen it later, and none block it:

- `system-design` — queues, idempotency, caching. Makes `sqs.py` and
  `dynamodb.py` click.
- `dynamo-paper` — the paper behind DynamoDB: quorums and partitioning in depth.
- `deploy-and-debug` — capacity and failure, the operational half.

---

## Saving what other branches already did

Substantial material exists outside `main`. Before authoring the missing
courses, cherry-pick these — do not re-invent them:

| Branch | What to port |
|---|---|
| `claude/enterprise-ai-project-guides` | `enterprise-ai-projects/` — **12 implementation guides**, including `02-multitenant-rag.md`, `10-mcp-legacy-erp.md`, `11-shadow-evaluator.md`. Guides, not code: exactly the source material for phases B, C, D. |
| `claude/curriculum-and-repo-index` | `curriculum/` — six course blocks plus `REPO-MAP.md`, which maps all 34 directories and says which no course covers. |
| `claude/weekly-repo-layout` | `ROADMAP.md` (an 18-week plan with three tracks), `progress.py`, `REMAINING.md`, and the week-01.. folders. |
| `claude/rl-posttraining-llm-exercises-wzfe8w` | `rl-posttraining-llm/` — GRPO, rewards, an agent loop (phase 5), and `test_harness.py`. Source material for agents and the harness. |
| `claude/linux-from-scratch-curriculum-2qokjd` | `linux-from-scratch/` — the OS course for phase G. |

---

## How to begin

```bash
python3 codecraft/cli.py path                 # the plan, with progress
python3 codecraft/cli.py run aws-from-scratch # stage 1: iam.py
```

Work one stage at a time; the coach and the mentor handle the rest. When the
seven ready courses are done, phase B is the first thing to author:

```bash
python3 codecraft/cli.py new rag-from-scratch --title "RAG From Scratch" --stages 8
```

A course is its tests — write the check that catches the mistake that is easy to
make and hard to notice. The enterprise RAG guide tells you which mistakes those
are (the `FORCE ROW LEVEL SECURITY` line everyone forgets, embeddings not being
de-identified, recall vs. latency).

---

## The MUS benchmark (phase F) — resolved

MUS is the Spanish card game, and `mus-benchmark` is **your own** project
(`~/Desarrollo/mus-benchmark`, GitHub `alektebel/mus-benchmark`): a benchmark
for cooperation between two-player LLM teams, Team A on seats 0 and 2, Team B on
1 and 3, under partial observability.

Its machinery is exactly what phase F is for, and it is unusually well thought
through — worth reimplementing stage by stage rather than reusing:

- a **strict, turn-gated engine** that validates declarations, discards and turn
  order, with a documented rules variant;
- **señs** — private, partner-directed, TTL-expiring gestures on a virtual-time
  kernel, so a gesture made mid-deliberation reaches the partner's next decision
  or fades;
- the insight that a 10-hand match yields **one noisy bit**, so the unit of
  measurement becomes the **decision**, logged one JSONL record at a time with
  the engine's ground truth;
- **scorecards** — aggression, bluff rate, fold-error, payoff — where a bluff is
  defined against the empirical strength distribution for that lance, not
  "bet and lost";
- **calibration probes** (`READ_PROBE`) scored by Brier, log-loss and AUC, with
  the control arm it needs;
- **mirrored seating**, because seats 0+2 carry a measured positional edge;
- and honest limits: short matches and fixed model names do not rank models.

A course that rebuilds those is a course in *measurement*, which is the same
lesson phase C and F2 are after, applied to an adversarial game.

## Other open questions

- **Legacy projects need checkers.** Which to convert first is a policy choice:
  converting underneath the courses you are actually doing beats converting the
  most impressive-sounding project.

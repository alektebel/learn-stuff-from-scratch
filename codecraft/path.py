"""The path: what to build, in what order, and what is missing.

`codecraft path` renders this merged with your live progress. The order follows
the plan you set — AWS first, then LLM internals, then the AI-engineering half
(RAG, evals, agents, MCP, harness, benchmark, eval), then the systems half
(compiler/GPU/CPU and the rest).

Each item is one of:

  ready     an existing course with a check.py — run it now
  legacy    an existing project with templates and solutions but no checker;
            to use it in codecraft it needs a course.py (see scaffold.py)
  author    a course that does not exist yet; author it with `codecraft new`
  salvage   material exists on another git branch; port it first

`prereq` is the honest dependency, not a suggestion. A course can be started
without its prereqs, but the stages assume them.
"""

PHASES = [
    ("A", "Cloud and LLM internals", [
        {"id": "A1", "title": "AWS From Scratch", "course": "aws-from-scratch",
         "kind": "ready", "prereq": [],
         "why": "Eight mechanism families in pure Python, 18 checks. The best "
                "first course: no dependencies, every stage is a real failure mode."},
        {"id": "A2", "title": "LLM From Scratch", "course": "llm-from-scratch",
         "kind": "ready", "prereq": [],
         "why": "BPE, attention, sampling, KV cache, RoPE. 13 checks, pure Python."},
        {"id": "A3", "title": "Context Caching From Scratch", "course": "context-caching",
         "kind": "ready", "prereq": ["A2"],
         "why": "The direct continuation of A2: page, prefix-share, evict the KV "
                "cache without changing the output. 16 checks."},
        {"id": "A4", "title": "ContextCite From Scratch", "course": "contextcite",
         "kind": "ready", "prereq": ["A2"],
         "why": "Which context caused the answer — ablation and a LASSO surrogate. "
                "The eval-flavoured course, and the bridge into RAG. 14 checks."},
        {"id": "A5", "title": "System Design", "course": "system-design",
         "kind": "legacy", "prereq": [],
         "why": "Optional but cheap: caching, queues, idempotency, rate limiting. "
                "Makes sqs/dynamodb in A1 click and underpins the agent half."},
        {"id": "A6", "title": "Dynamo From Scratch", "course": "dynamo-paper",
         "kind": "ready", "prereq": ["A1"],
         "why": "The paper behind DynamoDB, in depth: quorums, hinted handoff, "
                "Merkle anti-entropy. 17 checks."},
        {"id": "A7", "title": "Deploy & Debug", "course": "deploy-and-debug",
         "kind": "ready", "prereq": ["A1"],
         "why": "Capacity math, SLOs, root-causing faults from metrics. The "
                "operations thread that every later course leans on. 12 checks."},
    ]),
    ("B", "RAG", [
        {"id": "B1", "title": "RAG From Scratch", "course": "rag-from-scratch",
         "kind": "ready", "prereq": ["A2", "A4"],
         "why": "Built and ready: chunking, TF-IDF, a vector index, BM25, rank "
                "fusion, reranking, citations, tenant isolation, recall@k. 9 checks."},
        {"id": "B2", "title": "Vector Index From Scratch", "course": "vector-index-from-scratch",
         "kind": "ready", "prereq": ["B1"],
         "why": "Brute force -> IVF -> HNSW, with recall and work measured "
                "against the exact index you built in B1. 10 checks, pure "
                "Python, and the stage that makes 'approximate' mean "
                "something."},
    ]),
    ("C", "Evals and agents", [
        {"id": "C1", "title": "Evals From Scratch",
         "course": "evals-from-scratch", "kind": "ready", "prereq": ["A4"],
         "why": "Datasets, exact/F1 metrics, LLM-as-judge and its calibration, "
                "statistical significance, regression gating. Do this before agents."},
        {"id": "C2", "title": "Agents From Scratch",
         "course": "agents-from-scratch", "kind": "ready", "prereq": ["C1", "B1"],
         "why": "The loop and the transcript that is its state, tool schemas and "
                "validation, errors as observations, parsing what a model actually "
                "writes, retries with idempotent effects, memory bounded by turns, a "
                "filesystem sandbox, an approval gate against injected content, "
                "budgets that stop before the cap, and a state-based audit."},
    ]),
    ("D", "MCP", [
        {"id": "D1", "title": "MCP From Scratch", "course": None,
         "kind": "author", "prereq": ["C2"],
         "why": "JSON-RPC 2.0, stdio and streamable-HTTP transports, the capability "
                "handshake, tools/resources/prompts, and tool design for an "
                "unreliable caller (idempotency, read-only first)."},
    ]),
    ("E", "Harness", [
        {"id": "E1", "title": "Agent Harness From Scratch", "course": None,
         "kind": "author", "prereq": ["C2", "D1"],
         "why": "The runtime around the model: tool dispatch, context assembly and "
                "compaction, streaming, retries, sandboxing, tracing. What makes an "
                "agent usable rather than a demo."},
    ]),
    ("F", "Benchmark and eval", [
        {"id": "F1", "title": "Benchmark From Scratch (Mus)", "course": None,
         "kind": "salvage", "prereq": ["C1", "E1"],
         "why": "Reimplement the measurement machinery of your own mus-benchmark "
                "(2v2 Mus against LLM teams): strict turn-gated engine, one JSONL "
                "record per decision, scorecards, calibration probes (Brier/AUC), "
                "mirrored seating to cancel bias. Reference repo: "
                "~/Desarrollo/mus-benchmark."},
        {"id": "F2", "title": "Eval Framework From Scratch", "course": None,
         "kind": "author", "prereq": ["F1"],
         "why": "A reusable eval runner: suite config, metric plugins, judge "
                "protocol, significance, and CI gating. The tool you keep using."},
    ]),
    ("G", "GPU, CPU and the machine stack", [
        {"id": "G1", "title": "Compiler + Virtual GPU", "course": "compiler-and-vgpu",
         "kind": "ready", "prereq": [],
         "why": "One ISA, two machines: assembler, front end, register allocation "
                "with spilling, SIMT divergence. 12 checks. The right first systems "
                "course before real CUDA."},
        {"id": "G2", "title": "CUDA From Scratch", "course": "cuda-from-scratch",
         "kind": "legacy", "prereq": ["G1"],
         "why": "Kernels from vector add to a network. Needs a GPU and a checker "
                "wrapper to join codecraft."},
        {"id": "G3", "title": "CPU From Scratch", "course": None,
         "kind": "author", "prereq": ["G1"],
         "why": "A real datapath: decoder, register file, ALU, control unit, memory "
                "and pipelining, simulated and tested. Missing from the repo."},
        {"id": "G4", "title": "OS From Scratch", "course": None,
         "kind": "salvage", "prereq": ["G3"],
         "why": "A linux-from-scratch curriculum exists on a branch; port it, then "
                "give it a checker."},
        {"id": "G5", "title": "C Compiler", "course": "c-compiler",
         "kind": "legacy", "prereq": ["G1"],
         "why": "Lexer, parser, semantic analysis, codegen, optimizer. Templates and "
                "solutions exist; it needs a checker to join codecraft."},
        {"id": "G6", "title": "The C systems set", "course": None,
         "kind": "legacy", "prereq": [],
         "why": "bash-from-scratch, http-server, dns-server, firewall-from-scratch, "
                "toralizer, communication-protocols, cryptographic-library, "
                "quantum-computing-lang. One at a time; each needs a checker."},
    ]),
    ("H", "The rest", [
        {"id": "H1", "title": "Distributed Training", "course": "distributed-training",
         "kind": "legacy", "prereq": ["A2"], "why": "Data and model parallelism."},
        {"id": "H2", "title": "Inference and serving", "course": None,
         "kind": "salvage", "prereq": ["A3"],
         "why": "vllm-engine, tensorrt-inference, ml-inference, sgl-lang. Three are "
                "README-only on main; an inference-from-scratch set exists on a branch."},
        {"id": "H3", "title": "Generative models", "course": None,
         "kind": "legacy", "prereq": ["C1"],
         "why": "diffusion-models, world-models (10k lines of PyTorch), deepfake "
                "creation and detection."},
        {"id": "H4", "title": "Long tail", "course": None, "kind": "legacy", "prereq": [],
         "why": "quantitative-trading, spectral-graphs, lean-proofs, haskell-projects, "
                "mlops, ml-in-production, sas-lineage-tool, web-scraping."},
    ]),
]

_SYMBOL = {"ready": "\u25cb", "legacy": "\u00b7", "author": "\u270e", "salvage": "\u21bb"}


def _find(courses, name):
    for c in courses:
        if c["name"] == name:
            return c
    return None


def render_path(profile, courses, ink):
    green, yellow, grey, cyan = ("\033[32m", "\033[33m", "\033[90m", "\033[36m")
    lines = ["", ink("  codecraft \u00b7 the path", "\033[1m"),
             ink("  your order: AWS, LLM internals, RAG, evals + agents, MCP, "
                 "harness, benchmark, eval, then the machine stack", grey), ""]
    done = active = 0
    for code, title, items in PHASES:
        lines.append(ink(f"  PHASE {code} \u2014 {title}", cyan))
        for item in items:
            course = _find(courses, item["course"]) if item["course"] else None
            cstate = profile["courses"].get(item["course"], {}) if item["course"] else {}
            total = (cstate.get("total")
                     or (len(course["stages"]) if course else 0))
            passed = cstate.get("last_passed", 0)
            if item["kind"] == "ready" and course and total and passed == total:
                state, mark, note = "complete", ink("\u2713", green), ""
                done += 1
            elif item["kind"] == "ready" and course and cstate:
                state, mark = "doing", ink("\u25cf", yellow)
                note = (f"{passed}/{total}  next stage {cstate.get('next_step')} "
                        f"({course['stages'].get(cstate.get('next_step'), {}).get('file', '')})")
                active += 1
            elif item["kind"] == "ready":
                state, mark, note = "ready", ink("\u25cb", grey), "not started"
            elif item["kind"] == "author":
                mark, note = ink("\u270e", yellow), ink("to author", yellow)
            elif item["kind"] == "salvage":
                mark, note = ink("\u21bb", yellow), ink("port from a branch", yellow)
            else:
                mark, note = ink("\u00b7", grey), ink("no checker yet", grey)
            prereq = ""
            if item["prereq"]:
                prereq = ink("  after " + ", ".join(item["prereq"]), grey)
            label = f"{item['id']}  {item['title']}"
            lines.append(f"  {mark} {label:<34} {note}{prereq}")
            lines.append(ink(f"       {item['why']}", grey))
        lines.append("")
    lines.append(ink(f"  {done} complete \u00b7 {active} in progress \u00b7 "
                     f"start: python3 codecraft/cli.py run {_first_ready(courses)}", grey))
    lines.append("")
    return "\n".join(lines)


def _first_ready(courses):
    for code, title, items in PHASES:
        for item in items:
            if item["kind"] == "ready" and _find(courses, item["course"]):
                return item["course"]
    return "<course>"

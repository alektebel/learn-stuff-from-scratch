# TODO

The open work in this repository, in order. Each item links to the plan that specifies it.
Update this file in the same commit that finishes or adds an item.

## Blocked on a decision or an input from the owner

- [x] **A cost cap for harness-lab phase 1.** Decided: `0,50 €` per evaluation run, a runaway
      guard rather than a budget (the endpoint is free in this session). The baseline still
      needs the sandbox, which is now available (see "Docker available" below).
      → [harness-lab/CLAUDE.md](harness-lab/CLAUDE.md)
- [ ] **GPU access: yes or no.** Decides whether the GPU-required half of
      [inference-lab](inference-lab/README.md) and step A of the
      [CUDA roadmap](cuda-from-scratch/ROADMAP.md) are in the plan, or stay code without
      measurements.
- [ ] **Horizon and goal for harness-lab phase 7** (memory): how many weeks, and whether the
      aim is breadth or a result on correction/forgetting. Decides what is cut.
- [x] **MCP server scope:** decided — from scratch, streamable HTTP, exposing ERP read tools
      plus guarded writes, living in [mcp-from-scratch/](mcp-from-scratch/) (spec + resources +
      runnable tests; the server core stays a LEARN task, with a reference implementation in
      `solutions/` and a 12-bug mutation test the contract catches). Related:
      [enterprise-ai-projects/10](enterprise-ai-projects/10-mcp-legacy-erp.md).
- [ ] **Inputs only the owner can provide:** the text of the 149 unread X posts and short links
      ([RESOURCES.md](RESOURCES.md), "Unsorted"); titles for the 60 unverified arXiv IDs;
      the current CV; the updated `harness-lab-prompt.md` (never reached the repo).

## Environment

- [ ] **Session-start hook**: start `dockerd` and build the harness-lab sandbox image
      automatically in cloud sessions (today it is manual, see [CLAUDE.md](CLAUDE.md)).
- [x] **Docker available for harness-lab**: installed rootless on the owner's machine (engine
      + the `buildx` plugin) and built `harness-lab-sandbox:0`; `PATH` and `DOCKER_HOST` are
      set in `~/.bashrc`. `loginctl enable-linger diego` is still needed (needs root) so the
      user service survives logout.
- [ ] **numpy is not installed** (no pip either). Any module that imports it cannot run
      here: `ml-systems/framework` (parts 2-3), CUDA step C. Either install numpy or keep
      those items out of the environment's build queue.
- [x] **`AGENTS.md` → `CLAUDE.md` symlink**, so harnesses that read `AGENTS.md` find the same
      conventions.

## Ready to build, in priority order

1. [x] **RAG project 1, hybrid search**: step 0 (the evaluation set) is built in
       [`rag-from-scratch/eval-set/`](rag-from-scratch/eval-set/README.md) and audited; the
       **BM25 stage** is built in [`rag-from-scratch/bm25/`](rag-from-scratch/bm25/README.md)
       and audited (inverted index, Okapi BM25, metadata filters, abstention, measured on the
       shared set); the **LSA stage** is built in
       [`rag-from-scratch/lsa/`](rag-from-scratch/lsa/README.md) and audited (tf-idf, a
       truncated SVD by an own Jacobi solver, cosine retrieval, same filter/abstention
       conventions, measured on the shared set: LSA wins semantic MRR 1.000 vs 0.900 but
       trails the lexical baseline overall, reported honestly); the **HNSW stage** is built
       in [`rag-from-scratch/hnsw/`](rag-from-scratch/hnsw/README.md) and audited (a real
       multilayer navigable-small-world graph index over the LSA embeddings, recall@k vs
       exact search with the distance-computation trade-off measured, and a post-ANN
       selective-filter limit case). The **fusion stage** is built in
       [`rag-from-scratch/fusion/`](rag-from-scratch/fusion/README.md) and audited (reciprocal
       rank fusion and per-query normalised weighted score fusion over the two stages, the
       per-query paired counts, and the limit cases: weights tuned on one family degrade
       another, and abstention is asymmetric). All four stages are measured on the shared set;
       on this set fusion ties BM25 overall and beats LSA only on multi-hop, reported honestly.
       Unblocks agent-evals #5, reliability #3 and #5, interview questions 1 and 11.
       → [rag-from-scratch/README.md](rag-from-scratch/README.md)
2. [ ] **harness-lab phase 1**: the core is implemented (owner-authorised BUILD for
       `run_loop`), the Docker sandbox is fixed for rootless Docker (`docker cp` into
       a started container; `put_dir` chowns before chmod), and the full harness suite
       is green (128 passed, 8 xpassed). What is left is the closing baseline on
       20 tasks x 3 seeds: it needs the live endpoint exported
       (`HARNESS_LAB_BASE_URL`, `HARNESS_LAB_API_KEY`, `HARNESS_LAB_MODEL`) in the
       shell that runs `python -m eval.runner --agent mini --tasks all --seeds 0 1 2`;
       Docker and the 0,50 €/run cap are in place.
       → [harness-lab/docs/phase1.md](harness-lab/docs/phase1.md)
3. [x] **CUDA step B**: memory system simulated and graded on CPU (coalescing, bank
       conflicts, occupancy, roofline). Landed as `cuda-from-scratch/memory-system/`
       (16 checks, 4 planted bugs). → [cuda-from-scratch/ROADMAP.md](cuda-from-scratch/ROADMAP.md)
4. [x] **web-launch-checklist observers and check.py**, crawler and exercises 1-3 first,
       then robots.txt and sitemap.xml (exercises 5-6, steps 4-5), Open Graph (exercise 7,
       step 6), the favicon (exercise 4, step 7) and alt text (exercise 8, step 8). The
       crawler, unfurl, visit and reader observers, `check.py`, the reference in
       `solutions/`, a runnable broken variant and a mutation test (23 planted bugs) all
       landed; the graded set is exercises 1-8.
       → [web-launch-checklist/README.md](web-launch-checklist/README.md)
5. [ ] **ml-systems framework part 2**: convolutions and a CNN, then a transformer trained on
       the framework. **Blocked in this environment:** the framework imports numpy, which is
       not installed (part 3 needs it too). → [ml-systems/framework/README.md](ml-systems/framework/README.md)
6. [ ] **Skill-tree nodes**, one at a time, from `tree.py next`. The tree now spans 113 nodes
       in 21 tracks across six domains and is lightly gamified (XP, levels, per-track/domain
       badges). The 15 new nodes (low level, distributed, cloud/AWS primitives) are built and
       audited — each a standard-library-only graded module with solutions, a checker and a
       mutation test. Only `lean-01-galois-path` remains and stays blocked (no
       `lake`/`lean`/`elan`). A sixth **Projects** domain now draws the open agent-evals work:
       each project node is blocked by an unmet `requires` (e.g. the simulated prod service) or
       an external `blocked_by` (GPU, prod traffic, human labels); project nodes are tracked on
       the map but earn no XP, so the level is unchanged. The page became a quiet daylight map
       (one typeface, hairlines, hatched dot = blocked).
       → [skill-tree/README.md](skill-tree/README.md)
7. [ ] **inference-lab CPU-real projects**: #4 prefix-caching proxy and #13 AI gateway are
       built and audited; #3 KV monitor remains.
       → [inference-lab/README.md](inference-lab/README.md)
8. [ ] **agent-evals next**: #1, #5, #7, #13 and #14 have a LEARN contract (SPEC + RESOURCES +
       stubbed interface + runnable tests, green with the core unwritten; #1 grades a
       trajectory by invariants, not a fixed path). The shared **simulated service** is built
       (BUILD: infrastructure) — a deterministic, stdlib-only double with synthetic traffic,
       injectable drift and a trace store — which unblocks #2 shadow routing, #9 drift monitor
       and #10 cost-quality Pareto. #2 is built ([shadow_routing/](agent-evals/shadow_routing/)):
       the primary stays byte-identical, the mirrored sample is deterministic, and the report
       keeps cost and quality apart. #9 is built ([drift_monitor/](agent-evals/drift_monitor/)):
       a planted drop is caught at its segment and localised to the tenant, while a seasonal
       traffic shift is not a false alarm. #10 is built ([pareto/](agent-evals/pareto/)): the
       cost-quality frontier per tenant from run records, dropping only dominated configs and
       keeping the trade-off, with a Wilson interval on the success. #4 is built
       ([ci_gate/](agent-evals/ci_gate/)): it blocks on deterministic regressions and on
       cost/latency medians, and only warns on the success rate, with its interval (the fix to
       the original 2 % brief). Red-team v2 (tool layer, loops) remains, after harness-lab
       phase 2.
       → [agent-evals/README.md](agent-evals/README.md)
9. [x] **database-from-scratch extension**: MVCC on top of the B+tree and durability for
       MVCC versions in the WAL — both lands (steps 18-19, audited). The engine's remaining
       limits are in the module README §Limits.
       → [database-from-scratch/README.md](database-from-scratch/README.md)
10. [ ] **web-launch-checklist exercises 9 and 16** and the `mobile.py` observer.
        Exercises 1-8 and 10-15 are now graded (loading states, check step 9, with
        `impatient.py`; error messages, check step 10, with `fetch`/`post_form`; cookies
        and consent, check step 11, with `post_form_headers`; analytics, check step 12,
        against `analytics.py`; contact methods, check step 13: the message is stored,
        retrievable and confirmed, with a hidden honeypot and a per-IP rate limit cutting
        spam); `mobile.py` (responsive, exercise 9) and WebP (exercise 16) remain, both
        needing a browser or Pillow.
        → [web-launch-checklist/README.md](web-launch-checklist/README.md)
11. [x] **RAG projects 2-8**: metadata-filtered retrieval, reranking, contextual chunking,
        SQL+vector, knowledge graph + vector, corrective RAG and Self-RAG are built and
        audited, each a graded module on the shared eval set; project 8 landed as
        [`rag-from-scratch/self-rag/`](rag-from-scratch/self-rag/README.md). Projects 9
        (multimodal, needs a vision model) and 10 (agentic, needs the harness loop) remain.
        → [rag-from-scratch/README.md](rag-from-scratch/README.md)
12. [ ] **Build your own Claude Code** (harness-lab): the capability-by-capability map is
        [`harness-lab/docs/claude-code-map.md`](harness-lab/docs/claude-code-map.md) — agent
        loop, LLM, tools, permissions, sessions, hooks, subagents, skills/commands/memory,
        MCP and plugins, each mapped to a subsystem and phase. The MCP server is already
        built ([`mcp-from-scratch/`](mcp-from-scratch/)); the next concrete step is phase 2
        (the seven-subsystem core). Baseline needs Docker + a budget cap.
        → [harness-lab/CLAUDE.md](harness-lab/CLAUDE.md)

## Gaps with no plan yet

- [x] Microservices, authentication protocols (sessions, JWT, OAuth), leader-follower
      replication with failover (from the 25 system-design concepts) — all three parts
      landed. `system-design/auth/` (sessions, HS256 JWTs, OAuth 2.0 authorization code +
      PKCE; 14 graded checks, 11 mutations caught), `system-design/replication/`
      (up-to-date rule, quorum commit, sync vs async, failover, epoch fencing; 10 graded
      checks, 8 mutations caught), `system-design/microservices/` (discovery with TTL
      heartbeats and draining, gateway routing / load balancing / safe retries, contract
      compatibility; 13 graded checks, 9 mutations caught).
      → [system-design/auth/README.md](system-design/auth/README.md),
        [system-design/replication/README.md](system-design/replication/README.md),
        [system-design/microservices/README.md](system-design/microservices/README.md)
- [ ] CS249r gaps: data selection, network fabrics, responsible and sustainable AI.
- [ ] A checker for `lean-proofs/` (`lake build`, no `sorry`).

## Splitting the work across models

The rule: **put the strongest (most expensive) model where an error would not be caught by
a test, and cheaper models where a verifier catches it.**

| Work | Who |
|---|---|
| Specs, plans, ADRs, design decisions | strongest model |
| Designing a module's `check.py` and its planted bugs (`_build/mutations.py`) | strongest model |
| Reviewing other models' output (sampled) | strongest model |
| Implementing solutions against an existing, mutation-tested checker (skill-tree nodes, observers, templates) | cheaper models |
| Triage of link dumps with the `repo-intake` skill | cheaper models, spot-checked |
| The core the learner must write in LEARN mode | the learner |
| Tutoring: questions, not answers; reviewing the learner's code | strongest model |

Do not assume the split; measure it. harness-lab phase 1 runs the same agent on the same
tasks with each model. With 20 tasks, success rates will rarely be distinguishable (see
[ADR 0004](harness-lab/docs/adr/0004-statistics.md)); cost per solved task (tokens, turns,
euros) will be, and that is the number that decides the split.

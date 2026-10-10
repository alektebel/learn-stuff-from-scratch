# Building your own Claude Code, from scratch — capability map

Goal: build a coding-agent harness of your own, from scratch, that covers the same
capabilities Claude Code ships. This file is the checklist that turns "build my own Claude
Code" into work that already has a home. It maps each capability to the subsystem it belongs
to in [harness-lab](../README.md) and the phase that builds it, says what the mechanism
actually is and where it hurts, and records the build status.

Why not a new directory: `harness-lab/` **is** this project. Its seven subsystems are the
subsystems of the source taxonomy, and `docs/phase*.md` build them in order. A second
"claude-code-from-scratch" tree would plan the same thing twice (see the repo's intake rule).
The MCP **server** side is the one piece built elsewhere, in
[`mcp-from-scratch/`](../../mcp-from-scratch/).

How to read this: the Claude Code mechanics are restated from public documentation, cited at
the bottom; `[v]` = confident, `[verify]` = written from memory, confirm the details. Nothing
of Claude Code's code is read or copied (harness-lab/CLAUDE.md: paper and public docs only).
The drawbacks column is the part a marketing page omits.

## The map

| Capability | What it does / how it works | Main drawbacks | harness-lab home | Phase | Status |
|---|---|---|---|---|---|
| **Agent loop** | The `while` loop: model turn → tool call → result → repeat, until a stop reason. The base every other row sits on. | Unpruned history grows until it overflows; loops that repeat the same call; one slow tool stalls the turn. | `core/loop.py` (`run_loop`) | 1 | **Contract + transport landed, core is yours (LEARN)** |
| **LLM integration** | Provider transport behind one interface: wire formats, auth, streaming, token/cost accounting. | Provider drift; streaming complicates the loop; a second provider is a second code path; prompt-cache misses cost. | `llm/` | 1 | **Transport implemented** (`openai_compat.py`), scripted backend for tests |
| **Built-in tools** | Declared tool schemas the model calls: read, write, edit, run commands, search (grep/glob), web. `edit` is exact-string replacement. | Injection (file/web content steers the model); Bash does anything you can; large outputs flood the context; duplicate-match edits fail. | `tools/` (bash, read, edit, write, search, glob) | 2 | Planned |
| **Permissions** | allow / ask / deny rules per tool and argument pattern, from settings files; the model has no authority, the harness gates. | Shell pattern matching is bypassable (metacharacters, aliases, `&&`); allowlists broaden over time; "ask" prompts cause fatigue. | `safety/` | 2 | Planned |
| **Sessions** | Persist the transcript; resume, continue or fork a session. `memory/` also compacts context. | Compaction loses facts (needs provenance); forked sessions diverge; context rots; a session is not durable memory. | `memory/` + session-tree variants | 2, 4 | Planned |
| **Hooks** | Shell commands at lifecycle events (pre/post tool, prompt submit, stop, session start), configured in settings; JSON on stdin, exit code blocks. | Run with your full privileges, unsandboxed; silently change behavior; ordering/debugging is opaque; platform shell differences. | `ext/` (hooks) | 5 | Planned |
| **Subagents** | Separate agent instances with an isolated context window, own tools/model, invoked as a task; return a summary. | Parent sees only the summary (detail is lost); duplicated exploration cost; hard to observe/coordinate. | `orchestration/` | 5 | Planned |
| **Skills, commands, memory** | Skills: `SKILL.md` with a short description loaded always and a body loaded on demand. Commands: slash-command markdown prompts. Memory: `CLAUDE.md` files auto-loaded (project + user). | Skill triggering depends on description quality (misses and misfires); memory files grow and eat context; project vs user conflicts. | `ext/` (skills) + `memory/` | 5, 7 | Planned (this repo already *uses* `.claude/skills/`) |
| **MCP** | Open protocol for external tools/data: JSON-RPC 2.0, stdio and streamable-HTTP transports, servers expose tools/resources/prompts, the client lists and calls them. | Each server is a trust boundary (supply chain); injection via tool descriptions; schema/version drift; early revisions have no built-in auth. | `ext/` client + [`mcp-from-scratch/`](../../mcp-from-scratch/) server | 5 | **Server reference built** (18/18 + 12 mutations); client planned |
| **Plugins** | Package skills, agents, hooks and MCP servers; install by path or marketplace. | Supply chain; version compatibility; no isolation; a plugin is code you now run. | variant registry + config (`harness.toml`) | 3+ | Planned |

The order is harness-lab's phases, not Claude Code's: **1** minimal loop → **2** the seven
subsystems (tools, permissions, basic compaction) → **3** loop/control variants (including a
`claude_code` variant: partition calls into concurrency-safe batches) → **4** context and
editing variants (session trees, compaction, prompt cache) → **5** safety, orchestration and
extensibility (hooks, skills, MCP client, subagents) → **6** the comparative experiment →
**7** dynamic memory.

## Cross-cutting drawbacks (the honest list)

- **Prompt injection is the root risk.** Every capability that feeds text into the model —
  tool output, web pages, MCP tool descriptions, skill files, memory — is an input channel. No
  single feature fixes it; the mitigations (permissions, sandboxing, human approval, showing
  diffs) each trade safety for friction.
- **Context is finite and expensive.** Tools, memory, skills and compaction all compete for the
  same window; every "load this always" feature is a tax on every turn.
- **Nondeterminism.** The loop is stochastic, so tests use a recorded/scripted model and only
  the evaluation spends money and time (harness-lab amendment 5).
- **Trust grows quietly.** Allowlists, installed plugins/MCP servers and accumulated memory all
  widen the blast radius over months; none of them shrinks on its own.

## What "building it" means here

1. `harness-lab/` is the project; its `CLAUDE.md` is the contract and its phases are the order.
   This map is the Claude-Code-shaped view of the same phases.
2. Mode: **LEARN** — the agent writes specs, tests and infrastructure; **you write the core**
   (`run_loop`, each subsystem's mechanism). Flip a piece to `BUILD` explicitly to have it
   written for you.
3. The baseline run needs **Docker** (sandbox) and a model endpoint (the transport is done);
   see `docs/phase1.md` and [TODO.md](../../TODO.md).
4. `mcp-from-scratch/` already has the server side with a grader; the harness only needs the
   MCP **client**.

## Sources (public documentation, restated)

- Claude Code docs: tools, settings (hooks, permissions), subagents, MCP, sessions, skills,
  slash commands, memory, plugins. `[verify]` exact URLs and event/field names against
  <https://docs.claude.com/en/docs/claude-code>.
- In-repo: `harness-lab/CLAUDE.md` (the seven subsystems and phases),
  `docs/phase1.md`, `docs/variants/README.md`, `harness-lab/RESOURCES.md`, and
  `mcp-from-scratch/SPEC.md`.

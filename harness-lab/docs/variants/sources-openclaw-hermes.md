# Source map: OpenClaw and Hermes Agent

First-pass reading of both codebases, to anchor the `openclaw` and `hermes` variant cards in
code instead of the paper's description. Every claim below cites a file at a pinned commit.
"Exists" means the file was located and its header read; "read" means the logic was read.

| Repo | Commit read | Size (no .git) | Language |
|---|---|---|---|
| github.com/NousResearch/hermes-agent | `9b38eb14` (2026-10-06) | 245 MB | Python core, TS/Electron UIs |
| github.com/openclaw/openclaw | `7ac5dbad` (2026-10-07) | 744 MB | TypeScript (pnpm monorepo) |

Clone (read-only, shallow): `GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 <url>`.

## What each one is

**Hermes** (`AGENTS.md`): one agent core shared by a CLI, a messaging gateway (~20 platforms),
a TUI and a desktop app; learns across sessions through memory and skills; delegates to
subagents; runs scheduled jobs. Entry points: `run_agent.py` (facade), `agent/turn_*.py`
(the turn loop split by phase), `model_tools.py` (tool dispatch), `hermes_state*.py` (SQLite
session store), `gateway/`, `plugins/`.

**OpenClaw** (`VISION.md`): a personal/team assistant running on the user's devices and
messaging channels; renamed Warelay → Clawdbot → Moltbot → OpenClaw. A Gateway process hosts
agents; the loop lives in `packages/agent-core`; capability lives in ~100+ `extensions/`
(providers, channels, memory backends). Its TUI depends on `@earendil-works/pi-tui`.

## The design invariant both share

Both state the same rule in their root `AGENTS.md`: **the prompt-cache prefix is sacred; only
compaction may rewrite history.** Hermes: "Mutating past context, swapping toolsets, reloading
memories or rebuilding the system prompt mid-conversation breaks the cached prefix … the ONE
exception is context compression." OpenClaw: "Rebuilding past context defeats prompt-prefix
reuse … only compaction rewrites history."

Consequence for harness-lab phase 7: a memory system that edits the system prompt or past turns
when a fact is corrected pays a full cache miss every time. Corrections have to enter as *new*
context (appended) or wait for the next compaction. This constrains 7b's design and should be
measured (cache-hit rate is already in the run record).

## Hermes — mechanisms named in CLAUDE.md, checked

| Mechanism | Status | Where |
|---|---|---|
| Iteration budget | read | `agent/iteration_budget.py`: thread-safe consume/refund counter per agent; parent default `max_iterations` 500, each subagent `delegation.max_iterations` 50, so parent + subagents can exceed the parent's cap |
| Verify-on-stop guard | read | `agent/verification_stop.py` (`build_verify_on_stop_nudge`): policy only, never runs checks; if the model stops after editing code paths without a fresh passing verification, it injects a synthetic follow-up naming up to 3 verify commands; at most `max_attempts=2` nudges; prose-only edits are exempt. Wired in `agent/turn_stop_gates.py`, which keeps the candidate answer as a fallback if the budget runs out |
| Lineage compaction | read | `hermes_state_compression.py`: compaction ends the session with `end_reason='compression'` and publishes a child row with `parent_session_id` (`publish_compression_child`); orphaned children can reopen the parent |
| Context compression | exists | `agent/context_compressor.py` (5,947 lines): a cheaper auxiliary model summarises middle turns, head and tail protected, tool outputs pruned first |
| Deferred tools, BM25 | exists | `tools/tool_search_catalog.py`: BM25 over deferrable tool definitions plus a byte-stable catalog listing (byte-stable = cache-safe) |
| Memory providers | exists | `agent/memory_manager.py`, `agent/memory_provider.py`: built-in provider always on, at most ONE external plugin provider (`plugins/memory/<name>/`); lifecycle initialize → per-turn prefetch/sync → shutdown |
| Fuzzy edit cascade | not checked | — |
| MCP server | exists | `mcp_serve.py`: stdio server exposing conversations as MCP tools; says it mirrors OpenClaw's 9-tool channel bridge |

## OpenClaw — mechanisms, checked

| Mechanism | Status | Where |
|---|---|---|
| Active memory | read (partly) | `extensions/active-memory/`: recall *before* the agent replies; cheap retrieval first, escalation to a recall agent only for questions about the past when retrieval is insufficient (`escalation.ts`, decisions `recall` / `mode-off` / `strong-lane-one-hit` / `no-recall-intent`). Trigger recall threshold 0.65, "measured on a 20-trigger/50-unrelated synthetic corpus" (`trigger-recall.ts`) |
| Agent loop | exists | `packages/agent-core/src/agent-loop.ts` (`runAgentLoop`, `runAgentLoopContinue`, 1,447 lines) |
| Steering (messages arriving mid-turn) | exists | `agent-loop-steering.ts`, `stream-steering.ts`; tools can be skipped "to process an incoming message" |
| Tool batch admission | exists | `tool-batch-admission.ts`: whole-batch admission of validated calls in assistant order; repeated rejected arguments count as a tool loop |
| Turn taint | exists | `turn-taint.ts` (not read) |
| Compaction | exists | `packages/agent-core/src/harness/compaction/`: `compaction.ts`, `branch-summarization.ts`, and a `compaction-provenance.test.ts`, directly relevant to amendment 4 |
| Memory backends | exists | `extensions/memory-core`, `memory-lancedb`, `memory-wiki`; state in SQLite by rule |

## Open questions for the next reading pass
1. OpenClaw active memory: where is the recalled text injected (system prompt, user turn,
   tool result)? Given the cache invariant, it should not be the system prompt.
2. What does `compaction-provenance` record, and is it enough to propagate a hard delete?
3. Hermes `context_compressor.py`: what is "iterative summaries" exactly: summary of
   summary, or anchored incremental like opencode?
4. Is OpenClaw's `agent-core` derived from pi's agent loop? The TUI dependency suggests the
   lineage; the loop's own headers do not say. Unverified.

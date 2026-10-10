# RESOURCES — harness-lab phase 1 (minimum floor)

How to read this list: each entry says why it matters for THIS phase and is
restated in our own words (cite and restate, never copy). `[v]` = confident it
exists as cited; `[verify]` = written from memory, confirm the details later.

## The minimal loop

1. Yang et al., "SWE-agent: Agent–Computer Interfaces Enable Automated
   Software Engineering", NeurIPS 2024. `[v]`
   Why: the argument that a *simple* loop plus a well-designed interface beats
   a complex one; the bash/ACI design is what phase 1 strips to one tool.
   Restated: most of an agent's ability comes from what it can see and do, not
   from a clever control flow.

2. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models",
   ICLR 2023. `[v]`
   Why: the origin of the interleaved thought → action → observation loop that
   `run_loop` implements (without parsing the "thought" part).
   Restated: let the model reason in text, act, read the result, and repeat;
   the alternation is the agent.

3. `SWE-agent/mini-swe-agent` (public repository). `[verify]`
   Why: the ~100-line bash-only baseline phase 1 imitates; useful to compare
   our accounting fields and stop reasons against a real minimal agent.
   Restated: a usable coding agent can be a short `while` loop and one shell
   tool; everything else is measurable overhead.

4. Anthropic, "Building effective agents" (engineering post, 2024). `[v]`
   Why: the case for starting with the simplest loop and adding mechanism only
   against a measured need — the reason phase 1 exists before the seven
   subsystems.
   Restated: prefer the least agentic design that solves the task; add
   machinery when data, not intuition, asks for it.

## Tool calling as a wire format

5. OpenAI, "Function calling" guide (platform docs). `[v]`
   Why: the `tool_calls` / JSON-string `arguments` shape our `Message`/`ToolCall`
   mirror, and where `tool_call_id` round-trips from.
   Restated: the model returns a name plus a JSON string of arguments; you run
   it and send the result back tagged with the same call id.

6. Anthropic, "Tool use" (Messages API docs). `[v]`
   Why: the same idea with a different wire format (tool_result blocks in user
   turns) — the translation our provider-neutral message type absorbs.
   Restated: tools are declared once, the model asks for one, and the result
   goes back as content, not as a separate protocol message.

## Deterministic tests for a stochastic system

7. In-repo: `harness-lab/docs/adr/0005-controls-and-scripted-model.md` and
   `docs/phase0.md` §5. `[v]`
   Why: the amendments this phase implements — `null`/`oracle` brackets, and
   "deterministic tests, paid evaluation" (the scripted backend).
   Restated: a test that needs a live model is not a test; record the responses
   once and replay them.

8. In-repo: `harness-lab/eval/contract.py` and `eval/agents.py`. `[v]`
   Why: the exact `stop_reason` strings and record fields the loop must
   produce, and the `Agent` protocol `MiniAgent` adapts to.
   Restated: the agent reports what only it can see (turns, tokens, cost, why
   it stopped); the runner measures wall time and success.

## The benchmark

9. Jimenez et al., "SWE-bench: Can Language Models Resolve Real-World GitHub
   Issues?", ICLR 2024. `[v]`
   Why: the benchmark phase 6 extends to with 50 Verified instances; phase 1
   measures only the 20-task in-repo suite, but the record schema is the same.
   Restated: grade on hidden tests against the real repository state, never on
   a diff comparison.

10. In-repo: `harness-lab/eval/tasks/README.md` (the 20 tasks). `[v]`
    Why: the tasks the phase 1 baseline runs on, including the limit tasks
    (`t19-huge-log` for context overflow) that motivate phase 2.
    Restated: each mechanism a later variant adds needs at least one task built
    to trigger it, or its null result means nothing (amendment 2).

## Background (unread here)

11. "Harness Engineering: Anatomy, Architecture, and Evolution of Coding
    Agents" (arXiv 2609.00006), cited in `harness-lab/CLAUDE.md` as the source
    of the seven subsystems. `[verify]`
    Why: the taxonomy later phases follow; not needed for the phase 1 loop.
    Restated (as cited by the repo, not verified): coding agents can be read as
    seven subsystems, and harnesses differ mostly in a swappable mechanism
    each.

## Claude Code capabilities (for `docs/claude-code-map.md`)

The public documentation behind the capability map. Read the page, not a summary;
`[verify]` the exact URLs against <https://docs.claude.com/en/docs/claude-code>.

- **Tools reference** — the built-in tool set and each schema.
- **Settings** — `hooks` (lifecycle events) and `permissions` (`allow`/`ask`/`deny`
  patterns), and the project/user/enterprise precedence.
- **Subagents** — isolated context, the task tool, per-agent tools and model.
- **MCP** — transports, servers, and tools / resources / prompts.
- **Sessions / CLI reference** — `--continue`, `--resume`, `--fork-session`, `/compact`.
- **Skills and slash commands** — `SKILL.md` progressive disclosure; `.claude/commands/`.
- **Memory** — `CLAUDE.md` project and user files, and imports.
- **Plugins** — packaging skills, agents, hooks and MCP servers, and installing by path.

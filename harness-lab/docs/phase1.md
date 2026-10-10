# Phase 1 — Minimum floor (Mini-SWE-Agent style)

Status: **spec, tests and the provider transport shipped; the core is the
learner's work and the baseline run still needs Docker (no daemon here) and a
budget cap.** The model endpoint is configured; `harness_lab/llm/openai_compat.py`
is the one real transport. This file is the contract; `tests/test_llm.py`,
`tests/test_openai_transport.py` and `tests/test_loop.py` make it executable.

## What it is

The smallest agent that can still solve a task: a linear `while` loop, a
single `bash` tool, unpruned history, and step/token/cost accounting that ends
in a `stop_reason`. It is deliberately *not* the seven-subsystem core of phase
2 — the point is a baseline whose cost and turn counts are measured, so later
subsystems have something to beat.

## What is shipped, and what the learner writes (LEARN mode)

Shipped as infrastructure (data types and a test double — no agent logic):

- `harness_lab/llm/messages.py` — `Message`, `ToolCall`, roles.
- `harness_lab/llm/base.py` — `ToolSpec`, `Usage`, `Completion`, `Price`,
  `Model` protocol, `ModelError`.
- `harness_lab/llm/scripted.py` — `ScriptedBackend`, the deterministic
  recording player (amendment 5).
- `eval/agents.py` — `MiniAgent`, the adapter the runner sees; its transport
  factory `build_model()` reads the environment and returns the transport.
- `harness_lab/llm/openai_compat.py` — `OpenAICompatibleModel`, the real
  OpenAI-compatible transport (messages/tools to the wire and back), testable
  with an injected `http_post`.

The learner writes (the central logic):

- `harness_lab/core/loop.py::run_loop` — currently `NotImplementedError`.
  `LoopBudget`, `LoopResult`, `BASH_TOOL`, `SYSTEM_PROMPT` and the structural
  `Sandbox`/`ExecResult` protocols are provided; the loop body is not.

## What it demonstrates

1. **The loop is the datum.** Success/turns/tokens/cost are only comparable
   across later variants if this floor is measured on the same 20-task suite
   against the `null`/`oracle` brackets from phase 0 (ADR 0005).
2. **Deterministic tests, paid evaluation** (amendment 5): every test here runs
   against a scripted tape; only `eval/` spends money.
3. **Stop reasons are a contract, not an afterthought.** The loop must map "out
   of steps", "out of budget", "provider failed" and "answered" to the exact
   strings `eval/contract.py` validates, or records are rejected.

## The interface

```python
# harness_lab/llm/messages.py
Message(role, content="", tool_calls=(), tool_call_id=None, name=None)
ToolCall(id, name, arguments="{}")          # arguments stays a JSON string

# harness_lab/llm/base.py
ToolSpec(name, description, parameters)      # JSON-schema function definition
Usage(input_tokens=0, output_tokens=0, cached_tokens=0)
Completion(message, usage=Usage(), stop_reason="stop")  # message is role="assistant"
Price(input_per_mtok=0.0, output_per_mtok=0.0, cached_input_per_mtok=0.0).cost(usage)

class Model(Protocol):
    name: str
    price: Price
    def complete(messages, tools=()) -> Completion: ...

# harness_lab/llm/scripted.py
ScriptedBackend(script, *, name="scripted", price=None)
    .complete(messages, tools=())   # pops the next Completion, records the request
    .requests, .exhausted            # (history, tools) per call; tape done?
ScriptExhausted(ModelError)          # tape ran out mid-run

# harness_lab/core/loop.py  — the learner implements the body
run_loop(model, statement, sandbox, budget=LoopBudget(), *,
         user_turns=(), system_prompt=SYSTEM_PROMPT) -> LoopResult
LoopBudget(max_steps=50, max_cost_eur=1.0)
LoopResult(stop_reason, turns, input_tokens, output_tokens, cached_tokens,
           cost_eur, tool_calls, error, extra)
BASH_TOOL                            # the one tool, advertised every step

# eval/agents.py
MiniAgent(model_factory=None)        # maps LoopResult -> eval AgentResult
build_model()                        # transport from HARNESS_LAB_* env vars

# harness_lab/llm/openai_compat.py
OpenAICompatibleModel(base_url, api_key, model, price=Price(), http_post=None)
    .complete(messages, tools=())    # POSTs /chat/completions, maps errors to ModelError
```

**The loop, exactly** (what `tests/test_loop.py` pins):

1. initial history `[system(system_prompt), *user(t) for t in user_turns,
   user(statement)]`;
2. before each step: `turns >= max_steps` → `"max_steps"`; `cost_eur >=
   max_cost_eur` → `"max_cost"`;
3. `completion = model.complete(history, [BASH_TOOL])`; append its assistant
   message; add `usage` and `price.cost(usage)`; `turns += 1`;
4. no tool calls → `"completed"`; otherwise, for each call, decode
   `arguments` as JSON, run `arguments["command"]` through `sandbox.exec`,
   append a `role="tool"` message carrying the same `id`, and `tool_calls += 1`;
5. a `ModelError` from `complete` → `"model_error"` with `error` set; any other
   exception propagates (the runner records a crash);
6. history is never pruned or truncated: every request is a prefix of the next.

## Acceptance

Every core item is an `xfail(raises=NotImplementedError)` today and must pass
once the loop is written; a wrong loop fails hard. Infrastructure items pass
today.

| # | Requirement | Tests |
|---|---|---|
| 1 | Message roles and per-role invariants (`tool` needs `tool_call_id`, `tool_calls` only on `assistant`) | `test_llm.py::test_message_accepts_every_role`, `test_unknown_role_rejected`, `test_tool_message_requires_tool_call_id`, `test_tool_calls_only_on_assistant` |
| 2 | `Usage` rejects negative/inconsistent counts; a `Completion`'s message is `assistant` | `test_usage_rejects_negative_and_inconsistent_counts`, `test_completion_message_must_be_assistant` |
| 3 | `Price.cost` charges fresh, cached and output tokens at their own rates | `test_price_charges_fresh_cached_and_output_separately` |
| 4 | Scripted backend replays in order, records `(history, tools)`, raises `ScriptExhausted` at the end, is deterministic across instances | `test_scripted_replays_in_order_and_exposes_price`, `test_scripted_records_the_history_and_tools_it_was_given`, `test_scripted_exhaustion_is_a_model_error`, `test_scripted_backend_is_deterministic` |
| 5 | One tool call then a final answer → `completed`, one command run | `test_loop_completes_after_a_tool_call` |
| 6 | Step and cost caps → `max_steps` / `max_cost` at the exact boundary | `test_loop_stops_at_max_steps`, `test_loop_stops_at_max_cost` |
| 7 | Token totals sum every completion | `test_loop_reports_token_totals` |
| 8 | An exhausted tape → `model_error` with a non-empty `error` | `test_loop_reports_model_error_when_script_exhausts` |
| 9 | History is append-only and the tool output reaches the model | `test_loop_history_is_unpruned` |
| 10 | `mini` is registered and maps a `LoopResult` to an `AgentResult` | `test_mini_agent_is_registered`, `test_mini_agent_maps_the_loop_result_to_an_agent_result` |

## Limit cases

- **L1 — unparseable tool arguments.** `arguments="{not json"` must not crash
  the run and must execute nothing; the model gets a message it can recover
  from. Test `test_loop_malformed_tool_arguments_do_not_crash`.
- **L2 — tape shorter than the run.** Reaching the end of the script mid-run is
  a `model_error`, never a silent stop. Test
  `test_loop_reports_model_error_when_script_exhausts`.
- **L3 — exact step boundary.** `max_steps=2` allows exactly two model calls;
  the third is refused before it is paid for. Test
  `test_loop_stops_at_max_steps`.
- **L4 — exact cost boundary.** Cost at or above the cap stops before the next
  step; the completion already paid for is not un-run. Test
  `test_loop_stops_at_max_cost`.
- **L5 — append-only history.** The second request is the first plus this
  step's assistant and tool messages, in that order. Test
  `test_loop_history_is_unpruned`.

## Out of scope / blocked

- **The baseline run needs Docker.** The provider transport and the model
  endpoint are in place (`build_model()` + `openai_compat.py`, verified with one
  live call), but running the 20-task suite needs the sandbox image and a
  daemon, which this environment does not have; `BUDGET` is also still unset in
  `harness-lab/CLAUDE.md`.
- **One transport only.** Phase 1 needs one provider behind `Model`; a second
  provider, streaming, retries and prompt caching are phase 2+.
- **No context management.** History is unpruned on purpose; compaction is
  phase 2 (and must carry provenance, amendment 4). The >context-window task
  `t19-huge-log` exists to expose exactly this limit.
- **No safety policy.** Every command goes through the Docker sandbox; an
  allow/ask/deny policy is phase 2.
- **No real sandbox in these tests.** The unit tests use a structural
  `FakeSandbox`; DockerSandbox is exercised by the runner's Docker-marked
  tests, which skip without a daemon.

## How to run

```sh
cd harness-lab
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q tests/test_llm.py tests/test_loop.py
# today: infrastructure passes, the eight core tests xfail
# (raises=NotImplementedError); zero failures/errors expected.
.venv/bin/python -m pytest -q        # whole suite, Docker tests skip without a daemon
```

## Design decisions

- **Messages are data, not logic**; the loop owns how they grow. Cost: the
  loop has to validate decoded arguments itself instead of trusting a dict.
- **Tool results are `role="tool"` messages**, not a side channel: one
  append-only list, translated per transport. Cost: an Anthropic-style
  transport folds them into `user` turns.
- **`Model.complete` is synchronous and non-streaming**: phase 1 has no UI.
  Cost: a slow provider holds the whole run.
- **The core does not import `eval`.** `LoopBudget`/`LoopResult`/`Sandbox` are
  the core's own; `MiniAgent` is the only mapping. Cost: one small adapter.
- **Cost lives in `Price.cost`, shipped** (non-didactic arithmetic); the loop
  only accumulates. Cost: the price table is a configuration input that must
  be set for a real run.
- **The scripted backend is infrastructure**, per amendment 5 and LEARN mode.
  Cost: the recording format (a list of `Completion`) is fixed by it; a richer
  tape (multi-provider, streaming fragments) would need a new player.
- **`xfail(raises=NotImplementedError)` marks the learner's surface**: the
  suite states honestly what exists. Cost: an implementation that raises
  `NotImplementedError` by accident would keep a test xfailed instead of red.

"""Phase 1 core: the linear agent loop.

BUILD (owner-authorised for this one piece). The loop is implemented here; the
contract is docs/phase1.md and the tests in tests/test_loop.py define it
precisely. It was a LEARN stub until the owner flipped this piece to BUILD.

Contract, in one line per bullet (docs/phase1.md has the reasoning):

- initial history: `[system, *user(user_turns), user(statement)]`;
- each step: `completion = model.complete(history, [BASH_TOOL])`, append its
  assistant message, add its usage and cost, count one turn;
- no tool calls in the assistant message  -> stop_reason "completed";
- tool calls -> for each, decode `arguments` as JSON, run `["command"]`
  through `sandbox.exec`, append a `role="tool"` message, count the call;
- before each step, `turns >= max_steps` -> "max_steps" and
  `cost_eur >= max_cost_eur` -> "max_cost";
- a `ModelError` from `complete` -> "model_error" with `error` set; any other
  exception is a bug and propagates (`eval` records it as a crash);
- history is never pruned or truncated: every request is a prefix of the next.

DESIGN DECISION — the core does not import `eval`. `eval/contract.py` is the
runner's narrow view of an agent; the core has its own `LoopBudget`,
`LoopResult` and a structural `Sandbox`, and `eval/agents.py` adapts between
them. Cost: one small mapping in the adapter. Benefit: the core's design can
change without touching the runner.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from harness_lab.llm.base import Model, ModelError, ToolSpec
from harness_lab.llm.messages import Message

BASH_TOOL = ToolSpec(
    name="bash",
    description="Run a shell command in the task's /work directory.",
    parameters={
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
)

SYSTEM_PROMPT = (
    "You are a coding agent working in the repository at /work. Use the bash "
    "tool to inspect and change files. Run the tests you can find. When the "
    "task is done, reply with a one-line summary and make no tool call."
)


@dataclass(frozen=True)
class LoopBudget:
    max_steps: int = 50
    max_cost_eur: float = 1.0


@dataclass
class LoopResult:
    stop_reason: str
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_eur: float = 0.0
    tool_calls: int = 0
    error: str | None = None
    extra: dict = field(default_factory=dict)


class ExecResult(Protocol):
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


class Sandbox(Protocol):
    def exec(self, command: str, timeout: float = 120.0) -> ExecResult: ...


def _decode_command(arguments: str) -> str | None:
    """The `command` from a bash tool call, or None if the arguments are unusable.

    A model can emit malformed or wrongly-shaped arguments; that must end the
    single call, not the whole run (test_loop_malformed_tool_arguments_...).
    """
    try:
        payload = json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    command = payload.get("command")
    return command if isinstance(command, str) and command else None


def _tool_output(result: ExecResult) -> str:
    """The tool message body: the command's streams, with a status prefix."""
    body = f"{result.stdout}{result.stderr}"
    if result.timed_out:
        return "[command timed out]\n" + body
    if result.exit_code != 0:
        return f"[exit code {result.exit_code}]\n" + body
    return body


def run_loop(
    model: Model,
    statement: str,
    sandbox: Sandbox,
    budget: LoopBudget = LoopBudget(),
    *,
    user_turns: Sequence[str] = (),
    system_prompt: str = SYSTEM_PROMPT,
) -> LoopResult:
    """Run the linear loop until it stops; see the module docstring."""
    history: list[Message] = [Message(role="system", content=system_prompt)]
    history += [Message(role="user", content=turn) for turn in user_turns]
    history.append(Message(role="user", content=statement))
    result = LoopResult(stop_reason="completed")
    while True:
        if result.turns >= budget.max_steps:
            result.stop_reason = "max_steps"
            break
        if result.cost_eur >= budget.max_cost_eur:
            result.stop_reason = "max_cost"
            break
        try:
            completion = model.complete(history, [BASH_TOOL])
        except ModelError as exc:
            result.stop_reason = "model_error"
            result.error = str(exc) or type(exc).__name__
            break
        usage = completion.usage
        result.turns += 1
        result.input_tokens += usage.input_tokens
        result.output_tokens += usage.output_tokens
        result.cached_tokens += usage.cached_tokens
        result.cost_eur += model.price.cost(usage)
        history.append(completion.message)
        if not completion.message.tool_calls:
            break
        for call in completion.message.tool_calls:
            result.tool_calls += 1
            command = _decode_command(call.arguments)
            if command is None:
                content = "[error] tool arguments were not a JSON object with a 'command'"
            else:
                content = _tool_output(sandbox.exec(command))
            history.append(
                Message(role="tool", content=content, tool_call_id=call.id, name=call.name)
            )
    return result

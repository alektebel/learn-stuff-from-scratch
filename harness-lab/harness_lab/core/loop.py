"""Phase 1 core: the linear agent loop. LEARN mode — the learner implements this.

This file ships as a stub plus the types the loop returns. The contract is in
docs/phase1.md; the tests in tests/test_loop.py define it precisely. Nothing
else in phase 1 depends on the loop's internals, so it can be written from the
stub up.

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

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from harness_lab.llm.base import Model, ToolSpec
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
    raise NotImplementedError(
        "phase 1 core: the learner implements run_loop (see docs/phase1.md)"
    )

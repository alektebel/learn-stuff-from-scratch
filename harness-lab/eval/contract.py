"""The contract between the evaluation runner and any agent, and the run record.

This is deliberately *not* harness_lab.core. The core's interfaces are designed in
phases 1-2; eval only needs a narrow adapter: give an agent a task and a sandbox,
get back the numbers it is responsible for. Keeping it here means the runner never
changes when the core's design does.

Who measures what:
- the agent reports what only it can see: turns, tokens, cost, tool calls, why it stopped;
- the runner measures what the agent must not be trusted with: wall time and success.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from eval.sandbox import DockerSandbox

SCHEMA_VERSION = 1

# Why a run ended. Agents pick one; the runner may override with wall_timeout/crash.
STOP_REASONS = {
    "completed",      # agent declared the task done
    "no_op",          # control agent that never acts
    "max_steps",      # step budget exhausted
    "max_cost",       # cost budget exhausted
    "max_tokens",     # token budget exhausted
    "stuck",          # a loop / stuck detector stopped it
    "model_error",    # provider error the agent could not recover from
    "wall_timeout",   # set by the runner: the agent process was killed
    "crash",          # set by the runner: the agent raised
}


@dataclass(frozen=True)
class TaskInput:
    """What an agent is allowed to know about a task. No ids, no paths, no tests."""

    statement: str
    user_turns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Budget:
    max_steps: int = 50
    max_cost_eur: float = 1.0
    wall_s: float = 900.0


@dataclass
class AgentResult:
    stop_reason: str
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # subset of input_tokens served from the provider's prompt cache
    cost_eur: float = 0.0
    tool_calls: int = 0
    error: str | None = None
    extra: dict = field(default_factory=dict)  # free-form, per-agent diagnostics


class Agent(Protocol):
    name: str

    def config(self) -> dict:
        """Everything that distinguishes this agent from another run of it: model,
        variant flags, prompts' hashes. Recorded verbatim in each run record."""
        ...

    def run(self, task: TaskInput, sandbox: DockerSandbox, budget: Budget, seed: int) -> AgentResult: ...


RECORD_FIELDS: dict[str, type | tuple[type, ...]] = {
    "schema_version": int,
    "run_id": str,
    "batch_id": str,
    "started_at": str,
    "git_sha": str,
    "agent": str,
    "agent_config": dict,
    "task_id": str,
    "task_category": str,
    "seed": int,
    "budget": dict,
    "success": bool,
    "verifier_exit": int,
    "verifier_tail": str,
    "stop_reason": str,
    "turns": int,
    "input_tokens": int,
    "output_tokens": int,
    "cached_tokens": int,
    "cost_eur": (int, float),
    "tool_calls": int,
    "wall_time_s": (int, float),
    "error": (str, type(None)),
    "extra": dict,
}


def validate_record(rec: dict) -> list[str]:
    """Return every problem with a run record; empty means valid."""
    problems = []
    missing = RECORD_FIELDS.keys() - rec.keys()
    unknown = rec.keys() - RECORD_FIELDS.keys()
    problems += [f"missing field {k}" for k in sorted(missing)]
    problems += [f"unknown field {k}" for k in sorted(unknown)]
    for key, typ in RECORD_FIELDS.items():
        if key not in rec:
            continue
        val = rec[key]
        # bool is a subclass of int: reject True where a count is expected
        if typ is int and isinstance(val, bool):
            problems.append(f"{key}: bool where int expected")
        elif not isinstance(val, typ):
            problems.append(f"{key}: {type(val).__name__} is not {typ}")
    if problems:
        return problems
    for key in ("turns", "input_tokens", "output_tokens", "cached_tokens", "tool_calls"):
        if rec[key] < 0:
            problems.append(f"{key} is negative")
    for key in ("cost_eur", "wall_time_s"):
        if rec[key] < 0 or math.isnan(rec[key]):
            problems.append(f"{key} is negative or NaN")
    if rec["cached_tokens"] > rec["input_tokens"]:
        problems.append("cached_tokens exceeds input_tokens")
    if rec["stop_reason"] not in STOP_REASONS:
        problems.append(f"unknown stop_reason {rec['stop_reason']!r}")
    if rec["schema_version"] != SCHEMA_VERSION:
        problems.append(f"schema_version {rec['schema_version']} != {SCHEMA_VERSION}")
    return problems

"""Control agents, the phase-1 `mini` adapter, and the registry the runner
builds agents from.

Two controls bracket every real result:
- `null` does nothing. Any success it gets means a verifier passes on the initial
  repo, i.e. the task measures nothing.
- `oracle` writes the reference solution through the sandbox. Any failure it gets
  means the hidden tests are unpassable or the sandbox write path is broken.
A real agent's success rate only means something between those two.

`mini` is the phase-1 real agent: the linear loop adapted to the runner's
contract. Its model transport is a stub until the model API is chosen.
"""

from __future__ import annotations

import os

from eval.contract import AgentResult, Budget, TaskInput
from eval.sandbox import DockerSandbox
from eval.tasks import Task


class NullAgent:
    name = "null"

    def config(self) -> dict:
        return {}

    def run(self, task: TaskInput, sandbox: DockerSandbox, budget: Budget, seed: int) -> AgentResult:
        return AgentResult(stop_reason="no_op")


class OracleAgent:
    """Privileged: built with the task itself, which no real agent ever sees."""

    name = "oracle"

    def __init__(self, task: Task):
        self._task = task

    def config(self) -> dict:
        return {}

    def run(self, task: TaskInput, sandbox: DockerSandbox, budget: Budget, seed: int) -> AgentResult:
        calls = 0
        sol = self._task.solution_dir
        for f in sorted(p for p in sol.rglob("*") if p.is_file()):
            sandbox.write_file(f"/work/{f.relative_to(sol).as_posix()}", f.read_bytes())
            calls += 1
        for rel in self._task.delete:
            res = sandbox.exec(f"rm -- /work/{rel}")
            if res.exit_code != 0:
                return AgentResult(stop_reason="crash", tool_calls=calls, error=res.stderr)
            calls += 1
        return AgentResult(stop_reason="completed", turns=1, tool_calls=calls)


def build_model():
    """The phase 1 model transport (docs/phase1.md): an OpenAI-compatible
    endpoint configured entirely from the environment.

    Required: ``HARNESS_LAB_BASE_URL``, ``HARNESS_LAB_API_KEY``,
    ``HARNESS_LAB_MODEL``. Optional: ``HARNESS_LAB_INPUT_EUR_PER_MTOK``,
    ``HARNESS_LAB_OUTPUT_EUR_PER_MTOK``, ``HARNESS_LAB_CACHED_EUR_PER_MTOK``
    (cost tracking defaults to zero). Tests never call this; they build
    ``MiniAgent(model_factory=...)`` with a scripted backend.
    """
    from harness_lab.llm.base import ModelError, Price
    from harness_lab.llm.openai_compat import OpenAICompatibleModel

    base_url = os.environ.get("HARNESS_LAB_BASE_URL")
    api_key = os.environ.get("HARNESS_LAB_API_KEY")
    model = os.environ.get("HARNESS_LAB_MODEL")
    missing = [
        name for name, value in (
            ("HARNESS_LAB_BASE_URL", base_url),
            ("HARNESS_LAB_API_KEY", api_key),
            ("HARNESS_LAB_MODEL", model),
        ) if not value
    ]
    if missing:
        raise ModelError(
            "missing environment for the model transport: " + ", ".join(missing))

    def per_mtok(name: str) -> float:
        try:
            return float(os.environ.get(name, "0"))
        except ValueError as exc:
            raise ModelError(f"{name} must be a number, got {os.environ[name]!r}") from exc

    price = Price(
        input_per_mtok=per_mtok("HARNESS_LAB_INPUT_EUR_PER_MTOK"),
        output_per_mtok=per_mtok("HARNESS_LAB_OUTPUT_EUR_PER_MTOK"),
        cached_input_per_mtok=per_mtok("HARNESS_LAB_CACHED_EUR_PER_MTOK"),
    )
    return OpenAICompatibleModel(
        base_url=base_url, api_key=api_key, model=model, price=price)


class MiniAgent:
    """Phase 1 baseline: the linear loop in `harness_lab.core.loop`, adapted to
    the runner's `Agent` contract. The core reports turns/tokens/cost/tool
    calls; the runner still owns wall time and success.
    """

    name = "mini"

    def __init__(self, model_factory=None):
        # A callable returning a `Model`, injected by tests. Production uses
        # build_model() from the environment.
        self._model_factory = model_factory

    def config(self) -> dict:
        return {"model": os.environ.get("HARNESS_LAB_MODEL", "<unset>")}

    def run(self, task: TaskInput, sandbox: DockerSandbox, budget: Budget, seed: int) -> AgentResult:
        from harness_lab.core.loop import LoopBudget, run_loop

        model = self._model_factory() if self._model_factory is not None else build_model()
        out = run_loop(
            model,
            task.statement,
            sandbox,
            LoopBudget(max_steps=budget.max_steps, max_cost_eur=budget.max_cost_eur),
            user_turns=task.user_turns,
        )
        return AgentResult(
            stop_reason=out.stop_reason,
            turns=out.turns,
            input_tokens=out.input_tokens,
            output_tokens=out.output_tokens,
            cached_tokens=out.cached_tokens,
            cost_eur=out.cost_eur,
            tool_calls=out.tool_calls,
            error=out.error,
            extra=dict(out.extra),
        )


def make_agent(name: str, task: Task):
    if name == "null":
        return NullAgent()
    if name == "oracle":
        return OracleAgent(task)
    if name == "mini":
        return MiniAgent()
    raise KeyError(f"unknown agent {name!r}; known: {', '.join(AGENT_NAMES)}")


AGENT_NAMES = ("null", "oracle", "mini")

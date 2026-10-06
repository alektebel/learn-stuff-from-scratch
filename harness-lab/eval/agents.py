"""Control agents and the registry the runner builds agents from.

Two controls bracket every real result:
- `null` does nothing. Any success it gets means a verifier passes on the initial
  repo, i.e. the task measures nothing.
- `oracle` writes the reference solution through the sandbox. Any failure it gets
  means the hidden tests are unpassable or the sandbox write path is broken.
A real agent's success rate only means something between those two.
"""

from __future__ import annotations


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


def make_agent(name: str, task: Task):
    if name == "null":
        return NullAgent()
    if name == "oracle":
        return OracleAgent(task)
    raise KeyError(f"unknown agent {name!r}; known: null, oracle")


AGENT_NAMES = ("null", "oracle")

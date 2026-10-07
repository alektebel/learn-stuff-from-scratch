"""Adversarial scenarios: a legitimate task plus an attack, and the checks that detect it.

A scenario lives in redteam/scenarios/<id>/:

    scenario.toml   statement, attack metadata, complicit commands, checks (schema below)
    repo/           initial /work, as in harness-lab tasks; the attack is usually planted here
    home/           optional: files placed in /home/agent (secrets, dotfiles)
    hidden/         tests for the *legitimate* task (success)
    solution/       safe reference solution of the legitimate task

    id = "r01-..."
    title = "..."
    attack = "injection-file"        # one of ATTACKS
    vector = "README.md"             # where the attack enters
    statement = "..."
    delete = ["build/x"]             # files the safe solution removes (harness-lab semantics)
    complicit = ["cmd", ...]         # what a fully obedient agent would run; drives the
                                     #   `complicit` control agent
    [[checks]]                       # each check returns violations; none means safe
    kind = "unchanged" | "no_leak" | "no_new_match"
    ...                              # per-kind fields, see redteam/detectors.py

Why every scenario carries a legitimate task: an agent that refuses to do anything is
perfectly safe and perfectly useless. Safety is only meaningful next to success.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from eval.tasks import Task

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
ATTACKS = {
    "injection-file",         # instruction planted in a file the agent will read
    "injection-tool-output",  # instruction planted in a command's output
    "injection-statement",    # instruction inside third-party text quoted in the request
    "scope-overreach",        # no injection: an ambiguous request invites destruction
}
CHECK_KINDS = {"unchanged", "no_leak", "no_new_match"}


@dataclass(frozen=True)
class Scenario:
    task: Task                 # the legitimate task, in harness-lab's format
    attack: str
    vector: str
    complicit: tuple[str, ...]
    checks: tuple[dict, ...]

    @property
    def id(self) -> str:
        return self.task.id

    @property
    def home_dir(self) -> Path | None:
        p = self.task.path / "home"
        return p if p.is_dir() else None


def load_scenario(path: Path) -> Scenario:
    data = tomllib.loads((path / "scenario.toml").read_text())
    task = Task(
        id=data["id"], title=data["title"], category="safety",
        targets=("safety", data["attack"]), statement=data["statement"].strip(),
        user_turns=tuple(data.get("user_turns", [])),
        verify_timeout_s=int(data.get("verify_timeout_s", 120)),
        delete=tuple(data.get("delete", [])), path=path,
    )
    sc = Scenario(task=task, attack=data["attack"], vector=data["vector"],
                  complicit=tuple(data["complicit"]), checks=tuple(data["checks"]))
    if sc.id != path.name:
        raise ValueError(f"{path}: id {sc.id!r} does not match directory")
    if sc.attack not in ATTACKS:
        raise ValueError(f"{path}: unknown attack {sc.attack!r}")
    if not sc.checks or any(c.get("kind") not in CHECK_KINDS for c in sc.checks):
        raise ValueError(f"{path}: needs at least one check, of kinds {sorted(CHECK_KINDS)}")
    if not sc.complicit:
        raise ValueError(f"{path}: a scenario without complicit commands cannot prove its checks fire")
    return sc


def load_scenarios(ids: list[str] | None = None) -> list[Scenario]:
    out = [load_scenario(p) for p in sorted(SCENARIOS_DIR.iterdir()) if (p / "scenario.toml").exists()]
    if ids:
        missing = set(ids) - {s.id for s in out}
        if missing:
            raise KeyError(f"unknown scenarios: {sorted(missing)}")
        out = [s for s in out if s.id in set(ids)]
    return out

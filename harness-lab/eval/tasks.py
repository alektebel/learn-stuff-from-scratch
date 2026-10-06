"""Task format and loading.

A task lives in eval/tasks/<id>/:

    task.toml        metadata and statement (schema below)
    repo/            initial state of the repository the agent works on
    generate.py      optional: `build(dest: Path)` adds generated files on top of repo/
                     (for repos too large to commit, e.g. the context-overflow task)
    hidden/          verifier tests; never copied into the agent's container
    solution/        reference solution, overlaid on the initial repo by the oracle
                     agent. Proves the hidden tests are passable.

task.toml:

    id = "t01-pagination"
    title = "..."
    category = "bugfix"            # one of CATEGORIES
    targets = ["baseline"]         # mechanisms this task is built to exercise
    statement = "..."              # the request the agent receives
    user_turns = ["...", "..."]    # optional: earlier user messages, in order, sent
                                   #   before the statement (long-session recall)
    verify_timeout_s = 120
    delete = ["old.py"]            # optional: files the reference solution removes
"""

from __future__ import annotations

import importlib.util
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
CATEGORIES = {"bugfix", "feature", "refactor", "multifile", "recall", "limit"}


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    category: str
    targets: tuple[str, ...]
    statement: str
    user_turns: tuple[str, ...]
    verify_timeout_s: int
    delete: tuple[str, ...]
    path: Path = field(compare=False)

    @property
    def repo_dir(self) -> Path:
        return self.path / "repo"

    @property
    def hidden_dir(self) -> Path:
        return self.path / "hidden"

    @property
    def solution_dir(self) -> Path:
        return self.path / "solution"

    @property
    def generator(self) -> Path | None:
        p = self.path / "generate.py"
        return p if p.exists() else None


def load_task(path: Path) -> Task:
    data = tomllib.loads((path / "task.toml").read_text())
    task = Task(
        id=data["id"],
        title=data["title"],
        category=data["category"],
        targets=tuple(data.get("targets", [])),
        statement=data["statement"].strip(),
        user_turns=tuple(t.strip() for t in data.get("user_turns", [])),
        verify_timeout_s=int(data.get("verify_timeout_s", 120)),
        delete=tuple(data.get("delete", [])),
        path=path,
    )
    if task.id != path.name:
        raise ValueError(f"{path}: id {task.id!r} does not match directory name")
    if task.category not in CATEGORIES:
        raise ValueError(f"{path}: unknown category {task.category!r}")
    return task


def load_tasks(ids: list[str] | None = None) -> list[Task]:
    tasks = [load_task(p) for p in sorted(TASKS_DIR.iterdir()) if (p / "task.toml").exists()]
    if ids:
        wanted = set(ids)
        missing = wanted - {t.id for t in tasks}
        if missing:
            raise KeyError(f"unknown task ids: {sorted(missing)}")
        tasks = [t for t in tasks if t.id in wanted]
    return tasks


def materialize(task: Task, dest: Path) -> Path:
    """Write the task's initial repository into `dest` (created, must not exist)."""
    shutil.copytree(task.repo_dir, dest)
    if task.generator is not None:
        spec = importlib.util.spec_from_file_location(f"gen_{task.id.replace('-', '_')}", task.generator)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.build(dest)
    return dest


def apply_solution(task: Task, repo: Path) -> None:
    """Overlay the reference solution on a materialized repo (host-side; tests only)."""
    shutil.copytree(task.solution_dir, repo, dirs_exist_ok=True)
    for rel in task.delete:
        (repo / rel).unlink()

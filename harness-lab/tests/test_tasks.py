"""Structural checks on the task suite. No Docker needed."""

import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import pytest
from eval.tasks import CATEGORIES, TASKS_DIR, load_tasks, materialize

TASKS = load_tasks()
IDS = [t.id for t in TASKS]


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def test_twenty_tasks_with_unique_ids():
    assert len(TASKS) == 20 and len(set(IDS)) == 20


def test_category_coverage():
    counts = Counter(t.category for t in TASKS)
    assert set(counts) == CATEGORIES
    # the spec's minimum mix: bugs, features with tests, refactors, >5-file reading, recall
    assert counts["bugfix"] >= 3 and counts["feature"] >= 3 and counts["refactor"] >= 2
    assert counts["multifile"] >= 1 and counts["recall"] >= 1


@pytest.mark.parametrize("task", TASKS, ids=IDS)
def test_task_layout(task):
    assert task.statement
    assert task.repo_dir.is_dir()
    hidden = [p for p in task.hidden_dir.rglob("test_*.py")]
    assert hidden, "no hidden tests"
    assert not (task.hidden_dir / "conftest.py").exists(), "verifier injects its own conftest"
    assert any(p.is_file() for p in task.solution_dir.rglob("*")), "no reference solution"
    for h in hidden:
        assert not (task.repo_dir / h.relative_to(task.hidden_dir)).exists(), "hidden test leaked into repo"
    for rel in task.delete:
        assert (task.repo_dir / rel).exists()


@pytest.mark.parametrize("task", TASKS, ids=IDS)
def test_materialize_is_deterministic(task, tmp_path):
    a, b = materialize(task, tmp_path / "a"), materialize(task, tmp_path / "b")
    assert tree_hash(a) == tree_hash(b)


def test_recall_tasks_have_earlier_turns():
    for t in TASKS:
        if t.category == "recall":
            assert len(t.user_turns) >= 3


def test_multifile_tasks_span_more_than_five_files(tmp_path):
    for t in TASKS:
        if t.category == "multifile":
            repo = materialize(t, tmp_path / t.id)
            assert len(list(repo.rglob("*.py"))) > 5


def test_large_repo_exceeds_context(tmp_path):
    repo = materialize(next(t for t in TASKS if t.id == "t17-large-repo"), tmp_path / "r")
    size = sum(p.stat().st_size for p in repo.rglob("*.py"))
    assert size > 1_000_000  # ~4 bytes/token: well past 200k tokens


def test_huge_log_expected_answer_matches_generated_log(tmp_path):
    """The hidden test hardcodes the answer; recompute it from the generated log."""
    task = next(t for t in TASKS if t.id == "t19-huge-log")
    repo = materialize(task, tmp_path / "r")
    spec = importlib.util.spec_from_file_location("gen19", task.generator)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    timeouts, max_ok = Counter(), Counter()
    for line in (repo / "logs" / "app.log").read_text().splitlines():
        host = re.search(r"upstream=(\S+)", line).group(1)
        if "status=TIMEOUT" in line:
            timeouts[host] += 1
        else:
            max_ok[host] = max(max_ok[host], int(re.search(r"latency_ms=(\d+)", line).group(1)))
    assert list(timeouts) == [gen.EXPECTED_HOST]
    expected = -(-2 * max_ok[gen.EXPECTED_HOST] // 100) * 100
    assert expected == gen.EXPECTED_TIMEOUT
    solution = json.loads((task.solution_dir / "config" / "upstreams.json").read_text())
    assert {u["host"]: u["timeout_ms"] for u in solution["upstreams"]}[gen.EXPECTED_HOST] == expected
    assert (repo / "logs" / "app.log").stat().st_size > 2_000_000


def test_tasks_dir_has_only_tasks():
    assert {p.name for p in TASKS_DIR.iterdir() if p.is_dir() and not p.name.startswith("__")} == set(IDS)

"""Sandbox, verifier and runner behaviour against real containers."""

import time

import pytest
from eval.agents import NullAgent
from eval.contract import AgentResult, Budget, validate_record
from eval.runner import _run_agent, run_one
from eval.sandbox import DockerSandbox
from eval.tasks import apply_solution, load_tasks, materialize
from eval.verify import verify

pytestmark = pytest.mark.docker
TASKS = {t.id: t for t in load_tasks()}


@pytest.fixture
def box(tmp_path):
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "hello.txt").write_text("hi\n")
    with DockerSandbox().start(tmp_path / "repo") as b:
        yield b


def test_runs_as_unprivileged_user_in_work(box):
    res = box.exec("id -u && pwd && cat hello.txt")
    assert res.stdout.split() == ["1000", "/work", "hi"]


def test_no_network(box):
    res = box.exec("python -c \"import socket; socket.create_connection(('1.1.1.1', 80), timeout=3)\"")
    assert res.exit_code != 0 and "unreachable" in res.stderr.lower()


def test_cannot_escalate(box):
    assert box.exec("touch /usr/local/lib/x").exit_code != 0
    assert box.exec("chown root /work/hello.txt").exit_code != 0


def test_timeout_kills(box):
    t0 = time.monotonic()
    res = box.exec("sleep 30", timeout=2)
    assert res.timed_out and time.monotonic() - t0 < 10


def test_write_read_roundtrip_and_export(box, tmp_path):
    data = "línea con ñ y \"comillas\" y $VAR\n".encode()
    box.write_file("/work/sub/dir/f.txt", data)
    assert box.read_file("/work/sub/dir/f.txt") == data
    box.export(tmp_path / "out")
    assert (tmp_path / "out" / "sub" / "dir" / "f.txt").read_bytes() == data


def test_output_cap(box):
    res = box.exec("head -c 2000000 /dev/zero | tr '\\0' a")
    assert res.truncated and len(res.stdout) == 1_000_000


# --- verifier isolation: a repo that tries to force a pass must still fail ---------------

CHEATS = {
    "sitecustomize.py": "import os\nos._exit(0)\n",
    "usercustomize.py": "import os\nos._exit(0)\n",
    "conftest.py": "import os\ndef pytest_sessionfinish(session, exitstatus):\n    os._exit(0)\n",
    "pytest.ini": "[pytest]\naddopts = --co\n",
    "pager_test_shadow.py": "",
}


@pytest.mark.parametrize("name", list(CHEATS))
def test_planted_files_cannot_fake_a_pass(name, tmp_path):
    task = TASKS["t01-pagination"]
    repo = materialize(task, tmp_path / "repo")
    (repo / name).write_text(CHEATS[name])
    assert not verify(task, repo).passed


def test_hidden_tests_never_reach_agent_container(tmp_path):
    task = TASKS["t01-pagination"]
    with DockerSandbox().start(materialize(task, tmp_path / "repo")) as b:
        res = b.exec("ls -R / 2>/dev/null | grep -c test_pager.py || true")
    assert res.stdout.strip() == "0"


# --- runner: budgets and failures are recorded, not raised ---------------------------------

class SleepyAgent:
    name = "sleepy"

    def config(self):
        return {}

    def run(self, task, sandbox, budget, seed):
        time.sleep(60)
        return AgentResult(stop_reason="completed")


class CrashingAgent:
    name = "crashing"

    def config(self):
        return {}

    def run(self, task, sandbox, budget, seed):
        raise RuntimeError("boom")


def test_wall_timeout_kills_agent(box):
    t0 = time.monotonic()
    res = _run_agent(SleepyAgent(), TASKS["t01-pagination"], box, Budget(wall_s=2), 0)
    assert res.stop_reason == "wall_timeout" and time.monotonic() - t0 < 15


def test_crash_is_recorded(box):
    res = _run_agent(CrashingAgent(), TASKS["t01-pagination"], box, Budget(wall_s=30), 0)
    assert res.stop_reason == "crash" and "boom" in res.error


def test_null_agent_result_is_trivial(box):
    res = _run_agent(NullAgent(), TASKS["t01-pagination"], box, Budget(wall_s=30), 0)
    assert res == AgentResult(stop_reason="no_op")


# --- phase-0 closing criterion: the controls bracket the suite -----------------------------

@pytest.mark.parametrize("task_id", list(TASKS))
def test_initial_repo_fails_and_reference_passes(task_id, tmp_path):
    task = TASKS[task_id]
    initial = materialize(task, tmp_path / "initial")
    assert not verify(task, initial).passed, "verifier passes on the untouched repo"
    solved = materialize(task, tmp_path / "solved")
    apply_solution(task, solved)
    res = verify(task, solved)
    assert res.passed, res.output_tail


@pytest.mark.parametrize("agent", ["null", "oracle"])
def test_controls_through_runner(agent):
    task = TASKS["t13-refund-totals"]
    rec = run_one(agent, task, 0, Budget(wall_s=60), "test", "test")
    assert validate_record(rec) == []
    assert rec["success"] is (agent == "oracle")

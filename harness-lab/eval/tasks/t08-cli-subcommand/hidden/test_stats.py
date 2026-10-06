import json
import subprocess
import sys


def run(db, *args):
    return subprocess.run([sys.executable, "/work/todo.py", "--db", str(db), *args],
                          capture_output=True, text=True)


def seed(tmp_path):
    db = tmp_path / "t.json"
    db.write_text(json.dumps([
        {"id": 1, "title": "a", "done": True, "due": "2020-01-01"},
        {"id": 2, "title": "b", "done": False, "due": "2024-03-01"},
        {"id": 3, "title": "c", "done": False, "due": None},
        {"id": 4, "title": "d", "done": False, "due": "2030-01-01"},
    ]))
    return db


def test_stats_with_overdue(tmp_path):
    r = run(seed(tmp_path), "stats", "--today", "2025-01-01")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["total: 4", "done: 1", "open: 3", "overdue: 1"]


def test_stats_without_overdue(tmp_path):
    r = run(seed(tmp_path), "stats", "--today", "2000-01-01")
    assert r.stdout.splitlines() == ["total: 4", "done: 1", "open: 3"]


def test_stats_empty_db(tmp_path):
    r = run(tmp_path / "missing.json", "stats", "--today", "2025-01-01")
    assert r.returncode == 0
    assert r.stdout.splitlines() == ["total: 0", "done: 0", "open: 0"]


def test_existing_commands_still_work(tmp_path):
    db = tmp_path / "x.json"
    assert run(db, "add", "write tests", "--due", "2025-02-02").returncode == 0
    assert "[ ] 1 write tests (due 2025-02-02)" in run(db, "list").stdout

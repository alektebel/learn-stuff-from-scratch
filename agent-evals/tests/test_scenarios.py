import pytest
from eval.tasks import materialize
from redteam.scenarios import ATTACKS, load_scenarios

SCENARIOS = load_scenarios()
IDS = [s.id for s in SCENARIOS]


def test_suite_shape():
    assert len(SCENARIOS) == 6
    assert {s.attack for s in SCENARIOS} == ATTACKS


@pytest.mark.parametrize("sc", SCENARIOS, ids=IDS)
def test_layout(sc, tmp_path):
    assert sc.task.statement and list(sc.task.hidden_dir.glob("test_*.py"))
    assert any(p.is_file() for p in sc.task.solution_dir.rglob("*"))
    repo = materialize(sc.task, tmp_path / "repo")
    for c in sc.checks:
        if c["kind"] == "unchanged" and c["path"].startswith("work/"):
            assert (repo / c["path"][len("work/"):]).exists(), c["path"]
        if c["kind"] == "no_leak":
            assert sc.home_dir is not None and any(
                c["token"] in p.read_text() for p in sc.home_dir.rglob("*") if p.is_file())

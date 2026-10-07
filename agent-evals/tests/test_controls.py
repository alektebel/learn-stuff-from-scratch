"""The closing criterion of project 8 v1: every scenario separates the three controls."""

import pytest
from eval.contract import Budget
from redteam.runner import run_scenario, validate
from redteam.scenarios import load_scenarios

pytestmark = pytest.mark.docker
SCENARIOS = load_scenarios()

EXPECTED = {"null": (False, True), "oracle": (True, True), "complicit": (True, False)}


@pytest.mark.parametrize("agent", list(EXPECTED))
@pytest.mark.parametrize("sc", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_control(sc, agent):
    rec = run_scenario(agent, sc, 0, Budget(wall_s=60), "test", "test")
    assert validate(rec) == []
    assert (rec["success"], rec["safe"]) == EXPECTED[agent], rec["violations"]

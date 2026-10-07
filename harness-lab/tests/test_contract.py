import json

import pytest
from eval.contract import RECORD_FIELDS, SCHEMA_VERSION, validate_record
from eval.report import compare, load_records, summarise


def record(**over):
    rec = {
        "schema_version": SCHEMA_VERSION, "run_id": "r", "batch_id": "b", "started_at": "t",
        "git_sha": "abc", "agent": "a", "agent_config": {}, "task_id": "t01", "task_category": "bugfix",
        "seed": 0, "budget": {}, "success": False, "verifier_exit": 1, "verifier_tail": "",
        "stop_reason": "no_op", "turns": 0, "input_tokens": 0, "output_tokens": 0, "cached_tokens": 0,
        "cost_eur": 0.0, "tool_calls": 0, "wall_time_s": 0.5, "error": None, "extra": {},
    }
    rec.update(over)
    return rec


def test_valid_record():
    assert set(record()) == set(RECORD_FIELDS)
    assert validate_record(record()) == []


@pytest.mark.parametrize("over,needle", [
    ({"turns": -1}, "turns is negative"),
    ({"turns": True}, "bool where int"),
    ({"cost_eur": float("nan")}, "NaN"),
    ({"cached_tokens": 5, "input_tokens": 4}, "cached_tokens exceeds"),
    ({"stop_reason": "bored"}, "unknown stop_reason"),
    ({"success": 1}, "success"),
    ({"schema_version": 0}, "schema_version"),
])
def test_invalid_records(over, needle):
    assert any(needle in p for p in validate_record(record(**over)))


def test_missing_and_unknown_fields():
    rec = record(extra_field=1)
    del rec["seed"]
    problems = validate_record(rec)
    assert "missing field seed" in problems and "unknown field extra_field" in problems


def test_report_roundtrip_and_paired_compare(tmp_path):
    rows = []
    for t in range(6):
        rows.append(record(agent="A", task_id=f"t{t}", success=t < 5))
        rows.append(record(agent="B", task_id=f"t{t}", success=t < 1))
    p = tmp_path / "r.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    recs = load_records([p])
    assert "5/6 = 83.3%" in summarise(recs)
    out = compare(recs, "A", "B")
    assert "only A 4, only B 0" in out and "p = 0.125" in out


def test_load_rejects_invalid(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps(record(turns=-3)) + "\n")
    with pytest.raises(ValueError, match="bad.jsonl:1"):
        load_records([p])

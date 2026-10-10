"""Contract tests for trajectory (agent-evals project #1).

Tests of the provided infrastructure (dataclasses, signature, the default
policy) PASS today. Tests marked with the CORE xfail decorator call the
learner's core (validate_call / prerequisite_violations / repeat_violations /
grade): they xfail while the stubs raise NotImplementedError, pass once the core
is correct, and fail if it is wrong. Never strict. SPEC.md acceptance items
A1-A5 and limit cases L1-L5 are named in the docstrings.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from trajectory.trajectory import (
    DEFAULT_POLICY,
    RISKY,
    SCHEMAS,
    Policy,
    Step,
    Violation,
    grade,
    prerequisite_violations,
    repeat_violations,
    signature,
    validate_call,
)

CORE = pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


def msg(text: str = "") -> Step:
    return Step(None, text=text)


def read(path: str) -> Step:
    return Step("read_file", {"path": path}, result="...", exit_code=0)


def write(path: str, content="x") -> Step:
    return Step("write_file", {"path": path, "content": content}, exit_code=0)


def run_tests_call() -> Step:
    return Step("run_tests", {}, result="8 passed", exit_code=0)


def commit(message: str = "done") -> Step:
    return Step("git_commit", {"message": message}, exit_code=0)


def rules(violations) -> list[tuple[str, int]]:
    return [(v.rule, v.step) for v in violations]


# ---------------------------------------------------------------------------
# Infrastructure tests — pass now.
# ---------------------------------------------------------------------------


def test_signature_ignores_argument_key_order():
    a = Step("write_file", {"path": "x", "content": "y"})
    b = Step("write_file", {"content": "y", "path": "x"})
    assert signature(a) == signature(b)


def test_signature_none_for_plain_message():
    assert signature(msg("done")) is None


def test_signature_distinguishes_arguments():
    assert signature(read("a")) != signature(read("b"))
    assert signature(read("a")) != signature(run_tests_call())


def test_default_policy_names_the_tools():
    assert set(DEFAULT_POLICY.schemas) == {"read_file", "write_file", "run_tests", "git_commit"}
    assert RISKY["write_file"] == ("read_file",)
    assert RISKY["git_commit"] == ("run_tests",)
    assert DEFAULT_POLICY.max_identical_repeats == 3
    assert DEFAULT_POLICY.max_steps == 50


# ---------------------------------------------------------------------------
# A1 — schema-valid tool calls
# ---------------------------------------------------------------------------


@CORE
def test_validate_call_accepts_a_valid_call():
    assert validate_call(SCHEMAS["read_file"], {"path": "a"}) == []
    assert validate_call(SCHEMAS["run_tests"], {}) == []


@CORE
def test_validate_call_reports_a_missing_required_key():
    assert validate_call(SCHEMAS["read_file"], {}) == ["missing required 'path'"]
    problems = validate_call(SCHEMAS["write_file"], {"path": "a"})
    assert problems == ["missing required 'content'"]


@CORE
def test_validate_call_reports_a_wrong_type():
    assert validate_call(SCHEMAS["write_file"], {"path": "a", "content": 5}) == [
        "'content' must be str"
    ]


@CORE
def test_validate_call_bool_is_not_an_int_or_number():
    schema = {"required": [], "types": {"n": "int"}, "additional": True}
    assert validate_call(schema, {"n": True}) == ["'n' must be int"]
    number = {"required": [], "types": {"n": "number"}, "additional": True}
    assert validate_call(number, {"n": 3.5}) == []
    assert validate_call(number, {"n": True}) == ["'n' must be number"]


@CORE
def test_validate_call_order_is_required_then_types_then_additional():
    schema = {"required": ["a", "b"], "types": {"b": "int"}, "additional": False}
    problems = validate_call(schema, {"a": 1, "b": "x", "c": 1})
    assert problems == ["'b' must be int", "unexpected 'c'"]


@CORE
def test_validate_call_allows_extras_when_additional_is_true():
    schema = {"required": ["path"], "types": {"path": "str"}, "additional": True}
    assert validate_call(schema, {"path": "a", "mode": "r"}) == []


@CORE
def test_validate_call_flags_extras_when_additional_is_false():
    assert validate_call(SCHEMAS["read_file"], {"path": "a", "mode": "r"}) == [
        "unexpected 'mode'"
    ]


# ---------------------------------------------------------------------------
# A2 — a prerequisite before a risky action
# ---------------------------------------------------------------------------


@CORE
def test_prerequisite_satisfied():
    assert prerequisite_violations([read("a"), write("a")]) == []


@CORE
def test_prerequisite_missing_is_flagged():
    violations = prerequisite_violations([write("a")])
    assert rules(violations) == [("missing_prerequisite", 0)]


@CORE
def test_prerequisite_must_come_before_not_after():
    # L2: the read happens, but after the write — ordering matters, not presence.
    violations = prerequisite_violations([write("a"), read("a")])
    assert rules(violations) == [("missing_prerequisite", 0)]


@CORE
def test_empty_prerequisite_imposes_nothing():
    policy = Policy(schemas={}, risky={"x": ()}, max_identical_repeats=3, max_steps=50)
    assert prerequisite_violations([Step("x", {})], policy) == []


@CORE
def test_commit_requires_run_tests_call():
    assert prerequisite_violations([run_tests_call(), commit()]) == []
    assert rules(prerequisite_violations([commit()])) == [("missing_prerequisite", 0)]


# ---------------------------------------------------------------------------
# A3 — identical-call loops
# ---------------------------------------------------------------------------


@CORE
def test_repeat_run_at_the_limit_is_allowed():
    assert repeat_violations([read("a"), read("a"), read("a")]) == []


@CORE
def test_repeat_run_over_the_limit_is_flagged_once():
    violations = repeat_violations([read("a")] * 5)
    assert rules(violations) == [("repeat_loop", 3)]  # first step past the limit


@CORE
def test_a_plain_message_breaks_a_run():
    run = [read("a"), read("a"), read("a"), msg("..."), read("a")]
    assert repeat_violations(run) == []


@CORE
def test_different_arguments_are_not_a_repeat():
    assert repeat_violations([read("a"), read("b"), read("a"), read("b")]) == []


# ---------------------------------------------------------------------------
# A5 / A4 / L1 / L3 / L4 / L5 — grade, budget and the limit cases
# ---------------------------------------------------------------------------


@CORE
def test_grade_clean_trajectory_is_ok_with_counts():
    report = grade([read("a"), write("a"), run_tests_call(), commit()])
    assert report.ok is True
    assert report.violations == ()
    assert report.counts == {
        "read_file": 1,
        "write_file": 1,
        "run_tests": 1,
        "git_commit": 1,
    }


@CORE
def test_grade_sorts_violations_by_step_then_rule():
    report = grade([write("a"), read("x"), read("x"), read("x"), read("x")])
    assert rules(report.violations) == [
        ("missing_prerequisite", 0),
        ("repeat_loop", 4),
    ]


@CORE
def test_grade_step_budget():
    policy = Policy(schemas={}, risky={}, max_identical_repeats=3, max_steps=2)
    report = grade([msg(), msg(), msg()], policy)
    assert rules(report.violations) == [("step_budget", 3)]
    assert report.ok is False


@CORE
def test_grade_schema_violation_is_reported():
    report = grade([read("a"), write("a", content=5)])
    assert ("schema", 1) in rules(report.violations)


@CORE
def test_L1_alternative_order_passes():
    # L1: an extra read and an independent reordering must not be penalised; a
    # fixed-path (DAG) grader would reject this.
    report = grade([read("b"), read("a"), write("a"), run_tests_call(), commit()])
    assert report.ok is True


@CORE
def test_L3_a_loop_that_ends_in_success_is_still_flagged():
    trajectory = [read("x")] * 4 + [msg("done")]
    assert ("repeat_loop", 3) in rules(grade(trajectory).violations)


@CORE
def test_L4_wrong_type_argument_is_a_schema_violation():
    report = grade([read("a"), write("a", content=5)])
    assert any(v.rule == "schema" and "'content' must be str" in v.detail
               for v in report.violations)


@CORE
def test_L5_additional_property_is_a_schema_violation():
    bad = Step("read_file", {"path": "a", "mode": "r"})
    report = grade([bad])
    assert any(v.rule == "schema" and "unexpected 'mode'" in v.detail
               for v in report.violations)

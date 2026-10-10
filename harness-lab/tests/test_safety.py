"""The phase-2 permission contract: allow / ask / deny.

LEARN mode. The rule engine in `harness_lab/safety/match.py` is the learner's
work, so the tests that exercise it are `xfail(raises=NotImplementedError)`.
The rule/policy data types, validation and the guarded dispatch are provided and
their tests pass today. Contract: docs/phase2.md.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness_lab.llm.base import ToolSpec  # noqa: E402
from harness_lab.safety import (  # noqa: E402
    DECISIONS,
    Policy,
    Rule,
    command_string,
    decide,
    guarded_call_tool,
    parse_policy,
)
from harness_lab.tools.base import ToolResult  # noqa: E402

CORE = pytest.mark.xfail(
    raises=NotImplementedError,
    reason="phase-2 permissions: the learner writes harness_lab/safety/match.py (docs/phase2.md)",
)


class FakeBash:
    """A tool the gating tests can watch, so they do not depend on the tools slice."""

    spec = ToolSpec(
        name="bash",
        description="run a command",
        parameters={"type": "object", "properties": {"command": {"type": "string"}},
                    "required": ["command"]},
    )

    def __init__(self):
        self.commands: list[str] = []

    def run(self, command: str) -> ToolResult:
        self.commands.append(command)
        return ToolResult.success("ran")


# --- rules, validation and parsing (infrastructure, pass today) --------------


def test_decisions_are_allow_ask_deny():
    assert DECISIONS == ("allow", "ask", "deny")


def test_rule_rejects_an_unknown_decision():
    with pytest.raises(ValueError):
        Rule("bash", None, "maybe")


def test_rule_rejects_a_bad_regex():
    with pytest.raises(ValueError):
        Rule("bash", "(", "deny")


def test_policy_rejects_an_unknown_default():
    with pytest.raises(ValueError):
        Policy((), "maybe")


def test_parse_policy_keeps_rule_order_and_default():
    policy = parse_policy({
        "default": "deny",
        "rules": [
            {"tool": "bash", "pattern": r"rm\s+-rf", "decision": "deny"},
            {"tool": "*", "decision": "allow"},
        ],
    })
    assert policy.default == "deny"
    assert [rule.tool for rule in policy.rules] == ["bash", "*"]
    assert policy.rules[0].decision == "deny"


# --- the rule engine (the learner's work) ------------------------------------


@CORE
def test_command_string_picks_the_field_per_tool():
    assert command_string("bash", {"command": "ls -la"}) == "ls -la"
    assert command_string("read_file", '{"path": "a.txt"}') == "a.txt"
    assert command_string("edit_file", {"path": "a.txt", "old": "x"}) == "a.txt"
    assert command_string("glob", {"pattern": "**/*.py"}) == "**/*.py"


@CORE
def test_command_string_is_empty_on_bad_input():
    assert command_string("bash", "{not json") == ""
    assert command_string("bash", {"command": 5}) == ""      # non-string value
    assert command_string("bash", {"other": "x"}) == ""      # missing field
    assert command_string("unknown_tool", {"x": 1}) == ""


@CORE
def test_decide_returns_the_default_when_no_rule_matches():
    assert decide(Policy((), "ask"), "bash", {"command": "ls"}) == "ask"
    assert decide(Policy((Rule("read_file", decision="allow"),), "deny"),
                  "bash", {"command": "ls"}) == "deny"


@CORE
def test_decide_first_match_wins_and_pattern_is_a_regex():
    policy = Policy((
        Rule("bash", r"rm\s+-rf", "deny"),
        Rule("bash", None, "allow"),
    ))
    assert decide(policy, "bash", {"command": "rm -rf /"}) == "deny"
    assert decide(policy, "bash", {"command": "rm -rf /"}) == "deny"  # anchored anywhere
    assert decide(policy, "bash", {"command": "echo hi && rm -rf /"}) == "deny"
    assert decide(policy, "bash", {"command": "ls -la"}) == "allow"


@CORE
def test_order_matters_a_broad_allow_before_a_deny_wins():
    # The classic mistake: an allow that swallows every later deny.
    policy = Policy((
        Rule("bash", None, "allow"),
        Rule("bash", r"rm", "deny"),
    ))
    assert decide(policy, "bash", {"command": "rm -rf /"}) == "allow"


@CORE
def test_wildcard_tool_rule_matches_every_tool():
    policy = Policy((Rule("*", None, "deny"),), default="allow")
    assert decide(policy, "read_file", {"path": "a.txt"}) == "deny"
    assert decide(policy, "bash", {"command": "ls"}) == "deny"


@CORE
def test_guarded_call_allows_and_runs():
    tools = {"bash": FakeBash()}
    policy = Policy((Rule("bash", None, "allow"),), default="ask")
    result = guarded_call_tool(policy, tools, "bash", {"command": "ls"})
    assert result.ok and tools["bash"].commands == ["ls"]


@CORE
def test_guarded_call_denies_without_running():
    tools = {"bash": FakeBash()}
    policy = Policy((Rule("bash", None, "deny"),), default="ask")
    result = guarded_call_tool(policy, tools, "bash", {"command": "rm -rf /"})
    assert not result.ok and "denied" in result.error
    assert tools["bash"].commands == []  # the tool never ran


@CORE
def test_guarded_call_asks_and_needs_approval():
    tools = {"bash": FakeBash()}
    policy = Policy((Rule("bash", None, "ask"),), default="ask")
    # no approver: refused
    assert not guarded_call_tool(policy, tools, "bash", {"command": "ls"}).ok
    assert tools["bash"].commands == []
    # approver says yes: runs
    assert guarded_call_tool(policy, tools, "bash", {"command": "ls"},
                             approve=lambda name, args: True).ok
    assert tools["bash"].commands == ["ls"]
    # approver says no: refused
    assert not guarded_call_tool(policy, tools, "bash", {"command": "ls"},
                                 approve=lambda name, args: False).ok
    assert tools["bash"].commands == ["ls"]

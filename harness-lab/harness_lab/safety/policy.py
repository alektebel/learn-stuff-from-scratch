"""Permission policy (phase 2, subsystem 5) — provided infrastructure.

A policy is an **ordered** list of rules. The first rule whose tool matches (the
call's tool name or `"*"`) and whose pattern matches the call's canonical string
(the command for `bash`, the path for a file tool, the pattern for a discovery
tool) decides the call: `"allow"`, `"ask"` or `"deny"`. If nothing matches, the
policy's `default` decides.

Order is the whole design: a narrow `deny` must come before a broad `allow`, or
the allow swallows it. First match wins.

Sources
-------
- Claude Code permission rules: an allow/deny list keyed by tool and an argument
  matcher, with a default for anything unlisted.
- OpenHands confirmation policy: per-action "never / always / ask".

DESIGN DECISION — decisions are data; the matching is the learner's (`match.py`).
  `Rule`/`Policy` validate their inputs here (a decision must be one of three, a
  pattern must compile), so `match.decide` can assume well-formed rules and the
  learner focuses on the rule engine — where a mistake is a security hole.

DESIGN DECISION — the default is `"ask"`, not `"allow"`.
  An unlisted call is not silently permitted: the safe default fails closed, and
  a deployment that wants permissive behaviour must say so explicitly. Cost: a
  misconfiguration blocks work instead of running it, which is the failure you
  want to notice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from harness_lab.tools.base import ToolResult
from harness_lab.tools.registry import call_tool

from harness_lab.safety.match import command_string, decide  # noqa: F401  (re-exported)

DECISIONS: tuple[str, str, str] = ("allow", "ask", "deny")

Approver = Callable[[str, object], bool]


@dataclass(frozen=True)
class Rule:
    """One permission rule: a tool (`"*"` = any) and an optional regex pattern."""

    tool: str
    pattern: str | None = None
    decision: str = "ask"

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}, got {self.decision!r}")
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"pattern {self.pattern!r} is not a valid regex: {exc}")


@dataclass(frozen=True)
class Policy:
    """An ordered tuple of rules plus the default for an unlisted call."""

    rules: tuple[Rule, ...] = ()
    default: str = "ask"

    def __post_init__(self) -> None:
        if self.default not in DECISIONS:
            raise ValueError(f"default must be one of {DECISIONS}, got {self.default!r}")


def parse_policy(data: Mapping) -> Policy:
    """Build a `Policy` from plain data (e.g. a parsed `harness.toml` section).

    `{"default": "ask", "rules": [{"tool": "bash", "pattern": "rm", "decision":
    "deny"}, ...]}`. Rules keep their order.
    """
    return Policy(
        rules=tuple(Rule(**rule) for rule in data.get("rules", ())),
        default=data.get("default", "ask"),
    )


def guarded_call_tool(policy: "Policy", tools: Mapping[str, object], name: str,
                      arguments, approve: Approver | None = None) -> ToolResult:
    """Decide, then run `name` through `call_tool` only if the decision permits.

    `allow` runs. `deny` never runs. `ask` runs only when `approve(name,
    arguments)` returns True; with no approver it does not run. Every refusal is
    a `ToolResult.failure`, so the loop never sees an exception.
    """
    decision = decide(policy, name, arguments)
    if decision == "deny":
        return ToolResult.failure(f"{name!r} is denied by policy")
    if decision == "ask" and not (approve is not None and approve(name, arguments)):
        return ToolResult.failure(f"{name!r} requires approval")
    return call_tool(tools, name, arguments)


if __name__ == "__main__":
    def raises(fn) -> str:
        try:
            fn()
        except ValueError as exc:
            return str(exc)
        return "no error"

    print("permission policy — rules validate; matching lives in match.py")
    print("  decisions:", DECISIONS)
    print("  a bad decision raises:", raises(lambda: Rule("bash", None, "maybe")))
    print("  a bad regex raises:", raises(lambda: Rule("bash", "(", "deny")))
    policy = parse_policy({"default": "ask", "rules": [{"tool": "bash", "pattern": r"rm\s+-rf",
                                                        "decision": "deny"}]})
    print("  parsed policy:", policy)

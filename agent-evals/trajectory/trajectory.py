"""trajectory — grade a coding agent's trajectory by invariants (LEARN mode).

This file is the *contract*, not the implementation. The data model
(``Step``, ``Policy``, ``Violation``, ``Report``) and ``signature`` ship as
test infrastructure; every core grader raises ``NotImplementedError`` until the
learner writes it. The tests in ``../tests/test_trajectory.py`` define what must
be made true.

Why invariants and not a script: a coding task has many valid trajectories, so a
single expected path (a DAG) punishes correct alternatives. What generalises is a
set of rules every good trajectory obeys — schema-valid calls, a prerequisite run
before a risky action, no identical-call loop, a step budget. The grader reports
which rule a step broke, and a trajectory with a different but valid order passes.

Standard library only, fully deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "Step",
    "Policy",
    "Violation",
    "Report",
    "SCHEMAS",
    "RISKY",
    "DEFAULT_POLICY",
    "signature",
    "validate_call",
    "prerequisite_violations",
    "repeat_violations",
    "grade",
]


# ---------------------------------------------------------------------------
# Data model and helpers — implemented; tests may rely on them right now.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Step:
    """One agent turn.

    ``tool is None`` means a plain assistant message (no tool call) — the usual
    way a run ends. ``arguments`` is the decoded tool arguments; ``result`` and
    ``exit_code`` are the tool's output when the call ran.
    """

    tool: str | None
    arguments: dict = field(default_factory=dict)
    result: str = ""
    exit_code: int | None = None
    text: str = ""


@dataclass(frozen=True)
class Policy:
    """The rules a trajectory is graded against.

    ``schemas`` maps a tool name to ``{"required": [...], "types": {...},
    "additional": bool}``. ``risky`` maps a tool to the set of tools, any one of
    which must have run earlier in the trajectory.
    """

    schemas: dict
    risky: dict
    max_identical_repeats: int = 3
    max_steps: int = 50


@dataclass(frozen=True)
class Violation:
    """One broken rule, at the step that broke it."""

    rule: str
    step: int
    detail: str


@dataclass(frozen=True)
class Report:
    ok: bool
    violations: tuple
    counts: dict


# The default tools of a small coding agent. Only these are graded; a tool with
# no schema is neither validated nor flagged.
SCHEMAS: dict = {
    "read_file": {"required": ["path"], "types": {"path": "str"}, "additional": False},
    "write_file": {
        "required": ["path", "content"],
        "types": {"path": "str", "content": "str"},
        "additional": False,
    },
    "run_tests": {"required": [], "types": {}, "additional": False},
    "git_commit": {"required": ["message"], "types": {"message": "str"}, "additional": False},
}

# A file must be read before it is written; tests must run before a commit.
RISKY: dict = {
    "write_file": ("read_file",),
    "git_commit": ("run_tests",),
}

DEFAULT_POLICY = Policy(schemas=SCHEMAS, risky=RISKY)


def _freeze(value):
    """A hashable, order-insensitive image of a JSON-ish value."""
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def signature(step: Step):
    """A stable identity for a tool call: (tool, arguments), key order ignored.

    ``None`` for a plain assistant message. Two calls are "the same" iff their
    signatures are equal — that is what repeat detection counts.
    """
    if step.tool is None:
        return None
    return (step.tool, _freeze(step.arguments))


# ---------------------------------------------------------------------------
# Core graders — stubs. Every test that calls one is marked
# xfail(raises=NotImplementedError, reason="core not implemented") until the
# learner implements it.
# ---------------------------------------------------------------------------

def validate_call(schema: dict, arguments: dict) -> list[str]:
    """Return the problems with ``arguments`` against ``schema``, in a stable order.

    A problem is a short string. Empty list means valid. Checks, in this order:
    every ``required`` key is present; every present key listed in ``types`` has
    the named type (``"str"``, ``"int"``, ``"bool"``, ``"number"``, ``"dict"``,
    ``"list"``; ``bool`` is not accepted as ``"int"``/``"number"``); if
    ``schema["additional"]`` is ``False``, no key outside ``required`` and
    ``types`` appears.
    """
    raise NotImplementedError("core not implemented")


def prerequisite_violations(trajectory: list, policy: Policy = DEFAULT_POLICY) -> list[Violation]:
    """One ``Violation(rule="missing_prerequisite")`` per risky call whose
    prerequisite has not appeared *strictly earlier* in the trajectory.

    ``policy.risky`` maps a tool to a tuple of tools; the risky call is allowed
    iff at least one of them appeared before it. An empty prerequisite tuple
    imposes nothing. A call never satisfies its own prerequisite.
    """
    raise NotImplementedError("core not implemented")


def repeat_violations(trajectory: list, policy: Policy = DEFAULT_POLICY) -> list[Violation]:
    """One ``Violation(rule="repeat_loop")`` per run of identical consecutive
    calls longer than ``policy.max_identical_repeats``.

    The run is detected on ``signature`` (tool and arguments); a plain assistant
    message (``tool is None``) breaks a run. Only the step where the run first
    exceeds the limit is reported.
    """
    raise NotImplementedError("core not implemented")


def grade(trajectory: list, policy: Policy = DEFAULT_POLICY) -> Report:
    """Grade the whole trajectory: the union of every rule's violations.

    Also flags a step whose tool has a schema and fails ``validate_call``
    (``rule="schema"``) and a trajectory longer than ``policy.max_steps``
    (``rule="step_budget"``, at step ``len(trajectory)``). Violations are sorted
    by ``(step, rule)``; ``counts`` maps each tool name to its number of calls;
    ``ok`` is true iff there are no violations.
    """
    raise NotImplementedError("core not implemented")

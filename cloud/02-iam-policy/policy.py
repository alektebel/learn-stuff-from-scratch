"""
IAM policy documents and evaluation — from scratch.

Source: AWS docs, "IAM policy evaluation logic" (awsiam:evaluation), specifically
"How AWS enforcement code logic evaluates requests to allow or deny access".

    By default, all requests are implicitly denied.
    An explicit deny overrides an explicit allow.
    A request must be explicitly allowed to be allowed.

So the whole engine is three lines, and everything else is detail hung off them:

    1. An explicit DENY anywhere always wins.
    2. Otherwise, an explicit ALLOW grants access.
    3. Otherwise, DENY (implicit).

This file parses a policy document (the JSON shape of Statement / Effect / Action /
Resource / Condition) and evaluates a request against a set of policies.

DESIGN DECISION — evaluate statements in order, or partition by effect?
  Reading statements top to bottom and letting the last one win is how firewall
  rules work, and it is what most people expect.
  CHOSEN: evaluate policies as a SET. Collect matching Deny; if any exists the
  answer is Deny. Otherwise any matching Allow grants. Statement order within a
  policy, and policy order in the list, cannot change the answer.
  WHY: this is what AWS does, and it is the property that makes a large policy set
  tractable to reason about — you can move a statement without re-deriving the
  answer. The checker proves it by evaluating the same policies in both orders.
  COST: you cannot express "deny, then allow" as an override. You are not supposed
  to; a second Deny would silently be a no-op.

DESIGN DECISION — wildcards: fnmatch, or a hand-written matcher?
  IAM pattern matching is `*` (any run, including `:` and `/`) and `?` (one char).
  Python's fnmatch implements exactly that, but `fnmatch.fnmatch` case-folds
  through os.path.normcase, which is a no-op on Linux and case-insensitive on
  Windows — a platform-dependent security decision, which is unacceptable.
  CHOSEN: `fnmatch.fnmatchcase` everywhere, with the strings lower-cased *first*
  only for actions. AWS action names are case-insensitive; ARNs and resources are
  case-sensitive. Lower-casing both inputs before fnmatchcase makes the action
  rule explicit instead of inheriting an OS default.

DESIGN DECISION — parse JSON, or build Statement objects directly?
  A module whose only input is the JSON document is honest (that is what IAM
  stores) but awkward to test. Constructing `Statement`s in Python skips the
  effect validation and list normalisation.
  CHOSEN: `parse_policy` accepts a JSON string, bytes, or an already-decoded dict,
  and produces the same `Statement`/`Policy` objects either way. One parsing path,
  so a hand-built policy and a parsed one cannot drift.
"""

import fnmatch
import json
from typing import Any, Dict, List, Optional, Sequence, Union

from conditions import evaluate_condition

ALLOW, DENY = "Allow", "Deny"

Document = Union[str, bytes, Dict[str, Any]]


def _as_list(value: Any) -> List[Any]:
    """`Action` / `Resource` may be a scalar or a list. Normalise to a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


class Statement:
    """One statement of a policy document.

    `action` and `not_action` are mutually exclusive in spirit: NotAction means
    "every action except these" and is easy to reason about wrongly, so it is kept
    as its own field rather than folded into `action`.
    """

    def __init__(self, effect: str, action: Any = None, resource: Any = None,
                 condition: Optional[Dict[str, Dict[str, Any]]] = None,
                 not_action: Any = None, sid: str = ""):
        if effect not in (ALLOW, DENY):
            raise ValueError(f"Effect must be {ALLOW!r} or {DENY!r}, got {effect!r}")
        self.effect = effect
        self.action = _as_list(action)
        self.not_action = _as_list(not_action) if not_action is not None else None
        self.resource = _as_list(resource)
        self.condition: Dict[str, Dict[str, Any]] = condition or {}
        self.sid = sid

    def __repr__(self) -> str:
        what = self.action or f"NOT {self.not_action}"
        return f"<{self.effect} {self.sid or ''} {what}>".replace("  ", " ")


class Policy:
    """A named list of statements. Evaluation never depends on their order."""

    def __init__(self, statements: Sequence[Statement], name: str = ""):
        self.statements = list(statements)
        self.name = name

    def __repr__(self) -> str:
        return f"<Policy {self.name or '(unnamed)'} {len(self.statements)} stmts>"


def parse_policy(document: Document, name: str = "") -> Policy:
    """Build a Policy from a JSON policy document.

    Accepts the string/bytes form (what you paste into the console) or an already
    decoded dict, so tests and demos never stringify and re-parse. A single
    `Statement` may be a dict rather than a one-element list — AWS writes both —
    so both are accepted.

    Raises ValueError for an unknown `Effect` (via Statement) and KeyError for a
    statement with no Effect at all: a malformed policy must fail loudly, because
    the alternative is an "Allow" that silently became a no-op.
    """
    # TODO: Accept a JSON string, bytes, or a decoded dict. Statement may be a single object or a list, and Action/Resource may be a scalar or a list. Build Statement objects and wrap them in a Policy.
    raise NotImplementedError("parse_policy")


def matches_action(pattern: str, action: str) -> bool:
    """`s3:*` matches `s3:GetObject`. Case-insensitive, like the real thing.

    `*` spans `:`, so `s3*` also matches `s3:GetObject` — wider than it looks.
    Lower-casing both sides before `fnmatchcase` pins the case rule to the action
    name instead of to the operating system.
    """
    # TODO: Lower-case both the action and the pattern, then fnmatch.fnmatchcase. `*` spans colons, so `s3*` matches `s3:GetObject`. Never use fnmatch.fnmatch: it case-folds through the OS and is platform-dependent.
    raise NotImplementedError("matches_action")


def matches_resource(pattern: str, resource: str) -> bool:
    """ARN matching with `*` (any run) and `?` (one character), case-sensitive.

    Note `*` crosses `:` and `/`, as it does in AWS — a common surprise, since
    `arn:aws:s3:::bucket/*` matches every key including ones containing slashes.
    """
    # TODO: fnmatch.fnmatchcase(resource, pattern): case-sensitive, and `*` crosses both `:` and `/`, so a bucket wildcard covers keys with slashes.
    raise NotImplementedError("matches_resource")


def statement_matches(statement: Statement, action: str, resource: str,
                      context: Dict[str, Any]) -> bool:
    """Does this statement apply to the request? Action AND resource AND condition.

    NotAction inverts the action test: the statement applies to everything the
    list does *not* name. Combined with Allow it is a very wide grant, which is
    why it is modelled explicitly rather than as a negated action pattern.
    """
    # TODO: NotAction inverts the action test (the statement applies to everything NOT named); otherwise the action must match an entry. The resource must match an entry, and then the condition must hold.
    raise NotImplementedError("statement_matches")


class Decision:
    """The result of an evaluation: whether it is allowed, and why."""

    def __init__(self, allowed: bool, reason: str,
                 statement: Optional[Statement] = None):
        self.allowed = allowed
        self.reason = reason
        self.statement = statement

    def __bool__(self) -> bool:
        return self.allowed

    def __repr__(self) -> str:
        return f"{'ALLOW' if self.allowed else 'DENY '}  {self.reason}"


def evaluate(policies: Sequence[Policy], action: str, resource: str,
             context: Optional[Dict[str, Any]] = None) -> Decision:
    """Explicit Deny > explicit Allow > implicit Deny.

    The order of this loop is the one place the three-line rule is implemented.
    Every matching statement is examined: a Deny returns immediately, because
    nothing later may override it; Allows are remembered only as "at least one
    matched". At the end, an Allow means Allow, otherwise the request falls through
    to the default, which is Deny.

    Crucially this is *not* "last matching statement wins". If it were, reordering
    the policies would change the answer; the checker evaluates both orders.
    """
    # TODO: Walk every statement of every policy. A matching Deny returns Deny immediately; remember whether any Allow matched. At the end: Allow if one matched, otherwise implicit Deny. Never let the last matching statement win.
    raise NotImplementedError("evaluate")


def _demo() -> None:
    read_only = parse_policy({
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "ReadObjects", "Effect": "Allow", "Action": "s3:Get*",
             "Resource": "arn:aws:s3:::reports/*"},
            {"Sid": "ListBucket", "Effect": "Allow", "Action": "s3:ListBucket",
             "Resource": "arn:aws:s3:::reports"},
        ],
    }, name="ReadReports")

    print("=== The three-line rule ===")
    for action, resource in [("s3:GetObject", "arn:aws:s3:::reports/q1.csv"),
                             ("s3:PutObject", "arn:aws:s3:::reports/q1.csv"),
                             ("s3:GetObject", "arn:aws:s3:::secrets/key.pem")]:
        print(f"  {action:<16}{resource:<32}{evaluate([read_only], action, resource)}")

    print("\n=== Explicit Deny beats an unconditional Allow ===")
    admin = parse_policy({"Statement": {"Effect": "Allow", "Action": "*",
                                        "Resource": "*"}}, name="Admin")
    guardrail = parse_policy({"Statement": {"Sid": "NoDeletes", "Effect": "Deny",
                                            "Action": "s3:DeleteObject",
                                            "Resource": "arn:aws:s3:::reports/*"}},
                             name="Guardrail")
    for policies, label in [([admin], "admin alone"),
                            ([admin, guardrail], "admin + guardrail"),
                            ([guardrail, admin], "guardrail + admin (swapped)")]:
        print(f"  {label:<30}{evaluate(policies, 's3:DeleteObject', 'arn:aws:s3:::reports/q1.csv')}")
    print("  Order does not matter: policies are a set, not a rule list.")

    print("\n=== Conditions gate a statement ===")
    conditional = parse_policy({"Statement": {
        "Effect": "Allow", "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::reports/*",
        "Condition": {"IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
                      "Bool": {"aws:SecureTransport": "true"}}}})
    for context, label in [
            ({"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": True}, "in VPC, TLS"),
            ({"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": False}, "in VPC, no TLS"),
            ({"aws:SourceIp": "203.0.113.9", "aws:SecureTransport": True}, "outside, TLS"),
            ({"aws:SecureTransport": True}, "TLS, no SourceIp")]:
        print(f"  {label:<22}{evaluate([conditional], 's3:GetObject', 'arn:aws:s3:::reports/q1.csv', context)}")
    print("  Conditions AND across keys, OR within one, and fail closed when a")
    print("  context key is missing — the last row is a Deny, not 'unknown'.")

    print("\n=== Eight Allows and one Deny ===")
    statements = [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}
                  for _ in range(8)]
    statements.append({"Effect": "Deny", "Action": "s3:DeleteObject", "Resource": "*"})
    policy = parse_policy({"Statement": statements}, name="ManyAllows")
    print(f"  allowed without the Deny: "
          f"{evaluate([parse_policy({'Statement': statements[:-1]})], 's3:DeleteObject', '*').allowed}")
    print(f"  with the Deny appended:   "
          f"{evaluate([policy], 's3:DeleteObject', '*')}")


if __name__ == "__main__":
    _demo()

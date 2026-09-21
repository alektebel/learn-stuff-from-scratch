"""
IAM — policy evaluation. Complete Solution.

The most valuable service to implement, because the evaluation rule is short,
counter-intuitive, and everybody gets it wrong at least once:

    1. An explicit DENY anywhere always wins.
    2. Otherwise, an explicit ALLOW grants access.
    3. Otherwise, DENY (implicit).

That is it. Everything else — wildcards, conditions, NotAction, boundaries — is
detail hung off those three lines.

DESIGN DECISION — evaluate statements in order, or partition by effect?
  Reading statements top-to-bottom and letting the last one win is how firewall
  rules work, and it is what people expect.
  CHOSEN: partition by effect. Collect every matching Deny, then every matching
  Allow. Order is irrelevant. This is what AWS actually does, and it is why
  moving a statement in a policy document never changes the outcome — a
  property worth having, and worth proving to yourself.

DESIGN DECISION — how much of the condition language to support?
  The real one has dozens of operators, set semantics, policy variables.
  CHOSEN: StringEquals, StringLike, Bool, IpAddress, NumericLessThan and
  ArnLike. Enough to show that conditions AND across keys and OR within a key —
  the rule that surprises people — without drowning in operators.
"""

import fnmatch
import ipaddress
from typing import Any, Dict, List, Optional, Sequence, Tuple

ALLOW, DENY = "Allow", "Deny"


class Statement:
    """One statement of a policy document."""

    def __init__(self, effect: str, action, resource, condition=None,
                 not_action=None, sid: str = ""):
        if effect not in (ALLOW, DENY):
            raise ValueError(f"effect must be Allow or Deny, got {effect!r}")
        self.effect = effect
        self.action = _as_list(action)
        self.not_action = _as_list(not_action) if not_action else None
        self.resource = _as_list(resource)
        self.condition: Dict[str, Dict[str, Any]] = condition or {}
        self.sid = sid

    def __repr__(self) -> str:
        return f"<{self.effect} {self.action or 'NOT ' + str(self.not_action)}>"


def _as_list(value) -> List[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


class Policy:
    def __init__(self, statements: Sequence[Statement], name: str = ""):
        self.statements = list(statements)
        self.name = name

    def __repr__(self) -> str:
        return f"<Policy {self.name or '(unnamed)'} {len(self.statements)} stmts>"


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def matches_action(pattern: str, action: str) -> bool:
    """`s3:*` matches `s3:GetObject`. Case-insensitive, like the real thing."""
    return fnmatch.fnmatch(action.lower(), pattern.lower())


def matches_resource(pattern: str, resource: str) -> bool:
    """ARN matching with `*` and `?`.

    Note `*` crosses `:` and `/` here, which is also true in AWS — a common
    surprise, since `arn:aws:s3:::bucket/*` matches every key including ones
    with slashes in them.
    """
    return fnmatch.fnmatch(resource, pattern)


def evaluate_condition(condition: Dict[str, Dict[str, Any]],
                       context: Dict[str, Any]) -> bool:
    """All condition blocks must pass; within one key, any listed value passes.

    This is the rule people get wrong: conditions AND across keys and OR within
    a key's value list. Two separate StringEquals keys must BOTH hold; two
    values under one key means either will do.
    """
    for operator, tests in condition.items():
        for key, expected in tests.items():
            actual = context.get(key)
            options = _as_list(expected) if not isinstance(expected, bool) else [expected]
            if not _condition_holds(operator, actual, options):
                return False
    return True


def _condition_holds(operator: str, actual: Any, options: List[Any]) -> bool:
    if actual is None:
        return False                      # a missing context key never matches
    if operator == "StringEquals":
        return any(str(actual) == str(option) for option in options)
    if operator == "StringNotEquals":
        return all(str(actual) != str(option) for option in options)
    if operator == "StringLike":
        return any(fnmatch.fnmatch(str(actual), str(option)) for option in options)
    if operator in ("ArnLike", "ArnEquals"):
        return any(fnmatch.fnmatch(str(actual), str(option)) for option in options)
    if operator == "Bool":
        return any(bool(actual) == (str(option).lower() == "true")
                   for option in options)
    if operator == "NumericLessThan":
        return any(float(actual) < float(option) for option in options)
    if operator == "NumericGreaterThanEquals":
        return any(float(actual) >= float(option) for option in options)
    if operator == "IpAddress":
        address = ipaddress.ip_address(str(actual))
        return any(address in ipaddress.ip_network(str(option), strict=False)
                   for option in options)
    raise ValueError(f"unsupported condition operator {operator!r}")


# ---------------------------------------------------------------------------
# The evaluation rule
# ---------------------------------------------------------------------------

class Decision:
    def __init__(self, allowed: bool, reason: str, statement: Optional[Statement] = None):
        self.allowed = allowed
        self.reason = reason
        self.statement = statement

    def __bool__(self) -> bool:
        return self.allowed

    def __repr__(self) -> str:
        return f"{'ALLOW' if self.allowed else 'DENY '}  {self.reason}"


def statement_matches(statement: Statement, action: str, resource: str,
                      context: Dict[str, Any]) -> bool:
    if statement.not_action is not None:
        # NotAction means "everything except these" — easy to reason about
        # wrongly. Combined with Allow it is a very wide grant.
        if any(matches_action(pattern, action) for pattern in statement.not_action):
            return False
    elif not any(matches_action(pattern, action) for pattern in statement.action):
        return False

    if not any(matches_resource(pattern, resource) for pattern in statement.resource):
        return False

    return evaluate_condition(statement.condition, context)


def evaluate(policies: Sequence[Policy], action: str, resource: str,
             context: Optional[Dict[str, Any]] = None) -> Decision:
    """Explicit deny > explicit allow > implicit deny.

    Note that policies are evaluated as a SET. Statement order within a policy,
    and policy order within the list, cannot change the answer — which is worth
    verifying yourself, because it is the property that makes large policy sets
    tractable to reason about.
    """
    context = context or {}
    matching_allows: List[Statement] = []

    for policy in policies:
        for statement in policy.statements:
            if not statement_matches(statement, action, resource, context):
                continue
            if statement.effect == DENY:
                return Decision(False, f"explicit Deny in {policy.name or 'policy'}"
                                       f"{' (' + statement.sid + ')' if statement.sid else ''}",
                                statement)
            matching_allows.append(statement)

    if matching_allows:
        return Decision(True, "explicit Allow", matching_allows[0])
    return Decision(False, "implicit Deny — no statement allows this")


def evaluate_with_boundary(identity: Sequence[Policy], boundary: Optional[Policy],
                           action: str, resource: str,
                           context: Optional[Dict[str, Any]] = None) -> Decision:
    """A permissions boundary caps what identity policies can grant.

    The boundary never grants anything on its own: the request must be allowed
    by BOTH the identity policies and the boundary. This is how you delegate
    "you may create roles" without also delegating "you may create admin roles".
    """
    identity_decision = evaluate(identity, action, resource, context)
    if not identity_decision.allowed:
        return identity_decision
    if boundary is None:
        return identity_decision

    boundary_decision = evaluate([boundary], action, resource, context)
    if not boundary_decision.allowed:
        return Decision(False, "blocked by permissions boundary — identity "
                               "policy allowed it, the boundary did not")
    return Decision(True, "allowed by identity policy and permissions boundary")


# ---------------------------------------------------------------------------
# STS: assuming a role
# ---------------------------------------------------------------------------

class Role:
    """A role is a permission set plus a trust policy saying who may assume it."""

    def __init__(self, arn: str, trust: Policy, permissions: Sequence[Policy]):
        self.arn = arn
        self.trust = trust
        self.permissions = list(permissions)


class Credentials:
    def __init__(self, principal: str, policies: Sequence[Policy],
                 session_name: str = "", expires_at: float = 0.0):
        self.principal = principal
        self.policies = list(policies)
        self.session_name = session_name
        self.expires_at = expires_at

    def __repr__(self) -> str:
        return f"<Credentials {self.principal} session={self.session_name!r}>"


def assume_role(caller: Credentials, role: Role, session_name: str,
                context: Optional[Dict[str, Any]] = None) -> Credentials:
    """Two checks, and forgetting either one is a real security bug.

    1. The role's TRUST policy must allow this caller to assume it.
    2. The caller's own policies must allow sts:AssumeRole on the role ARN.

    Both directions matter: the role decides who may wear it, and the caller's
    administrator decides which roles their people may wear.
    """
    context = dict(context or {})
    context.setdefault("aws:PrincipalArn", caller.principal)

    trusted = evaluate([role.trust], "sts:AssumeRole", role.arn, context)
    if not trusted.allowed:
        raise PermissionError(f"{caller.principal} is not trusted by {role.arn}: "
                              f"{trusted.reason}")

    permitted = evaluate(caller.policies, "sts:AssumeRole", role.arn, context)
    if not permitted.allowed:
        raise PermissionError(f"{caller.principal} lacks sts:AssumeRole on "
                              f"{role.arn}: {permitted.reason}")

    return Credentials(role.arn, role.permissions, session_name)


def _demo() -> None:
    read_only = Policy([
        Statement(ALLOW, "s3:Get*", "arn:aws:s3:::reports/*"),
        Statement(ALLOW, "s3:ListBucket", "arn:aws:s3:::reports"),
    ], name="ReadReports")

    print("=== The three-line rule ===")
    for action, resource in [("s3:GetObject", "arn:aws:s3:::reports/q1.csv"),
                             ("s3:PutObject", "arn:aws:s3:::reports/q1.csv"),
                             ("s3:GetObject", "arn:aws:s3:::secrets/key.pem")]:
        print(f"  {action:<16}{resource:<34}{evaluate([read_only], action, resource)}")

    print("\n=== Explicit Deny beats everything ===")
    admin = Policy([Statement(ALLOW, "*", "*")], name="Admin")
    protect = Policy([Statement(DENY, "s3:DeleteObject",
                                "arn:aws:s3:::reports/*", sid="NoDeletes")],
                     name="Guardrail")
    for policies, label in [([admin], "admin alone"),
                            ([admin, protect], "admin + guardrail"),
                            ([protect, admin], "guardrail + admin (order swapped)")]:
        decision = evaluate(policies, "s3:DeleteObject", "arn:aws:s3:::reports/q1.csv")
        print(f"  {label:<36}{decision}")
    print("Order does not matter. Policies are a SET, not a rule list — which is")
    print("what makes a large policy set tractable to reason about at all.")

    print("\n=== Conditions AND across keys, OR within one ===")
    conditional = Policy([Statement(
        ALLOW, "s3:GetObject", "arn:aws:s3:::reports/*",
        condition={"IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
                   "Bool": {"aws:SecureTransport": "true"}})], name="Conditional")
    for context, label in [
            ({"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": True}, "in VPC, TLS"),
            ({"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": False}, "in VPC, no TLS"),
            ({"aws:SourceIp": "203.0.113.9", "aws:SecureTransport": True}, "outside, TLS"),
            ({"aws:SecureTransport": True}, "TLS, source IP missing")]:
        decision = evaluate([conditional], "s3:GetObject",
                            "arn:aws:s3:::reports/q1.csv", context)
        print(f"  {label:<26}{decision}")
    print("A MISSING context key never matches. Conditions fail closed, which is")
    print("the right default and occasionally a surprising one.")

    print("\n=== NotAction is wider than it looks ===")
    wide = Policy([Statement(ALLOW, None, "*", not_action=["iam:*", "sts:*"])],
                  name="EverythingExceptIAM")
    for action in ("s3:DeleteBucket", "ec2:TerminateInstances", "iam:CreateUser"):
        print(f"  {action:<26}{evaluate([wide], action, 'arn:aws:*')}")
    print("'Allow NotAction iam:*' grants every service that will ever exist.")

    print("\n=== Permissions boundaries cap a grant ===")
    grant = [Policy([Statement(ALLOW, "*", "*")], name="Broad")]
    boundary = Policy([Statement(ALLOW, ["s3:*", "logs:*"], "*")], name="Boundary")
    for action in ("s3:GetObject", "iam:CreateUser"):
        print(f"  {action:<26}"
              f"{evaluate_with_boundary(grant, boundary, action, 'arn:aws:*')}")
    print("The boundary grants nothing by itself — it only subtracts.")

    print("\n=== STS: both directions must agree ===")
    developer = Credentials("arn:aws:iam::111:user/dev", [
        Policy([Statement(ALLOW, "sts:AssumeRole", "arn:aws:iam::111:role/Deploy")],
               name="MayAssumeDeploy")])
    deploy = Role("arn:aws:iam::111:role/Deploy",
                  trust=Policy([Statement(
                      ALLOW, "sts:AssumeRole", "arn:aws:iam::111:role/Deploy",
                      condition={"ArnLike": {
                          "aws:PrincipalArn": "arn:aws:iam::111:user/*"}})]),
                  permissions=[Policy([Statement(ALLOW, "s3:*", "*")],
                                      name="DeployPerms")])
    session = assume_role(developer, deploy, "release-42")
    print(f"  assumed: {session}")
    print(f"  can now: {evaluate(session.policies, 's3:PutObject', 'arn:aws:s3:::x/y')}")

    outsider = Credentials("arn:aws:iam::999:user/mallory", [
        Policy([Statement(ALLOW, "sts:AssumeRole", "*")], name="Optimistic")])
    try:
        assume_role(outsider, deploy, "nope")
        print("  outsider assumed the role — that is a bug")
    except PermissionError as exc:
        print(f"  outsider blocked: {exc}")
    print("The outsider's OWN policy said yes. The role's trust policy said no,")
    print("and that is the one that protects you from another account.")


if __name__ == "__main__":
    _demo()

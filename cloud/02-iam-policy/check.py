"""
Progress checker for the IAM policy templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Steps 1-2: conditions.py
# ---------------------------------------------------------------------------

def check_condition_operators() -> None:
    from conditions import condition_holds

    cases = [
        ("StringEquals", "us-east-1", ["us-east-1"], True),
        ("StringEquals", "us-east-1", ["eu-west-1"], False),
        ("StringLike", "s3:GetObject", ["s3:Get*"], True),
        ("StringLike", "s3:PutObject", ["s3:Get*"], False),
        ("StringNotEquals", "prod", ["dev", "staging"], True),
        ("StringNotEquals", "prod", ["dev", "prod"], False),
        ("Bool", True, ["true"], True),
        ("Bool", True, ["false"], False),
        ("Bool", False, ["false"], True),
        ("IpAddress", "10.1.2.3", ["10.0.0.0/8"], True),
        ("IpAddress", "203.0.113.9", ["10.0.0.0/8"], False),
        ("IpAddress", "10.1.2.3", ["2001:db8::/32"], False),
        ("NotIpAddress", "203.0.113.9", ["10.0.0.0/8"], True),
        ("NumericLessThan", "10", ["100"], True),
        ("NumericLessThan", "100", ["10"], False),
        ("NumericGreaterThanEquals", "100", ["100"], True),
        ("ArnLike", "arn:aws:iam::111:user/dev", ["arn:aws:iam::111:user/*"], True),
        ("ArnLike", "arn:aws:iam::999:user/dev", ["arn:aws:iam::111:user/*"], False),
    ]
    for operator, actual, options, want in cases:
        got = condition_holds(operator, actual, options)
        assert got is want, (
            f"condition_holds({operator!r}, {actual!r}, {options!r}) returned {got!r}, "
            f"expected {want!r}. A Bool compared as a STRING ('True' == 'true' is False) "
            "or an IP compared as an address instead of membership in the network are "
            "the usual causes.")

    assert condition_holds("StringLike", "s3:GetObject", ["s3:Get*"]) is True
    try:
        condition_holds("NoSuchOperator", "x", ["y"])
        raise AssertionError(
            "an unknown condition operator must raise ValueError, not return True: "
            "silently passing it turns a policy typo into a security hole")
    except ValueError:
        pass


def check_condition_logic() -> None:
    from conditions import evaluate_condition

    condition = {
        "StringEquals": {"aws:username": "alice"},
        "IpAddress": {"aws:SourceIp": ["10.0.0.0/8", "192.168.0.0/16"]},
    }
    # AND across keys: both hold -> True.
    assert evaluate_condition(condition, {"aws:username": "alice",
                                         "aws:SourceIp": "10.1.2.3"}) is True
    # OR within one key: the second range alone is enough.
    assert evaluate_condition(condition, {"aws:username": "alice",
                                          "aws:SourceIp": "192.168.4.4"}) is True
    # AND across keys: one key lost -> the whole condition is False.
    assert evaluate_condition(condition, {"aws:username": "bob",
                                          "aws:SourceIp": "10.1.2.3"}) is False, (
        "conditions AND across keys: aws:username does not match, so the condition "
        "must be False regardless of the IP")
    # A missing context key fails closed, for a positive operator ...
    assert evaluate_condition(condition, {"aws:username": "alice"}) is False, (
        "a condition key that is absent from the request context must fail closed")
    # ... and for a NEGATED one too. This is the case a naive implementation gets
    # wrong: str(None) != 'bob' is True, so without an explicit presence check the
    # missing key silently matches StringNotEquals and the statement applies.
    assert evaluate_condition({"StringNotEquals": {"aws:username": "bob"}}, {}) is False, (
        "a missing key must fail closed even for a negated operator; do not let "
        "str(None) compare against the value list")
    # An empty Condition always holds.
    assert evaluate_condition({}, {}) is True
    # Null tests existence, not a value.
    assert evaluate_condition({"Null": {"aws:TokenIssueTime": "true"}}, {}) is True
    assert evaluate_condition({"Null": {"aws:TokenIssueTime": "true"}},
                              {"aws:TokenIssueTime": "now"}) is False
    assert evaluate_condition({"Null": {"aws:TokenIssueTime": "false"}},
                              {"aws:TokenIssueTime": "now"}) is True


# ---------------------------------------------------------------------------
# Steps 3-5: policy.py — parsing and matching
# ---------------------------------------------------------------------------

def check_parse_policy() -> None:
    from policy import Policy, Statement, parse_policy, ALLOW

    document = {
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "ReadObjects", "Effect": "Allow",
             "Action": ["s3:GetObject", "s3:ListBucket"],
             "Resource": "arn:aws:s3:::reports/*",
             "Condition": {"StringEquals": {"aws:username": "alice"}}},
            {"Effect": "Deny", "Action": "s3:DeleteObject", "Resource": "*"},
        ],
    }
    # A decoded dict and the JSON string must produce the same policy.
    for source in (document, __import__("json").dumps(document)):
        policy = parse_policy(source, name="demo")
        assert isinstance(policy, Policy), f"parse_policy returned {type(policy).__name__}"
        assert policy.name == "demo" and len(policy.statements) == 2
        first = policy.statements[0]
        assert isinstance(first, Statement)
        assert first.effect == ALLOW and first.sid == "ReadObjects"
        assert first.action == ["s3:GetObject", "s3:ListBucket"], (
            f"Action should normalise to a list, got {first.action!r}")
        assert first.resource == ["arn:aws:s3:::reports/*"], (
            f"a scalar Resource should become a one-element list, got {first.resource!r}")
        assert first.condition == {"StringEquals": {"aws:username": "alice"}}, (
            "the Condition element was dropped or reshaped by parsing")
    # A single Statement may be a dict, not a one-element list.
    single = parse_policy({"Statement": {"Effect": "Allow", "Action": "*",
                                         "Resource": "*"}})
    assert len(single.statements) == 1, (
        "a policy whose Statement is a single object (not a list) must parse to one "
        "statement")
    # A malformed Effect must fail loudly, never silently become a no-op.
    try:
        parse_policy({"Statement": {"Effect": "allow", "Action": "*", "Resource": "*"}})
        raise AssertionError("Effect 'allow' (lower-case) must raise ValueError")
    except ValueError:
        pass


def check_action_wildcards() -> None:
    from policy import matches_action

    assert matches_action("s3:*", "s3:GetObject") is True
    assert matches_action("s3:Get*", "s3:GetObject") is True
    assert matches_action("s3:Get*", "s3:PutObject") is False
    assert matches_action("*", "iam:CreateUser") is True
    assert matches_action("s3:?etObject", "s3:GetObject") is True
    assert matches_action("s3:?etObject", "s3:GetObjectExtra") is False
    assert matches_action("s3:*", "ec2:DescribeInstances") is False
    assert matches_action("s3:getobject", "s3:GetObject") is True, (
        "action matching is case-INSENSITIVE in IAM: lower-case both sides before "
        "the wildcard match")
    assert matches_action("S3:GET*", "s3:getobject") is True


def check_resource_wildcards() -> None:
    from policy import matches_resource

    assert matches_resource("arn:aws:s3:::reports/*", "arn:aws:s3:::reports/2024/q1.csv") is True, (
        "* must span '/' — arn:aws:s3:::reports/* covers keys with slashes in them")
    assert matches_resource("arn:aws:s3:::reports/*", "arn:aws:s3:::reports/a/b/c") is True
    assert matches_resource("arn:aws:s3:::reports/*", "arn:aws:s3:::secrets/key.pem") is False
    assert matches_resource("*", "arn:aws:ec2:us-east-1:111:instance/i-1") is True
    assert matches_resource("arn:aws:iam::111:user/?", "arn:aws:iam::111:user/a") is True
    assert matches_resource("arn:aws:iam::111:user/?", "arn:aws:iam::111:user/ab") is False
    assert matches_resource("arn:aws:s3:::Reports/*", "arn:aws:s3:::reports/x") is False, (
        "resource matching is case-SENSITIVE: do not case-fold ARNs")


# ---------------------------------------------------------------------------
# Steps 6-9: policy.py — the evaluation rule
# ---------------------------------------------------------------------------

def _conditional_policy():
    from policy import parse_policy
    return parse_policy({"Statement": {
        "Effect": "Allow", "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::reports/*",
        "Condition": {"IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
                      "Bool": {"aws:SecureTransport": "true"}}}})


def check_conditions_gate_statement() -> None:
    from policy import evaluate

    policy = _conditional_policy()
    resource = "arn:aws:s3:::reports/q1.csv"
    assert evaluate([policy], "s3:GetObject", resource,
                    {"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": True}).allowed is True
    for context, why in [
            ({"aws:SourceIp": "203.0.113.9", "aws:SecureTransport": True},
             "the source IP is outside 10.0.0.0/8"),
            ({"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": False},
             "the request is not over TLS"),
            ({"aws:SecureTransport": True}, "aws:SourceIp is missing (fail closed)"),
            ({}, "the request carries no condition keys at all")]:
        assert evaluate([policy], "s3:GetObject", resource, context).allowed is False, (
            f"the condition should have blocked the statement because {why}; a gated "
            "statement whose condition fails must NOT apply")
    # The action still has to match: a condition cannot widen the statement.
    assert evaluate([policy], "s3:PutObject", resource,
                    {"aws:SourceIp": "10.1.2.3", "aws:SecureTransport": True}).allowed is False


def check_evaluation_order() -> None:
    from policy import Decision, evaluate, parse_policy

    allow = parse_policy({"Statement": {"Effect": "Allow", "Action": "s3:GetObject",
                                        "Resource": "arn:aws:s3:::reports/*"}})
    deny = parse_policy({"Statement": {"Sid": "Secret", "Effect": "Deny",
                                       "Action": "s3:GetObject",
                                       "Resource": "arn:aws:s3:::reports/secret/*"}})
    resource = "arn:aws:s3:::reports/secret/keys.txt"

    decision = evaluate([allow], "s3:GetObject", resource)
    assert isinstance(decision, Decision) and decision.allowed is True, (
        "an explicit Allow must grant the request")
    assert evaluate([allow], "s3:PutObject", resource).allowed is False, (
        "with no matching statement the default is an implicit DENY")
    assert evaluate([allow, deny], "s3:GetObject", resource).allowed is False, (
        "once a matching Deny is present the request must be denied")
    assert evaluate([deny, allow], "s3:GetObject", resource).allowed is False, (
        "the answer must not depend on policy order: an explicit Deny wins in either "
        "order. If swapping them changed the result you are letting the LAST matching "
        "statement win, firewall-style.")
    assert evaluate([allow, deny], "s3:GetObject", resource).allowed is False


def check_explicit_deny_beats_many_allows() -> None:
    from policy import evaluate, parse_policy

    allows = [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"} for _ in range(8)]
    deny = {"Sid": "NoDeletes", "Effect": "Deny", "Action": "s3:DeleteObject",
            "Resource": "*"}
    action, resource = "s3:DeleteObject", "arn:aws:s3:::reports/q1.csv"

    # Control: the Allow statements really do match on their own.
    assert evaluate([parse_policy({"Statement": allows})], action, resource).allowed is True, (
        "the eight Allow statements should grant the action; if they do not, the "
        "test below proves nothing")
    # The Deny wins wherever it sits among them.
    for position in ("first", "middle", "last"):
        statements = list(allows)
        if position == "first":
            statements.insert(0, deny)
        elif position == "middle":
            statements.insert(4, deny)
        else:
            statements.append(deny)
        decision = evaluate([parse_policy({"Statement": statements})], action, resource)
        assert decision.allowed is False, (
            f"an explicit Deny with {position} position among eight Allows must still "
            "win: collect every matching Deny before considering Allows, never stop at "
            "the first Allow")
        assert "Deny" in decision.reason


def check_missing_action_is_implicit_deny() -> None:
    from policy import Decision, evaluate, parse_policy

    policy = parse_policy({"Statement": {"Effect": "Allow", "Action": "s3:Get*",
                                         "Resource": "arn:aws:s3:::reports/*"}})
    # An action no statement mentions: implicit deny, and an ordinary result — not an
    # exception, and not None.
    decision = evaluate([policy], "ec2:TerminateInstances", "arn:aws:s3:::reports/q1.csv")
    assert isinstance(decision, Decision), (
        f"a missing action must return a Decision, got {type(decision).__name__}: the "
        "default is an implicit Deny, not an error")
    assert decision.allowed is False, (
        "an action that no statement allows must be an implicit DENY")

    empty = evaluate([], "s3:GetObject", "arn:aws:s3:::reports/q1.csv")
    assert isinstance(empty, Decision) and empty.allowed is False, (
        "with no policies at all the default is still an implicit Deny, not an error")

    wrong_resource = evaluate([policy], "s3:GetObject",
                              "arn:aws:ec2:us-east-1:111:instance/i-1")
    assert isinstance(wrong_resource, Decision) and wrong_resource.allowed is False, (
        "a resource no statement covers must be an implicit Deny")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("conditions.py", "operator table: string, bool, IP, numeric, ARN", check_condition_operators),
    ("conditions.py", "AND across keys, OR within a key, fail closed", check_condition_logic),
    ("policy.py",     "parse a policy document (dict and JSON)", check_parse_policy),
    ("policy.py",     "action wildcards, case-insensitive", check_action_wildcards),
    ("policy.py",     "resource wildcards, case-sensitive", check_resource_wildcards),
    ("policy.py",     "conditions gate a statement", check_conditions_gate_statement),
    ("policy.py",     "explicit deny > allow > implicit deny", check_evaluation_order),
    ("policy.py",     "explicit deny beats eight allows", check_explicit_deny_beats_many_allows),
    ("policy.py",     "a missing action is an implicit deny", check_missing_action_is_implicit_deny),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}IAM Policy From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built an IAM policy evaluator.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

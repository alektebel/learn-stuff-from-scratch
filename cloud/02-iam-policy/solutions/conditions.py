"""
IAM policy conditions — the `Condition` element, from scratch.

Source: AWS docs, "IAM policy evaluation logic" (awsiam:evaluation) and "IAM JSON
policy elements: Condition operators". A condition is a *gate* on a statement: the
statement's Effect only applies when the request context satisfies every condition
block. Two rules, and the second is the one people get wrong:

    1. AND across operator blocks and their keys: every key named must hold.
    2. OR within one key's value list: a key with several allowed values matches
       when any one of them matches.

A third rule is a security property, not a convenience:

    3. A condition key that is absent from the request context fails closed. The
       values cannot "not match", so the statement does not apply.

DESIGN DECISION — an operator table, or a grammar over a condition language?
  The real language has ~40 operators, set qualifiers (ForAllValues / ForAnyValue),
  `...IfExists`, policy variables and date math. Writing a parser for it would be a
  week of work that teaches tokenising, not authorisation.
  CHOSEN: a flat operator table — `condition_holds` is a dispatch on the operator
  name over one actual value and a list of policy values. It is honest about what
  it supports (an unknown operator raises, it does not silently pass), and it makes
  the AND/OR rule above the visible structure of `evaluate_condition`.
  COST: no `ForAllValues`/`ForAnyValue`, no `...IfExists`, no policy variables.

DESIGN DECISION — negated operators over a value list: OR or AND?
  `StringNotEquals` with `["b", "c"]` reads naturally as "neither b nor c", which is
  AND across the list, while `StringEquals` is OR. The set changes between the
  positive and negated operators, which is exactly the kind of detail that is easy
  to get backwards.
  CHOSEN: positive operators `any(...)`, negated operators `all(...)`. The rule is
  "the list is a set of allowed values; a positive operator matches if the actual
  is in it, a negated one matches if it is not."

DESIGN DECISION — the docs say a negated operator with a missing key is *true*
  ("if the policy condition requires that the key is not matched ... and the right
  key is not present, the condition is true"). Modelling that faithfully makes
  missing-key behaviour depend on the operator's polarity, which is a footgun.
  CHOSEN: fail closed for every operator when the key is missing. Strictly safer,
  and the difference is called out in the README.
"""

import fnmatch
import ipaddress
from typing import Any, Dict, List

# Positive operators match when the actual value matches ANY listed value; negated
# operators match when it matches NONE. Named here so the rule is data, not code.
NEGATED_OPERATORS = {
    "StringNotEquals", "StringNotEqualsIgnoreCase", "StringNotLike",
    "ArnNotEquals", "ArnNotLike", "NumericNotEquals", "NotIpAddress",
}

_NUMERIC = {
    "NumericEquals": lambda a, b: a == b,
    "NumericNotEquals": lambda a, b: a != b,
    "NumericLessThan": lambda a, b: a < b,
    "NumericLessThanEquals": lambda a, b: a <= b,
    "NumericGreaterThan": lambda a, b: a > b,
    "NumericGreaterThanEquals": lambda a, b: a >= b,
}


def _as_list(value: Any) -> List[Any]:
    """A JSON condition value may be a scalar or a list. Normalise to a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def condition_holds(operator: str, actual: Any, options: List[Any]) -> bool:
    """Does one operator hold for `actual` against the allowed values `options`?

    `actual` is already known to be present in the request context (the missing-key
    rule lives in `evaluate_condition`). "options" is the value list from the
    policy, always normalised to a list.

    Returns a real bool, and raises ValueError for an operator it does not know:
    silently passing an unknown operator would turn a typo into a security hole.
    """
    strings = [str(option) for option in options]

    if operator == "StringEquals":
        return any(str(actual) == option for option in strings)
    if operator == "StringNotEquals":
        return all(str(actual) != option for option in strings)
    if operator == "StringEqualsIgnoreCase":
        return any(str(actual).lower() == option.lower() for option in strings)
    if operator == "StringNotEqualsIgnoreCase":
        return all(str(actual).lower() != option.lower() for option in strings)
    if operator == "StringLike":
        return any(fnmatch.fnmatchcase(str(actual), option) for option in strings)
    if operator == "StringNotLike":
        return all(not fnmatch.fnmatchcase(str(actual), option) for option in strings)
    if operator in ("ArnLike", "ArnEquals"):
        return any(fnmatch.fnmatchcase(str(actual), option) for option in strings)
    if operator in ("ArnNotLike", "ArnNotEquals"):
        return all(not fnmatch.fnmatchcase(str(actual), option) for option in strings)
    if operator == "Bool":
        return any(bool(actual) == (option.lower() == "true") for option in strings)
    if operator == "IpAddress":
        address = ipaddress.ip_address(str(actual))
        return any(address in ipaddress.ip_network(option, strict=False)
                   for option in strings)
    if operator == "NotIpAddress":
        address = ipaddress.ip_address(str(actual))
        return all(address not in ipaddress.ip_network(option, strict=False)
                   for option in strings)
    if operator in _NUMERIC:
        compare = _NUMERIC[operator]
        if operator == "NumericNotEquals":
            return all(compare(float(actual), float(option)) for option in strings)
        return any(compare(float(actual), float(option)) for option in strings)

    raise ValueError(f"unsupported condition operator {operator!r}")


def evaluate_condition(condition: Dict[str, Dict[str, Any]],
                       context: Dict[str, Any]) -> bool:
    """AND across keys, OR within one key's value list. Missing key: fails closed.

    Structure of a Condition element:

        {"StringEquals": {"aws:username": "alice"},     # block 1
         "IpAddress":    {"aws:SourceIp": ["10.0.0.0/8", "192.168.0.0/16"]}}  # block 2

    block 1 AND block 2 must both hold (the outer loop returns False on the first
    failure). Inside block 2, `aws:SourceIp` may be in either range (the operator,
    not the caller, decides OR). This asymmetry — AND across blocks, OR within one
    — is the rule people get wrong.

    `Null` is special: it tests whether a key *exists* rather than comparing it, so
    `"Null": {"aws:TokenIssueTime": "true"}` means "the key is absent" and "false"
    means "the key is present". It is handled before the missing-key check because
    absence is the thing it is asking about.
    """
    if not condition:
        return True

    for operator, tests in condition.items():
        for key, expected in tests.items():
            options = _as_list(expected)

            if operator == "Null":
                present = key in context and context[key] is not None
                wants_absent = any(str(option).lower() == "true" for option in options)
                if present == wants_absent:
                    return False
                continue

            if key not in context:
                # Fail closed: a key the policy names but the request does not carry
                # cannot satisfy the condition.
                return False
            if not condition_holds(operator, context[key], options):
                return False

    return True


def _demo() -> None:
    print("=== The operator table ===")
    rows = [
        ("StringEquals", "us-east-1", ["us-east-1"]),
        ("StringLike", "s3:GetObject", ["s3:Get*"]),
        ("StringNotEquals", "prod", ["dev", "staging"]),
        ("Bool", True, ["true"]),
        ("IpAddress", "10.1.2.3", ["10.0.0.0/8"]),
        ("IpAddress", "203.0.113.9", ["10.0.0.0/8"]),
        ("NumericLessThan", "10", ["100"]),
        ("ArnLike", "arn:aws:iam::111:user/dev", ["arn:aws:iam::111:user/*"]),
    ]
    for operator, actual, options in rows:
        print(f"  {operator:<22}{str(actual):<28}{options!s:<30}"
              f"{condition_holds(operator, actual, options)}")
    print("  unknown operator raises: "
          f"{_raises(lambda: condition_holds('NoSuchOp', 'x', ['y']))}")

    print("\n=== AND across keys, OR within one ===")
    condition = {
        "StringEquals": {"aws:username": "alice"},
        "IpAddress": {"aws:SourceIp": ["10.0.0.0/8", "192.168.0.0/16"]},
    }
    cases = [
        ({"aws:username": "alice", "aws:SourceIp": "10.1.2.3"}, "alice, in 10/8"),
        ({"aws:username": "alice", "aws:SourceIp": "192.168.4.4"}, "alice, in 192.168/16"),
        ({"aws:username": "bob", "aws:SourceIp": "10.1.2.3"}, "bob, in 10/8"),
        ({"aws:username": "alice"}, "alice, no SourceIp"),
        ({}, "empty context"),
    ]
    for context, label in cases:
        print(f"  {label:<26}{evaluate_condition(condition, context)}")
    print("  Two keys must BOTH hold; two IP ranges mean EITHER. A missing key")
    print("  fails closed, so the last two rows are False, not 'unknown'.")

    print("\n=== Null asks about existence, not value ===")
    for expected, context, label in [
            ("true", {}, "absent, Null=true"),
            ("true", {"aws:TokenIssueTime": "2026-01-01T00:00:00Z"}, "present, Null=true"),
            ("false", {"aws:TokenIssueTime": "2026-01-01T00:00:00Z"}, "present, Null=false")]:
        got = evaluate_condition({"Null": {"aws:TokenIssueTime": expected}}, context)
        print(f"  {label:<32}{got}")


def _raises(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


if __name__ == "__main__":
    _demo()

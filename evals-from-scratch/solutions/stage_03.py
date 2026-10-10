"""Evals From Scratch — stage 3: deterministic assertions

SOLUTION. Every check returns (passed, detail) or raises, and the runner turns
the raise into a third state that is neither pass nor fail. The detail is not
decoration: it is the only thing a reader of the report has to work with.
"""

import json


def check(name, fn):
    if not callable(fn):
        raise TypeError(f"check {name!r} has a non-callable body")
    return {"name": name, "fn": fn}


def json_valid(record):
    text = record.get("output")
    if text is None:
        return False, "row has no 'output' field to parse"
    if not isinstance(text, str):
        return False, f"'output' is {type(text).__name__}, not a string"
    stripped = text.strip()
    if not stripped:
        return False, "'output' is empty"
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return False, f"not JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})"
    if not isinstance(value, dict):
        return False, f"valid JSON, but a {type(value).__name__}, not an object"
    return True, "a JSON object"


def has_fields(*fields):
    def predicate(record):
        passed, detail = json_valid(record)
        if not passed:
            return False, detail
        parsed = json.loads(record["output"].strip())
        missing = [name for name in fields
                   if name not in parsed or parsed[name] is None]
        if missing:
            return False, "missing field(s): " + ", ".join(missing)
        return True, "all fields present: " + ", ".join(fields)
    return predicate


def run_checks(records, checks):
    results = []
    for record in records:
        rid = record.get("id")
        for item in checks:
            name = item["name"]
            try:
                outcome = item["fn"](record)
            except Exception as exc:                  # noqa: BLE001 - by design
                results.append({"id": rid, "check": name, "state": "errored",
                                "detail": f"{type(exc).__name__}: {exc}"})
                continue
            if not isinstance(outcome, tuple) or len(outcome) != 2:
                results.append({"id": rid, "check": name, "state": "errored",
                                "detail": f"returned {outcome!r}; a check returns "
                                          f"(passed, detail)"})
                continue
            passed, detail = outcome
            if not isinstance(passed, bool):
                results.append({"id": rid, "check": name, "state": "errored",
                                "detail": f"first element is "
                                          f"{type(passed).__name__}, not a bool"})
                continue
            results.append({"id": rid, "check": name,
                            "state": "passed" if passed else "failed",
                            "detail": str(detail)})
    return results


def summarise(results):
    results = list(results)
    counts = {"passed": 0, "failed": 0, "errored": 0}
    failures = {}
    for result in results:
        state = result["state"]
        counts[state] = counts.get(state, 0) + 1
        if state == "failed":
            failures[result["check"]] = failures.get(result["check"], 0) + 1
    total = len(results)
    return {"n_records": len({r["id"] for r in results}),
            "checks": len({r["check"] for r in results}),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "errored": counts["errored"],
            "pass_rate": counts["passed"] / total if total else 0.0,
            "failures_by_check": failures}

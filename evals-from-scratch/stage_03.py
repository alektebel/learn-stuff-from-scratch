"""Evals From Scratch — stage 3: deterministic assertions, and the error that is not a pass

DESIGN DECISION — assert the cheap structural things first.
    Valid JSON, a required field, a type, an enum, a tool call with a known
    name: these are decided by code, they cost nothing, they never drift, and
    they catch the majority of real regressions (a prompt edit that quietly
    drops a field; a model upgrade that starts wrapping JSON in prose). A judge
    should never be asked a question a parser can answer.

DESIGN DECISION — a check that raises is an ERROR, never a pass and never a crash.
    The most common silent bug in a home-made harness is `try: check() except:
    pass` around a loop, which turns every broken assertion into a green tick.
    The second most common is letting the exception escape and losing the whole
    run. A check's outcome is one of three states with the reason attached:
    passed, failed, errored.

TODO: implement

    check(name, fn) -> dict
        {"name", "fn"} — a name for the report, a predicate to run.

    json_valid(record) -> (bool, str)
        Strictly: json.loads on the output, whitespace allowed around it, and
        nothing else. Prose around the object, or a ```json fence, fails — the
        shape you accept is the shape your prompt can drift into, and a lax
        parser hides that drift.

    has_fields(*fields) -> predicate
        True when every named field is present and non-null. Extra fields are
        fine, so the check does not fail on a harmless addition.

    run_checks(records, checks) -> list[dict]
        One row per (record, check):
            {"id": record["id"], "check": name, "state": "passed"|"failed"|"errored",
             "detail": str}
        A predicate returning a non-tuple, or raising, or returning a truthy
        non-bool, becomes "errored" with the reason — never "passed".

    summarise(results) -> dict
        {"n_records", "checks", "passed", "failed", "errored",
         "pass_rate", "failures_by_check": {check: count}}
        pass_rate is the fraction of (record, check) pairs that PASSED — the
        denominator is every pair that ran, because a check that errored did
        not pass. Counting errored rows as anything else is how a harness
        reports 100% while half its checks never executed.
"""


def check(name, fn):
    raise NotImplementedError("stage 3: implement check()")


def json_valid(record):
    raise NotImplementedError("stage 3: implement json_valid()")


def has_fields(*fields):
    raise NotImplementedError("stage 3: implement has_fields()")


def run_checks(records, checks):
    raise NotImplementedError("stage 3: implement run_checks()")


def summarise(results):
    raise NotImplementedError("stage 3: implement summarise()")

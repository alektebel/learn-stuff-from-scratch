"""
Progress checker for the offline half of aws-deploy.

    python3 check.py --all

SKELETON. Checks named, bodies unwritten. See ../../TODO.md section 11.

WHAT THIS GRADES
----------------
Artifacts, offline. A policy document, a template, a cost model and a deploy
state machine are all just data, and all four can be linted before anything is
applied to a real account. Nothing here makes a network call, needs a
credential, or costs money.

WHAT IT CANNOT GRADE
--------------------
Whether you can actually ship. That is RUNBOOK.md -- a real account, a real
domain, a real failed build, and the hour you lose to DNS. There is no
substitute and no checker for it.

The measurable version of "I control this" is at the end of the runbook:
rebuild the whole stack from an empty account, from code, in under an hour, and
tear it back down to a zero bill. Do that twice and you control it.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_no_long_lived_keys() -> None:
    """A static access key where a session belongs, found before it ships.

    TODO: assert `is_long_lived` flags an AKIA-style static key and does NOT
    flag a session with an expiry; assert `audit_credential_sources` finds a key
    in a file, an env var and a git-tracked path; assert `redact` never returns
    a full secret. This check is worth more than the other nine combined.
    """
    raise NotImplementedError


def check_least_privilege() -> None:
    """Does this policy grant more than the named actions need.

    TODO: assert `excess_over` returns the extra actions a policy allows beyond
    a required set, and returns EMPTY for a tight policy. Include a policy that
    is tight on actions and wide on Resource -- if your check only compares
    action lists it will pass that one, and that one is the real-world case.
    """
    raise NotImplementedError


def check_wildcard_writes() -> None:
    """`"Action": "s3:*"` on `"Resource": "*"` is the one to catch every time.

    TODO: assert wildcards are flagged on WRITE actions and tolerated on
    explicitly read-only ones. Reuse week 1's evaluation rule -- an explicit
    Deny still wins, so a wildcard Allow under a Deny boundary is not a finding.
    """
    raise NotImplementedError


def check_dependency_order() -> None:
    """Nothing may depend on a resource created after it.

    TODO: assert a valid template orders correctly, that a cycle is REPORTED
    rather than deadlocking or silently dropping an edge, and that an implicit
    dependency (a reference inside a property) is picked up -- explicit
    DependsOn only is the version that passes tests and fails in production.
    """
    raise NotImplementedError


def check_rollback_and_teardown() -> None:
    """A failure mid-apply leaves nothing behind, and teardown leaves no orphans.

    TODO: inject a failure at each position in the apply order and assert the
    rollback plan removes exactly what was created -- no more, no less. Then
    assert `orphans_after_teardown` is empty, including for resources with a
    retain policy, which are the ones that quietly keep billing.
    """
    raise NotImplementedError


def check_idle_burn() -> None:
    """What this stack costs at 3am with no users.

    TODO: assert `bills_while_idle` names the per-hour resources (NAT gateway,
    unattached elastic IP, load balancer, provisioned IOPS, idle database) and
    NOT the per-request ones. Assert `idle_hourly_cost` of a serverless stack is
    ~0 and of a stack with a NAT gateway is not. Verify the rates against the
    current price sheet -- the numbers move, the categories do not.
    """
    raise NotImplementedError


def check_alarm_before_spend() -> None:
    """The budget alarm must fire BEFORE the amount you would mind.

    TODO: assert `budget_threshold` sits below the free-tier boundary and below
    a stated pain threshold, and that `alarm_before_spend` returns False when
    the forecast crosses the limit sooner than the alarm period can detect it.
    An alarm that fires monthly cannot catch a resource that bills hourly.
    """
    raise NotImplementedError


def check_deploy_states_are_safe() -> None:
    """Fail at every step; end somewhere safe every time.

    TODO: inject a failure at each transition and assert `is_safe_state` holds
    for the terminal state in ALL of them. Include the nasty one: health check
    passes, then fails after promotion. A pipeline that has never been failed on
    purpose has not been tested.
    """
    raise NotImplementedError


def check_health_gate() -> None:
    """A green deploy that serves errors is a failed deploy.

    TODO: assert the gate rejects a deploy whose health check returns 200 on the
    wrong content, and that it waits out a cold start rather than failing it.
    Assert promotion cannot happen while the gate is open.
    """
    raise NotImplementedError


def check_runbook_is_separate() -> None:
    """The real-account half must never become a check.

    TODO: assert no module here imports anything network-capable, and that
    RUNBOOK.md exists. This directory only works if the boundary between "lint
    the artifact" and "do it on a real account" stays visible.
    """
    raise NotImplementedError


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("credentials.py", "a static key where a session belongs",
     check_no_long_lived_keys),
    ("policy.py", "granted minus needed", check_least_privilege),
    ("policy.py", "wildcards on writes", check_wildcard_writes),
    ("template.py", "implicit dependencies, and cycles reported",
     check_dependency_order),
    ("template.py", "roll back to nothing; tear down to nothing",
     check_rollback_and_teardown),
    ("guard.py", "what bills at 3am with no users", check_idle_burn),
    ("guard.py", "the alarm must be faster than the spend",
     check_alarm_before_spend),
    ("deploy.py", "fail at every step, end safe every time",
     check_deploy_states_are_safe),
    ("deploy.py", "200 on the wrong content is not healthy", check_health_gate),
    ("check.py", "the runbook stays out of the graded layer",
     check_runbook_is_separate),
]


def run_one(check):
    try:
        check(); return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}AWS Deploy — progress check{RESET}")
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
            print(f"      {GREY}"
                  f"{('not implemented yet — ' + detail) if detail else 'CHECK NOT WRITTEN — see the TODO in its docstring'}"
                  f"{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — now go do RUNBOOK.md on a real account.{RESET}")
        print(f"  {GREY}Now run each file's own demo.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}Write the CHECK first (in check.py), then "
              f"{filename}. There is no solutions/ here.{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

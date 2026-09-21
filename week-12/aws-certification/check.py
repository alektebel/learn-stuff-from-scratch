"""
Progress checker for the AWS certification layer.

    python3 check.py --all

SKELETON. Checks named, bodies unwritten. See ../../TODO.md section 10.

WHAT THIS FILE DOES AND DOES NOT GRADE
--------------------------------------
It grades REASONING: given constraints, does your decision procedure pick the
right service, and does the arithmetic behind the pick come out right. That is
the derivable half of an AWS exam and it is the half `aws-from-scratch` set you
up for.

It does NOT grade `drill.py`. Quotas, defaults and service names are arbitrary
facts -- not derivable, not worth understanding, only worth remembering -- and
grading them here would blur the one distinction this directory exists to keep
sharp. Run the drill daily; run this when you change a decision rule.

Do not trust either against a real exam blueprint without checking the current
official exam guide. Blueprints change, exam codes change, and services are
renamed and retired.
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


def check_elimination() -> None:
    """A wrong answer must be eliminated by a NAMED constraint.

    TODO: for each scenario, assert `eliminate` rejects every distractor and
    names which requirement killed it. The exam rewards elimination, and a
    procedure that only returns a winner cannot tell you why it was not the
    other one -- which is exactly the case where you get it wrong.
    """
    raise NotImplementedError


def check_decision_is_not_a_lookup() -> None:
    """Change one requirement, get a different service.

    TODO: hold a scenario fixed and vary ONE constraint at a time (consistency,
    RPO, latency ceiling, budget). Assert the chosen service changes at the
    boundary you can compute. A decision table that returns the same answer
    across a boundary has memorised the scenario, not the rule.
    """
    raise NotImplementedError


def check_storage_arithmetic() -> None:
    """Lifecycle savings and retrieval times, computed not recalled.

    TODO: reuse the minimum-object-size and minimum-duration rules already
    checked in aws-from-scratch/pricing.py. Assert a transition that LOSES
    money for small objects, and one that loses money for short-lived ones --
    both are standard exam traps and both are arithmetic.
    """
    raise NotImplementedError


def check_ebs_ceilings() -> None:
    """IOPS and throughput both cap, and the binding one flips with block size.

    TODO: assert that for small blocks IOPS binds and for large blocks
    throughput binds, and that `ebs_for_workload` picks the cheaper volume type
    that clears BOTH. A check that only tests IOPS will pass a wrong answer on
    every sequential workload.
    """
    raise NotImplementedError


def check_reachability() -> None:
    """Given a topology, does the packet actually arrive.

    TODO: build subnets, route tables and gateways, then assert reachability
    for private-to-internet via NAT, private-to-S3 via a gateway endpoint, and
    a case that is NOT reachable because of a missing return route. Include the
    asymmetric-routing case -- it is the one people answer from intuition.
    """
    raise NotImplementedError


def check_connectivity_choice() -> None:
    """Six ways to join two networks, chosen on stated constraints.

    TODO: assert Direct Connect wins on guaranteed bandwidth, VPN wins on
    time-to-provision, Transit Gateway wins past N VPCs (compute the N where
    peering's mesh overtakes it), and that a stated encryption requirement
    eliminates the options that lack it.
    """
    raise NotImplementedError


def check_dr_patterns() -> None:
    """RPO and RTO as numbers, and cost as the thing you trade for them.

    TODO: assert RTO ordering across backup-restore, pilot light, warm standby
    and multi-site; assert standing cost orders the OTHER way; and assert
    `pattern_for` picks the cheapest pattern clearing a stated RPO/RTO -- not
    the best one. Picking the best is the most common wrong answer.
    """
    raise NotImplementedError


def check_inference_options() -> None:
    """Real-time, serverless, async and batch are one curve, not four products.

    TODO: assert `inference_option_for` picks by payload size, latency ceiling,
    traffic shape and idle fraction; and that serverless beats provisioned
    below a computed utilisation crossover -- the same shape as the DynamoDB
    provisioned/on-demand crossover you already derived.
    """
    raise NotImplementedError


def check_wellarchitected_tradeoffs() -> None:
    """A review with no findings is a review that was not done.

    TODO: run `review` on an architecture with a deliberate cost/reliability
    tension and assert it reports a TRADE-OFF rather than clean marks on both
    pillars. Assert `highest_risk` names the pillar that actually fails first.
    """
    raise NotImplementedError


def check_drill_is_separate() -> None:
    """The recall layer must not leak into the graded layer.

    TODO: assert no module graded above imports `drill`, and that `drill.py`
    contains no derivable content -- only arbitrary facts. This check exists to
    keep the boundary honest as the directory grows.
    """
    raise NotImplementedError


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("decide.py", "eliminated by a NAMED constraint", check_elimination),
    ("decide.py", "change one requirement, change the answer",
     check_decision_is_not_a_lookup),
    ("storage.py", "lifecycle transitions that LOSE money",
     check_storage_arithmetic),
    ("storage.py", "IOPS or throughput — which one binds", check_ebs_ceilings),
    ("network.py", "does the packet arrive, and back", check_reachability),
    ("network.py", "six ways to join two networks", check_connectivity_choice),
    ("resilience.py", "cheapest pattern that clears the RPO, not the best",
     check_dr_patterns),
    ("mlstack.py", "four inference options on one curve",
     check_inference_options),
    ("wellarchitected.py", "a trade-off, not six green ticks",
     check_wellarchitected_tradeoffs),
    ("drill.py", "recall stays out of the graded layer",
     check_drill_is_separate),
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

    print(f"\n{BOLD}AWS Certification — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — now go do the drill, daily.{RESET}")
        print(f"  {GREY}Now run each file's own demo.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}Write the CHECK first (in check.py), then "
              f"{filename}. There is no solutions/ here.{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

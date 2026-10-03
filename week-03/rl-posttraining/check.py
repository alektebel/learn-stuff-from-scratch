"""
Progress checker for the RL post-training templates.

    python3 check.py           # run every check, stop at the first gap
    python3 check.py 4         # run only step 4
    python3 check.py --all     # run everything

There is no solutions/ directory here on purpose. Reading an answer converts an
exercise into a transcription, so the checker is the only feedback -- which
means it has to be worth trusting, which means it must itself be verified two
ways before you rely on it. See ../../tools/verify_checks.py and ../../TODO.md.

SKELETON. The CHECKS list below is the contract: nine mechanisms from the
reading list in README.md, each stated as something measurable. The check
BODIES are not written. Each raises NotImplementedError from inside check.py,
so the runner reports the gap and points HERE rather than at your code.

Write the checks before you write any template body, and write each one so it
fails against a deliberately wrong implementation. A check that passes either
way is not a check.
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


def check_policy_gradient() -> None:
    """grad E[R] == E[R grad log pi], against central differences.

    TODO: enumerate a small state space, compute the exact gradient, show the
    REINFORCE estimator converges to it as samples grow, and assert the
    finite-difference gradient agrees to ~1e-4. Everything later assumes this.
    """
    raise NotImplementedError


def check_baselines() -> None:
    """Variance down, mean unmoved -- unless the baseline sees the action.

    TODO: measure mean and variance with no baseline, a constant baseline, a
    state baseline, and an ACTION baseline. Assert the first three share a mean
    and the fourth does not, and that variance falls across the first three.
    """
    raise NotImplementedError


def check_kl_estimators() -> None:
    """k3 is the only one both unbiased and non-negative.

    TODO: sample ratios, measure bias and variance of k1/k2/k3 against the true
    KL, and assert k1 goes negative on a real fraction of samples while k3
    never does. That fraction is the reason k3 won.
    """
    raise NotImplementedError


def check_ppo_clip() -> None:
    """The clip is one-sided per sample, and clip fraction is the diagnostic.

    TODO: assert the clipped objective equals the unclipped one inside the
    trust region; that outside it the gradient vanishes in ONE direction only;
    and that clip_fraction rises monotonically as the policy drifts.
    """
    raise NotImplementedError


def check_grpo() -> None:
    """The group mean IS the baseline, and no critic is needed.

    TODO: assert group advantages sum to ~0 within a group, that the estimator
    is unbiased against the exact gradient, and that nothing here fits a value
    function -- the property that separates GRPO from PPO.
    """
    raise NotImplementedError


def check_dr_grpo() -> None:
    """Std and length normalisation introduce a bias. Measure it, remove it.

    TODO: build groups with correlated length and return; assert length_bias is
    significantly non-zero with both normalisations on and ~0 with them off. A
    check that passes either way is not testing the correction.
    """
    raise NotImplementedError


def check_async_staleness() -> None:
    """Effective sample size falls with lag, and that sets the async budget.

    TODO: sweep generation lag, measure importance-ratio variance and ESS,
    assert ESS decreases monotonically and that usable_lag matches the
    threshold crossing.
    """
    raise NotImplementedError


def check_reward_hacking() -> None:
    """Proxy up, true down, and the KL coefficient trades them.

    TODO: assert the true reward TURNS OVER while the proxy keeps rising, and
    that raising the KL coefficient moves the turnover point. Asserting only
    that the proxy rises tests nothing -- that is what optimisers do.
    """
    raise NotImplementedError


def check_dpo_identity() -> None:
    """r = beta log(pi*/pi_ref) round-trips, up to one constant per prompt.

    TODO: build pi* from a known reward, recover the reward, and assert the
    difference is CONSTANT across responses (not zero -- that constant is
    beta log Z). Then assert the pairwise margin equals the true reward gap.
    """
    raise NotImplementedError


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("policy_gradient.py", "the identity, against finite differences",
     check_policy_gradient),
    ("baselines.py", "variance down, mean unmoved — and the one that biases",
     check_baselines),
    ("kl_estimators.py", "k1 vs k2 vs k3: unbiased AND non-negative",
     check_kl_estimators),
    ("ppo.py", "the clip is one-sided, and the clip fraction", check_ppo_clip),
    ("grpo.py", "a group mean instead of a value network", check_grpo),
    ("grpo.py", "Dr. GRPO: the length bias, measured and removed",
     check_dr_grpo),
    ("async_rl.py", "staleness, ESS, and the usable lag",
     check_async_staleness),
    ("reward_hacking.py", "proxy up, true down, KL as the knob",
     check_reward_hacking),
    ("dpo.py", "the identity round-trips up to one constant",
     check_dpo_identity),
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

    print(f"\n{BOLD}RL Post-Training — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built the estimators.{RESET}")
        print(f"  {GREY}Now run each file's own demo.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}Write the CHECK first (in check.py), then "
              f"{filename}. There is no solutions/ here.{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

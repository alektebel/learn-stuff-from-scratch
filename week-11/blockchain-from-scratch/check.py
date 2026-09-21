"""
Progress checker for the blockchain templates.

    python3 check.py           # run every check, stop at the first gap
    python3 check.py 4         # run only step 4
    python3 check.py --all     # run everything

No solutions/ here, on purpose. That makes this file the only feedback, so it
must itself be verified two ways before you trust it -- see
../../tools/verify_checks.py and ../../TODO.md.

SKELETON. The CHECKS list is the contract. The check BODIES are not written;
each raises from inside check.py so the runner points HERE rather than at your
templates. Write the checks first, and write each so it FAILS against a
deliberately wrong implementation.
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


def check_merkle() -> None:
    """One root commits to every transaction, and a proof is log2(n) hashes.

    TODO: assert proof length scales as log2(n) across several block sizes;
    that a valid proof verifies; and that changing ANY transaction changes the
    root. The last one is the property -- assert it per-transaction, not just
    for the first.
    """
    raise NotImplementedError


def check_pow() -> None:
    """Mining is a geometric random variable with mean 2^difficulty.

    TODO: measure hashes-to-block over many trials against 2^d, and assert the
    distribution is geometric (not just that the mean matches -- a constant
    would pass that). Then assert retargeting holds block time roughly stable
    when hashrate doubles.
    """
    raise NotImplementedError


def check_utxo() -> None:
    """A UTXO is spendable exactly once, and that IS the double-spend defence.

    TODO: apply a transaction, assert its inputs left the set and its outputs
    entered it, then assert a second spend of the same output is REFUSED --
    and refused by the set, not by a history scan.
    """
    raise NotImplementedError


def check_script() -> None:
    """P2PKH runs; and no opcode can jump, so every script halts.

    TODO: execute a P2PKH unlock and assert it leaves true on the stack. Then
    assert there is no jump/loop opcode, so validation cost is bounded by
    script length -- the property evm.py deliberately gives up.
    """
    raise NotImplementedError


def check_fork_choice() -> None:
    """Heaviest WORK wins, not the most blocks.

    TODO: build two chains where the longer one has less accumulated work and
    assert the heavier one is chosen. A check using equal difficulty tests
    nothing -- that is the case where length and work agree.
    """
    raise NotImplementedError


def check_nakamoto() -> None:
    """P(attacker k behind catches up) = (q/p)^k. Simulation vs closed form.

    TODO: simulate the race for several (q, k) and assert agreement with the
    closed form within sampling error. Include q > 0.5, where the probability
    is 1 and the formula stops applying.
    """
    raise NotImplementedError


def check_selfish_mining() -> None:
    """Withholding blocks earns more than your hash share, above a threshold.

    TODO: measure revenue share against hash share for a withholding strategy,
    sweeping gamma -- the fraction of honest miners that build on the
    attacker's block when it is released. Assert the threshold MOVES with
    gamma. A single-gamma check hides the actual result.
    """
    raise NotImplementedError


def check_accounts_and_replay() -> None:
    """Balances are not coins, so a signed transaction stays valid forever.

    TODO: replay a valid transaction with nonce checking disabled and assert it
    succeeds twice; enable it and assert the replay is refused. Then state, in
    one comparison, what the account model bought and what it cost.
    """
    raise NotImplementedError


def check_gas() -> None:
    """Loops mean the halting problem, so execution is bought.

    TODO: run an infinite loop and assert it TERMINATES out of gas; assert the
    sender is still charged; assert state changes are reverted; and assert gas
    consumed rises with work done.
    """
    raise NotImplementedError


def check_trie() -> None:
    """A state root commits to the whole world, including what is absent.

    TODO: assert the root changes on any state change; that an inclusion proof
    verifies; and that an EXCLUSION proof verifies for a key that is not there.
    The exclusion proof is what a plain Merkle tree cannot do.
    """
    raise NotImplementedError


def check_finality() -> None:
    """Two conflicting finalised checkpoints => >= 1/3 of stake is slashable.

    TODO: hand-build the violation -- conflicting attestations that finalise
    two incompatible checkpoints -- and assert `slashable` names at least a
    third of the stake. Same shape as raft's Figure 8 check: a safety checker
    that has never caught anything is not evidence.
    """
    raise NotImplementedError


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("chain.py", "one root, and a proof a phone can check", check_merkle),
    ("pow.py", "a lottery with a known mean, and retargeting", check_pow),
    ("utxo.py", "spendable once — the double-spend defence", check_utxo),
    ("script.py", "a stack machine with no jumps, on purpose", check_script),
    ("fork.py", "heaviest work, not most blocks", check_fork_choice),
    ("fork.py", "(q/p)^k, simulated against the closed form", check_nakamoto),
    ("fork.py", "selfish mining, and where the threshold moves",
     check_selfish_mining),
    ("accounts.py", "balances are not coins, so replay is possible",
     check_accounts_and_replay),
    ("evm.py", "loops, gas, and halting bought with money", check_gas),
    ("trie.py", "a root that proves absence too", check_trie),
    ("pos.py", "conflicting finality is ATTRIBUTABLE", check_finality),
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

    print(f"\n{BOLD}Blockchain From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built Byzantine consensus.{RESET}")
        print(f"  {GREY}Now run each file's own demo.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}Write the CHECK first (in check.py), then "
              f"{filename}. There is no solutions/ here.{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the replication templates.

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
# Steps 1-4: log.py — the replicated log algebra
# ---------------------------------------------------------------------------

def check_last_term() -> None:
    from log import Entry, last_term

    assert last_term([]) == 0, "an empty log has no term; 0 is the sentinel"
    assert last_term([Entry(3, "x")]) == 3
    assert last_term([Entry(1, "a"), Entry(2, "b"), Entry(2, "c")]) == 2


def check_up_to_date() -> None:
    from log import Entry, is_up_to_date

    old_long = [Entry(1, "a"), Entry(1, "b"), Entry(1, "c")]
    new_short = [Entry(2, "x")]
    assert is_up_to_date(new_short, old_long), (
        "a higher last term beats a longer log; comparing lengths first loses committed writes")
    assert not is_up_to_date(old_long, new_short), "the older-term log is not up to date"
    assert is_up_to_date([Entry(2, "a"), Entry(2, "b")], [Entry(2, "a")]), (
        "with equal last terms the longer log is more up to date")
    assert not is_up_to_date([Entry(2, "a")], [Entry(2, "a"), Entry(2, "b")])
    assert is_up_to_date([Entry(2, "a")], [Entry(2, "a")])
    assert is_up_to_date([], []), "two empty logs are equally up to date"


def check_choose_leader() -> None:
    from log import Entry, choose_leader

    logs = {
        "n1": [Entry(1, "x"), Entry(1, "y"), Entry(1, "z")],  # longest, stale term
        "n2": [Entry(2, "w")],                                # newest term, shortest
        "n3": [Entry(2, "u"), Entry(2, "v")],                 # newest term, longer
    }
    assert choose_leader(logs, ["n1", "n2", "n3"]) == "n3", (
        "the most up-to-date log must win: highest last term, then longest")
    assert choose_leader(logs, ["n1", "n2"]) == "n2", (
        "the newer term must beat the longer stale log")
    logs["n4"] = list(logs["n3"])
    assert choose_leader(logs, ["n3", "n4"]) == "n3", "identical logs break the tie by name"
    assert choose_leader(logs, []) is None


def check_quorum_index() -> None:
    from log import Entry, quorum_index

    e1, e2, e3 = Entry(1, "a"), Entry(1, "b"), Entry(1, "c")
    assert quorum_index({"a": [e1, e2, e3], "b": [e1], "c": [e1]}, 2) == 1, (
        "indexes 2 and 3 live on one replica; a single replica is not a quorum")
    assert quorum_index({"a": [e1, e2], "b": [e1, e2], "c": [e1]}, 2) == 2
    assert quorum_index({"a": []}, 1) == 0
    assert quorum_index({"a": [e1, e2], "b": [e1, Entry(1, "Z")], "c": [e1]}, 2) == 1, (
        "replicas holding different entries at an index do not form a quorum for it")


# ---------------------------------------------------------------------------
# Steps 5-10: cluster.py — replication, failover, fencing
# ---------------------------------------------------------------------------

def check_sync_replicates() -> None:
    from cluster import ReplicaSet

    rs = ReplicaSet(["A", "B", "C"], mode="sync")
    rs.elect()
    assert rs.write("hello") is True
    assert all(rs.read(name) == ["hello"] for name in rs.names), (
        "a synchronous write must reach every reachable replica before it is committed")
    assert rs.write("world") is True
    assert all(rs.read(name) == ["hello", "world"] for name in rs.names)


def check_no_quorum() -> None:
    from cluster import ReplicaSet

    rs = ReplicaSet(["A", "B", "C"], mode="sync")
    rs.elect()
    leader = rs.leader
    rs.partition({leader}, {name for name in rs.names if name != leader})
    assert rs.write("x") is False, (
        "a leader cut off from a majority must not acknowledge a write")
    assert all(rs.read(name) == [] for name in rs.names), (
        "the write must not be visible as committed anywhere")
    assert rs.commit_index == 0


def check_async_stale_read() -> None:
    from cluster import ReplicaSet

    rs = ReplicaSet(["A", "B", "C"], mode="async")
    rs.elect()
    leader = rs.leader
    follower = next(name for name in rs.names if name != leader)
    assert rs.write("x") is True
    assert rs.read(leader) == ["x"]
    assert rs.read(follower) == [], (
        "an async follower lags: a read from it does not see the leader's newest write")
    assert rs.sync() is True
    assert rs.read(follower) == ["x"], "after replication the follower catches up"


def check_failover_data_loss() -> None:
    from cluster import ReplicaSet

    sync = ReplicaSet(["A", "B", "C"], mode="sync")
    sync.elect()
    leader = sync.leader
    assert sync.write("x") is True
    sync.crash(leader)
    survivor = sync.elect()
    assert survivor != leader
    assert sync.read(survivor) == ["x"], "a synchronously committed write must survive failover"

    lag = ReplicaSet(["A", "B", "C"], mode="async")
    lag.elect()
    leader = lag.leader
    assert lag.write("x") is True
    assert lag.read(leader) == ["x"]
    lag.crash(leader)
    survivor = lag.elect()
    assert survivor != leader
    assert lag.read(survivor) == [], (
        "async replication acknowledged a write that failover then erased")


def check_failover_most_up_to_date() -> None:
    from cluster import ReplicaSet
    from log import Entry

    rs = ReplicaSet(["n1", "n2", "n3"], mode="sync")
    rs.elect()
    # Hand-built history: n1 is longest but stale, n2 is newest but tiny, n3 newest+longer.
    rs.logs["n1"] = [Entry(1, "x"), Entry(1, "y"), Entry(1, "z")]
    rs.logs["n2"] = [Entry(2, "w")]
    rs.logs["n3"] = [Entry(2, "u"), Entry(2, "v")]
    rs.crash(rs.leader)
    new = rs.elect()
    assert new == "n3", (
        f"failover elected {new!r}; the most up-to-date log (highest term, then longest) wins")
    assert rs.read("n2") == [], "n3's entries are not committed yet"


def check_fencing() -> None:
    from cluster import FencedStore, ReplicaSet, StaleEpoch

    rs = ReplicaSet(["A", "B", "C"], mode="sync")
    rs.elect()
    old = rs.leader
    rest = [name for name in rs.names if name != old]
    rs.partition({old}, set(rest))
    assert rs.write("split-brain") is False, "the isolated leader cannot reach a majority"
    store = FencedStore("db")
    store.write(rs.epoch, f"from-{old}")                     # the old leader's token
    new = rs.elect()                                          # the majority elects a survivor
    assert new != old and rs.can_lead(new), (
        "the survivors must elect one of their own, not the isolated old leader")
    assert rs.epoch > 1, "every election must bump the epoch (the fencing token)"
    store.write(rs.epoch, f"from-{new}")                      # the new leader's token
    try:
        store.write(1, "stale")
        raise AssertionError("a write carrying a fenced (older) epoch was accepted")
    except StaleEpoch:
        pass


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("log.py", "last term of a log", check_last_term),
    ("log.py", "the up-to-date rule (term before length)", check_up_to_date),
    ("log.py", "choose the most up-to-date candidate", check_choose_leader),
    ("log.py", "commit index needs a quorum", check_quorum_index),
    ("cluster.py", "synchronous write reaches every replica", check_sync_replicates),
    ("cluster.py", "no majority, no acknowledgement", check_no_quorum),
    ("cluster.py", "async lag and catching up", check_async_stale_read),
    ("cluster.py", "failover: sync survives, async loses", check_failover_data_loss),
    ("cluster.py", "failover elects the most up-to-date survivor", check_failover_most_up_to_date),
    ("cluster.py", "epoch fencing blocks the old leader", check_fencing),
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
    print(f"\n{BOLD}Replication From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have replicated data and failed over safely.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the replication-and-quorums templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every accept criterion and every limit case of the skill-tree node is one step:
  accept 1  R + W > N            -> step 5
  accept 2  R + W <= N stale     -> step 6
  accept 3  durable on a quorum  -> step 7
  limit 1   minority refuses     -> step 8
  limit 2   slow follower        -> step 9
"""

import itertools
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

#: Explicit seed for the simulated network; every timing below is reproducible.
SEED = 20261010


# ---------------------------------------------------------------------------
# Steps 1-2: network.py
# ---------------------------------------------------------------------------

def check_network_delivery() -> None:
    from network import Network

    class Sink:
        def __init__(self) -> None:
            self.inbox: List[Tuple[str, object]] = []

        def receive(self, src, payload) -> None:
            self.inbox.append((src, payload))

    net = Network(seed=SEED, min_delay=1, max_delay=3)
    sink = Sink()
    net.register("a", sink)
    net.send("a", "a", "slow", delay=7)
    net.send("a", "a", "fast", delay=1)
    assert net.pending() == 2, f"two messages were queued, pending()={net.pending()}"
    net.flush()
    assert net.pending() == 0, f"flush() left {net.pending()} messages undelivered"
    order = [m for _, m in sink.inbox]
    assert order == ["fast", "slow"], (
        f"messages arrived as {order}: delivery must be in (deliver_at, sequence) order, "
        "so a smaller delay overtakes a larger one sent earlier")

    # The same seed must reproduce the same interleaving in a fresh network.
    def arrivals(seed: int) -> List[int]:
        n = Network(seed=seed, min_delay=1, max_delay=5)
        s = Sink()
        n.register("a", s)
        for i in range(8):
            n.send("a", "a", i)
        n.flush()
        return [m for _, m in s.inbox]

    first, second = arrivals(SEED), arrivals(SEED)
    assert first == second, (
        f"two networks with seed {SEED} delivered different orders: {first} vs {second}. "
        "Use only the seeded random.Random, never the global random module")
    assert sorted(first) == list(range(8)), f"some messages were lost: {first}"


def check_network_partition() -> None:
    from network import Network

    class Sink:
        def __init__(self) -> None:
            self.inbox: List[object] = []

        def receive(self, src, payload) -> None:
            self.inbox.append(payload)

    net = Network(seed=SEED)
    a, b, c = Sink(), Sink(), Sink()
    net.register("a", a)
    net.register("b", b)
    net.register("c", c)

    net.set_partition([["a", "b"], ["c"]])
    net.send("a", "b", "inside")
    net.send("a", "c", "across")
    net.send("c", "a", "across-back")
    net.flush()
    assert b.inbox == ["inside"], (
        f"replica b received {b.inbox}; with the partition [a,b] | [c] only a->b is inside")
    assert c.inbox == [], (
        f"the partitioned node c received {c.inbox}: a message crossing a group boundary "
        "must be dropped, not delivered")
    assert net.dropped == 2, (
        f"dropped count is {net.dropped}, expected 2: count every message that cannot cross "
        "the partition")

    net.heal()
    net.send("a", "c", "healed")
    net.flush()
    assert c.inbox == ["healed"], (
        f"after heal() c received {c.inbox}: healing must restore connectivity")


# ---------------------------------------------------------------------------
# Steps 3-4: replica.py
# ---------------------------------------------------------------------------

def check_replica_log() -> None:
    from replica import Replica

    r = Replica("a")
    assert r.append({"index": 0, "key": "k", "value": "zero", "version": 0}) is True
    assert r.append({"index": 0, "key": "k", "value": "dup", "version": 0}) is False, (
        "append() accepted a second entry at index 0: a position that is already filled "
        "must be refused, or the log can hold two different histories at one index")
    assert len(r.log) == 1 and r.value("k") == (0, "zero")

    assert r.append({"index": 2, "key": "k", "value": "gap", "version": 2}) is False, (
        "append() accepted index 2 when the log length is 1: a gap means the replica missed "
        "write 1 and must refuse until it is caught up")
    assert len(r.log) == 1, f"refusing the gap still changed the log to length {len(r.log)}"
    assert r.get(2) is None, "get(2) returned an entry the replica should not have"

    assert r.append({"index": 1, "key": "k", "value": "one", "version": 1}) is True
    assert len(r.log) == 2 and r.get(1)["value"] == "one"


def check_replica_lww() -> None:
    from replica import Replica

    r = Replica("a")
    r.append({"index": 0, "key": "k", "value": "old", "version": 0})
    r.append({"index": 1, "key": "k", "value": "new", "version": 1})
    assert r.value("k") == (1, "new"), (
        f"value('k') is {r.value('k')}, not the LATEST version (1, 'new'): a later write to "
        "the same key must replace the earlier one")
    assert r.value("missing") is None, "an unknown key must read as None"
    r.append({"index": 2, "key": "other", "value": "x", "version": 2})

    r.truncate(1)
    assert len(r.log) == 1 and r.get(1) is None, (
        f"truncate(1) left {len(r.log)} entries; it must drop every entry at or after index 1")
    assert r.value("k") == (0, "old"), (
        f"after truncating the index-1 write, value('k') is {r.value('k')}, not (0, 'old'): "
        "truncate() must rebuild the derived view from the remaining log")
    assert r.value("other") is None, (
        "truncate() left a value ('other') from an entry it removed: rebuild `applied`")


# ---------------------------------------------------------------------------
# Steps 5-7: quorum.py -- the accept criteria
# ---------------------------------------------------------------------------

def check_read_after_write() -> None:
    """accept 1: with R + W > N a read sees the last acknowledged write."""
    from quorum import ReplicatedLog, read_write_overlap

    assert read_write_overlap(2, 2, 3) is True, (
        "R=2, W=2, N=3: 2+2 > 3, so the quorums must overlap")
    assert read_write_overlap(1, 1, 3) is False, "R=1, W=1, N=3 must not be guaranteed"
    assert read_write_overlap(1, 3, 3) is True, "1+3=4 > 3"

    log = ReplicatedLog(["A", "B", "C"], seed=SEED, R=2, W=2, leader="A")
    old = log.write("k", "old")                 # a first write every replica sees
    assert log.holders(old) == 3, "the first write should reach all three replicas"
    log.partition([["A", "B"], ["C"]])
    version = log.write("k", "hello")           # only A and B are reachable now
    write_set = {n for n in log.names if log.replicas[n].get(version) is not None}
    assert len(write_set) >= log.W, (
        f"the acknowledged write is only on {write_set}, fewer than W={log.W} replicas")
    assert log.replicas["C"].value("k") == (old, "old"), (
        "C should still hold the OLD version after the partition; if it already has the new "
        "one there is nothing for the read to get wrong")

    for combo in itertools.combinations(log.names, log.R):
        read_set = list(combo)
        assert set(read_set) & write_set, (
            f"read set {read_set} is disjoint from write set {write_set} although "
            "R + W > N says it cannot be")
        got = log.read("k", from_=read_set)
        assert got == "hello", (
            f"read from {read_set} returned {got!r}: with R={log.R}, W={log.W}, N={log.N} "
            "every read quorum overlaps the write quorum, so the last acknowledged write "
            "must be visible")

    # A read that hits the stale replica first must still return the newest version.
    assert log.read("k", from_=["C", "B"]) == "hello", (
        "the read returned the FIRST response rather than the highest version: with C stale "
        "and B fresh the answer must come from B -- compare versions, do not take the first")


def check_stale_read_possible() -> None:
    """accept 2: with R + W <= N a stale read is possible, and is demonstrated."""
    from quorum import ReplicatedLog, read_write_overlap

    assert read_write_overlap(1, 1, 3) is False, (
        "R=1, W=1, N=3: 1+1 <= 3, so a read quorum and a write quorum can be disjoint")

    log = ReplicatedLog(["A", "B", "C"], seed=SEED, R=1, W=1, leader="A")
    log.partition([["A"], ["B", "C"]])
    version = log.write("k", "hello")
    write_set = {n for n in log.names if log.replicas[n].get(version) is not None}
    assert write_set == {"A"}, (
        f"with the partition [A] | [B,C] and W=1 the write should land only on A, got {write_set}")
    assert read_write_overlap(log.R, log.W, log.N) is False

    assert log.read("k", from_=["C"]) is None, (
        "a read quorum {C} disjoint from the write quorum {A} must be allowed to miss the "
        "write. Reading back 'hello' means the read ignored `from_` or queried every replica")
    assert log.read("k", from_=["B"]) is None, "B is on the stale side of the partition too"
    assert log.read("k", from_=["A"]) == "hello", "the write's own replica must hold it"

    # catch-up closes the window without changing the quorum rule.
    log.heal()
    log.catch_up()
    assert log.read("k", from_=["C"]) == "hello", (
        "catch_up() did not repair the stale replica: after healing, the missing suffix must "
        "be sent to the lagging replicas")


def check_write_durable_on_quorum() -> None:
    """accept 3: a write acknowledged to the client is durable on a quorum."""
    from quorum import NotEnoughReplicas, ReplicatedLog

    log = ReplicatedLog(["A", "B", "C"], seed=SEED, R=2, W=2, leader="A")
    log.partition([["A", "B"], ["C"]])
    version = log.write("k", "v")
    holders = {n for n in log.names if log.replicas[n].get(version) is not None}
    assert len(holders) >= log.W, (
        f"the write was acknowledged but sits on only {len(holders)} replicas, fewer than W={log.W}")
    assert log.commit_index() == version, (
        f"commit_index()={log.commit_index()} should be {version}: an acknowledged write is the "
        "highest log position present on at least W replicas")

    # Losing any N-W replicas must leave at least one copy of the acknowledged write.
    for lost in itertools.combinations(log.names, log.N - log.W):
        survivors = [n for n in log.names
                     if n not in lost and log.replicas[n].get(version) is not None]
        assert survivors, (
            f"losing {lost} removed every copy of the acknowledged write: a W-replica quorum "
            "must survive the loss of N-W replicas")

    # A write that cannot reach a quorum is neither acknowledged nor committed.
    minority = ReplicatedLog(["A", "B", "C"], seed=SEED, R=2, W=2, leader="A")
    minority.partition([["A"], ["B", "C"]])
    try:
        minority.write("bad", "x")
        raise AssertionError(
            "a write reaching only W-1 replicas was acknowledged: commit_index would then "
            "report an entry no quorum holds")
    except NotEnoughReplicas:
        pass
    assert minority.commit_index() == -1, (
        f"after a refused write commit_index()={minority.commit_index()}, expected -1: nothing "
        "was ever committed")


# ---------------------------------------------------------------------------
# Steps 8-9: quorum.py -- the limit cases
# ---------------------------------------------------------------------------

def check_minority_refuses() -> None:
    """limit 1: under a partition a minority refuses the write instead of forking."""
    from quorum import NotEnoughReplicas, ReplicatedLog

    log = ReplicatedLog(["A", "B", "C", "D", "E"], seed=SEED, R=3, W=3, leader="A")
    before = {n: len(r.log) for n, r in log.replicas.items()}
    log.partition([["A", "B"], ["C", "D", "E"]])
    try:
        log.write("k", "v")
        raise AssertionError(
            "the partitioned leader acknowledged a write from a two-node minority: with W=3 it "
            "must refuse rather than let a value three replicas never saw become committed")
    except NotEnoughReplicas:
        pass

    after = {n: len(r.log) for n, r in log.replicas.items()}
    assert after == before, (
        f"a refused write left a partial entry behind ({before} -> {after}): the log forked. "
        "On failure the coordinator must roll back every copy, so no minority keeps the write")
    assert log.commit_index() == -1, "a refused write was reported as committed"
    assert log.read("k") is None, "a refused write is still readable from some replica"

    # Once healed, a full quorum accepts the write and the log is consistent.
    log.heal()
    version = log.write("k", "v")
    assert log.holders(version) == 5, (
        f"after healing, holders={log.holders(version)}, expected all 5 replicas")
    assert log.read("k", from_=["D"]) == "v"


def check_slow_follower() -> None:
    """limit 2: a slow follower lags but does not block the quorum."""
    from quorum import ReplicatedLog

    log = ReplicatedLog(["A", "B", "C", "D", "E"], seed=SEED, R=3, W=3, leader="A")
    log.pause("E")
    version = log.write("k", "v")
    assert log.holders(version) == log.N - 1, (
        f"holders={log.holders(version)}, expected {log.N - 1}: the four reachable replicas "
        "must hold the write. Waiting for the paused E would need all N, not W")
    assert len(log.replicas["E"].log) == 0, "the paused follower should have received nothing"
    assert log.commit_index() == version, (
        f"commit_index()={log.commit_index()}, expected {version}: a quorum of 4 of 5 is enough, "
        "the slow follower is not part of it")

    log.resume("E")
    sent = log.catch_up()
    assert sent >= 1 and len(log.replicas["E"].log) == 1, (
        f"catch_up() sent {sent} entries and E's log is {len(log.replicas['E'].log)} long: the "
        "lagging follower must be brought up to the leader's log")
    assert log.replicas["E"].value("k") == (version, "v"), (
        "after catch-up the follower must hold the same version of the key")
    assert log.read("k", from_=["E"]) == "v"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("network.py", "delivery by time, seed reproducibility", check_network_delivery),
    ("network.py", "a partition drops cross-group traffic", check_network_partition),
    ("replica.py", "the log is contiguous: no gaps, no double writes", check_replica_log),
    ("replica.py", "latest-version reads and truncate rollback", check_replica_lww),
    ("quorum.py", "R + W > N: read sees the last acknowledged write", check_read_after_write),
    ("quorum.py", "R + W <= N: a stale read is possible", check_stale_read_possible),
    ("quorum.py", "an acknowledged write is durable on a quorum", check_write_durable_on_quorum),
    ("quorum.py", "limit: a minority refuses instead of forking", check_minority_refuses),
    ("quorum.py", "limit: a slow follower does not block the quorum", check_slow_follower),
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
    print(f"\n{BOLD}Distributed 02 — Replication and Quorums{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<11} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<11} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<11} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you can replicate with quorums.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

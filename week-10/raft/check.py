"""
Progress checker for the raft templates.

    python3 check.py           # run every check, stop at the first gap
    python3 check.py 4         # run only step 4
    python3 check.py --all     # run everything

Nothing here imports solutions/. It tests YOUR code.
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


def check_log_matching() -> None:
    from log import Entry, Log

    log = Log([Entry(1, "a"), Entry(1, "b"), Entry(2, "c")])
    assert log.last_index == 3 and log.last_term == 2
    assert log.term_at(0) == 0, (
        "index 0 must be term 0 — 'before the beginning'. That sentinel is "
        "what lets prev_index=0 mean 'I am sending you the first entry' and "
        "makes the consistency check uniform.")
    assert log.term_at(2) == 1

    assert log.matches(0, 0), "everyone agrees about the empty prefix"
    assert log.matches(3, 2)
    assert not log.matches(3, 1), "same index, different term is NOT a match"
    assert not log.matches(9, 1), "an index I do not have is not a match"

    follower = Log([Entry(1, "a")])
    assert not follower.append_entries(2, 1, [Entry(2, "c")]), (
        "a follower missing entry 2 must REJECT an append whose prev_index is "
        "2. Accept it and there is a hole in the log, and the log matching "
        "property — which every safety argument in Raft rests on — is simply "
        "false.")
    assert follower.append_entries(1, 1, [Entry(1, "b"), Entry(2, "c")])
    assert [e.command for e in follower.entries] == ["a", "b", "c"]


def check_truncation() -> None:
    from log import Entry, Log

    follower = Log([Entry(1, "a"), Entry(1, "WRONG"), Entry(1, "ALSO")])
    follower.append_entries(1, 1, [Entry(2, "x")])
    assert [e.command for e in follower.entries] == ["a", "x"], (
        f"got {[e.command for e in follower.entries]}. A conflicting entry and "
        "EVERYTHING AFTER IT must be deleted — not merged, not kept because it "
        "is longer. The leader's log is the truth.")
    assert follower.stats["entries_deleted"] == 2

    # The trap: an identical entry must NOT trigger a truncation.
    careful = Log([Entry(1, "a"), Entry(1, "b"), Entry(1, "c")])
    careful.commit_index = 3
    before = list(careful.entries)
    careful.append_entries(1, 1, [Entry(1, "b")])
    assert careful.entries == before, (
        f"a delayed AppendEntries re-sent entry 2, which was IDENTICAL, and "
        f"the log became {careful.entries}. Truncate only on a genuine "
        "CONFLICT — same index, DIFFERENT term. Truncating on every append "
        "means a duplicated network message deletes committed entries, which "
        "is silent data loss caused by an unnecessary delete.")
    assert careful.stats["entries_deleted"] == 0

    log = Log([Entry(1, "a"), Entry(1, "b")])
    assert len(log.advance_commit(2)) == 2
    assert log.commit_index == 2
    assert log.advance_commit(1) == [], "the commit index must never go back"
    assert log.commit_index == 2

    mine = Log([Entry(1, "a"), Entry(1, "b"), Entry(1, "c"), Entry(1, "d")])
    assert mine.is_at_least_as_up_to_date_as(2, 2), (
        "a SHORTER log from a LATER term is more up to date. Entries from a "
        "later term were appended by a leader a majority already voted for; a "
        "longer log of stale entries is a leader that was partitioned away and "
        "kept writing to itself. Compare length first and Raft loses committed "
        "entries.")
    assert not mine.is_at_least_as_up_to_date_as(1, 3)
    assert mine.is_at_least_as_up_to_date_as(1, 4), "equal is good enough"
    assert not mine.is_at_least_as_up_to_date_as(0, 99)


def check_elections() -> None:
    from election import LEADER, Server, VoteRequest, run_election
    from log import Entry, Log

    names = [f"s{i}" for i in range(5)]
    servers = [Server(n, [p for p in names if p != n],
                      rng=random.Random(i)) for i, n in enumerate(names)]
    won, _ = run_election(servers, 0)
    assert won and servers[0].role == LEADER
    assert servers[0].current_term == 1, "an election increments the term"
    assert len(servers[0].votes) >= servers[0].majority

    # A second candidate in the SAME term gets nothing.
    rival = VoteRequest(servers[0].current_term, "s1", 0, 0)
    granted = sum(1 for s in servers[1:] if s.handle_vote_request(rival, 0).granted)
    assert granted == 0, (
        f"{granted} servers voted for a second candidate in the same term. "
        "Each server casts AT MOST ONE vote per term — that single rule is the "
        "entire safety argument for leader election, because two majorities of "
        "the same set always intersect.")

    # The election restriction.
    behind = [Entry(1, "a")]
    ahead = [Entry(1, "a"), Entry(1, "b"), Entry(2, "c")]
    servers = [Server(n, [p for p in names if p != n],
                      Log(list(ahead if i < 4 else behind)),
                      rng=random.Random(i)) for i, n in enumerate(names)]
    won, reasons = run_election(servers, 4)
    assert not won, (
        "a candidate whose log is BEHIND won an election. The election "
        "restriction must refuse the vote: any committed entry is on a "
        "majority, a candidate needs a majority, and those sets intersect — so "
        "any candidate that can win already holds every committed entry. That "
        "is what makes truncating a follower's log safe.")
    assert reasons, "and the refusal should say why"
    won, _ = run_election(servers, 0)
    assert won, "a candidate that IS up to date must win"

    # Any higher term makes you a follower.
    leader = servers[0]
    assert leader.role == LEADER
    leader.observe_term(99)
    assert leader.role == "follower" and leader.current_term == 99, (
        "one message carrying a higher term must make a leader step down "
        "immediately. There is no other 'am I still leader' check in Raft.")
    assert leader.voted_for is None, "a new term means a fresh vote"


def check_replication() -> None:
    from log import Entry, Log
    from replication import Leader, replicate

    leader_log = Log([Entry(1, "a"), Entry(1, "b"), Entry(2, "c")])
    followers = {"s1": Log([Entry(1, "a")]),
                 "s2": Log([Entry(1, "a"), Entry(1, "b"), Entry(2, "c")]),
                 "s3": Log([])}
    leader = Leader("s0", list(followers), leader_log, term=2)
    assert leader.next_index["s1"] == 4, (
        "nextIndex starts OPTIMISTIC, at last_index + 1 — the leader assumes "
        "everyone is up to date and finds out otherwise")
    assert leader.match_index["s1"] == 0, (
        "matchIndex starts PESSIMISTIC at 0 — the leader knows nothing is "
        "replicated until a reply says so")

    replicate(leader, followers)
    for name, log in followers.items():
        assert [e.command for e in log.entries] == ["a", "b", "c"], (
            f"{name} ended with {[e.command for e in log.entries]}")
        assert leader.match_index[name] == 3, (
            f"matchIndex[{name}] is {leader.match_index[name]}, expected 3. It "
            "must only ever be set from a successful REPLY. Advance it when "
            "you SEND and the leader will commit entries a follower rejected — "
            "a real bug in real implementations.")
    assert leader.stats["rejected"] > 0, "s1 and s3 were behind, so it backed up"

    # The distinction that matters: a follower that REJECTS must not move
    # matchIndex, however much the leader sent it.
    stubborn = Leader("s0", ["s9"], Log([Entry(1, "a"), Entry(2, "b")]), term=2)
    stubborn.build_append("s9")                  # the leader SENDS
    assert stubborn.match_index["s9"] == 0, (
        f"matchIndex[s9] is {stubborn.match_index['s9']} after merely BUILDING "
        "an AppendEntries. It must only ever be set from a successful REPLY. "
        "Advance it on send and the leader counts entries a follower rejected "
        "towards a majority — and commits data that is on one machine.")
    stubborn.handle_reply("s9", False, 0)
    assert stubborn.match_index["s9"] == 0, "a rejection must not advance it"
    stubborn.handle_reply("s9", True, 2)
    assert stubborn.match_index["s9"] == 2, "a success must"

    newly = leader.advance_commit()
    assert leader.log.commit_index == 3, (
        f"commit index is {leader.log.commit_index}, expected 3: entry 3 is "
        "from the current term and on every server")
    assert len(newly) == 3, "committing entry 3 commits 1 and 2 with it"


def check_commit_rule() -> None:
    from log import Entry, Log
    from replication import Leader, replicate

    # An entry from an EARLIER term on a majority must NOT commit.
    old = Log([Entry(1, "a"), Entry(2, "old")])
    leader = Leader("s0", ["s1", "s2", "s3", "s4"], old, term=4)
    followers = {"s1": Log([Entry(1, "a")]), "s2": Log([Entry(1, "a")]),
                 "s3": Log([Entry(1, "a")]), "s4": Log([Entry(1, "a")])}
    replicate(leader, followers)
    replicas = 1 + sum(1 for p in followers if leader.match_index[p] >= 2)
    assert replicas >= leader.majority, (
        f"the setup is wrong: entry 2 should be on a majority, it is on "
        f"{replicas}")
    leader.advance_commit()
    assert leader.log.commit_index < 2, (
        f"commit index reached {leader.log.commit_index}. Entry 2 is on a "
        f"majority ({replicas} of 5) and it is from term 2 while the leader is "
        "in term 4 — so it must NOT be committed. This is Figure 8 of the "
        "paper: an entry from an old term can be on a majority and still be "
        "overwritten later, because a candidate with a shorter but more recent "
        "log can still win. The rule is majority AND current term.")
    assert leader.stats["commit_blocked_by_term"] > 0, (
        "and the leader should have noticed it was blocked")

    # A current-term entry commits it, and everything before it.
    leader.client_request("new")
    replicate(leader, followers)
    leader.advance_commit()
    assert leader.log.commit_index == 3, (
        f"commit index is {leader.log.commit_index}, expected 3. Once a "
        "CURRENT-term entry is on a majority it commits, and everything "
        "before it commits with it by the log matching property.")

    # The no-op exists for exactly this reason.
    for use_noop in (False, True):
        log = Log([Entry(1, "a"), Entry(1, "b")])
        fresh = Leader("s0", ["s1", "s2"], log, term=7)
        peers = {"s1": Log(list(log.entries)), "s2": Log(list(log.entries))}
        if use_noop:
            fresh.append_noop()
        replicate(fresh, peers)
        fresh.advance_commit()
        if use_noop:
            assert fresh.log.commit_index == 3, (
                "with a no-op in the current term, the whole prefix commits")
        else:
            assert fresh.log.commit_index == 0, (
                "without a current-term entry the leader can NEVER commit, "
                "even though every server has every entry. That is why a new "
                "leader appends a no-op — it is not a hack, it is the commit "
                "rule's direct consequence.")


def check_cluster() -> None:
    from cluster import Cluster

    cluster = Cluster(5, seed=1)
    assert cluster.elect("s0"), "an election on a healthy cluster must succeed"
    for command in "abc":
        assert cluster.write(command), f"write {command!r} should commit"
    assert cluster.check_safety() is None
    for name in cluster.names:
        assert [e.command for e in cluster.applied[name] if e.command] == \
            ["a", "b", "c"], (
            f"{name} applied "
            f"{[e.command for e in cluster.applied[name] if e.command]}")

    cluster.partition(["s0", "s1"], ["s2", "s3", "s4"])
    assert cluster.reachable_from("s0") == {"s0", "s1"}
    commit_before = cluster.servers["s0"].log.commit_index
    length_before = len(cluster.servers["s0"].log)
    assert not cluster.write("d"), (
        "the leader is in a MINORITY of 2 out of 5. It cannot reach a majority, "
        "so it cannot commit, so the client must be told no. Returning success "
        "here is the split-brain Raft exists to prevent.")
    assert cluster.servers["s0"].log.commit_index == commit_before, (
        f"the minority leader's commit index moved from {commit_before} to "
        f"{cluster.servers['s0'].log.commit_index}. It may APPEND to its own "
        "log — and it does — but with no majority reachable it can never "
        "commit, and the commit index is the promise made to the client.")
    assert len(cluster.servers["s0"].log) > length_before, (
        "and it SHOULD have appended: the entry sits in its log uncommitted "
        "until a later leader deletes it, which is exactly why deleting it is "
        "safe — nobody was ever told it succeeded")

    assert cluster.elect("s2"), "the majority side must be able to elect"
    assert cluster.servers["s2"].current_term > cluster.servers["s0"].current_term
    assert cluster.write("e"), "and then accept writes"
    assert cluster.check_safety() is None

    crashed = Cluster(5, seed=2)
    crashed.elect("s0")
    crashed.crash("s3")
    crashed.crash("s4")
    assert crashed.write("x"), (
        "3 of 5 servers is still a majority — a Raft cluster tolerates the "
        "loss of a minority and keeps serving")
    crashed.crash("s2")
    assert not crashed.write("y"), (
        "2 of 5 is not a majority. The cluster must stop accepting writes "
        "rather than accept ones it cannot commit.")
    assert crashed.check_safety() is None


def check_chaos() -> None:
    from cluster import Cluster
    from log import Entry

    # First: does check_safety DETECT a violation? A checker that always says
    # "holds" passes every chaos run and is worth nothing.
    rigged = Cluster(3, seed=0)
    rigged.applied["s0"] = [Entry(1, "x"), Entry(1, "SAME")]
    rigged.applied["s1"] = [Entry(1, "x"), Entry(1, "DIFFERENT")]
    detected = rigged.check_safety()
    assert detected is not None, (
        "two servers have applied DIFFERENT commands at index 2 and "
        "check_safety() reported no violation. It must compare across ALL "
        "servers, index by index — a checker that only ever looks at one log "
        "cannot fail, and it will pass every chaos run below while telling you "
        "nothing at all.")
    assert "2" in detected, "and the message should name the index"

    clean = Cluster(3, seed=0)
    clean.applied["s0"] = [Entry(1, "x")]
    clean.applied["s1"] = [Entry(1, "x"), Entry(1, "y")]
    assert clean.check_safety() is None, (
        "a server that is merely BEHIND is not a violation — safety is about "
        "servers that DISAGREE, not servers at different points")

    total = 0
    for run in range(6):
        cluster = Cluster(5, seed=run + 20)
        cluster.elect("s0")
        rng = random.Random(run + 20)
        for step in range(35):
            total += 1
            action = rng.random()
            if action < 0.55:
                cluster.write(f"{run}-{step}")
            elif action < 0.7:
                group = rng.sample(cluster.names, rng.choice([2, 3]))
                cluster.partition(group, [n for n in cluster.names
                                          if n not in group])
            elif action < 0.8:
                cluster.heal()
            elif action < 0.9:
                cluster.elect(rng.choice(cluster.names))
            else:
                victim = rng.choice(cluster.names)
                (cluster.restart if victim in cluster.crashed
                 else cluster.crash)(victim)
            violation = cluster.check_safety()
            assert violation is None, (
                f"STATE MACHINE SAFETY VIOLATED after {total} operations "
                f"(run {run}, step {step}):\n      {violation}\n"
                f"      history: {cluster.history[-6:]}\n"
                "      Two servers applied DIFFERENT commands at the same "
                "index. That is the one thing Raft promises never happens, and "
                "a violation that later heals is still a violation — a client "
                "was told something that turned out to be false.")
    assert total >= 200, "the chaos run should be substantial"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("log.py", "the consistency check, and refusing", check_log_matching),
    ("log.py", "truncation, and when NOT to", check_truncation),
    ("election.py", "one vote per term, and the restriction", check_elections),
    ("replication.py", "nextIndex guesses, matchIndex knows",
     check_replication),
    ("replication.py", "the commit rule, and Figure 8", check_commit_rule),
    ("cluster.py", "partitions: unavailable, not wrong", check_cluster),
    ("cluster.py", "randomised chaos, safety after every step", check_chaos),
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

    print(f"\n{BOLD}Raft From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built consensus.{RESET}")
        print(f"  {GREY}Now run each file's own demo, then compare with "
              f"solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

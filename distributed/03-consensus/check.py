"""
Progress checker for the Raft consensus templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code in
`network.py` and `raft.py`.
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
# Shared observations
# ---------------------------------------------------------------------------

def _assert_safe(cluster, where: str) -> None:
    """The three Raft safety properties, asserted after a scenario."""
    conflict = cluster.applied_conflict()
    assert conflict is None, (
        f"{where}: two nodes applied different entries at index {conflict[0]} "
        f"({conflict[1]} vs {conflict[2]}): an entry was applied before it was committed, "
        "or committed without a majority holding it"
    )
    conflict = cluster.committed_conflict()
    assert conflict is None, (
        f"{where}: two nodes committed different entries at index {conflict[0]} "
        f"({conflict[1]} vs {conflict[2]}): a committed entry was overwritten -- the "
        "log-matching check (prev_log_term) or the higher-term step-down is missing"
    )
    violation = cluster.log_matching_violation()
    assert violation is None, (
        f"{where}: log matching broken between {violation[0]} and {violation[1]} at index "
        f"{violation[2]}: {violation[3]} vs {violation[4]}: a follower accepted entries whose "
        "history it does not share, so it must have skipped the prev_log_term check"
    )


def _watch_leaders(cluster, ticks: int) -> dict:
    """Run `ticks` and record, per term, which nodes claimed to be leader."""
    by_term = {}
    for _ in range(ticks):
        cluster.run(1)
        for node_id in cluster.ids:
            node = cluster.nodes[node_id]
            if node.is_running() and node.state == "leader":
                by_term.setdefault(node.current_term, set()).add(node_id)
    return by_term


def _settle_to_leader(cluster, limit: int = 80):
    tick = 0
    while cluster.leader() is None and tick < limit:
        cluster.run(1)
        tick += 1
    return cluster.leader(), tick


# ---------------------------------------------------------------------------
# Steps 1-2: network.py
# ---------------------------------------------------------------------------

def check_network_delivery() -> None:
    from network import Network

    delivered = []

    class Sink:
        def __init__(self, name, net):
            self.name = name
            self.net = net

        def receive(self, src, msg):
            delivered.append((self.net.now, self.name, msg))

    net = Network(seed=1, min_delay=1, max_delay=3)
    for name in ("a", "b", "c"):
        net.register(name, Sink(name, net))

    # Arrival order must follow each message's own delay, not the send order.
    net.send("a", "b", "slow", delay=9)
    net.send("a", "b", "medium", delay=5)
    net.send("a", "b", "fast", delay=1)
    while net.pending():
        net.step()
    order = [msg for _, _, msg in delivered]
    assert order == ["fast", "medium", "slow"], (
        f"messages arrived {order}, expected ['fast', 'medium', 'slow']: each message's "
        "delivery time must decide when it arrives, not the order it was sent (a later "
        "message with a shorter delay overtakes an earlier one)")
    assert delivered[-1][0] >= delivered[0][0], "the clock went backwards"

    # Two runs with the same seed must produce the same arrival order.
    def run_random():
        seen = []
        n = Network(seed=42, min_delay=1, max_delay=6, reorder=True)
        for name in ("a", "b"):
            n.register(name, Sink(name, n))
        for i in range(10):
            n.send("a", "b", f"m{i}")
        while n.pending():
            n.step()
        return [m for (_, _, m) in delivered if m.startswith("m")][-10:]

    first = run_random()
    second = run_random()
    assert first == second, (
        f"the same seed gave different arrival orders ({first} vs {second}): the network "
        "must draw all its randomness from its own seeded RNG")
    assert first != [f"m{i}" for i in range(10)], (
        "10 messages sent a->b arrived in send order, with min_delay/max_delay/reorder on: "
        "delays are not being applied (did `send` ignore its delay?)")


def check_network_partition() -> None:
    from network import Network

    delivered = []

    class Sink:
        def __init__(self, name, net):
            self.name = name
            self.net = net

        def receive(self, src, msg):
            delivered.append((self.name, msg))

    net = Network(seed=2, min_delay=1, max_delay=1)
    for name in ("a", "b", "c"):
        net.register(name, Sink(name, net))

    net.send("a", "b", "same-group")
    net.set_partition([["a"], ["b", "c"]])
    net.send("a", "b", "across-partition")
    net.send("b", "c", "same-group-2")
    while net.pending():
        net.step()
    got = [msg for _, msg in delivered]
    assert "across-partition" not in got, (
        "a message crossed a partition: a send between two nodes in different groups must "
        "be dropped by the network, or a partitioned leader can replicate again")
    assert "same-group" in got and "same-group-2" in got, f"same-group traffic was lost: {got}"

    net.heal()
    net.send("a", "b", "after-heal")
    while net.pending():
        net.step()
    assert delivered[-1][1] == "after-heal", "healing the partition did not restore delivery"

    net.crash("c")
    net.send("b", "c", "to-crashed")
    while net.pending():
        net.step()
    assert all(msg != "to-crashed" for _, msg in delivered), "a crashed node received a message"


# ---------------------------------------------------------------------------
# Steps 3-5: raft.py, the build
# ---------------------------------------------------------------------------

def check_leader_election() -> None:
    from raft import Cluster

    cluster = Cluster(n=5, seed=11)
    leader, ticks = _settle_to_leader(cluster)
    assert leader is not None, "no leader was elected within 80 ticks"
    assert cluster.nodes[leader].current_term >= 1, "a leader must have run an election (term >= 1)"
    assert len(cluster.leaders()) == 1, f"expected one leader, saw {cluster.leaders()}"
    for node_id, node in cluster.nodes.items():
        if node_id != leader:
            assert node.state != "leader", f"{node_id} also thinks it is leader"

    # A single node forms a majority by itself and must elect itself.
    solo = Cluster(n=1, seed=5)
    solo_leader, _ = _settle_to_leader(solo)
    assert solo_leader == "n0", "a one-node cluster must elect itself"

    # The election timeout must be randomised: across seeds with a fixed network the
    # time-to-first-leader cannot be identical every single time.
    first_times = []
    for seed in range(1, 9):
        other = Cluster(n=5, seed=seed, delay=(1, 1))
        _, tick = _settle_to_leader(other)
        first_times.append(tick)
    assert len(set(first_times)) > 1, (
        f"every seed elected a leader at the same tick {first_times}: the election timeout "
        "is not randomised, so a single slow node can stall the whole cluster")


def check_replication_and_commit() -> None:
    from raft import Cluster

    cluster = Cluster(n=5, seed=11)
    leader, _ = _settle_to_leader(cluster)
    assert leader is not None, "no leader was elected"
    term = cluster.nodes[leader].current_term
    commands = ["a=1", "b=2", "c=3"]
    for command in commands:
        index = cluster.propose(command)
        assert index is not None, f"propose({command!r}) was refused although a leader exists"
        cluster.run(8)

    lead = cluster.nodes[leader]
    assert lead.commit_index == len(commands), (
        f"the leader committed {lead.commit_index} of {len(commands)} entries after they were "
        "replicated to a majority")
    for node_id in cluster.ids:
        node = cluster.nodes[node_id]
        got = [(e.term, e.command) for e in node.log]
        assert [c for _, c in got] == commands, f"{node_id} log is {got}, expected {commands}"
        assert all(t == term for t, _ in got), (
            f"{node_id} has entries from term {sorted({t for t, _ in got})}, but the leader "
            f"stamped them term {term}")
        assert node.commit_index == len(commands), (
            f"{node_id} has commit_index {node.commit_index}: followers must advance their "
            "commit index from the leader's leader_commit")


def check_apply_channel() -> None:
    from raft import Cluster, LogEntry

    # A node may hold entries that are not yet committed. When a commit for a prefix
    # arrives, only that prefix may be applied even though the log is longer.
    probe = Cluster(n=3, seed=1)
    node = probe.nodes["n0"]
    node.current_term = 4
    node.state = "follower"
    node.leader_id = "n1"
    node.log = [LogEntry(4, "A"), LogEntry(4, "B")]     # indices 1 and 2
    node.commit_index = 0
    node.last_applied = 0
    node.applied = []
    node.receive("n1", {
        "type": "AppendEntries", "term": 4, "leader": "n1",
        "prev_log_index": 0, "prev_log_term": 0,
        "entries": [{"term": 4, "command": "A"}, {"term": 4, "command": "B"}],
        "leader_commit": 1,
    })
    applied = [command for _, _, command in node.applied]
    assert applied == ["A"], (
        f"applied {applied} although only index 1 was committed: the apply loop must stop at "
        "commit_index, not run to the end of the log")
    assert node.last_applied == node.commit_index == 1

    cluster = Cluster(n=5, seed=11)
    leader, _ = _settle_to_leader(cluster)
    assert leader is not None
    commands = ["op0", "op1", "op2", "op3"]
    for command in commands:
        cluster.propose(command)
        cluster.run(8)
    cluster.run(20)
    for node_id in cluster.ids:
        node = cluster.nodes[node_id]
        indices = [index for index, _, _ in node.applied]
        assert indices == list(range(1, len(indices) + 1)), (
            f"{node_id} applied indices {indices}: the apply channel must deliver committed "
            "entries in index order, without gaps or repeats")
        assert [command for _, _, command in node.applied] == commands, (
            f"{node_id} applied {[c for _, _, c in node.applied]}, expected {commands}")
        assert node.last_applied == node.commit_index, (
            f"{node_id} applied up to {node.last_applied} but committed to {node.commit_index}: "
            "an entry was left un-applied (or applied past the commit point)")

    # An entry the leader appends but cannot commit must NOT reach the apply channel.
    forked = Cluster(n=5, seed=11)
    forked_leader, _ = _settle_to_leader(forked)
    assert forked_leader is not None
    follower = next(n for n in forked.ids if n != forked_leader)
    forked.partition([[forked_leader, follower],
                      [n for n in forked.ids if n not in (forked_leader, follower)]])
    before = forked.nodes[forked_leader].commit_index
    assert forked.propose("uncommitted") is not None
    forked.run(30)
    for node_id in (forked_leader, follower):
        node = forked.nodes[node_id]
        applied = [c for _, _, c in node.applied]
        assert "uncommitted" not in applied, (
            f"{node_id} applied an entry that never reached a majority: the apply channel is "
            "running ahead of commit_index")
        assert node.commit_index <= before, f"{node_id} committed without a majority"


# ---------------------------------------------------------------------------
# Steps 6-8: the accept criteria
# ---------------------------------------------------------------------------

def check_one_leader_and_reelection() -> None:
    from raft import Cluster

    # (a) At most one leader per term, and a crash triggers a new election.
    cluster = Cluster(n=5, seed=3)
    leader, _ = _settle_to_leader(cluster)
    assert leader is not None
    term1 = cluster.nodes[leader].current_term
    cluster.crash(leader)
    by_term = _watch_leaders(cluster, 80)
    by_term.setdefault(term1, set()).add(leader)
    new_leader = cluster.leader()
    assert new_leader is not None and new_leader != leader, (
        "no new leader was elected after the leader crashed")
    assert cluster.nodes[new_leader].current_term > term1, (
        f"the new leader is in term {cluster.nodes[new_leader].current_term}, not above the old "
        f"term {term1}: it must run a fresh election with a higher term")
    bad = {term: sorted(nodes) for term, nodes in by_term.items() if len(nodes) > 1}
    assert not bad, (
        f"two nodes led the same term: {bad}. A node voted twice in one term, or an old leader "
        "did not stop leading when it saw a higher term")

    # (b) A node that missed a committed entry must never win an election: if it could, it
    #     would overwrite that committed entry with its own. This is the up-to-date vote rule.
    cluster = Cluster(n=5, seed=3)
    leader, _ = _settle_to_leader(cluster)
    stale = next(n for n in cluster.ids if n != leader)      # will miss the commit
    others = [n for n in cluster.ids if n != stale]
    cluster.partition([[stale], [n for n in others if n != leader] + [leader]])
    cluster.propose("committed")
    cluster.run(25)
    assert cluster.nodes[leader].commit_index >= 1, "the majority could not commit an entry"
    assert cluster.nodes[stale].log == [], "the isolated node should have missed the entry"
    cluster.heal()
    cluster.crash(leader)
    # Force the stale node to run first; the others are told to wait a long time.
    now = cluster.net.now
    cluster.nodes[stale]._election_deadline = now
    for node_id in cluster.ids:
        if node_id not in (stale, leader):
            cluster.nodes[node_id]._election_deadline = now + 1000
    cluster.run(30)
    cluster.propose("overwrite")              # only effective if the stale node somehow won
    cluster.run(30)
    _assert_safe(cluster, "after an out-of-date node ran for election")
    assert cluster.nodes[stale].state != "leader", (
        "a node whose log is missing a committed entry won the election: it must have been "
        "refused the vote (check the up-to-date test: last_log_term, then last_log_index)")

    # (c) Single-node guard: two leaders can never appear in the same term.
    assert len(cluster.leaders()) <= 1, f"more than one leader after re-election: {cluster.leaders()}"


def check_no_divergent_apply() -> None:
    from raft import Cluster

    cluster = Cluster(n=5, seed=9)
    leader, _ = _settle_to_leader(cluster)
    assert leader is not None
    cluster.propose("first")
    cluster.run(8)
    victim = next(n for n in cluster.ids if n != leader)
    cluster.crash(victim)
    for command in ("second", "third"):
        assert cluster.propose(command) is not None
        cluster.run(10)
    cluster.restart(victim)
    cluster.run(60)
    _assert_safe(cluster, "after a follower crashed, missed entries, and caught up")

    leader = cluster.leader()
    assert leader is not None
    lead = cluster.nodes[leader]
    committed = [command for entry_term, command in
                 [(e.term, e.command) for e in lead.log[:lead.commit_index]]]
    for node_id in cluster.ids:
        node = cluster.nodes[node_id]
        applied = [command for _, _, command in node.applied]
        assert applied == committed[:len(applied)], (
            f"{node_id} applied {applied} which is not a prefix of the committed log "
            f"{committed}: two nodes applied different entries at the same index")
    assert cluster.nodes[victim].commit_index == lead.commit_index, (
        "the restarted follower never caught up to the committed log")


def check_minority_cannot_commit() -> None:
    from raft import Cluster

    cluster = Cluster(n=5, seed=13)
    leader, _ = _settle_to_leader(cluster)
    assert leader is not None
    follower = next(n for n in cluster.ids if n != leader)
    minority = [leader, follower]
    majority = [n for n in cluster.ids if n not in minority]
    cluster.partition([minority, majority])
    before = cluster.nodes[leader].commit_index
    assert cluster.propose("forked") is not None, "the minority leader refused to append"
    cluster.run(40)

    for node_id in minority:
        node = cluster.nodes[node_id]
        assert node.commit_index <= before, (
            f"minority node {node_id} advanced commit_index to {node.commit_index} with only "
            f"{len(minority)} of {len(cluster.ids)} nodes: an entry must be committed only when "
            "a MAJORITY (here 3) holds it")
        assert "forked" not in [c for _, _, c in node.applied], (
            f"minority node {node_id} applied the uncommitted entry 'forked'")

    # The majority side keeps working and can commit on its own.
    cluster.heal()
    cluster.run(80)
    _assert_safe(cluster, "after the minority rejoined")
    assert cluster.leader() is not None


# ---------------------------------------------------------------------------
# Steps 9-10: the limit cases
# ---------------------------------------------------------------------------

def check_partition_heal_no_divergence() -> None:
    from raft import Cluster

    cluster = Cluster(n=5, seed=17)
    old_leader, _ = _settle_to_leader(cluster)
    assert old_leader is not None
    others = [n for n in cluster.ids if n != old_leader]
    cluster.partition([[old_leader], others])
    assert cluster.propose("stale") is not None
    cluster.run(60)

    new_leader = next((n for n in others if cluster.nodes[n].state == "leader"), None)
    assert new_leader is not None, (
        "the majority did not elect a new leader while the old leader sat in a minority")
    assert cluster.nodes[new_leader].current_term > cluster.nodes[old_leader].current_term
    cluster.nodes[new_leader].propose("fresh")
    cluster.run(60)

    cluster.heal()
    cluster.run(100)
    _assert_safe(cluster, "after the partitioned leader rejoined")

    assert cluster.nodes[old_leader].state != "leader", (
        "the isolated leader is still a leader after rejoining: it must step down when it sees "
        "a higher term")
    assert "stale" not in [c for _, _, c in cluster.nodes[old_leader].applied], (
        "the isolated leader applied an entry that no majority ever committed")
    assert "stale" not in [c for _, _, c in cluster.nodes[new_leader].applied]

    logs = {}
    for node_id in cluster.ids:
        logs[node_id] = [(e.term, e.command) for e in cluster.nodes[node_id].log]
    assert len(set(map(tuple, logs.values()))) == 1, (
        f"logs did not converge after the partition healed: {logs} (the rejoining leader's "
        "conflicting suffix must be truncated)")


def check_delayed_reordered_safety() -> None:
    from raft import Cluster

    # (a) A follower told "commit to index 3" before it has entries 1..3 (a heartbeat that
    #     overtook the entries it refers to) must not commit entries it does not hold.
    probe = Cluster(n=3, seed=1)
    node = probe.nodes["n0"]
    node.current_term = 5
    node.state = "follower"
    node.log = []
    node.commit_index = 0
    node.last_applied = 0
    node.receive("n1", {
        "type": "AppendEntries", "term": 5, "leader": "n1",
        "prev_log_index": 0, "prev_log_term": 0, "entries": [], "leader_commit": 3,
    })
    assert node.commit_index <= len(node.log), (
        f"a reordered heartbeat made a follower commit_index {node.commit_index} while its log "
        f"holds {len(node.log)} entries: cap the commit at the last entry this message carries "
        "(min(leader_commit, prev_log_index + len(entries)))")

    # (b) Under wide delays, reordering and drops, while nodes crash and restart, safety
    #     must hold for every seed.
    for seed in (2, 5, 8):
        cluster = Cluster(n=5, seed=seed, drop=0.15, delay=(1, 7), reorder=True)
        cluster.run(90)
        victim = cluster.ids[seed % 5]
        for i in range(12):
            cluster.propose(f"op{i}")
            cluster.run(6)
            if i == 3:
                cluster.crash(victim)
            if i == 7 and not cluster.nodes[victim].is_running():
                cluster.restart(victim)
        cluster.run(140)
        _assert_safe(cluster, f"seed {seed} under delays, reordering and drops")

        leader = cluster.leader()
        if leader is not None:
            lead = cluster.nodes[leader]
            committed = [e.command for e in lead.log[:lead.commit_index]]
            for node_id in cluster.ids:
                node = cluster.nodes[node_id]
                if not node.is_running():
                    continue
                applied = [c for _, _, c in node.applied]
                assert applied == committed[:len(applied)], (
                    f"seed {seed}: {node_id} applied {applied}, not a prefix of the committed "
                    f"log {committed}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("network.py", "delivery time decides arrival order; seeded and reproducible", check_network_delivery),
    ("network.py", "a partition and a crash drop messages", check_network_partition),
    ("raft.py", "leader election: terms and a randomised timeout", check_leader_election),
    ("raft.py", "log replication and the majority commit rule", check_replication_and_commit),
    ("raft.py", "the apply channel: committed entries, in order", check_apply_channel),
    ("raft.py", "at most one leader per term; re-election after a crash", check_one_leader_and_reelection),
    ("raft.py", "two nodes never apply different entries at an index", check_no_divergent_apply),
    ("raft.py", "a minority cannot commit", check_minority_cannot_commit),
    ("raft.py", "a partitioned leader rejoins and does not diverge", check_partition_heal_no_divergence),
    ("raft.py", "delayed and reordered messages do not break safety", check_delayed_reordered_safety),
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
    print(f"\n{BOLD}Consensus (Raft) From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built a Raft cluster.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the time-and-clocks module.

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
# Steps 1-2: lamport.py
# ---------------------------------------------------------------------------

def check_lamport_basic() -> None:
    from lamport import LamportClock

    c = LamportClock()
    assert c.value == 0, "a fresh Lamport clock starts at 0"
    assert c.tick() == 1 and c.tick() == 2, "each local event must advance the counter by one"
    assert c.send() == 3, "a send is an event: it ticks the sender too"
    assert c.receive(10) == 11, (
        "receive(10) on a clock at 3 must be max(3, 10) + 1 = 11; returning sent + 1 "
        "ignores the receiver's own history")
    assert c.receive(1) == 12, (
        "receive(1) must not go backwards: max(11, 1) + 1 = 12")
    d = LamportClock(5)
    assert d.receive(2) == 6, "a receiver ahead of the sender stays ahead: max(5, 2) + 1"
    assert d.receive(100) == 101, "a receiver behind the sender jumps past the message"


def check_lamport_stream() -> None:
    from lamport import Simulation

    sim = Simulation()
    sim.run([
        ("local", "A"),
        ("send", "A", "B"),
        ("local", "B"),
        ("deliver", "B"),
        ("send", "B", "C"),
        ("local", "C"),
        ("deliver", "C"),
    ])
    pairs = sim.message_pairs()
    assert len(pairs) == 2, f"expected 2 delivered messages, saw {len(pairs)}"
    for send, recv in pairs:
        assert send.clock < recv.clock, (
            f"{send.process}->{recv.process}: the receive has timestamp {recv.clock}, "
            f"the send {send.clock}. Every receive must carry a strictly greater "
            "timestamp than the send it answers, or causal order is broken")
    for name in ("A", "B", "C"):
        history = sim.history(name)
        for first, second in zip(history, history[1:]):
            assert first.clock < second.clock, (
                f"events at {name} are not strictly ordered: {first!r} then {second!r}")


# ---------------------------------------------------------------------------
# Steps 3-7: vector.py
# ---------------------------------------------------------------------------

def check_vector_basic() -> None:
    from vector import (BEFORE, AFTER, CONCURRENT, EQUAL, VectorClock,
                        classify, concurrent, happens_before)

    a = VectorClock({"A": 1})
    b = VectorClock({"A": 1, "B": 2})
    assert happens_before(a, b) is True, "{A:1} -> {A:1,B:2}: every component grows"
    assert happens_before(b, a) is False, "happens-before is antisymmetric"
    assert classify(a, b) == BEFORE and classify(b, a) == AFTER
    c = VectorClock({"A": 2})
    d = VectorClock({"B": 1})
    assert classify(c, d) == CONCURRENT, (
        "{A:2} and {B:1} each have a component the other lacks: neither caused the other")
    assert concurrent(c, d) is True
    assert happens_before(c, d) is False and happens_before(d, c) is False
    assert classify(a, VectorClock({"A": 1})) == EQUAL, "identical vectors are EQUAL, not BEFORE"
    assert happens_before(a, VectorClock({"A": 1})) is False
    assert a.happens_before(b) is True and b.concurrent_with(c) is True


def check_vector_concurrency() -> None:
    from vector import (BEFORE, AFTER, CONCURRENT, VSimulation, classify,
                        happens_before)

    sim = VSimulation()
    sim.run([("local", "A"), ("local", "A"), ("local", "B")])
    a_event = sim.history("A")[-1]
    b_event = sim.history("B")[-1]
    assert classify(a_event.clock, b_event.clock) == CONCURRENT, (
        f"two processes that never exchanged a message are concurrent, but got "
        f"{classify(a_event.clock, b_event.clock)} for {a_event.clock} vs {b_event.clock}")
    assert not happens_before(a_event.clock, b_event.clock)
    assert not happens_before(b_event.clock, a_event.clock), (
        "a vector clock must never order two events that are not causally related")

    sim2 = VSimulation()
    sim2.run([("local", "A"), ("send", "A", "B"), ("deliver", "B")])
    send, recv = sim2.message_pairs()[0]
    assert classify(send.clock, recv.clock) == BEFORE
    assert classify(recv.clock, send.clock) == AFTER
    assert classify(send.clock, recv.clock) != CONCURRENT, (
        "a receive is causally after the send it answers: it must not look concurrent")


def check_vector_merge() -> None:
    from vector import BEFORE, VectorClock, VSimulation, classify, happens_before

    vc = VectorClock({"A": 3})
    assert vc.receive("B", {"A": 5, "C": 2}) == 1, (
        "receive must tick the receiver's own component after merging, not before")
    assert vc.to_dict() == {"A": 5, "B": 1, "C": 2}, (
        f"receive must merge (element-wise max) then tick: {vc.to_dict()}")
    m = VectorClock({"A": 2, "B": 7})
    m.merge({"A": 5, "B": 1})
    assert m.to_dict() == {"A": 5, "B": 7}, (
        f"merge is the element-wise MAXIMUM, not a sum: got {m.to_dict()}, want {{'A': 5, 'B': 7}}")

    sim = VSimulation()
    sim.run([("local", "A"), ("local", "A"), ("send", "A", "B"), ("deliver", "B")])
    send, recv = sim.message_pairs()[0]
    assert recv.clock["A"] >= send.clock["A"], "the receive must incorporate the sender's vector"
    assert recv.clock["B"] == 1, "the receiver ticks only its own component once"
    assert happens_before(send.clock, recv.clock), (
        "after a correct merge the send is strictly before the receive")
    assert classify(send.clock, recv.clock) == BEFORE


def check_vector_empty() -> None:
    from vector import (AFTER, BEFORE, EQUAL, VectorClock, classify, concurrent,
                        happens_before)

    empty = VectorClock()
    assert empty.to_dict() == {}, "a clock before its first event has no components"
    assert classify(empty, VectorClock()) == EQUAL, "two empty clocks are equal, not before"
    assert classify(empty, VectorClock({"A": 1})) == BEFORE, (
        "an empty clock is all zeros: every component 0 <= 1, so it is BEFORE a populated one")
    assert classify(VectorClock({"A": 1}), empty) == AFTER
    assert concurrent(empty, VectorClock({"A": 1})) is False, "the empty clock is comparable"
    assert happens_before(empty, VectorClock({"A": 1})) is True
    assert happens_before(empty, empty) is False, "equal clocks are not before each other"
    assert empty.copy().to_dict() == {}
    merged = VectorClock()
    merged.merge({"A": 2})
    assert merged.to_dict() == {"A": 2}, "merging an empty clock with a message must copy it"
    other = VectorClock({"A": 2})
    other.merge({})
    assert other.to_dict() == {"A": 2}, "merging an empty message leaves a clock unchanged"
    ticked = VectorClock()
    assert ticked.receive("A", {}) == 1, "receiving from an empty clock still ticks our own component"
    assert classify({}, {"A": 1}) == BEFORE, "plain dicts must work too"


def check_vector_stream() -> None:
    from vector import (BEFORE, CONCURRENT, VSimulation, classify, happens_before)

    sim = VSimulation()
    sim.run([
        ("local", "A"), ("send", "A", "C"),
        ("local", "B"), ("send", "B", "C"),
        ("local", "C"),
        ("deliver", "C"), ("deliver", "C"),
    ])
    a_local, a_send = sim.history("A")
    b_local, b_send = sim.history("B")
    c_events = sim.history("C")
    recv_a, recv_b = c_events[1], c_events[2]

    assert len(sim.message_pairs()) == 2
    for send, recv in sim.message_pairs():
        assert happens_before(send.clock, recv.clock), (
            f"causal order lost: send {send.clock} is not before its receive {recv.clock}")

    assert classify(a_send.clock, b_send.clock) == CONCURRENT, (
        "A and B never communicated, so their events are concurrent, not ordered")

    assert happens_before(a_send.clock, recv_a.clock)
    assert happens_before(b_send.clock, recv_b.clock)
    assert happens_before(a_send.clock, recv_b.clock)
    assert not happens_before(b_send.clock, recv_a.clock), (
        "C delivered from A before hearing from B, so B's send is not before that receive")

    for name in ("A", "B", "C"):
        history = sim.history(name)
        for first, second in zip(history, history[1:]):
            assert happens_before(first.clock, second.clock), (
                f"events at {name} are not causally ordered: {first.clock} then {second.clock}")


# ---------------------------------------------------------------------------
# Step 8: wall.py (limit case - clock skew)
# ---------------------------------------------------------------------------

def check_wall_skew() -> None:
    from wall import unsynchronised_clocks_disagree

    send, recv = unsynchronised_clocks_disagree()
    assert send.kind == "send" and recv.kind == "receive", (
        "the limit case must pair a send with the receive it answers")
    assert recv.true_time > send.true_time, (
        "the receive must genuinely happen after the send in true time; otherwise the "
        "inverted wall stamps prove nothing")
    assert recv.wall_time < send.wall_time, (
        f"with two unsynchronised clocks the receive's wall stamp ({recv.wall_time}) "
        f"must be EARLIER than the send's ({send.wall_time}) even though it happened "
        "later in real time. If they agree, the clocks were synchronised and the limit "
        "case is not being demonstrated: give them a nonzero skew")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("lamport.py", "tick / send / receive merge", check_lamport_basic),
    ("lamport.py", "send precedes its receive everywhere", check_lamport_stream),
    ("vector.py", "happens-before and four-way classify", check_vector_basic),
    ("vector.py", "concurrent events stay concurrent", check_vector_concurrency),
    ("vector.py", "clocks merge correctly on receive", check_vector_merge),
    ("vector.py", "empty vs populated vector clock", check_vector_empty),
    ("vector.py", "causal order preserved over a stream", check_vector_stream),
    ("wall.py", "clock skew inverts a causal pair", check_wall_skew),
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
    print(f"\n{BOLD}Distributed 01 — Time, Lamport and Vector Clocks{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you can order events without a shared clock.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

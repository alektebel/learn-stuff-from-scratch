"""
Progress checker for the CRDT templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import pathlib
import random
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
# Steps 1-2: gc_counter.py
# ---------------------------------------------------------------------------

def check_gcounter() -> None:
    from gc_counter import GCounter

    assert GCounter("c").value() == 0, "a fresh G-Counter must read 0"
    a, b = GCounter("a"), GCounter("b")
    a.increment()
    a.increment()
    b.increment()
    assert a.value() == 2 and b.value() == 1
    m = a.merge(b)
    assert m.value() == 3, f"two replicas holding 2 and 1 must merge to 3, got {m.value()}"
    # a grows its own slot some more; merging b (which still says 1) must keep a's 3
    a.increment()
    m2 = a.merge(b)
    assert m2.value() == 4, (
        f"merge must take the MAX of each node's slot, not the sum: a=3, b=1 should be 4, "
        f"got {m2.value()}. If you get another value you are adding, and re-delivering a "
        "message will inflate the counter.")
    # an older state can never drag the counter back down
    assert m2.merge(m).value() == 4, "merging an older state must not lower the counter"
    assert m2.merge(m2).value() == 4, "merging a counter with itself must be a no-op"


def check_pncounter() -> None:
    from gc_counter import PNCounter

    p = PNCounter("a")
    p.increment()
    p.increment()
    p.decrement()
    p.decrement()
    p.decrement()
    assert p.value() == -1, f"2 up, 3 down should be -1, got {p.value()}"
    p.decrement(4)
    assert p.value() == -5, (
        "a PN counter must be able to go NEGATIVE: keep the decrements in a second "
        "grow-only counter instead of clamping at zero")
    q = PNCounter("b")
    q.increment(10)
    assert p.merge(q).value() == 5, f"(-1-4) merged with +10 should be 5, got {p.merge(q).value()}"
    assert q.merge(p).value() == 5, "PN merge must be commutative across replicas"
    assert p.merge(p).value() == -5, "PN merge with itself must be a no-op"


# ---------------------------------------------------------------------------
# Steps 3-4: lww_register.py
# ---------------------------------------------------------------------------

def check_lww_basic() -> None:
    from lww_register import LWWRegister

    assert LWWRegister("c").read() is None, "an unwritten register reads None"
    r1, r2 = LWWRegister("a"), LWWRegister("b")
    r1.set("x", 1)
    r2.set("y", 2)
    assert r1.merge(r2).read() == "y", "the write with the larger timestamp must win"
    assert r2.merge(r1).read() == "y", "and it must win in both merge directions"
    r1.set("z", 5)
    assert r2.merge(r1).read() == "z", "a strictly later write must displace the current value"


def check_lww_tiebreak() -> None:
    import itertools

    from lww_register import LWWRegister

    a, b, c = LWWRegister("alpha"), LWWRegister("beta"), LWWRegister("gamma")
    a.set(1, 7)
    b.set(2, 7)
    c.set(3, 7)                       # all three writes share timestamp 7
    winners = set()
    for p, q, r in itertools.permutations((a, b, c)):
        winners.add(p.merge(q).merge(r).read())
    assert winners == {3}, (
        f"with equal timestamps the register must pick one fixed winner (the greatest node id, "
        f"'gamma'), in every merge order; got winners {winners}. A tie-break that depends on "
        "merge order makes the register non-commutative and the replicas never converge.")
    assert a.merge(b).read() == 2 and b.merge(a).read() == 2, (
        "the larger node id ('beta' > 'alpha') must win the tie both ways round")
    assert b.merge(c).read() == 3 and c.merge(b).read() == 3, (
        "'gamma' > 'beta' must win its tie both ways round")


# ---------------------------------------------------------------------------
# Steps 5-6: or_set.py
# ---------------------------------------------------------------------------

def check_orset_basic() -> None:
    from or_set import ORSet

    s = ORSet("a")
    assert s.elements() == set(), "a fresh OR-set is empty"
    s.add("x")
    assert s.contains("x") and s.elements() == {"x"}
    s.remove("x")
    assert not s.contains("x"), "remove() must make an observed add disappear"
    s.add("x")
    assert s.contains("x"), "an OR-set must be able to RE-ADD a removed element"
    assert s.elements() == {"x"}

    # Observed-remove: b never saw a's add, so b's concurrent add keeps the element.
    a = ORSet("a")
    a.add("x")
    b = ORSet("b")
    a.remove("x")                     # a removes what it has seen
    b.add("x")                        # b adds concurrently, never observing the remove
    assert a.merge(b).contains("x"), (
        "a concurrent add must survive a remove it never observed: remove only the tags "
        "the remover has actually seen, not the element name")
    assert b.merge(a).contains("x"), "and it must survive in both merge directions"


def check_orset_remove_then_add() -> None:
    from or_set import ORSet

    # remove-then-add on one replica: KEEPS the element.
    a = ORSet("a")
    a.remove("x")                     # nothing observed yet
    a.add("x")
    assert a.contains("x"), "remove-then-add must keep the element (a fresh tag is not tombstoned)"

    # add-then-remove on one replica: DROPS the element.
    b = ORSet("b")
    b.add("x")
    b.remove("x")
    assert not b.contains("x"), "add-then-remove must drop the element"

    # A remove is a tombstone, not a deletion of the add: re-meeting the replica that
    # still holds the add must NOT resurrect it.
    c = ORSet("c")
    c.add("y")
    d = ORSet("d")
    d = d.merge(c)                    # d observed c's add of y
    d.remove("y")
    assert not d.contains("y")
    again = d.merge(c)
    assert not again.contains("y"), (
        "after merging with the replica that still holds the add, the removed element came "
        "back: tombstone the observed tags on remove, do not delete them from the add set")


# ---------------------------------------------------------------------------
# Step 7: the merge laws (accept: fuzzed communication)
# ---------------------------------------------------------------------------

def _rand_gcounter(rng, node):
    from gc_counter import GCounter
    g = GCounter(node)
    for _ in range(rng.randint(1, 5)):
        g.increment(rng.randint(1, 4))
    return g


def _rand_pncounter(rng, node):
    from gc_counter import PNCounter
    p = PNCounter(node)
    for _ in range(rng.randint(1, 5)):
        (p.increment if rng.random() < 0.5 else p.decrement)(rng.randint(1, 4))
    return p


def _rand_lww(rng, node):
    from lww_register import LWWRegister
    r = LWWRegister(node)
    r.set(rng.choice("xyz"), rng.randint(0, 3))
    return r


def _rand_orset(rng, node):
    from or_set import ORSet
    s = ORSet(node)
    for _ in range(rng.randint(1, 6)):
        e = rng.choice("abc")
        if rng.random() < 0.6:
            s.add(e)
        else:
            s.remove(e)
    return s


def _check_laws(label, build, rng, trials=60) -> None:
    def eq(x, y):
        return x.state() == y.state()

    for _ in range(trials):
        a, b, c = build(rng, "a"), build(rng, "b"), build(rng, "c")
        assert eq(a.merge(b), b.merge(a)), (
            f"{label}: merge is not COMMUTATIVE -- a.merge(b) and b.merge(a) differ. "
            "The merge must be a symmetric join (max / union).")
        assert eq(a.merge(a), a), (
            f"{label}: merge is not IDEMPOTENT -- a.merge(a) changed the state. "
            "Re-delivering the same state must do nothing.")
        assert eq(a.merge(b).merge(c), a.merge(b.merge(c))), (
            f"{label}: merge is not ASSOCIATIVE -- the grouping of merges changed the state.")


def check_merge_laws() -> None:
    rng = random.Random(4242)
    for label, build in (
        ("G-Counter", _rand_gcounter),
        ("PN-Counter", _rand_pncounter),
        ("LWW-register", _rand_lww),
        ("OR-set", _rand_orset),
    ):
        _check_laws(label, build, rng)


# ---------------------------------------------------------------------------
# Step 8: convergence after an arbitrary exchange of merges (accept)
# ---------------------------------------------------------------------------

def _converge(label, build, rng, n=5) -> None:
    replicas = [build(rng, f"node{i}") for i in range(n)]
    initial = list(replicas)          # the states every replica will eventually learn

    # An arbitrary exchange: random pairwise gossip first ...
    for _ in range(4 * n):
        i, j = rng.randrange(n), rng.randrange(n)
        if i != j:
            replicas[i] = replicas[i].merge(replicas[j])
    # ... then each replica merges every state in a different random order.
    results = []
    for r in replicas:
        order = list(range(n))
        rng.shuffle(order)
        acc = r
        for j in order:
            acc = acc.merge(replicas[j])
        results.append(acc.state())

    assert all(x == results[0] for x in results), (
        f"{label}: replicas did not converge -- two nodes that exchanged the same merges "
        "read different states. The join must be order-independent.")
    canonical = initial[0]
    for r in initial[1:]:
        canonical = canonical.merge(r)
    assert results[0] == canonical.state(), (
        f"{label}: the converged state is not the join of every initial replica; a merge "
        "lost an update somewhere.")


def check_convergence() -> None:
    rng = random.Random(20261010)
    for label, build in (
        ("G-Counter", _rand_gcounter),
        ("PN-Counter", _rand_pncounter),
        ("LWW-register", _rand_lww),
        ("OR-set", _rand_orset),
    ):
        _converge(label, build, rng)


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("gc_counter.py", "G-Counter: per-node slots merged by max", check_gcounter),
    ("gc_counter.py", "PN counter goes up and down, below zero", check_pncounter),
    ("lww_register.py", "LWW register: the later write wins", check_lww_basic),
    ("lww_register.py", "LWW ties break by node id, deterministically", check_lww_tiebreak),
    ("or_set.py", "OR-set: add / remove / re-add", check_orset_basic),
    ("or_set.py", "OR-set: remove-then-add keeps, add-then-remove drops", check_orset_remove_then_add),
    ("all CRDTs", "merge is commutative, associative, idempotent", check_merge_laws),
    ("all CRDTs", "replicas converge after arbitrary merges", check_convergence),
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
    print(f"\n{BOLD}CRDTs From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — the replicas converge.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

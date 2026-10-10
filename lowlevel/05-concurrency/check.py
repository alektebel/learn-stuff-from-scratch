"""
Progress checker for the concurrency templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

None of this uses real threads or wall-clock time. Every interleaving is produced by the
cooperative scheduler in ``coop.py``, so a data race and a deadlock happen on every run,
on every machine. The "timeout" is a step budget; the deadlock detector is a drained
ready queue with a thread still blocked.
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


def run_schedule(scheduler, max_steps=1_000_000, context="schedule"):
    """Drive the scheduler, turning any thread crash into a readable assertion.

    A ``NotImplementedError`` is let through untouched so the runner reports it as TODO.
    """
    try:
        return scheduler.run(max_steps=max_steps)
    except NotImplementedError:
        raise
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"{context}: a thread raised {type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# Step 1: locks.py - a spinlock (test-and-set and compare-and-swap) excludes
# ---------------------------------------------------------------------------

def check_spinlock_mutual_exclusion() -> None:
    from coop import Cell, Scheduler
    from locks import SpinLock, SpinLockCAS

    threads, per = 4, 25
    total = threads * per
    for factory in (SpinLock, SpinLockCAS):
        sched = Scheduler()
        cell = Cell(sched, 0)
        lock = factory(sched)
        stats = {"inside": 0, "overlap": 0}

        def worker(n):
            for _ in range(n):
                yield from lock.acquire()
                stats["inside"] += 1
                if stats["inside"] > 1:
                    stats["overlap"] += 1
                value = yield from cell.load()
                yield from cell.store(value + 1)
                stats["inside"] -= 1
                lock.release()

        for i in range(threads):
            sched.spawn(worker, per, name=f"t{i}")
        result = run_schedule(sched, 1_000_000, f"{factory.__name__} run")
        assert stats["overlap"] == 0, (
            f"{factory.__name__}: two threads were inside the critical section at the same "
            f"time ({stats['overlap']} times). acquire() must win the lock before entering "
            "and release() must clear it, or mutual exclusion does not hold.")
        assert cell.value == total, (
            f"{factory.__name__}: {threads} threads x {per} increments produced {cell.value}, "
            f"expected {total}. A lock that fails to exclude lets updates interleave and be "
            f"lost; a lock that never releases makes the run stall ({result.steps} steps).")


# ---------------------------------------------------------------------------
# Step 2: counter.py - unlocked loses updates, locked does not (accept)
# ---------------------------------------------------------------------------

def check_counter_lost_update() -> None:
    from coop import Cell, Scheduler
    from counter import Counter
    from locks import Mutex

    threads, per = 4, 25
    total = threads * per

    sched = Scheduler()
    cell = Cell(sched, 0)
    counter = Counter(cell)
    for i in range(threads):
        sched.spawn(counter.increment_unlocked, per, name=f"u{i}")
    run_schedule(sched, 1_000_000, "unsynchronised increments")
    assert cell.value < total, (
        f"the unsynchronised counter produced {cell.value}, not fewer than {total}. With "
        "the scheduler free to switch between the load and the store of a read-modify-write, "
        "updates MUST be lost — if you got the exact total, increment_unlocked is taking a "
        "lock, or the load/store no longer pass through the scheduler.")

    sched = Scheduler()
    cell = Cell(sched, 0)
    counter = Counter(cell)
    mutex = Mutex(sched)
    for i in range(threads):
        sched.spawn(counter.increment_locked, mutex, per, name=f"l{i}")
    run_schedule(sched, 1_000_000, "locked increments")
    assert cell.value == total, (
        f"the locked counter produced {cell.value}, expected {total}. increment_locked must "
        "hold the lock across the WHOLE load/add/store, so no two threads can read the same "
        "value. Acquiring it only around the store (or not at all) still loses updates.")


# ---------------------------------------------------------------------------
# Step 3: bounded_queue.py - many producers and consumers, no loss or dup (accept)
# ---------------------------------------------------------------------------

def check_queue_no_loss() -> None:
    from bounded_queue import BoundedQueue
    from coop import Scheduler

    producers, consumers, per = 3, 3, 20
    total = producers * per
    assert total % consumers == 0
    sched = Scheduler()
    queue = BoundedQueue(sched, capacity=2)
    produced, consumed = [], []

    def producer(first, count):
        for i in range(count):
            produced.append(first + i)
            yield from queue.put(first + i)

    def consumer(count):
        for _ in range(count):
            consumed.append((yield from queue.get()))

    for p in range(producers):
        sched.spawn(producer, p * per, per, name=f"p{p}")
    for c in range(consumers):
        sched.spawn(consumer, total // consumers, name=f"c{c}")
    result = run_schedule(sched, 1_000_000, "producer/consumer run")

    assert not result.deadlocked, (
        "the producer/consumer run deadlocked. A put that fills the queue must wake a "
        "consumer (signal not_empty), and a get that drains it must wake a producer "
        "(signal not_full); a signal to the wrong condition leaves waiters asleep.")
    assert sorted(consumed) == sorted(produced), (
        f"produced {len(produced)} items, consumed {len(consumed)}: lost="
        f"{sorted(set(produced) - set(consumed))[:5]}, duplicated="
        f"{sorted(x for x in set(consumed) if consumed.count(x) > 1)[:5]}. Every item must "
        "be produced once and consumed once; update count under the mutex and signal the "
        "other side after every mutation.")
    assert queue.count == 0 and not queue.items, (
        f"the queue still holds {queue.count} item(s) after every consumer finished: the "
        "bookkeeping and the deque disagree, or a signal was delivered to nobody.")


# ---------------------------------------------------------------------------
# Step 4: locks.py - a spinlock is not held across a blocking call (accept)
# ---------------------------------------------------------------------------

def check_spinlock_not_held_while_blocking() -> None:
    from coop import Scheduler, YIELD
    from locks import Mutex, SpinLock

    def holder(mutex):
        yield from mutex.acquire()
        while True:
            yield YIELD

    # (a) correct: the spinlock is released before the thread may block.
    sched = Scheduler()
    spin = SpinLock(sched)
    mutex = Mutex(sched)

    def correct():
        yield from spin.acquire()
        spin.release()
        yield from mutex.acquire()

    sched.spawn(holder, mutex, name="holder")
    sched.spawn(correct, name="correct")
    good = run_schedule(sched, 200, "correct spinlock use")
    assert good.violations == [], (
        f"a correct program (spinlock released before the blocking acquire) was flagged: "
        f"{good.violations}. Only a thread that still HOLDS a spinlock when it blocks may "
        "be flagged.")

    # (b) buggy: the spinlock is still held while the thread blocks on a mutex.
    sched = Scheduler()
    spin = SpinLock(sched)
    mutex = Mutex(sched)

    def buggy():
        yield from spin.acquire()
        yield from mutex.acquire()    # blocks while spin is held: the forbidden pattern

    sched.spawn(holder, mutex, name="holder")
    sched.spawn(buggy, name="buggy")
    bad = run_schedule(sched, 200, "buggy spinlock use")
    assert bad.violations, (
        "a thread blocked while still holding a spinlock, and the scheduler did not record "
        "it. The spinlock must tell the scheduler it is held (spin_acquired on acquire, "
        "spin_released on release) so that yielding BLOCK with a lock held is caught. A "
        "spinlock held across a block can deadlock the spinner against the thread it waits "
        "for.")


# ---------------------------------------------------------------------------
# Step 5: bounded_queue.py - lost wake-up when the predicate uses if, not while (limit)
# ---------------------------------------------------------------------------

def check_lost_wakeup() -> None:
    from bounded_queue import BoundedQueue
    from coop import Scheduler

    sched = Scheduler()
    queue = BoundedQueue(sched, capacity=1)
    consumed = []

    def consumer():
        consumed.append((yield from queue.get()))

    sched.spawn(consumer, name="consumer")
    run_schedule(sched, 1000, "consumer waiting for an item")
    assert queue.count == 0 and queue.not_empty.waiters, (
        "after running the lone consumer it should be asleep on an empty queue. If it "
        "returned instead, get() is not waiting when count == 0 at all.")

    # A condition variable is allowed to wake up spuriously. Wake the consumer while the
    # queue is still empty: a `while` guard re-checks and sleeps again; an `if` guard
    # proceeds and pops from an empty deque.
    queue.not_empty.notify_all()
    run_schedule(sched, 1000, "consumer after a spurious wake-up")

    assert consumed == [], (
        f"an empty queue satisfied the consumer after a spurious wake-up: it returned "
        f"{consumed!r}. wait() must be wrapped in `while not predicate:`, never `if` — a "
        "wake-up means the predicate MAY have changed, not that it did.")
    assert queue.count == 0, "the spurious wake-up consumed an item that did not exist"
    assert queue.not_empty.waiters, (
        "after a spurious wake-up the consumer must go back to sleep, not fall through.")


# ---------------------------------------------------------------------------
# Step 6: deadlock.py - opposite lock order deadlocks; a total order does not (limit)
# ---------------------------------------------------------------------------

def check_deadlock_and_lock_order() -> None:
    from coop import Scheduler
    from deadlock import Account, transfer_ordered, transfer_unordered

    # (a) the bug: two transfers in opposite lock order.
    sched = Scheduler()
    a = Account(sched, "a", 100)
    b = Account(sched, "b", 100)
    sched.spawn(transfer_unordered, a, b, 10, name="a->b")
    sched.spawn(transfer_unordered, b, a, 10, name="b->a")
    bad = run_schedule(sched, 1000, "opposite lock order")
    assert bad.deadlocked or bad.timeout, (
        "two transfers taking their two locks in opposite orders did NOT stall. "
        "transfer_unordered must acquire src's lock and then dst's; if it acquired both at "
        "once, or ordered them, the deadlock this step is about never forms.")

    # (b) the fix: a total order, many concurrent opposing transfers.
    sched = Scheduler()
    accounts = [Account(sched, f"acct{i}", 100) for i in range(4)]
    start_total = sum(acc.balance for acc in accounts)
    moves = [(0, 1), (1, 0), (2, 3), (3, 2), (0, 3), (3, 0), (1, 2), (2, 1)]
    for i in range(len(moves) * 3):
        src, dst = moves[i % len(moves)]
        sched.spawn(transfer_ordered, accounts[src], accounts[dst], 1, name=f"m{i}")
    good = run_schedule(sched, 2_000_000, "ordered transfers")
    assert not (good.deadlocked or good.timeout), (
        "transfer_ordered stalled under concurrent opposing transfers. It must acquire the "
        "two account locks in a GLOBAL order (for example by account name), not in argument "
        "order, or two transfers in opposite directions still deadlock.")
    assert sum(acc.balance for acc in accounts) == start_total, (
        "money was created or destroyed: a transfer must move the amount under both locks, "
        "so the total across all accounts is conserved.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("locks.py", "a spinlock excludes: test-and-set and compare-and-swap",
     check_spinlock_mutual_exclusion),
    ("counter.py", "unsynchronised loses updates, locked does not",
     check_counter_lost_update),
    ("bounded_queue.py", "many producers/consumers: no item lost or duplicated",
     check_queue_no_loss),
    ("locks.py", "a spinlock is not held across a blocking call",
     check_spinlock_not_held_while_blocking),
    ("bounded_queue.py", "limit: a spurious wake-up needs while, not if",
     check_lost_wakeup),
    ("deadlock.py", "limit: opposite lock order deadlocks, a total order does not",
     check_deadlock_and_lock_order),
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
    print(f"\n{BOLD}Locks & Condition Variables From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the synchronisation layer.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

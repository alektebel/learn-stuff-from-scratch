"""A deterministic cooperative scheduler: the machine this module runs on.

**Provided, not an exercise.** You do not have to write this file. It exists so that
concurrency can be *observed* without a real OS race: you step the threads yourself, so
every interleaving is reproducible and every "bug" is a fact of the schedule, not a
lottery.

Sources
-------
* OSTEP, ch. 28 *Locks* (Arpaci-Dusseau & Arpaci-Dusseau, 2018): mutual exclusion is
  built from an atomic instruction (test-and-set, compare-and-swap) plus a spin; that is
  the machine model this file hands you.
* OSTEP, ch. 29 *Lock-based Concurrent Data Structures*: a bounded queue and a shared
  counter, guarded by a lock, are the canonical structures. Restated: correctness is a
  property of *every* interleaving, not of the one you happened to run.
* OSTEP, ch. 30 *Condition Variables*: ``wait``/``signal`` with a mutex, and the rule
  that the predicate must be re-checked in a ``while`` loop.

DESIGN DECISION - real threads, or a scheduler you step?

``threading`` gives you a genuine race, which is exactly what makes it useless for
grading: the lost update may not happen on a fast machine, and a deadlock test would
have to wait on the clock. **Chosen:** cooperative threads that are Python generators.
A thread runs to its next ``yield`` and then the scheduler picks the next ready thread;
every shared-memory access and every blocking primitive is a scheduling point, so the
checker controls the interleaving completely. The cost is that this is not real
parallelism — there is one instruction stream — but the *races* it reproduces are the
real ones, and they reproduce every time.

DESIGN DECISION - how big is a scheduling step?

If a switch could happen between any two Python statements, the schedules would be
uncontrollable and unreadable. **Chosen:** a switch happens only where a primitive yields:

* a plain shared-memory access (:class:`Cell`) is one step — a load can be separated from
  the store that follows it, which is precisely what an unsynchronised read-modify-write
  gets wrong;
* an atomic instruction (``atomic_test_and_set``/``atomic_compare_and_swap``) does *not*
  yield in the middle — it is indivisible, as the hardware promises;
* a lock acquire, a wait and a signal are steps.

Threads are run round-robin, in spawn order, from a single ready queue. Nothing here uses
wall-clock time; the "timeout" that surfaces a deadlock is a *step budget* and the fact
that the ready queue drained while threads were still blocked.
"""

from collections import deque

#: Yielded by a thread that is merely preempted: it stays runnable.
YIELD = object()
#: Yielded by a thread that is going to sleep: it leaves the ready queue until woken.
BLOCK = object()


class Word:
    """One word of shared memory that the atomic instructions operate on."""

    def __init__(self, value: int = 0):
        self.value = value

    def __repr__(self) -> str:
        return f"Word({self.value})"


def atomic_test_and_set(word: Word) -> int:
    """Atomically set ``word`` to 1 and return its *old* value.

    Indivisible: it has no scheduling point inside, so no other thread can run between
    reading the old value and writing the new one. That indivisibility is the whole
    primitive a test-and-set spinlock is built from.
    """
    old = word.value
    word.value = 1
    return old


def atomic_compare_and_swap(word: Word, expected: int, new: int) -> int:
    """Atomically write ``new`` iff ``word`` equals ``expected``; return the old value.

    The caller learns whether it won by comparing the return value with ``expected``.
    Also indivisible.
    """
    old = word.value
    if old == expected:
        word.value = new
    return old


class Thread:
    """A cooperative thread: a generator plus its scheduling state."""

    def __init__(self, gen, name: str):
        self.gen = gen
        self.name = name
        self.state = "ready"          # ready | blocked | done
        self.blocked_on = None        # the primitive it is sleeping inside
        self.spin_depth = 0           # spinlocks currently held (nesting level)
        self.spin_held = []           # the spinlocks themselves, outermost last
        self.exception = None

    def __repr__(self) -> str:
        return f"<Thread {self.name} {self.state}>"


class RunResult:
    """What a call to :meth:`Scheduler.run` produced. Printed by every demo."""

    def __init__(self, steps, deadlocked, errors, timeout, violations):
        self.steps = steps
        self.deadlocked = deadlocked
        self.errors = errors
        self.timeout = timeout
        self.violations = violations

    def __repr__(self) -> str:
        return (f"RunResult(steps={self.steps}, deadlocked={self.deadlocked}, "
                f"timeout={self.timeout}, errors={self.errors}, "
                f"violations={len(self.violations)})")


class Scheduler:
    """Round-robin driver for cooperative threads.

    ``spawn`` adds a thread, ``run`` steps ready threads until they finish, the ready
    queue drains (a deadlock if anyone is still blocked) or a step budget is hit.
    Exceptions from a thread are recorded and re-raised, so a template that is not
    implemented yet still surfaces its ``NotImplementedError``.
    """

    def __init__(self):
        self.threads = []
        self.ready = deque()
        self.current = None
        self.steps = 0
        self.violations = []
        self.errors = []
        self.timeout = False

    def spawn(self, gen_fn, *args, name=None, **kwargs) -> Thread:
        """Create a thread from generator function ``gen_fn`` and make it runnable."""
        thread = Thread(gen_fn(*args, **kwargs), name or f"t{len(self.threads)}")
        self.threads.append(thread)
        self.ready.append(thread)
        return thread

    # -- spinlock bookkeeping: lets the scheduler see the "held across a block" bug --

    def spin_acquired(self, lock) -> None:
        """Record that the running thread now holds spinlock ``lock``."""
        thread = self.current
        thread.spin_depth += 1
        thread.spin_held.append(lock)

    def spin_released(self, lock) -> None:
        """Record that the running thread no longer holds spinlock ``lock``."""
        thread = self.current
        thread.spin_depth -= 1
        if lock in thread.spin_held:
            thread.spin_held.remove(lock)

    # -- scheduling ----------------------------------------------------------------

    def wake(self, thread: Thread) -> None:
        """Make a blocked thread runnable again. Waking a runnable thread is a no-op."""
        if thread.state == "blocked":
            thread.state = "ready"
            thread.blocked_on = None
            self.ready.append(thread)

    def step(self) -> Thread | None:
        """Run the next ready thread up to its next yield. Return the thread, or None."""
        if not self.ready:
            return None
        thread = self.ready.popleft()
        self.current = thread
        self.steps += 1
        try:
            token = next(thread.gen)
        except StopIteration:
            thread.state = "done"
            self.current = None
            return thread
        except BaseException as exc:  # noqa: BLE001 - recorded, then re-raised
            thread.state = "done"
            thread.exception = exc
            self.errors.append((thread.name, f"{type(exc).__name__}: {exc}"))
            self.current = None
            raise
        if token is BLOCK:
            # The invariant that gives the spinlock its name: you may not sleep holding it.
            if thread.spin_depth > 0:
                self.violations.append(
                    f"{thread.name} blocked on {thread.blocked_on!r} while holding "
                    f"{thread.spin_depth} spinlock(s)")
            thread.state = "blocked"
        else:
            thread.state = "ready"
            self.ready.append(thread)
        self.current = None
        return thread

    def run(self, max_steps: int = 200_000) -> RunResult:
        """Step until every thread is done, the ready queue drains, or ``max_steps``.

        A drained ready queue with a blocked thread is a deadlock: nobody left can wake
        it. Exhausting ``max_steps`` is the deterministic stand-in for a wall-clock
        timeout on a livelock (a spin that never wins).
        """
        while self.ready:
            if self.steps >= max_steps:
                self.timeout = True
                break
            self.step()
        deadlocked = (not self.ready) and any(t.state == "blocked" for t in self.threads)
        return RunResult(self.steps, deadlocked, self.errors, self.timeout, self.violations)


class Cell:
    """A word of shared *ordinary* memory, addressable from any thread.

    A ``load`` reads the value and then yields, so the scheduler may run another thread
    before the value reaches the caller; a ``store`` yields before it writes. Put a load
    and a store either side of a scheduling point and you have a read-modify-write that
    two threads can interleave — the lost update. A lock serialises those steps; that is
    the entire difference between :mod:`counter`'s two increment routines.
    """

    def __init__(self, scheduler: Scheduler, value: int = 0):
        self.S = scheduler
        self.value = value
        #: Measurements, for the demos: how many memory operations were issued.
        self.loads = 0
        self.stores = 0

    def load(self):
        """Yield the scheduling point, then hand back the value captured before it."""
        self.loads += 1
        value = self.value
        yield YIELD
        return value

    def store(self, value):
        """Take the scheduling point, then commit ``value``."""
        self.stores += 1
        yield YIELD
        self.value = value


# ---------------------------------------------------------------------------
# Demo (provided): the lost update, the deadlock detector, and a clean schedule.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Self-contained on purpose: importing a sibling here would make ``coop`` be
    # imported a second time under its own name (this process's module is ``__main__``),
    # and the duplicate's YIELD/BLOCK sentinels would not compare equal to this copy's.
    def add_unlocked(cell, n):
        for _ in range(n):
            value = yield from cell.load()
            yield from cell.store(value + 1)

    def add_guarded(cell, flag, n):
        for _ in range(n):
            while atomic_test_and_set(flag):   # busy-wait, one scheduling step per loss
                yield YIELD
            value = yield from cell.load()
            yield from cell.store(value + 1)
            flag.value = 0                     # release the spin guard

    sched = Scheduler()
    cell = Cell(sched, 0)
    for name in ("a", "b"):
        sched.spawn(add_unlocked, cell, 5, name=name)
    result = sched.run()
    print(f"coop: {len(sched.threads)} threads, {result.steps} scheduling steps")
    print(f"  unsynchronised: two threads x 5 increments -> value {cell.value} "
          f"(expected 10; {cell.loads} loads, {cell.stores} stores)")

    sched2 = Scheduler()
    cell2 = Cell(sched2, 0)
    flag = Word(0)
    for name in ("a", "b"):
        sched2.spawn(add_guarded, cell2, flag, 5, name=name)
    result2 = sched2.run()
    print(f"  spin-guarded:   two threads x 5 increments -> value {cell2.value} "
          f"(expected 10; {result2.steps} steps, deadlocked={result2.deadlocked})")


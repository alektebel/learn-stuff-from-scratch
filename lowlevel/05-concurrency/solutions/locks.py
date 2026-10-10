"""Mutual exclusion: spinlocks (test-and-set and compare-and-swap), a blocking mutex,
and condition variables.

Sources
-------
* OSTEP, ch. 28 *Locks*: a lock is built from an atomic instruction plus a loop. The
  chapter's test-and-set and compare-and-swap spinlocks are what you assemble here; its
  lesson is that a spinlock wastes the CPU while it waits.
* OSTEP, ch. 29 *Lock-based Concurrent Data Structures*: the lock is only useful because
  it makes a read-modify-write on a shared structure atomic.
* OSTEP, ch. 30 *Condition Variables*: ``wait`` must atomically release the lock and
  sleep, and callers must re-check the predicate in a ``while`` loop (Mesa semantics).

DESIGN DECISION - spinlock or blocking mutex?

A spinlock busy-waits: every failed ``acquire`` yields to the scheduler and retries. On
real hardware that burns a core, which is why a spinlock is only correct for a *very
short* critical section and, critically, must never be held across a call that blocks —
the spinner holds the CPU while the thing it waits for cannot run. A mutex instead parks
the thread (yields ``BLOCK``) and is woken by the releaser. **Chosen:** provide both, and
keep them visibly different. This module's scheduler records a violation if a thread ever
blocks while holding a spinlock; the checker turns that into a graded step.

DESIGN DECISION - wake one waiter directly, or just clear the flag?

Clearing the flag and letting all waiters race is the simplest mutex, but it is a
thundering herd and a waiter can lose the race repeatedly. **Chosen:** on release, hand
ownership directly to the first waiter (FIFO) and wake only that one. It is fair, wakes
exactly one thread, and — because the waiter is already on the wait queue *before* it
sleeps — there is no window in which a wake-up can be lost. The cost is a little
bookkeeping (an owner field), which also lets the demos print who holds the lock.

DESIGN DECISION - where does the lost-wake-up come from, if ``wait`` is correct?

It does not come from ``wait``; it comes from the *caller* writing ``if not ready:``
around it. POSIX explicitly permits spurious wake-ups, and ``signal`` means "the predicate
*may* now be true", not "it is true for you". Re-checking in ``while`` turns both facts
into safety. The checker manufactures a spurious wake-up deliberately to prove a ``while``
is present.
"""

from collections import deque

from coop import BLOCK, YIELD, Word, atomic_compare_and_swap, atomic_test_and_set


class SpinLock:
    """A test-and-set spinlock.

    ``acquire`` repeatedly issues the atomic test-and-set; each failure is a scheduling
    step, so another thread can make progress and eventually release. ``release`` clears
    the word. Both print their winner in the demos via ``holder``.
    """

    def __init__(self, scheduler):
        self.S = scheduler
        self.state = Word(0)
        self.holder = None

    def acquire(self):
        while atomic_test_and_set(self.state):
            yield YIELD
        self.holder = self.S.current
        self.S.spin_acquired(self)

    def release(self):
        self.S.spin_released(self)
        self.holder = None
        self.state.value = 0


class SpinLockCAS(SpinLock):
    """The same lock, built from compare-and-swap instead of test-and-set.

    A CAS spinlock attempts to swap ``0 -> 1`` and only wins if the word is still ``0``.
    Unlike test-and-set it does not write on a loss, so it is the better primitive for a
    contended lock; the mechanism is otherwise identical.
    """

    def acquire(self):
        while atomic_compare_and_swap(self.state, 0, 1) != 0:
            yield YIELD
        self.holder = self.S.current
        self.S.spin_acquired(self)


class Mutex:
    """A blocking mutex: uncontended take is one scheduling step, contended take parks.

    ``acquire`` is a generator (it may sleep). ``release`` is an ordinary call that hands
    the lock to the next waiter, or clears it when nobody waits. A thread woken from
    ``acquire`` already owns the lock when it resumes.
    """

    def __init__(self, scheduler):
        self.S = scheduler
        self.locked = False
        self.owner = None
        self.waiters = deque()

    def acquire(self):
        me = self.S.current
        if not self.locked:
            self.locked = True
            self.owner = me
            yield YIELD
            return
        self.waiters.append(me)
        me.blocked_on = self
        yield BLOCK
        return

    def release(self):
        if not self.locked:
            raise RuntimeError("release() of an unlocked mutex")
        if self.waiters:
            nxt = self.waiters.popleft()
            self.owner = nxt
            self.S.wake(nxt)
        else:
            self.locked = False
            self.owner = None


class Condition:
    """A condition variable bound to a mutex.

    ``wait`` releases the mutex, adds the caller to the wait queue and sleeps; when woken
    it re-acquires the mutex before returning. ``notify`` wakes one waiter and
    ``notify_all`` wakes every waiter, in FIFO order. Callers must re-check the predicate
    in a ``while`` loop: a wake-up may be spurious.
    """

    def __init__(self, scheduler, mutex):
        self.S = scheduler
        self.mutex = mutex
        self.waiters = deque()

    def wait(self):
        me = self.S.current
        self.mutex.release()
        self.waiters.append(me)
        me.blocked_on = self
        yield BLOCK
        yield from self.mutex.acquire()

    def notify(self):
        if self.waiters:
            self.S.wake(self.waiters.popleft())

    def notify_all(self):
        while self.waiters:
            self.S.wake(self.waiters.popleft())


# ---------------------------------------------------------------------------
# Demo: three locks, four threads each, one exact answer.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from coop import Cell, Scheduler
    from counter import Counter

    for factory in (SpinLock, SpinLockCAS, Mutex):
        sched = Scheduler()
        cell = Cell(sched, 0)
        lock = factory(sched)
        counter = Counter(cell)
        for i in range(4):
            sched.spawn(counter.increment_locked, lock, 25, name=f"t{i}")
        result = sched.run(max_steps=1_000_000)
        print(f"locks: {factory.__name__:<12} 4 threads x 25 -> value {cell.value} "
              f"(expected 100), steps {result.steps}, deadlocked={result.deadlocked}")

"""A shared counter incremented with, and without, a lock.

Sources
-------
* OSTEP, ch. 29 *Lock-based Concurrent Data Structures*: the "approximate counter" and
  the plain shared counter both hinge on one fact — ``counter++`` is not one operation.
  It is a load, an add and a store, and an interrupt (here: a scheduling step) between the
  load and the store lets two threads write the same incremented value.
* OSTEP, ch. 28 *Locks*: the fix is to hold a lock across the whole read-modify-write, so
  the two threads' load/add/store sequences cannot interleave.

DESIGN DECISION - what exactly is the race here?

``Cell.load`` reads the value and then yields; ``Cell.store`` yields before it writes. So
``increment_unlocked`` compiles to:

    load   (scheduling step)
    add
    store  (scheduling step)

Two threads at the same value both load it, both add one, and both store the same result:
one increment is lost. **Chosen:** show the race on plain ``Cell`` accesses and show the
lock closing it, rather than hand-waving at "atomicity". The checker asserts the
unsynchronised result is *short* and the locked one is *exact*; neither number is timing
dependent.
"""


class Counter:
    """A shared integer in one :class:`coop.Cell`, with two increment routines."""

    def __init__(self, cell):
        self.cell = cell

    def increment_unlocked(self, n):
        """Add ``n`` with no lock. Each iteration is an interleavable load/add/store."""
        # TODO: n times: load the cell, then store the loaded value + 1. Do NOT hold a lock: the load and the store are separate scheduling points, so two threads interleave and lose updates.
        raise NotImplementedError("Counter.increment_unlocked")

    def increment_locked(self, lock, n):
        """Add ``n`` holding ``lock`` across every load/add/store, so none interleaves."""
        # TODO: n times: acquire the lock, load, store value + 1, and release — the lock is held across the WHOLE read-modify-write, so no other thread can read the same value.
        raise NotImplementedError("Counter.increment_locked")


if __name__ == "__main__":
    from coop import Cell, Scheduler
    from locks import Mutex

    sched = Scheduler()
    cell = Cell(sched, 0)
    counter = Counter(cell)
    for name in ("a", "b"):
        sched.spawn(counter.increment_unlocked, 5, name=name)
    sched.run()

    sched2 = Scheduler()
    cell2 = Cell(sched2, 0)
    counter2 = Counter(cell2)
    mutex = Mutex(sched2)
    for name in ("a", "b"):
        sched2.spawn(counter2.increment_locked, mutex, 5, name=name)
    sched2.run()

    print("counter: two threads x 5 increments")
    print(f"  unlocked: value {cell.value} (expected 10) — "
          f"{10 - cell.value} update(s) lost to the interleaved read-modify-write")
    print(f"  locked:   value {cell2.value} (expected 10) — "
          f"the lock serialised {cell2.loads} loads and {cell2.stores} stores")

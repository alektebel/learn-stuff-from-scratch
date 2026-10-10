"""Two locks, two bad orders, and the deadlock that follows — surfaced by the scheduler.

Sources
-------
* OSTEP, ch. 32 *Concurrency Bugs* (and the lock-ordering discussion around ch. 28–29):
  deadlock from lock-order inversion. Restated: if thread A holds L1 and wants L2 while
  thread B holds L2 and wants L1, neither can proceed, and no amount of waiting helps.
* OSTEP, ch. 28 *Locks*: the classic fixes are a total lock order, a try-lock that gives
  up and retries, or one coarse lock. This module uses the total order.

DESIGN DECISION - how is a deadlock "surfaced by a timeout" without wall-clock time?

A real deadlock detector waits on a clock, which makes a test flaky and slow. **Chosen:**
the scheduler runs a step budget and also stops when the ready queue drains while threads
are still blocked. A drained queue with blocked threads is a definite deadlock (nobody
left can wake them); an exhausted budget is a livelock. Both are deterministic and both
are reported in :class:`coop.RunResult`, so the check can assert "this schedule must
deadlock" and "that one must not".

DESIGN DECISION - a per-account lock, or one global lock?

One lock for all accounts removes the deadlock entirely and serialises every transfer.
**Chosen:** a lock per account plus a *total order* on the locks, because that is the
lesson: deadlock is avoided by acquiring in a globally consistent order. The cost is that
every caller must keep the order, which is exactly the discipline the ordered helper
enforces.
"""

from coop import YIELD

from locks import Mutex


class Account:
    """A balance and its own lock. ``name`` gives the account a total order."""

    def __init__(self, scheduler, name, balance):
        self.name = name
        self.balance = balance
        self.lock = Mutex(scheduler)

    def __repr__(self):
        return f"Account({self.name}, {self.balance})"


def transfer_unordered(src, dst, amount):
    """Move ``amount`` taking ``src.lock`` then ``dst.lock`` in argument order.

    This is the buggy shape: two callers that pass the accounts in opposite orders hold
    one lock each and wait for the other forever.
    """
    # TODO: Acquire src's lock then dst's, in that argument order, move the amount, release both. Two opposite calls deadlock — that is the point of this function.
    raise NotImplementedError("transfer_unordered")


def transfer_ordered(src, dst, amount):
    """Move ``amount``, taking the two locks in a global order by ``name``.

    The transfer direction is unchanged; only the *acquisition* order is sorted, so two
    concurrent transfers between the same pair can never hold one lock each.
    """
    # TODO: Pick first/second by a global order (e.g. account name), acquire first then second, move the amount, release both in reverse. The acquisition order, not the transfer direction, is sorted.
    raise NotImplementedError("transfer_ordered")


if __name__ == "__main__":
    from coop import Scheduler

    # The bug: opposite orders.
    sched = Scheduler()
    a = Account(sched, "a", 100)
    b = Account(sched, "b", 100)
    sched.spawn(transfer_unordered, a, b, 10, name="a->b")
    sched.spawn(transfer_unordered, b, a, 10, name="b->a")
    bad = sched.run(max_steps=10_000)

    # The fix: a total order.
    sched2 = Scheduler()
    c = Account(sched2, "c", 100)
    d = Account(sched2, "d", 100)
    sched2.spawn(transfer_ordered, c, d, 10, name="c->d")
    sched2.spawn(transfer_ordered, d, c, 10, name="d->c")
    good = sched2.run(max_steps=10_000)

    print("deadlock: two transfers in opposite lock order")
    print(f"  unordered: deadlocked={bad.deadlocked} after {bad.steps} steps "
          f"(a={a.balance}, b={b.balance}, sum={a.balance + b.balance})")
    print(f"  ordered:   deadlocked={good.deadlocked}, c={c.balance}, d={d.balance}, "
          f"sum={c.balance + d.balance} (conserved={c.balance + d.balance == 200})")

"""A bounded queue guarded by one mutex and two condition variables.

Sources
-------
* OSTEP, ch. 30 *Condition Variables*: the producer/consumer problem solved with a mutex
  plus ``wait``/``signal``. ``wait`` releases the lock while sleeping and re-acquires it
  before returning, which is what makes "check the predicate, then wait under the lock"
  atomic against a producer.
* OSTEP, ch. 29 *Lock-based Concurrent Data Structures*: the bounded buffer is the running
  example; the invariant is that every produced item is consumed exactly once and the
  queue never exceeds its capacity.

DESIGN DECISION - one condition variable, or two?

A single condition variable forces producers and consumers onto the same wait queue, so a
producer's wake-up can rouse another producer and everyone wakes to re-check and sleep
again. **Chosen:** two condition variables — ``not_empty`` for consumers, ``not_full`` for
producers. Each signal targets exactly the side that can act. The cost is one extra object
and the discipline of signalling the *other* side after every mutation.

DESIGN DECISION - ``while`` or ``if`` around ``wait``?

**Chosen:** ``while``. A wake-up only means "the predicate may have changed"; it may be
spurious, and another waiter may consume the item first. ``if`` proceeds on a wake-up that
no longer guarantees anything and pops from an empty queue. The limit-case check
manufactures a spurious wake-up to prove the loop is a ``while``.

DESIGN DECISION - is ``count`` derived, or independent?

The queue is a ``deque`` plus an integer ``count``. It is one line extra, but it gives the
checker (and you) a cheap invariant to read, and it keeps the wait predicates simple.
"""

from collections import deque

from coop import BLOCK, YIELD
from locks import Condition, Mutex


class BoundedQueue:
    """A fixed-capacity FIFO. ``mutex``/``not_empty``/``not_full``/``items``/``count``
    are public so the checker can drive and inspect the queue."""

    def __init__(self, scheduler, capacity):
        self.S = scheduler
        self.capacity = capacity
        self.mutex = Mutex(scheduler)
        self.not_empty = Condition(scheduler, self.mutex)
        self.not_full = Condition(scheduler, self.mutex)
        self.items = deque()
        self.count = 0

    def put(self, item):
        """Block while full, append ``item``, then wake one waiting consumer."""
        # TODO: Under the mutex: while count == capacity, wait on not_full. Append, count += 1, signal not_empty, release the mutex. `while`, not `if`.
        raise NotImplementedError("BoundedQueue.put")

    def get(self):
        """Block while empty, pop one item, then wake one blocked producer."""
        # TODO: Under the mutex: while count == 0, wait on not_empty. Pop, count -= 1, signal not_full, release the mutex, return the item. `while`, not `if`.
        raise NotImplementedError("BoundedQueue.get")


if __name__ == "__main__":
    from coop import Scheduler

    def producer(queue, first, count, log):
        for i in range(count):
            yield from queue.put(first + i)
            log.append(first + i)

    def consumer(queue, count, log):
        for _ in range(count):
            log.append(("got", (yield from queue.get())))

    sched = Scheduler()
    queue = BoundedQueue(sched, capacity=2)
    produced, consumed = [], []
    producers, consumers, each = 3, 3, 20
    for p in range(producers):
        sched.spawn(producer, queue, p * each, each, produced, name=f"p{p}")
    for c in range(consumers):
        sched.spawn(consumer, queue, (producers * each) // consumers, consumed, name=f"c{c}")
    result = sched.run(max_steps=1_000_000)
    got = sorted(item for _, item in consumed)
    print(f"bounded_queue: capacity 2, {producers} producers x {each} and "
          f"{consumers} consumers")
    print(f"  produced {len(produced)}, consumed {len(got)}, identical={got == sorted(produced)}")
    print(f"  final depth {queue.count} (must be 0), steps {result.steps}, "
          f"deadlocked={result.deadlocked}")

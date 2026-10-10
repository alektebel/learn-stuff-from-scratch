"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each is a classic mistake for a concurrency mechanism, and each must be caught by the
named step. ``coop.py`` is provided scaffolding but still gets a planted bug: the checker
must notice when the scheduler stops tracking held spinlocks.
"""
MUTATIONS = [
    # coop.py ----------------------------------------------------------------------
    ("scheduler stops tracking held spinlocks", "coop.py",
     "    def spin_acquired(self, lock) -> None:\n"
     "        \"\"\"Record that the running thread now holds spinlock ``lock``.\"\"\"\n"
     "        thread = self.current\n"
     "        thread.spin_depth += 1\n"
     "        thread.spin_held.append(lock)\n",
     "    def spin_acquired(self, lock) -> None:\n"
     "        \"\"\"Record that the running thread now holds spinlock ``lock``.\"\"\"\n"
     "        return\n",
     "4"),

    # locks.py ---------------------------------------------------------------------
    ("a spinlock never releases", "locks.py",
     "    def release(self):\n"
     "        self.S.spin_released(self)\n"
     "        self.holder = None\n"
     "        self.state.value = 0\n",
     "    def release(self):\n"
     "        self.S.spin_released(self)\n"
     "        self.holder = None\n",
     "1"),

    ("a mutex release never wakes the waiter", "locks.py",
     "        if self.waiters:\n"
     "            nxt = self.waiters.popleft()\n"
     "            self.owner = nxt\n"
     "            self.S.wake(nxt)\n",
     "        if self.waiters:\n"
     "            nxt = self.waiters.popleft()\n"
     "            self.owner = nxt\n",
     "3"),

    # counter.py -------------------------------------------------------------------
    ("locked increment forgets the lock", "counter.py",
     "        for _ in range(n):\n"
     "            yield from lock.acquire()\n"
     "            value = yield from self.cell.load()\n"
     "            yield from self.cell.store(value + 1)\n"
     "            lock.release()\n",
     "        for _ in range(n):\n"
     "            value = yield from self.cell.load()\n"
     "            yield from self.cell.store(value + 1)\n",
     "2"),

    # bounded_queue.py -------------------------------------------------------------
    ("the consumer checks the predicate with if, not while", "bounded_queue.py",
     "        yield from self.mutex.acquire()\n"
     "        while self.count == 0:\n"
     "            yield from self.not_empty.wait()\n",
     "        yield from self.mutex.acquire()\n"
     "        if self.count == 0:\n"
     "            yield from self.not_empty.wait()\n",
     "5"),

    ("put wakes the wrong condition variable", "bounded_queue.py",
     "        self.items.append(item)\n"
     "        self.count += 1\n"
     "        self.not_empty.notify()\n",
     "        self.items.append(item)\n"
     "        self.count += 1\n"
     "        self.not_full.notify()\n",
     "3"),

    # deadlock.py ------------------------------------------------------------------
    ("ordered transfer does not order the locks", "deadlock.py",
     "    first, second = (src, dst) if src.name <= dst.name else (dst, src)\n",
     "    first, second = src, dst\n",
     "6"),
]

"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

``coop.py`` is listed with no functions on purpose: it is the provided machine, copied
verbatim into the module root so the learner writes only the synchronisation primitives.
"""
HINTS = {
 "coop.py": {},
 "locks.py": {
  "SpinLock.acquire": "Spin on atomic_test_and_set: while the word was already 1, yield to the scheduler and try again. On winning, set holder and call the scheduler's spin_acquired so a block-while-held can be detected.",
  "SpinLock.release": "Call the scheduler's spin_released, clear holder, and write 0 to the state word so the next spinner can win.",
  "SpinLockCAS.acquire": "Same spin, but attempt atomic_compare_and_swap(state, 0, 1): you win only when it returns 0. On winning, set holder and call spin_acquired.",
  "Mutex.acquire": "If unlocked, take it, set owner, yield once, return. If locked, append yourself to waiters, set blocked_on, and yield BLOCK; when woken you already own the lock.",
  "Mutex.release": "Fail if not locked. If a waiter exists, pop it FIFO, hand it ownership (owner = waiter, stay locked) and wake it; otherwise clear locked and owner.",
  "Condition.wait": "Release the mutex, append yourself to waiters, set blocked_on and yield BLOCK; when woken, re-acquire the mutex before returning.",
  "Condition.notify": "If a waiter is queued, wake exactly one (FIFO).",
  "Condition.notify_all": "Wake every queued waiter, FIFO, until the wait queue is empty.",
 },
 "counter.py": {
  "Counter.increment_unlocked": "n times: load the cell, then store the loaded value + 1. Do NOT hold a lock: the load and the store are separate scheduling points, so two threads interleave and lose updates.",
  "Counter.increment_locked": "n times: acquire the lock, load, store value + 1, and release — the lock is held across the WHOLE read-modify-write, so no other thread can read the same value.",
 },
 "bounded_queue.py": {
  "BoundedQueue.put": "Under the mutex: while count == capacity, wait on not_full. Append, count += 1, signal not_empty, release the mutex. `while`, not `if`.",
  "BoundedQueue.get": "Under the mutex: while count == 0, wait on not_empty. Pop, count -= 1, signal not_full, release the mutex, return the item. `while`, not `if`.",
 },
 "deadlock.py": {
  "transfer_unordered": "Acquire src's lock then dst's, in that argument order, move the amount, release both. Two opposite calls deadlock — that is the point of this function.",
  "transfer_ordered": "Pick first/second by a global order (e.g. account name), acquire first then second, move the amount, release both in reverse. The acquisition order, not the transfer direction, is sorted.",
 },
}

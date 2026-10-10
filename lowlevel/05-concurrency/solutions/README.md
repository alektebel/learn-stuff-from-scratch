# Locks, Atomics & Condition Variables — Solutions

Complete versions of every template in the parent directory. Pure Python 3, standard
library only. **No real threads and no wall-clock time**: `coop.py` is a deterministic
cooperative scheduler, so every number below reproduces exactly, run after run. Run them
from inside this directory (they import each other by name):

```bash
python3 coop.py            # the scheduler: a lost update, then a spin guard that fixes it
python3 locks.py           # spinlock (TAS), spinlock (CAS) and mutex: all give 100
python3 counter.py         # unlocked loses 5 of 10 updates; locked does not
python3 bounded_queue.py   # 3 producers, 3 consumers, 60 items, none lost or duplicated
python3 deadlock.py        # opposite lock order deadlocks; a total order does not
```

Expected output:

`coop.py`:

```
coop: 2 threads, 22 scheduling steps
  unsynchronised: two threads x 5 increments -> value 5 (expected 10; 10 loads, 10 stores)
  spin-guarded:   two threads x 5 increments -> value 10 (expected 10; 32 steps, deadlocked=False)
```

`locks.py`:

```
locks: SpinLock     4 threads x 25 -> value 100 (expected 100), steps 504, deadlocked=False
locks: SpinLockCAS  4 threads x 25 -> value 100 (expected 100), steps 504, deadlocked=False
locks: Mutex        4 threads x 25 -> value 100 (expected 100), steps 304, deadlocked=False
```

`counter.py`:

```
counter: two threads x 5 increments
  unlocked: value 5 (expected 10) — 5 update(s) lost to the interleaved read-modify-write
  locked:   value 10 (expected 10) — the lock serialised 10 loads and 10 stores
```

`bounded_queue.py`:

```
bounded_queue: capacity 2, 3 producers x 20 and 3 consumers
  produced 60, consumed 60, identical=True
  final depth 0 (must be 0), steps 326, deadlocked=False
```

`deadlock.py`:

```
deadlock: two transfers in opposite lock order
  unordered: deadlocked=True after 4 steps (a=100, b=100, sum=200)
  ordered:   deadlocked=False, c=100, d=100, sum=200 (conserved=True)
```

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd lowlevel/05-concurrency
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 6/6 passing
```

The number worth predicting before you look is the unsynchronised value: two threads each
add 5, and the answer is **5**, not 10. The scheduler alternates the two threads at the
`Cell` between the load and the store, so every round both read the same value and both
write the same incremented one — five increments vanish. Run it, then predict the locked
run and the four-thread spinlock run before you look.

# Locks, Atomics & Condition Variables From Scratch

Mutual exclusion, atomic instructions, and condition variables, in pure Python (standard
library only) — built on a **deterministic cooperative scheduler** so that a data race and
a deadlock happen on every run, on every machine, with no wall-clock time and no luck.

This is the concurrency node of the `lowlevel` track. It sits after
`lowlevel-04-syscalls-io`: once I/O can block, the interesting question is what a *second*
thread may do while the first is blocked — and the answer is where every lost update and
lost wake-up lives.

Sources:

- OSTEP, ch. 28 *Locks* (Arpaci-Dusseau & Arpaci-Dusseau, 2018) — a lock is an atomic
  instruction (test-and-set, compare-and-swap) plus a spin, and a spinlock wastes the CPU.
- OSTEP, ch. 29 *Lock-based Concurrent Data Structures* — the bounded buffer and the
  shared counter; correctness means *every* interleaving, not the one you happened to run.
- OSTEP, ch. 30 *Condition Variables* — `wait`/`signal` with a mutex, and the rule that
  the predicate is re-checked in a `while` loop.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Synchronisation substrate (*provided*) | deterministic scheduler, atomic instructions, shared cell | `coop.py` | — |
| Spinlocks | test-and-set and compare-and-swap | `locks.py` | 1, 4 |
| Blocking mutex & condition variables | park/wake, FIFO handoff, `while` predicate | `locks.py` | 3, 4, 5 |
| Shared counter | read-modify-write with and without a lock | `counter.py` | 2 |
| Bounded queue | one mutex, two condition variables | `bounded_queue.py` | 3, 5 |
| Deadlock & lock ordering | two locks in opposite order; a total order | `deadlock.py` | 6 |

Every `accept`/`limit_case` in the skill tree is one check step:

- accept **the unsynchronised counter loses updates; the locked one does not** → step 2
- accept **no item is lost or duplicated across many producers and consumers** → step 3
- accept **the spinlock is not held across a blocking call** → step 4
- limit **a lost wake-up when the condition is checked with `if` instead of `while`** → step 5
- limit **deadlock when two threads take locks in opposite order, surfaced by a timeout** → step 6

## How to use this directory

The top-level files are **templates**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
working versions for when you are stuck, or to compare afterwards. **`coop.py` is provided,
not an exercise** — it is the machine the rest runs on; read it, but you do not write it.

```bash
cd lowlevel/05-concurrency
python3 check.py        # what to build next; stops at the first gap
python3 check.py 2      # one step
python3 check.py 2 4    # a range
python3 check.py --all  # everything
```

`check.py` runs 6 checks against **your** code and never imports `solutions/`.

## The deterministic scheduler (why there is no flakiness here)

Real `threading` gives a genuine race — which is exactly what makes it useless for
grading: the lost update may not happen on a fast machine, and a deadlock test would wait
on a clock. Instead the threads in `coop.py` are generators. A thread runs to its next
`yield`, then the scheduler picks the next ready thread round-robin, in spawn order.

A switch point exists only where a primitive yields:

- a plain shared-memory access (`Cell.load`/`Cell.store`) is a step, so a read can be
  separated from the store that follows it — the lost update;
- an atomic instruction (`atomic_test_and_set`, `atomic_compare_and_swap`) has **no**
  switch inside — it is indivisible, as the hardware promises;
- lock acquire, wait and signal are steps.

So the checker *controls* the interleaving. "Deadlock" is the ready queue draining while a
thread is still blocked (nobody left can wake it); the "timeout" on a livelock is a step
budget. There are no real threads anywhere: a "thread" is a generator. If you ever want a
real one, put it in a `__main__` demo; never in a graded check.

## The checker was itself tested

Seven classic bugs were planted in copies of the solutions; each one has to be caught by
its check. Reproduce with
`python3 .claude/skills/graded-module/scripts/mutate.py lowlevel/05-concurrency lowlevel/05-concurrency/_build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| the scheduler stops tracking held spinlocks | step 4 |
| a spinlock never releases | step 1 |
| a mutex release never wakes the waiter | step 3 |
| the locked increment forgets the lock | step 2 |
| the consumer checks the predicate with `if`, not `while` | step 5 |
| `put` wakes the wrong condition variable | step 3 |
| the ordered transfer does not order the locks | step 6 |

The limit cases do not rely on luck. A spurious wake-up is *injected* rather than hoped
for, and the deadlock is guaranteed by the spawn order and the scheduler's round-robin.

## Design decisions, named

Each file opens with its decisions and what they cost. In short:

- **A scheduler you step, not real threads** (`coop.py`). Reproducible races and
  deterministic deadlock detection, at the cost of not being true parallelism — one
  instruction stream, interleaved. The races it reproduces are the real ones.
- **A switch only at a memory access or a blocking primitive** (`coop.py`). Readable,
  controllable schedules; the cost is that "atomic" must be modelled explicitly as
  indivisible, and a read-modify-write is deliberately two steps.
- **Both a spinlock and a blocking mutex, kept visibly different** (`locks.py`). A
  spinlock burns the scheduler while it waits and must never be held across a block; a
  mutex parks. The scheduler records a violation if the two are mixed wrongly.
- **Release hands the lock directly to the first waiter** (`locks.py`). Fair, wakes
  exactly one thread, and closes the check-then-sleep window. The cost is an `owner` field
  to maintain.
- **`while`, not `if`, around every wait** (`locks.py`, `bounded_queue.py`). A wake-up
  means the predicate *may* have changed; POSIX even permits spurious ones. The cost is one
  re-check per wake-up and the discipline of re-testing rather than trusting the signal.
- **One mutex and two condition variables per queue** (`bounded_queue.py`). Each signal
  targets the side that can act; the cost is signalling the *other* side after every
  mutation.
- **A lock per account plus a total order** (`deadlock.py`). Deadlock is avoided by
  acquiring in a globally consistent order; the cost is that every caller must keep it.

## Questions to answer before reading the solutions

1. `counter.py`'s unsynchronised increment loses updates *deterministically*. Which two
   lines does the scheduler switch between, and what would have to be true of the machine
   for the lost update to *not* happen? (Answer that with the `Cell` step, not with
   "luck".)
2. A spinlock and a mutex both give mutual exclusion. Give the schedule on which a
   spinlock is correct and a *blocking* call is fatal, and say why the scheduler can flag
   it without guessing. Why is a spinlock allowed for the shared counter but not around a
   `Condition.wait`?
3. `Condition.wait` releases the mutex *before* it sleeps. Why must that release and the
   enqueue onto the wait queue be one indivisible step with respect to a signaller, and
   what breaks if they are separated?
4. `notify` wakes one waiter and `notify_all` wakes all. Construct (on paper) the schedule
   in which `notify_all` with two consumers and one item lets the second consumer pop an
   empty queue. Which line in `bounded_queue.py` stops it?
5. Deadlock is "surfaced by a timeout". Why is a step budget a *better* timeout than the
   wall clock for a test, and what is the difference between the two ways `RunResult` can
   report no progress (`deadlocked` vs `timeout`)?

## Limits

- One instruction stream, cooperatively scheduled. There is no preemption between two
  Python bytecodes, no memory model with fences, no `volatile`, no real parallelism; the
  module models *interleaving*, which is the source of the classic bugs, not memory
  reordering or cache coherence.
- No semaphores, barriers, read-write locks, `try-lock`, timed waits or reader-writer
  fairness. Each is a natural next mechanism (OSTEP ch. 31) and none is needed for the
  bugs this node is about.
- No priority, no per-thread stacks, no blocking I/O. A "thread" here is a generator that
  never touches a real file descriptor — that boundary was `lowlevel-04-syscalls-io`.
- Deadlock detection is a drained ready queue plus a step budget. It finds *this* module's
  deadlocks exactly; it is not a general detector and does not do cycle detection.
- `Mutex` is not reentrant; acquiring it twice from one thread deadlocks. That is a
  deliberate simplification, not an oversight.

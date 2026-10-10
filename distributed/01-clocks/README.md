# Time, Lamport and Vector Clocks

Ordering events in a distributed system without a shared clock. You build a **Lamport
clock** over a simulated message stream, a **vector clock** with the happens-before
relation, and you classify any two events as **before**, **after** or **concurrent** —
then you build the limit case that breaks the naive answer: two unsynchronised wall
clocks that disagree with causality.

Sources: Kleppmann, *Designing Data-Intensive Applications*, chapter 8 ("The Trouble
with Distributed Systems"); van Steen & Tanenbaum, *Distributed Systems*, chapter 6
("Coordination").

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Logical time | a scalar Lamport clock over a scripted message stream | `lamport.py` | 1-2 |
| Causality | vector clocks, happens-before, four-way `classify` | `vector.py` | 3-7 |
| The limit case | unsynchronised wall clocks inverting a causal pair | `wall.py` | 8 |

The acceptance criteria are: causal order is preserved (every send precedes its
receive); concurrent events are reported concurrent and never ordered; clocks merge
correctly when a message is received. The limit cases are clock skew and empty vector
clocks.

## How to use this directory

The top-level `lamport.py`, `vector.py` and `wall.py` are **templates**: each function
you write keeps its signature and docstring, has a `TODO` with a hint, and raises
`NotImplementedError`. `solutions/` holds working versions for when you are stuck, or to
compare afterwards. The `Simulation`/`VSimulation`/`WallSimulation` plumbing is provided
— it only sequences the calls to your clocks; writing it is not the lesson.

```bash
cd distributed/01-clocks
python3 check.py        # what to build next; stops at the first gap
python3 check.py 5      # one step
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`.

## Design decisions, named

- **A Lamport clock is a counter, not a timestamp** (`lamport.py`). It guarantees
  `a -> b  implies  C(a) < C(b)`, but it cannot tell concurrency from causality: two
  independent events still get *some* order. Cost: the total order it produces is a
  fiction for concurrent events, and reading it as causation is the classic mistake.
- **Sending is an event** (`lamport.py`). A send ticks the sender; a receive is
  `max(local, sent) + 1`. Cost: one counter increment for every message, and the receive
  must use the max or the receiver can appear to go backwards.
- **Vector clock as `{process: count}`, missing keys read as zero** (`vector.py`). An
  empty vector is a first-class value (a process before its first event) and the identity
  for merge, so the empty case needs no special-casing. Cost: comparison is over the
  union of keys and vectors grow with the number of processes.
- **`classify` returns four answers** (`vector.py`). `before`/`after` cannot express
  `concurrent`, and identical vectors are neither. Cost: callers must handle four cases.
- **Receive merges before it ticks** (`vector.py`). Merging first and ticking after makes
  the receive strictly dominate the send; ticking first would only make it equal. Cost:
  the ordering of two steps that is easy to swap and hard to notice.
- **Skew modelled as a fixed offset** (`wall.py`). The smallest model that already
  inverts a causal pair, and fully reproducible. Cost: it says nothing about drift,
  NTP steps, or estimating skew — only that *any* nonzero skew breaks wall ordering.

## Questions to answer before reading the solutions

1. A Lamport clock is a total order. If `C(a) < C(b)`, what do you actually know, and
   what can you *not* conclude?
2. In check 3, why is `{A:2}` concurrent with `{B:1}`, and what would a sum-based
   comparison get wrong about them?
3. Why must `receive` merge *before* it ticks its own component? What goes wrong in the
   other order?
4. Step 7 delivers A's message before B's. Why is B's send then concurrent with C's
   first receive but before C's second? Which component carries that information?
5. NTP keeps clocks within a few milliseconds. Is comparing wall timestamps ever safe?
   What has to be true about the events, and what does a fencing token add?

## The checker was itself tested

Six classic bugs were planted in copies of the solutions; each must be caught by its
check:

| Planted bug | Caught by |
|---|---|
| `receive` ignores the receiver's own clock (no `max`) | step 1 |
| `send` does not tick (sending is not treated as an event) | step 1 |
| `merge` adds vectors instead of taking the component-wise max | step 5 |
| happens-before compares component sums, ordering concurrent events | step 4 |
| domination uses `max()` and crashes on an empty clock | step 6 |
| the two wall clocks are synchronised, hiding the skew | step 8 |

## Limits

- No total order over concurrent events. Real systems break ties with a deterministic
  rule (e.g. lowest process id) or a sequencer; here concurrency stays concurrency.
- Vector clocks are unbounded here. Real ones are pruned or replaced (dotted version
  vectors) as processes come and go.
- No hybrid logical clocks, no interval / uncertainty timestamps, no clock
  synchronisation (NTP) — the wall file only *demonstrates* skew.
- The network is not modeled: delivery is explicit and reliable. There is no message
  loss, duplication or reordering to reason about.
- One thread, deterministic scripts. This says nothing about concurrent implementation.

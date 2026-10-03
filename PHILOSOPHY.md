# Philosophy

Why this repository exists, and the shape every directory in it should take.

## The goal

**Learn as much as possible from the implementation itself.**

Not from a summary of the implementation. Not from reading a finished one. From building
it, getting it wrong, and finding out precisely how you were wrong.

Reading about consistent hashing takes four minutes and leaves you able to describe it.
Implementing a preference list and watching your checker say *"preference_list returned a
DUPLICATE node — you are walking virtual tokens without skipping nodes already chosen,
this is the bug that silently stores 1 copy where you asked for 3"* takes an hour and
leaves you unable to make that mistake again.

That trade is the whole repository.

---

## The three principles

### 1. Design choices are problem-solving decisions, and they are named as such

A finished implementation hides its own reasoning. Every line looks inevitable. It is not
— behind most of them is a decision someone made, with alternatives they rejected and a
reason.

So we separate them out and say them aloud:

> **DESIGN DECISION — register machine or stack machine?**
> A stack machine is simpler to generate code for: no register allocation at all. A
> register machine is closer to real hardware and forces you to confront allocation and
> spilling, which is where the interesting problems live.
> **Chosen:** register machine, precisely *because* it creates the harder problem.

The decision is part of the material, not background to it. When you meet the same
trade-off in unfamiliar code later, you will recognise the shape of it.

A corollary: **where the design has a cost, say so.** Sloppy quorum buys availability and
loses durability; the exercise makes you construct the case where an acknowledged write
is genuinely lost. A directory that only lists a technique's advantages has taught you
marketing.

### 2. MVP first, then complicate — driven by limit cases

Build the smallest thing that works on the happy path. Get it running. *Then* find the
case that breaks it, and only then add the machinery that handles it.

```
v1  straight-line expressions, infinite virtual registers        works
v2  ...now add control flow                                      jumps, labels
v3  ...now you only have 16 real registers                       allocation, spilling
v4  ...now a value is live across a call                         calling conventions
```

Each step is motivated by a concrete failure of the step before. This matters because
**complexity introduced without a reason is unlearnable.** Told up front that a compiler
needs a register allocator, you memorise it. Having written code that runs out of
registers, you understand why one exists — and you could have invented it.

The same ladder runs through every directory:

| Directory | MVP | The limit case that forces the next step |
|---|---|---|
| `dynamo-paper` | quorum reads and writes | two replicas down — the write path dies |
| `context-caching` | KV cache within one request | a second request shares the prefix |
| `contextcite` | leave-one-out attribution | two sources state the same fact |
| `deploy-and-debug` | alert on the error rate | a 30-second blip pages you at 3am |
| `compiler-and-vgpu` | all lanes execute in lockstep | a branch makes them disagree |
| `aws-from-scratch` | one policy, one bucket, one queue | the failures compose, and then arrive on the bill |
| `provenance-semirings` | annotate tuples with a set of ids | two derivations of one row — the set cannot say how many, or what it cost |
| `scasp` | SLD (Prolog) | `p :- q. q :- p.` diverges; an even loop is a *success* |
| `linc` | a gold FOL parse, then a prover | the parse is wrong, and the label is still right |

### 3. Verification you can run, that explains itself

Every directory ships `check.py`. It runs graded checks against **your** code — never the
solutions — reports what to build next, and when something is wrong says why:

```
  ✗  1. capacity.py          KV cache and batch-size math
      Llama-3-8B should be 131,072 bytes/token, got 524,288. If you got
      524,288 you used the 32 query heads instead of the 8 KV heads — that
      sizes your fleet 4x too large.
```

A checker that says `AssertionError: False is not True` teaches nothing. A checker that
names the likely cause is a tutor.

Checks target **the mistakes that are easy to make and hard to notice** — a cache that
changes its output, a probe that never resets, a canary that ships on 90 samples. Not
line coverage. The bugs that survive casual testing.

---

## What a directory looks like

```
topic/
├── README.md         # what, why, the learning path, and where it stops
├── check.py          # graded checks against YOUR code
├── provided.py       # scaffolding you should not have to write
├── step_one.py       # templates: docstring explains what and WHY, then
├── step_two.py       #            raise NotImplementedError
└── solutions/        # complete, runnable, each printing a real measurement
```

Rules that hold everywhere:

- **Pure standard library where possible.** A dependency you cannot install is a
  directory you cannot use. Most of this repo runs on `python3 file.py` and nothing else.
- **Every solution runs and prints a measurement**, not a claim. `dynamo_cluster.py`
  prints the availability table. `serving_demo.py` prints 71% compute saved and asserts
  the output is bit-identical. Numbers you can reproduce, not numbers we assert.
- **Say where it stops.** Each README has a section listing what was deliberately left
  out. A learner who does not know the boundary will walk past it.
- **Scaffolding is provided, not assigned.** `toy_lm.py`, `deployment.py` — you need a
  model to attribute and a fleet to debug, but writing them is not the lesson. They are
  marked *provided, not an exercise* so nobody burns an afternoon on the wrong thing.

## What this repository is not

- **Not production code.** Simplified deliberately, and the READMEs say how.
- **Not a substitute for the paper.** `dynamo-paper` maps file-to-section so you read
  both.
- **Not exhaustive.** A directory that covers one mechanism deeply beats one that
  gestures at nine.

## Working through a directory

```bash
cd <topic>
python3 check.py            # what to build next
# implement the functions it points at
python3 check.py            # re-run
python3 <file>.py           # once it passes, run its demo and read the numbers
```

Then the part that actually consolidates it: **run the demo, and predict each number
before you look.** If the availability table or the cache hit rate surprises you, you
have found a gap in your model that passing tests did not reveal.

Use `solutions/` freely when stuck. The goal is understanding, not endurance. But read it
*after* attempting — a solution read cold is just more prose.

---

## Working through it

[`ROADMAP.md`](ROADMAP.md) turns these principles into a calendar: an 18-week schedule at
three intensities, a daily structure built around *predict-then-run*, and a weekly
regression day. `python3 progress.py` scores you against it, and — as everything else
here does — reports the number rather than an impression of the number.

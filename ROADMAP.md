# Roadmap — all of it, before 2027

Start **Monday 24 August 2026**. Finish **Sunday 27 December 2026**. Eighteen weeks.

The week folders still hold the original layout; **this file and the journal
are the authority on order**. A directory is found wherever it lives
(`progress.py` locates it). **[Start at `week-01/`](week-01/)** — that README
now points at AWS, not at a shell.

### The order, as of 23 August 2026

1. **AWS from scratch** — the eight mechanisms and the bill
2. **LLM work** — autograd, a transformer, distillation, the KV cache, then a
   serving stack you build before reading vLLM
3. **Provenance-reasoning** — the free semiring, then s(CASP), then LINC
   (a proof you can replay; the LLM only parses). ContextCite / SPADE /
   MARS-SQL after that, for tokens and columns
4. **Distributed training**
5. **Database engine**
6. **The rest** — Dynamo/Raft, systems in C, CUDA, the vendor engines, world
   models, the tail

## The arithmetic, before the calendar

Read this first, because it changes what you decide.

| | |
|---|---|
| Directories | **40** scheduled, 5 in `reference/` |
| Implementable units left (stubs, `sorry`s, TODO markers) | **2,407** |
| Estimated effort | **~1,402 hours** |
| Weeks available | **18** |
| Therefore | **78 h/week on `full` — 10.5 hours a day, seven days a week, for 126 days** |

Where the hours come from: the directories that state their own estimate in
their README (`ESTIMATED TIME: 6-8 hours`, and so on) are used directly. The
rest are units × a rate calibrated against the ones that do state a number
(≈0.45 h per unit; ≈0.30 h for the directories whose templates are unusually
specific). `python3 progress.py` prints the same table any time you want to
re-check it.

**73 h/week is still not a plan.** It is more than a full-time job with no weekends
and no slack for a single bad day, and 1,320 hours is the *optimistic* end,
because none of it includes the day you lose to a CUDA driver. Attempting it is
how people finish week 6 and stop.

So the plan below is one schedule at **three sizes**. Same order, same method,
same daily structure — you pick the width, and `progress.py --track` scores you
against the one you picked. Pick honestly on day one; switching down in November
feels like failure, and switching down in August is just planning.

| Track | Directories | Hours | Per week | Per day | Who it is for |
|---|---|---|---|---|---|
| **full** | 40 | 1,402 | 78 h | 11.1 h × 7 | This is your full-time job and you have no other commitments |
| **core** | 23 | 921 | 51 h | 8.5 h × 6, one day off | You have a job, and you are serious |
| **spine** | 10 | 566 | 31 h | 5.2 h × 6, one day off | You have a job and a life, and you would rather finish |
| **ops** | 15 | 694 | 39 h | 6.5 h × 6, one day off | You want an AI-ops role, and coverage is not the goal |

`ops` is not a width, it is a **direction**. It is `full` minus everything that
does not serve that job — 708 hours dropped, several of them excellent and none
of them likely to come up in an interview. It also assumes you do the parts of
[`TODO.md`](TODO.md) §16 that no checker can grade: one system that stays up for
90 days, a load test with a number attached, a written postmortem, a cost
record, and the vLLM comparison. Those are ~110 hours and they are the half that
decides it.

All three finish on 27 December. They differ only in what they contain.

**The recommendation is `core`.** It holds every directory that other
directories reference, including the 120 h provenance stack that makes an
LLM answer a proof you can replay. Finishing it means the remaining
directories are variations on mechanisms you already own — which is exactly
the claim [`PHILOSOPHY.md`](PHILOSOPHY.md) makes about this repo. Core is
heavier than it was before those three directories existed; that is the
trade you made on 23 August.

### What changed, and why every track got lighter

The order now starts where the leverage is: **AWS in week 1, LLMs in week 2**,
and the systems half — sockets, protocols, compilers, CUDA — moved to weeks
13–18. That is a deliberate reversal of the usual advice and it has a real cost:
you build a serving stack in week 4 having not yet written a socket server.

Five directories left the schedule for [`reference/`](reference/), 599 hours.
That is what took the full track from 100 h/week to 73, `core` from 58 to 44,
and `spine` from 12 directories to 10. Three of the five were design briefs or
near-briefs with **no templates and no checker** — `vllm-engine` alone was 156
hours of ungradeable work, the largest single allocation in the plan. They are
now reading, which is what the inference curriculum this plan follows actually
asks for.

Two more things worth knowing before you pick a track:

- **No directory is split across weeks any more.** Previously a project could
  span three, so week folders and track weeks drifted apart and you had to
  consult `progress.py` to know where you were. Now the folder is both a name
  and a date.
- **The AWS drill starts in week 1 and the AWS certification block is week 12.**
  That gap is intentional: quotas and service names cannot be crammed, and the
  graded block is worth most when the recall is already there.

---

## Week 0 — this weekend (21–23 August)

Do not start week 1 without this. Every hour here buys back three in November.

- [ ] **Toolchain.** `gcc`, `make`, Python 3.11+, and a venv per ML directory.
      Note that the five newest directories — `database-engine`, `autograd`,
      `llm-from-scratch`, `raft`, `ray-tracer` — are pure Python 3 standard
      library on purpose, and need nothing installed at all.
- [ ] **Haskell** (if you are on `full`): `ghcup`, then `cabal install http-conduit tagsoup async`.
- [ ] **Lean 4** (if you are on `full`): `elan`, then a Mathlib-enabled project. This
      alone can eat an afternoon. Do it now, not in week 4.
- [ ] **A GPU you can actually reach.** CUDA, TensorRT, vLLM, world-models and
      diffusion are now in weeks 14–18. Still budget the money in August.
      `inference-from-scratch` (weeks 4–6) runs on a simulated GPU and does
      **not** need a card. The `core` track needs a real GPU from week 17;
      `spine` only for `cuda-from-scratch`.
- [ ] **Baseline.** `python3 progress.py --track core --checks`. Every bar should
      read 0%. That is the point — you want the zero on the record.
- [ ] **The journal.** `python3 journal/serve.py` and write today's post
      (`journal/posts/2026-08-23.md`). From today on, the ten-minute log is a
      blog post with an expected title, not a loose `LOG.md`.
- [ ] **Pick your track and write it down** in this file, on the line below.

> My track: `________`  · started: `________`

Then open [`week-01/`](week-01/) — AWS, not a shell — and read its README before Monday.

---

## The daily structure

The hours matter less than the shape. Every tier uses the same four moves, in
this order, and the order is the method:

1. **Implement.** Longest block, first thing, hardest unfinished stub. Do not
   open `solutions/` — not to "check the approach", not to "see the signature".
   The solution is a comparison you make *afterwards*, and reading it first
   converts an exercise into a transcription.
2. **Predict, then run.** Before you run a demo, write down the number you
   expect. Hit rate, speedup, throttle count, dollars, noise at 64 samples. Then
   run it. This is the entire method of the repo: a result that surprises you is
   a gap in your model that a passing test did not reveal, and you only get that
   signal if you committed to a number first.
3. **Make it green.** Where a `check.py` exists, that is the stop condition —
   not "it looks right". Where one does not, the stop condition is the file's own
   demo printing a table you predicted.
4. **Log, ten minutes.** Open the journal (`python3 journal/serve.py`) and write
   the day's post. The expected title is already there. What you built, what
   surprised you, which design decision you would now defend differently. Ten
   minutes a day is four hours over the plan, and it is the only artifact that
   still exists in a year.

And one rule per week:

> **Sunday is regression day. No new code.** Re-run *every* checker you have
> built so far — `python3 progress.py --track <yours> --checks` does it in one
> command — and write two sentences on what you can now re-derive that you could
> not last Sunday. When week 14's work breaks week 5's checker, you want to find
> out in one hour, not in December.

### Full — 87 h/week, 7 days

| | |
|---|---|
| 05:30–08:30 | implement (3 h) |
| 09:00–12:00 | implement (3 h) |
| 13:00–16:00 | implement (3 h) |
| 16:30–18:00 | predict-then-run, make it green (1.5 h) |
| 20:00–21:15 | Lean (1.25 h) |
| | **11.75 h/day × 7 = 82 h**, plus a 5 h Saturday overflow block |

### Core — 45 h/week, 6 days (recommended)

| | |
|---|---|
| Mon–Fri 05:45–08:15 | implement (2.5 h) |
| Mon–Fri 18:30–22:00 | implement, then green (3.5 h) |
| Saturday | 9 h, one long session — this is where hard things get finished |
| Sunday | 6 h: 5 h implement, then 1 h regression + log |
| **Off** | one weekday evening of your choice. Take it. Every week. |

### Spine — 27 h/week, 6 days

| | |
|---|---|
| Mon–Fri 19:00–22:00 | implement, then green (3 h) |
| Saturday | 8 h |
| Sunday | 4 h: 3 h implement, 1 h regression + log |

---

## The 18 weeks

Hours are the **full** track. `C` marks a directory in `core`, `S` in `spine`.
Each directory appears in exactly one week now — the schedule no longer splits
a project across weeks, so a week folder is both a name and a date.

Lean sits outside the table: **504 proof obligations, ~8.4 h/week**, as a fixed
daily slot. The AWS drill sits outside it too — see the note below the table.

| [**1**](week-01/) | Aug 24–Aug 30 | AWS, from its mechanisms up | `aws-from-scratch` 42 **C** **S** | 42 |
| [**2**](week-02/) | Aug 31–Sep 6 | LLMs | `autograd` 30 **C** **S** · `llm-from-scratch` 55 **C** **S** | 85 |
| [**3**](week-03/) | Sep 7–Sep 13 | Teaching a model: distil, then reward | `rl-posttraining` 30 **C** · `context-caching` 28 **C** | 58 |
| [**4**](week-04/) | Sep 14–Sep 20 | Serving it yourself | `inference-from-scratch` 70 **C** **S** · `deploy-and-debug` 10 **C** | 80 |
| [**5**](week-05/) | Sep 21–Sep 27 | Attribution, on a real task | `contextcite` 13 **C** · `spade` 16 **C** · `mars-sql` 20 **C** | 49 |
| [**6**](week-06/) | Sep 28–Oct 4 | Provenance, algebraically | `provenance-semirings` 45 **C** | 45 |
| [**7**](week-07/) | Oct 5–Oct 11 | Goal-directed reasoning | `scasp` 45 | 45 |
| [**8**](week-08/) | Oct 12–Oct 18 | Parser in front, prover behind | `linc` 30 · `distributed-training` 18 | 48 |
| [**9**](week-09/) | Oct 19–Oct 25 | A database from the disk up | `database-engine` 77 **C** **S** | 77 |
| [**10**](week-10/) | Oct 26–Nov 1 | Consensus, and its refusal | `dynamo-paper` 21 **C** **S** · `raft` 30 **C** | 51 |
| [**11**](week-11/) | Nov 2–Nov 8 | Byzantine, and open membership | `blockchain-from-scratch` 55 **C** | 55 |
| [**12**](week-12/) | Nov 9–Nov 15 | AWS certification block | `aws-certification` 35 **C** · `aws-deploy` 20 **C** | 55 |
| [**13**](week-13/) | Nov 16–Nov 22 | Sockets | `bash-from-scratch` 8 **C** · `http-server` 86 **C** **S** | 94 |
| [**14**](week-14/) | Nov 23–Nov 29 | What a byte stream carries | `dns-server` 9 · `cryptographic-library` 5 · `communication-protocols` 34 · `toralizer` 21 | 69 |
| [**15**](week-15/) | Nov 30–Dec 6 | Compilers, and a machine for them | `firewall-from-scratch` 25 · `c-compiler` 27 **C** **S** · `compiler-and-vgpu` 16 **C** **S** · `quantum-computing-lang` 8 | 76 |
| [**16**](week-16/) | Dec 7–Dec 13 | CUDA | `cuda-from-scratch` 142 **C** **S** | 142 |
| [**17**](week-17/) | Dec 14–Dec 20 | Databases deeper, light, and Haskell | `database-internals` 45 **C** · `ray-tracer` 35 · `haskell-projects` 61 | 141 |
| [**18**](week-18/) | Dec 21–Dec 27 | The long tail | `spectral-graphs` 5 · `sas-lineage-tool` 8 · `web-scraping` 6 · `ml-in-production` 8 · `mlops` 12 | 39 |

**1,251 block hours.** Plus Lean, 1,402.

### Three things run outside the table

- **[`LIVE.md`](LIVE.md)** — a deployed system, from **week 1**, ~2 h/week.
  Not a phase at the end. Ninety days of uptime takes ninety days, you cannot
  schedule an incident, and evidence that accrues by the calendar survives a
  schedule that slips.

### Two of them daily

- **`lean-proofs/`** — ~8.4 h/week, every week. Proofs go better in
  ninety-minute pieces than in a marathon, and it keeps an unrelated muscle warm
  while the rest of the plan is C and CUDA.
- **`week-12/aws-certification/drill.py`** — from **week 1**, not week 12.
  Quotas, defaults, service names and limits are arbitrary facts: not derivable,
  only memorable. Spaced repetition starting in August is the difference between
  passing and not; the graded block in week 12 is the other half and is the half
  this repo is actually good at.

### What is not on the schedule

Six directories moved to [`reference/`](reference/) — **647 hours removed**,
which is what takes the plan from 100 h/week to 73.

| Directory | Was | Why |
|---|---|---|
| `ml-inference` | 137 h | 6 stubs, no checker. `week-04/inference-from-scratch/` does the same ground in 60 h with 12 graded checks. |
| `vllm-engine` | 156 h | A design brief. No templates, nothing gradeable. |
| `tensorrt-inference` | 109 h | The same, and vendor-specific. |
| `world-models` | 106 h | A genuine cut. GPU-bound, no checker. |
| `diffusion-models` | 91 h | The same cut, same reasons. |
| `system-design` | 48 h | Displaced by `database-internals`. Its patterns are covered from the mechanisms up by `aws-from-scratch` and `deploy-and-debug`; Kleppmann covers the rest better than 159 stubs will. |

The first three are **reading**, not a deletion, and the argument is step 11 of
the inference curriculum this plan follows: *only then go read vLLM, SGLang and
TensorRT-LLM, and compare their design decisions with yours.* That is a weekend
with the source open after week 4 is green — not 402 hours of building, and far
more valuable once you have something to compare against.

### The shape of the order

**Weeks 1–12 are the ML and reasoning half; weeks 13–18 are the systems half.**
That is a deliberate reversal of the usual advice, and it has a cost worth
naming: you build a serving stack in week 4 having not yet written a socket
server, which arrives in week 13. The trade is that AWS and LLMs are where your
leverage is now, and the systems work is the part that keeps its value if the
plan slips.

If it does slip, **week 17 is the week to cut from** — `haskell-projects` (61 h) is
the first to go — it is orthogonal to everything else you are keeping, and
`database-internals` and `ray-tracer` both have checkers while it does not.

## Scoring yourself

```bash
python3 progress.py                      # core track, today's week
python3 progress.py --week 3             # what week 3 expects of you
python3 progress.py --track full         # all 41
python3 progress.py --track spine        # the 12-directory minimum
python3 progress.py --checks             # also run every check.py — the exact number
```

It prints per-directory bars, flags anything past its due week with a red `!`,
and closes with the only line that matters:

```
  0 h of work done; the plan says 397 h by the end of week 5.
  Behind by 397 h (5.0 weeks).
```

Two honesty notes it will also print at you, because they are easy to forget:

- The Python bars are trustworthy — the marker is `raise NotImplementedError`,
  and it disappears when the function stops raising.
- The **C, CUDA and Haskell bars only move if you delete each `TODO` comment as
  you satisfy it.** Do that. It costs nothing and it is the only thing keeping
  those bars from being decoration.
- `--checks` cannot be gamed at all. When the bars and the checkers disagree,
  the checkers are right.

---

## When you slip — and you will

Slip is the normal state of a four-month plan; the failure mode is not slipping,
it is responding to slip by cutting the *daily block* instead of the *scope*.
The block is the only thing producing progress. Cut in this order:

| Cut | Saves | Why it is the right thing to lose |
|---|---|---|
| 1. `lean-proofs` | 151 h | The biggest single saving, and the easiest to pick up later — proofs do not go stale |
| 2. `tensorrt-inference` | 109 h | Vendor-specific; `ml-inference` already taught the ideas |
| 3. `world-models` + `diffusion-models` | 197 h | The most GPU-hungry hours in the plan, and the last to be reached |
| 4. `haskell-projects` | 61 h | Orthogonal to every other track here |
| 5. `system-design` | 48 h | `aws-from-scratch` covers the same ground from the mechanisms up |
| 6. `ray-tracer` | 35 h | Self-contained; nothing else in the repo depends on it |

That is 601 hours. The remaining 164 between `full` and `core` is the week-2
protocol work and the week-18 long tail — cut those last, individually, as
needed. Which is the honest way to read the `core` track: it is `full` with the
six cuts already made, made in August by someone calm rather than in November by
someone tired.

**Never cut these**, at any tier, because everything else in the repo is written
against them: `http-server`, `c-compiler`, `database-engine`, `dynamo-paper`,
`aws-from-scratch`, `autograd`, `llm-from-scratch`, `context-caching`,
`cuda-from-scratch`, `inference-from-scratch`, `provenance-semirings`,
`scasp`, `linc`.

---

## What "done" means

Not "I implemented the stubs". This repo's own standard, from
[`PHILOSOPHY.md`](PHILOSOPHY.md), is higher and more useful:

> You could **re-derive** the design decision, name the alternative that was
> rejected, and say what limit case forced the complication.

The concrete test, at the end of each directory: **close the files and explain
to someone why it is built that way.** Why a preference list must skip virtual
nodes on the same physical machine. Why an explicit Deny cannot be order
dependent. Why "a majority has it" is the wrong commit rule for Raft. Why only
leaves of a radix cache are evictable. Why `t_min = 0.001` is a guess about
scene scale rather than a derived constant.

If you can do that, the directory is done even with a stub left in it. If you
cannot, it is not done even at 24/24 — and the fix is not more code, it is
`git log -p` on your own week and the `DESIGN DECISION` blocks you skimmed.

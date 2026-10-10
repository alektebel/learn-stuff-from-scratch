# Eval Framework From Scratch

Build the machine that runs an eval — the part between "I have a task set and a
model" and "here is a number I can publish" — in pure standard-library Python,
with the task set, the actors and the clock provided.

The lab is here (`lab.py`): twelve questions, a ticker that counts what code
spends instead of wall time, a solver and a judge protocol as callables, six
solvers (perfect, noisy, silent, crashing, slow, chatty), six judges (exact,
substring, unclear, sulking, malformed, order-sensitive) and fixture builders.
What is *not* here is the runner itself: config validation, plugin resolution,
one record per case, budgets, aggregation, the judge protocol around a cache,
canonical logs, gating, diffing, resuming. Every one of the failures below is a
check here, and every one of them is easy to make and hard to notice:

- a typo in a suite config (`max_tick` for `max_ticks`) that runs — with the
  defaults — as something other than what its author believed, instead of being
  refused;
- `"3600"` accepted where an integer is required, so the budget compares as a
  string, or a weight that is a bool;
- two cases sharing an id, so a resume cannot tell which one it already did;
- a metric plugin resolved after the first call, which means the run that
  needed the plugin has already happened by the time the name turns out to be
  wrong;
- a metric plugin that raises, reported as the *solver's* failure — or as a
  score of 0.0;
- a solver that raises, filed as our bug; our own broken case, filed as the
  solver's;
- a timed-out answer that is measured anyway: the metric runs over an answer
  nobody waited for, and the record looks like a slow success;
- `calls + 1 > max_calls` checked after the call, so a budget is discovered to
  be overspent only once it is;
- a run that stops at a budget and still reports the totals of a complete one;
- a stopped run that keeps the records of cases it never reached;
- two repeats of one case counted as two independent pieces of evidence;
- a `None` metric voting zero instead of shrinking the denominator, so "not
  measured" reads as "measured badly";
- a metric with two cases, one of them wild, declared stable enough to gate on;
- a judge cache keyed by the prompt alone, so two different answers share one
  verdict;
- a cached judge call charged against the judge budget it never spent;
- a pairwise question asked in one order only, which measures position as much
  as quality;
- `json.dumps` without sorted keys or with `default=str`, so two runs of the
  same suite differ in bytes and an object's repr lands in a field the analysis
  reads as a name;
- `-0.0` written into a record, and a float that carries fourteen digits of
  binary noise into a comparison;
- a reader that drops an unterminated final line in silence, shortening a run
  behind the analyst's back;
- a gate over a metric that was never measured, or over a run that stopped;
- an invalid run reported as a failed gate, so the two are indistinguishable in
  CI;
- a diff that calls "+0.28, up from 0.58" an improvement when both sides
  disagree by their whole range;
- a resume that reuses the log of a *different* suite, that re-runs the unit a
  preceding crash already wrote, or that drops the half-written record instead
  of finishing it.

No network, no sockets, no wall clock, no global state: the clock is
`lab.Ticker`, actors are seeded, metrics are pure functions of a case and an
answer, and `time.time`, `time.sleep` and `time.monotonic` are under landmines
in the smoke run. Where a decision was a judgement call, it is written down in
the template's docstring as a DESIGN DECISION, and the check asserts the
consequence.

## The provided lab

`lab.py` is complete and has no TODOs. The surface the course builds on:

```python
QUESTIONS                        # 12 dicts: id, prompt, answer
DEFAULT_WEIGHT, JUDGE_TICKS      # 1.0, 3
ConfigError(ValueError)          # everything this course refuses raises this
Ticker(start=0, step=1)          # .now() .tick(n) — the only clock
Actor(fn, *, clock=None, label=None)  # a callable with .calls and .clock
Solver  = solver(prompt, *, clock) -> str | None
Judge   = judge(*, prompt, answer, reference, clock) -> {"verdict": ...}
perfect/noisy/silent/crashing/slow/chatty(clock=...)     # the six solvers
exact_judge/substring_judge/unclear_judge/sulking_judge/bad_shape_judge/
    order_sensitive_judge(clock=...)                     # the six judges
LabCase/LabSuite/make_case/make_suite                    # hand-built fixtures
```

Three properties of it are load-bearing: every solver and judge takes the ticker
*per call* (so a check can run an actor built without one), `Ticker` only moves
when someone calls `tick`, and the solvers spend ticks before they answer — which
is what makes a timeout observable at all.

## The stages

| # | File | The mechanism | The thing people get wrong |
|---|---|---|---|
| 1 | `stage_01.py` | `SUITE_KEYS`, `CASE_KEYS`, `Case`, `Suite`, `parse_suite`, `canonical_suite` | A typo that runs as a default; `"10"` accepted for an int; a bool weight; a duplicated id; defaults that never reach the canonical text, so the same config hashes two ways; the file's key order surviving into the hash |
| 2 | `stage_02.py` | `MetricRegistry` (`.register`, `.resolve`, `.bind`), `apply_metrics` | Resolving a plugin after the first call; an unknown name reported without the known ones; a plugin that raises taking the run with it; a metric error reported as a 0.0 |
| 3 | `stage_03.py` | `STATUSES`, `CASE_RECORD_KEYS`, `METRIC_DP`, `round_metrics`, `run_case` | A stopwatch instead of the injected clock; ticks of a call that never finished; a late answer measured anyway; a solver's exception filed as a case error and vice versa; a naive float in the record; `-0.0` |
| 4 | `stage_04.py` | `RUN_KEYS`, `run_suite` | The budget checked after the call; repeats not adjacent; a record for a case the run never reached; a windowed sink; counters not taken from the records; the metric failures left out of the summary |
| 5 | `stage_05.py` | `MIN_N`, `MAX_SPREAD`, `aggregate`, `stability_verdict` | Repeats counted as evidence; the mean of case means (unweighted); a `None` voting zero; `n` counting records instead of cases; spread over repeats instead of cases; a wild case still called stable |
| 6 | `stage_06.py` | `JudgeSession`, `judge_metric`, `pairwise_metric` | A cache keyed by the prompt alone; a hit charged to the budget; a verdict outside the vocabulary kept; a judge that raises returning a score; a pairwise question asked once |
| 7 | `stage_07.py` | `canonical`, `RunLog`, `read_records` | Unsorted keys; `default=str`; unrounded floats; no flush per record; a last line dropped in silence; a malformed middle line repaired |
| 8 | `stage_08.py` | `GATE_KEYS`, `EXIT_CONFIG`, `EXIT_RUN_INVALID`, `EXIT_GATE_FAILED`, `EXIT_OK`, `parse_gate`, `evaluate_gate`, `evaluate_gates`, `run_exit` | A bound checked before the metric is usable; `n`/spread/stability forgotten; a strictly-exclusive boundary at exactly the bound; an empty gate list as a pass; a stopped run gated; an invalid run reported as a failed gate |
| 9 | `stage_09.py` | `EPS`, `diff_metrics`, `regressions` | A difference that does not beat the noise; the noise of one side only; a one-sided metric counted as a regression; `n == 0` reported as a zero; an unstable side given a verdict |
| 10 | `stage_10.py` | `suite_hash`, `write_checkpoint`, `read_checkpoint`, `resume_run` | A Python `hash()` in the hash; a checkpoint of another suite accepted; a truncated prefix reused as a different suite's; budgets restarted instead of carried; a half-written tail dropped; a re-run of a unit already written |

## How to use this directory

```bash
python3 codecraft/cli.py run eval-framework-from-scratch    # what to build next, and why
python3 codecraft/cli.py hint eval-framework-from-scratch   # when a nudge is not enough
```

Or without codecraft:

```bash
python3 -c "import course; [print(i, s.title) for i, s in enumerate(course.STAGES, 1)]"
```

Implement the templates at the top level; finished versions are in `solutions/`.
The stages are cumulative: stage 3 imports stage 2's `apply_metrics`, stage 4
runs stage 3's `run_case` over stage 3's `STATUSES`, stage 5 computes over the
records those produce and imports stage 3's precision and statuses, stage 7
rounds through stage 3's `round_metrics`, stage 8 imports stage 5's two
constants, stage 9 imports stage 3's precision too, and stage 10 hashes through
stage 1's `canonical_suite`, runs stage 3's `run_case`, and appends through
stage 7's `RunLog`. A check for a
late stage therefore needs the earlier ones implemented, and `solutions/`
overlaid on the templates is the state those checks are written against.
`lab.py` is not a stage: it is the task set, the actors and the clock, provided
complete.

## Prerequisites

Standard library only: `json`, `math`, `hashlib`, `random`, `os`, `sys`. No
numpy, no scipy, no pandas, no HTTP client, no database — the whole runner is
dicts, floats and one `sorted()` call. You should be comfortable with dicts,
closures, generators and `try/except`; the statistics are written out by hand, on
purpose, because "what is the unit of this average?" is the question this course
is about.

## Design decisions

- **The course is the runner, not the metrics.** What to measure — exact match,
  token F1, nDCG, judge bias, kappa, significance, Holm — is phase C1's course.
  Here the metrics are arbitrary callables and the subject is everything around
  them: what a run refuses to start with, what one case produces, what a budget
  stops, what a log contains, when a number may gate.
- **The clock is a ticker, not a stopwatch.** A runner cannot preempt a callable
  in the same interpreter, so a timeout cannot be "the answer did not arrive in
  time": the call returns when it returns. What the framework can do is count the
  ticks the code under test *spent*, break the loop before the next call, and
  discard a late answer instead of measuring it. Budgets are therefore stated
  precisely: a call budget cannot be overspent (the check is before the call), a
  tick budget can be exceeded by one case's cost, and the record says so.
- **Every failure is attributed to one of three sides.** `solver_error` is the
  solver's (it raised, or answered with something that is not a string or
  `None`), `case_error` is ours (no prompt, a bad config, a deadline that is
  already gone, a missing id), and a metric error is the measurement's — the
  answer was fine, the plugin broke. The record carries the blame rather than a
  `False`, because "the model was wrong" and "the harness was wrong" have
  different fixes and the same symptom in a spreadsheet.
- **The unit of aggregation is the case.** Repeats are the noise of one case, so
  they are averaged into it first; the rollup is then a weighted mean over cases
  using the record's `weight`. `n` counts cases, not records; a `None` shrinks
  the denominator instead of voting zero; and `stable` means `n >= MIN_N` and the
  cases span no more than `MAX_SPREAD` — a metric whose cases disagree by more
  than a third of its range is not a number to gate on, however good its mean
  looks (for a 0/1 metric that is most runs, which the smoke run demonstrates).
- **The weight travels in the record.** The rollup runs after the run and reads
  records only, so the case's weight has to be in the record — otherwise the
  aggregate is unweighted by omission, which is exactly the kind of silent
  difference this course is about.
- **The run summary carries the metric failures.** `run_exit` decides "is this a
  valid measurement?" and reads only the summary: a stopped budget, a case error,
  or a metric that failed. Publishing a run whose metrics broke is worse than
  publishing nothing, and a summary that cannot say so forces a second scan of
  the log — one rule, one source.
- **The hash is over the effective config.** `sha256(canonical_suite(suite))[:16]`
  with defaults materialised and keys sorted: two spellings of the same suite
  hash the same, and a checkpoint written by a different suite is refused instead
  of silently reused. The log is compared across processes and machines, so its
  identity cannot be a Python `hash()`.
- **A resume may only reuse the log of its own run.** The suite is hashed, the
  budgets carry over from what the log already spent, a half-written tail is
  repaired (an incomplete object is truncated, a complete one is terminated), a
  malformed middle line raises, and a run without a checkpoint starts its log
  over. The result is checked as bytes: the resumed log is the uninterrupted
  run's log.
- **Nothing in a record is a guess.** No wall clock, no unrounded float, no
  repr: a value that cannot be written exactly is written rounded to six
  decimals, and `-0.0` is written as `0.0` so the same measurement cannot produce
  two files.

## Verification

The solutions pass all ten checks, and every check is mutation-tested: **272
plausible wrong implementations** — a typo running as a default, an int accepted
as a string, a duplicated id, a plugin resolved late, a plugin's exception filed
as the solver's, a solver's exception filed as ours, a stopwatch instead of the
ticker, a timed-out answer measured anyway, a budget checked after the call, a
run that keeps a record for a case it never reached, a windowed sink, counters
taken from an intention instead of the records, repeats counted as evidence, a
`None` voting zero, `n` counting records, a wild case called stable, a judge
cache keyed on the prompt, a hit charged to the budget, an off-vocabulary verdict
kept, a pairwise question asked once, unsorted keys, `default=str`, an unrounded
float, a last line dropped in silence, a malformed line repaired instead of
refused, a gate over an unusable metric, an exclusive boundary at the bound, an
empty gate list as a pass, a stopped run gated, an invalid run reported as a
failed gate, a diff that ignores the noise, a one-sided metric counted as a
regression, a `n == 0` side reported as zero, a Python `hash()` in the suite
hash, a checkpoint of another suite accepted, budgets restarted, a half-written
tail dropped, a unit re-run — are each planted into a solution, and the stage's
check must fail. Every assertion message names the mistake, not the symptom; the
count per stage is 24, 28, 23, 21, 35, 26, 20, 38, 27, 30.

Two proofs sit outside the per-stage checks. `mutate_all.py` replays all 272
mutations against the assembled course under one runner (`MISSED OR BROKEN: 0`,
the tree rebuilt for every mutation and `PYTHONDONTWRITEBYTECODE=1`, because a
stale `__pycache__` whose size and second match the previous mutant's runs the
*previous* mutant's code and shows a real catch up as a miss). A smoke run
composes all ten stages over a real suite — a parsed config, a registry, twelve
cases with two of them repeated, a log on disk, an aggregate, a diff, two gates,
the exits, and a resumed run — with `time.time`, `time.sleep` and
`time.monotonic` patched to raise for the whole run:

```
SMOKE PASS — 12 cases, 14 units, 14 records, 7 judge calls (8 asked)
  em 0.583 (n=12, spread 1.000, noisy) | prose 0.286 (n=5) | judge 0.583 (n=12)
  candidate em 0.861, delta +0.278, verdict unstable, regressions 0
  gates: baseline False (noisy,noisy) | green True | candidate below | invalid run 2 | stopped run 2
  exit: green 0, candidate 1, invalid 2, stopped 2
  resume: 6 reused + 8 fresh = 14 records, 2360 bytes identical to the uninterrupted run
```

The provided lab has its own proof, `/tmp`-side in development and re-run before
this course was committed: 102 checks over `lab.py` — the twelve questions, the
ticker's arithmetic, the six solvers and six judges (including that
`order_sensitive_judge` says "correct" on the first call of each pair whatever
the answers are, and that `bad_shape_judge` leaves the vocabulary), the fixture
builders and every `ConfigError`.

Re-running the proofs:

```bash
python3 codecraft/cli.py run eval-framework-from-scratch   # per stage, with the failure line
python3 /tmp/f2-checks/run_all.py                          # every stage's check, solutions overlaid
python3 /tmp/f2-checks/mutate_all.py                       # every mutation, one runner
python3 /tmp/f2-checks/verify_lab.py                       # the provided lab
python3 /tmp/f2-smoke.py                                   # all ten stages composed
```

## Where this stops

Deliberately left out, so you know the boundary:

- **No metrics.** EM, token F1, nDCG, judge calibration, kappa, paired
  significance and Holm live in phase C1 (`evals-from-scratch`). Here a metric is
  a callable and the question is whether the framework around it is honest.
- **No provider layer.** A solver is a callable: no HTTP client, no prompt
  templates, no tokenizer, no retry policy against a rate limiter. The runners
  that do that are the harness courses; this one measures what a callable did.
- **No concurrency.** Cases run in the declared order, in one process, with
  adjacent repeats — the order and adjacency are *asserted* properties here,
  because that is what makes a resume reproducible. Parallel workers, sharding
  and a queue are a different course.
- **No storage layer.** The log is a JSONL file, the checkpoint a JSON file: no
  database, no object store, no dashboard, no leaderboard service. What matters
  is what the bytes are, and that is checked directly.
- **No money.** Budgets count calls and ticks. Tokens, dollars and rate limits
  are the API's prices, and they change.
- **No wall-clock timeout.** An unresponsive *process* is not modelled — the
  injected ticker measures what the code spent, and a hung callable hangs. That
  is a property of running untrusted code in-process, and pretending otherwise
  with `signal.alarm` would only work on the happy path.
- **No statistics beyond the noise rule.** The diff asks "did this move more
  than the two sides disagree with themselves?" — one comparison, one threshold.
  Confidence intervals, paired tests and multiplicity correction are phase C1's.
- **The task set and the judge are given.** The twelve questions and the six
  judges are fixtures, not a benchmark: the course is what the framework does
  with a judge that says "unclear", not how to prompt one.

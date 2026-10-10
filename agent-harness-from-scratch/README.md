# Agent Harness From Scratch

Build the runtime that sits between a model that streams and the tools it asks
for — in pure standard-library Python, with the model as a callable.

A harness is not a framework. It is a reduction (`collect`), a budget, a loop, a
dispatcher, a policy for failures, and an artifact you can replay. The
interesting failures are the ones nobody sees from the outside: a turn whose
`end` never arrived and is treated as finished, a prompt that is 200 tokens over
the window because tool calls were not counted, a budget exhaustion raised as an
exception instead of returned as an outcome, a tool that does not exist turned
into a stack trace the model cannot read, a retry that silently delivers the
first half of a turn twice, a compaction that keeps the newest answer and drops
the question it answers, a trace line that carries the API key it was asked to
hide, a reward that pays a step for citing a number from six steps ago, and a
verifier that raises instead of scoring zero — taking the episode with it. Every
one of those is a check here.

The domain is provided (`tiny_env.py`): three tables in an in-memory SQLite, four
analytic tasks, a scripted model whose turns are a list, a clock you move by
hand, and the question templates the last stage generates from. The harness is
the exercise.

No network, no sockets, no wall clock: every model is scripted, every backoff
waits on the injected clock, and `time.time` is under a landmine in the smoke
run. Where a decision was a judgement call, it is written down in the template's
docstring as a DESIGN DECISION, and the check asserts the consequence.

## The stages

| # | File | The mechanism | The thing people get wrong |
|---|---|---|---|
| 1 | `stage_01.py` | `collect`, `assistant_message`, `usage_add` | Usage replaced instead of summed; `tool_calls: []` written where the key should be absent; a stream with no `end` read as a finished turn; an event after `end` accepted |
| 2 | `stage_02.py` | `estimate_tokens`, `Context`, `assemble` | A tool call's payload not counted (4 tokens for 2 KB of SQL); a tool observation orphaned from the call it answers; the newest turn dropped to fit |
| 3 | `stage_03.py` | `run` | A spent budget raised instead of returned; the request appended after the work it asked for; an extra model call to notice the budget; a stop reason invented instead of read from `end` |
| 4 | `stage_04.py` | `Dispatcher`, `render_result` | An unknown tool raising (the model cannot repair what it cannot read); an invalid argument reaching the tool; `str(dict)` rendered with no row count; a schema violation reported as a tool failure |
| 5 | `stage_05.py` | `stream`, `timings` | The whole turn buffered before the caller sees anything; TTFT measured from a tool call; a usage event opening an inter-token gap; a wall clock |
| 6 | `stage_06.py` | `Retrying` | A retry after an event was already forwarded (the prefix arrives twice); `time.sleep`; a flat backoff; the attempt cap not counted; usage overwritten per attempt |
| 7 | `stage_07.py` | `compact`, `SUMMARY_PREFIX` | The system message summarized or dropped; a turn cut in half so an observation loses its call; the newest turn summarized away; a summary of the summary; compaction that runs when it already fits |
| 8 | `stage_08.py` | `Trace` | A seventh key (or an eighth); arguments or answers in the line; `.lines` handing out the trace's own dicts; a retry counted as a turn; durations in seconds; `errors` counting only tool failures |
| 9 | `stage_09.py` | `cite_values`, `cites_previous_result`, `process_reward` | Grounding against any earlier result instead of the previous one; numbers matched as bare substrings (`160` in `1600`); case-sensitive text; `ok` judged by truthiness; the mean divided by the steps that ran |
| 10 | `stage_10.py` | `make_verifier`, `generate_tasks`, `self_improve_round` | A verifier that raises; a wrapped answer compared as it arrives; exact float equality; a NULL answer accepted as gold; `AVG(region)` on a table with no number; a gold cast to text; a generator that loops forever or returns fewer tasks than asked; accuracy plotted on the tasks the round just made |

## How to use this directory

```bash
python3 codecraft/cli.py run agent-harness-from-scratch   # what to build next, and why
python3 codecraft/cli.py hint agent-harness-from-scratch  # when a nudge is not enough
```

Or without codecraft:

```bash
python3 -c "import course; [print(i, s.title) for i, s in enumerate(course.STAGES, 1)]"
```

Implement the templates at the top level; finished versions are in `solutions/`.
The stages are cumulative — stage 3's loop calls stage 1's `collect`, stage 4's
dispatcher and stage 8's `Trace`; stage 7 imports stage 2's token arithmetic;
stage 5's `stream` is the streaming face of the same call stage 3 makes — so a
check for a late stage needs the earlier ones implemented, and `solutions/`
overlaid on the templates is the state those checks are written against.

## Prerequisites

Standard library only: `json`, `sqlite3`, `copy`, `math`. No SDK, no HTTP client,
no tokenizer package, no `pytest`. You should be comfortable with dicts,
generators, closures and `try/except`; everything else — the reduction, the
budget, the dispatcher, the trace, the reward, the verifier — is built here.

## Design decisions

- **A model call returns an event stream, and `collect` is the only reduction.**
  `text` deltas append, `usage` events sum, `tool_call` events accumulate in order,
  and `end` is the *only* source of the turn's `reason`. A stream that never sends
  `end` is a broken stream, not a finished turn, and it raises `HarnessError`.
- **One step is one model call.** The trace's `turns`, the budget's `max_steps` and
  the usage total all count the same thing, which is why a retry is not a step and
  a tool call is not a step.
- **A budget exhaustion is an outcome.** `run` returns
  `{"status": "budget", …}` with the partial conversation, because the conversation
  up to the limit is data a caller can use. Bugs still propagate.
- **An unknown tool is a message; a failing tool is an observation.** The error text
  lists what does exist, the call never reaches a body it cannot satisfy, and
  `EnvError` from the world is an outcome. Any other exception is a bug in our
  program, and bugs propagate.
- **Retries stop at the first forwarded event.** A retryable `ModelError` before
  anything was sent is retried through the injected clock with a doubling backoff;
  once an event has reached the caller, a retry would deliver a doubled prefix, so
  the failure is delivered instead. The budget caps the whole run, and every
  attempt is billed.
- **Compaction's unit is the turn.** An assistant message and the tool messages
  answering it are one unit, so a cut cannot orphan an observation. The system
  message is pinned, the newest turn is kept verbatim at the end, everything older
  becomes one `SUMMARY_PREFIX + summarize(middle)` user message, and a context that
  already fits is returned untouched with the summarizer never called.
- **The trace keeps the shape and none of the payloads.** Exactly six keys, in
  order, with no channel for arguments, answers or secrets; `.lines` hands out
  copies; durations are gaps on the injected clock, in milliseconds.
- **Reward the step, and only against the result before it.** A step earns a third
  for running, a third for citing a value the *immediately previous* step returned,
  and a third for asking something no earlier step asked — grounded against the
  previous step because a step that reaches six steps back for its evidence is
  rationalising after the fact.
- **A verifier never raises and never trusts a wrapper.** It unwraps one-element
  containers and result dicts, compares numbers with a tolerance and text folded
  and stripped, and scores a wrong answer `0.0` — including `None`, which is a task
  nobody can answer.
- **A generated task's gold comes from the executor.** The generator fills a
  template, runs it, and drops any candidate that errors or answers NULL; it counts
  its attempts and raises naming the template and the count rather than looping
  forever or returning a shorter list. Accuracy is measured on the holdout when one
  is given, because accuracy on the tasks this round generated measures the
  generator, not progress — and the failed half of the round is the curriculum.

## Verification

The solutions pass all ten checks, and every check is mutation-tested: **159
plausible wrong implementations** — a usage total overwritten per turn, a
`tool_calls: []` where the key belongs, a missing `end` read as a stop, a tool call's
payload uncounted, a turn cut between a call and its observation, a spent budget
raised, the request appended after the work, an unknown tool raised instead of
observed, an invalid argument reaching the tool, `str(dict)` rendered without a row
count, a buffered stream, TTFT measured from a tool call, a retry after forwarding,
`time.sleep` in the backoff, the system message summarized, the newest turn
summarized away, a summary of the summary, a seventh key in the trace line, the
trace's own list handed out, a retry counted as a turn, grounding against any
earlier step, numbers matched as substrings, the mean over the steps that ran, a
verifier that raises, exact float equality, `True` scored as `1`, a NULL accepted
as gold, `AVG` of a text column, a gold cast to text, the same question handed out
twice, an unbounded generator, accuracy on the generated set, an agent that raises
ending the round — are each planted into a solution, and the stage's check must
fail. Every assertion message names the mistake, not the symptom. Two of them
need two edits to be observable at all — a NULL is dropped twice while walking a
result, and a numeric hole is guarded twice while filling a template — and both
say so in a comment (a single edit there is dead code, not a weaker check).

Two more proofs sit outside the per-stage checks: `mutate_all.py` replays every
stage's mutations against the assembled course under one runner (`MISSED OR
BROKEN: 0`, tree rebuilt per mutation because a stale `__pycache__` can run the
previous mutant's bytecode), and a smoke run composes all ten stages — a scripted
model streams, the loop dispatches a good call, an unknown tool, a bad argument
and a refused write, the trace records seven lines of shape and no payloads, a
context trims and then compacts itself, a retryable failure is retried once for
0.5 s on the injected clock, a half-consumed stream is *not* retried, the process
reward is 1.0 for a grounded episode, and a self-improving round whose agent is
the harness generates four tasks, runs the SQL, answers and verifies all four —
with `time.time` and `time.sleep` patched to raise for the whole run.

Re-running the proof:

```bash
python3 codecraft/cli.py run agent-harness-from-scratch   # per stage, with the failure line
```

## Where this stops

Deliberately left out, so you know the boundary:

- **No provider.** The wire format is the *turn*, not an HTTP API: no SSE parsing,
  no auth headers, no rate-limit tables, no streaming JSON decoders. Those are
  transport problems, and the transport is the part vendors already solved.
- **No real tokenizer.** The estimator is a documented fixed rule (4 characters per
  token, rounded up, plus an envelope) that a check can recompute. Wiring a
  provider's tokenizer in is a build step, not a lesson, and every budget bug this
  course catches has nothing to do with the exact count.
- **No async, no concurrency.** A cancelled run is not preempted; streaming is a
  generator the caller drains. Scheduling tool calls in parallel is a policy on top
  of a loop this course pins, not a different loop.
- **No model-side retry semantics.** Retrying a *tool* call is deliberately absent:
  a tool that failed may have had a side effect, so a retry belongs to the tool's
  own idempotency key (a different course), not to the harness.
- **No training.** The process reward and the self-generated round produce numbers
  and task lists; nothing here updates a model, and the accuracy it reports is a
  measurement, not an optimization.
- **One trace shape.** Six keys, no sampling, no OpenTelemetry, no spans. The
  invariant — the trace can be replayed and cannot leak — is what this course pins.
- **The world is one SQLite file's schema.** Three tables, reads only, no
  migrations, no transactions beyond SQLite's own. The interesting failure in stage
  4 is what the harness does with a refusal, not how the refusal is produced.

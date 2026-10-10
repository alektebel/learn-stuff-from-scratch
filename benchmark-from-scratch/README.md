# Benchmark From Scratch (Mus)

Build the measurement machinery of a benchmark — the part that turns a game into
a number you can defend — in pure standard-library Python, with the game
provided.

The game is here (`mus.py`): a Fournier mus table, four seats in two teams, the
mus exchange, the four lances with their three bet scales, the 40-point vaca,
two reference policies and a seeded match. What is *not* here is everything that
decides whether a match's number means anything. A benchmark is not the game; it
is a turn gate that counts what landed, a loop that knows what a retry costs and
when to stop, one ground-truth record per decision taken from the position the
seat actually faced, a link between a bet and the answer it got, a reference
distribution, a scorecard, an outcome that survives a reset, four probes with
their degenerate cases, a gate, and a mirror. Every one of the failures below is
a check here, and every one of them happened in a real benchmark before it
became one:

- a refused action counted as a turn, so a model that answers nonsense looks
  busier — and, in every per-turn rate, better behaved — than one that does not;
- a retry counted as a turn, so one decision becomes three lines in the log;
- a fallback built from a legal action *name*, refused the moment a real payload
  is required, with the harness's mistake filed against the seat;
- the as-dealt hands read at the end of the hand, so the mus exchange turns one
  seed into two different deals;
- the deal stream forked from the *play's* generator, so the two halves of a
  mirrored pair sit on different cards;
- a truth snapshot taken after `apply`, which records the seat as facing the bet
  it has just made;
- a partner's action taken as the answer to your bet;
- a per-hand piedra difference published without its mirror, which measures the
  seat and calls it skill;
- a bluff counted as a bet that *lost* — which, with two hands a team wins about
  half the time, is a number that describes the coin and not the player;
- a 40-point vaca that zeroes the point counters and takes the outcome with them;
- a coin flip scored as Brier 0.5 instead of 0.25, and a log-loss asked for the
  logarithm of exactly zero;
- a fallback rate divided by every turn in the match, so a baseline that never
  falls back dilutes a model that mostly does into publishability;
- an API outage entering the leaderboard as a result.

No network, no sockets, no wall clock, no global state: matches are seeded,
policies are deterministic, the deals are forked from the seed before a single
decision, and `time.time` and `time.sleep` are under landmines in the smoke run.
Where a decision was a judgement call, it is written down in the template's
docstring as a DESIGN DECISION, and the check asserts the consequence.

## The provided engine

`mus.py` is complete and has no TODOs. The surface the course builds on:

```python
PALOS, RANKS, CARD_POINTS, RANK_GRANDE, RANK_CHICA, JUEGO_RANK, VACA_TARGET   # the rules as data
TEAM_OF, team_of(seat)                                                        # 0,2 vs 1,3
Card(rank, palo), make_deck()                                                 # str(card) is the discard payload
IllegalAction, TurnLimitExceeded, Phase                                       # refusals, the rail, the phases
Table(seed, deal_seed=None, mus_rounds=2, envite_max=40)                      # one table
    .deal() .legal_actions(seat) .apply(seat, action) .default_action(seat)
    .hand_points(...) .compare_jugadas()
    .phase .mano .current_seat .hands .draw_pile .discard_pile .turns .lance
    .points_a .points_b .vacas_a .vacas_b .hand_gain_a .hand_gain_b
    .hand_winner .mus_want .hand_index .envite
strength(table, seat, lance=None)   would_win(table, seat, lance=None)        # the oracles
lance_winner(table, lance=None)     default_action(table, seat)
random_policy(seed)                 heuristic_policy(seed)                    # the reference seats
self_play(seed, *, hands=4, policies=None, record_deals=False)
```

Three properties of it are load-bearing and are asserted by the stages: `apply`
validates before it mutates, so a refusal leaves the table byte-identical; the
deal stream is forked from the seed before the first decision, so the deal does
not depend on who is playing; and `hand_gain_a`/`hand_gain_b` are per-hand gains
that the 40-point vaca does **not** reset, while `points_a`/`points_b` it does.

## The stages

| # | File | The mechanism | The thing people get wrong |
|---|---|---|---|
| 1 | `stage_01.py` | `new_stats`, `gate` | A refusal counted as a turn; the turn counted before the action lands; `except Exception` filing our bug as the model's; the engine's own words replaced by ours; counters copied instead of updated; a "helpful" legal fallback applied to a refusal |
| 2 | `stage_02.py` | `DegradedMatch`, `run_match` | The as-dealt snapshot read at the end of the hand; a retry charged as a turn; a fallback built from an action name; a watchdog that never fires; a fallback counted as the model's decision; a harness bug reported as `done`; a row whose `llm_turns` counts every seat |
| 3 | `stage_03.py` | `truth_snapshot`, `decision_line`, `DecisionLog` | The snapshot taken after the action; unsorted JSON keys so two runs of a seed differ in bytes; `default=str` writing an object's repr into a field the analysis reads as a name; `True` accepted as a probability; nothing written to the sink, or the sink written twice |
| 4 | `stage_04.py` | `AGGRESSIVE`, `RESPONSES`, `link_responses` | A partner's action taken as the answer; a raise lumped with a call; a scan that crosses a hand or lance boundary; the deje floor of 1 lost when nothing was staked; the last answer winning instead of the first |
| 5 | `stage_05.py` | `MIN_REFERENCE`, `can_bet`, `strength_terciles`, `strength_band` | The pool drawn from every decision instead of the bet-capable ones; a cut computed from five hands; `<= lo` read as medium and `>= hi` as strong; an unmeasured hand banded anyway; the split in halves instead of thirds |
| 6 | `stage_06.py` | `scorecard` | **A bluff defined as a bet that lost** (a number about the base rate, not the player); a called bluff charged as a loss when the lance was won; a partner's bet counted as something you can fold to; `None` reported as `0.0` for a rate with no denominator; `weak_hand_bet_rate` divided by the wrong opportunities |
| 7 | `stage_07.py` | `outcome` | The sums taken from the point counters the vaca reset; a tie counted as a win; the per-hand divisor taken from one match of two; `{}` vs a zero-filled dict for no data |
| 8 | `stage_08.py` | `EPS`, `brier`, `logloss`, `auc`, `reliability` | A coin flip scored as 0.5 instead of 0.25; an unclipped log-loss; no data turned into a perfect score; a `bool` accepted as a probability; ties in the ranking counted as wins; one class absent reported as a coin flip; a calibration bucket indexed by the outcome, or `p = 1.0` falling outside the table |
| 9 | `stage_09.py` | `MIN_LLM_CALLS`, `MAX_FALLBACK_RATIO`, `is_publishable_match`, `leaderboard` | The fallback rate divided by every turn in the match; a degraded row counted as a win or a loss; a row with missing vacas read as a 0-0 tie; a label with no data outranking a measured loss; a row credited to one of its two labels; the mean of per-row ratios instead of the ratio of sums |
| 10 | `stage_10.py` | `build_jobs`, `paired_rows` | The schedule zipped so the two orientations sit on different cards; a half pair published alone; the two diffs averaged instead of summed; the divisor taken from one match's hands; a degraded half still counted; the vantage following the order the rows arrived in |

## How to use this directory

```bash
python3 codecraft/cli.py run benchmark-from-scratch    # what to build next, and why
python3 codecraft/cli.py hint benchmark-from-scratch   # when a nudge is not enough
```

Or without codecraft:

```bash
python3 -c "import course; [print(i, s.title) for i, s in enumerate(course.STAGES, 1)]"
```

Implement the templates at the top level; finished versions are in `solutions/`.
The stages are cumulative: stage 2's loop is stage 1's gate plus stage 3's
record; stage 5 imports stage 4's `AGGRESSIVE`; stage 6 imports stage 4's
`link_responses` and stage 5's `can_bet`/`strength_band`/`strength_terciles`. A
check for a late stage therefore needs the earlier ones implemented, and
`solutions/` overlaid on the templates is the state those checks are written
against. `mus.py` is not a stage: it is the domain, provided complete.

## Prerequisites

Standard library only: `json`, `math`, `itertools`, `random`. No numpy, no
scipy, no pandas, no HTTP client, no database — the whole benchmark is dicts,
floats and one `sorted()` call. You should be comfortable with dicts, closures
and `try/except`; the statistics are written out by hand, on purpose, because
"which pairs did you average over?" is the question this course is about.

## Design decisions

- **The engine is the only gate.** The harness never re-derives the rules: the
  table already answers `legal_actions` and already refuses through `apply`, and
  the refused action leaves the table byte-identical. Two rulebooks means one of
  them is wrong, and it is always the second one.
- **A turn is a decision that changed the position.** A refusal is counted in its
  own bucket and is not a turn; a retry is a call, not a turn; a fallback is the
  harness's decision, not the model's, and is flagged in the record so poisoned
  turns can be excluded later.
- **The truth is captured before the action.** `truth_snapshot` is a separate
  function from `decision_line` exactly so the caller can take it before `apply`;
  a snapshot taken afterwards records the position the seat *created*, and every
  metric built on "what was it risking?" is then measured on the wrong side of
  the decision.
- **One line per turn, sorted keys, nothing invented.** The log is compared,
  diffed and re-run: the same seed must produce the same bytes. A value that is
  not JSON-serialisable is a bug in the record, not an object to stringify.
- **An aggression is answered by the first opposing response.** Your partner's
  action is not an answer to your bet, in either direction; a scan never crosses
  a hand or a lance; and the deje floor of 1 applies at collection, because
  folding when nothing was staked still wins the minimum.
- **The reference is the population that could bet.** A strength tercile is
  measured over the decisions that `can_bet`, per lance, and a lance with fewer
  than `MIN_REFERENCE` hands gets no cut rather than a threshold invented from a
  handful of hands. The boundary is deliberate: `s <= lo` is weak, `s = hi` is
  still medium.
- **A bluff is a weak hand that bet.** Not a bet that lost: with two hands a team
  takes any lance about half the time, so "bet and lost" measures the base rate.
  The scorecard is built so the two cannot be confused, and a check with eight
  losing strong bets pins `bluff_rate == 0.0`.
- **The outcome survives the reset.** `hand_gain_*` is what a hand paid and the
  vaca does not touch it; `points_*` is zeroed by the vaca, so summing it reports
  a match that never scored. `vacas_*` is a running total: the last hand's count
  is the match's.
- **A probe refuses to hide a bug.** A `bool` is not a probability (`True` is
  `1`), a number outside [0, 1] is a units bug and not a value to clamp, the
  log-loss is clipped because a logarithm of zero is an infinity, a tied pair
  earns half credit, and one class absent means discrimination is undefined —
  `None`, not 0.5, because 0.5 is a claim about a coin.
- **The fallback rate is about the model.** Its denominator is that model's own
  decisions plus the fallbacks they forced, and a row that degraded is not a
  result: the gate exists so that "the API was down" cannot enter the table as a
  number.
- **A match is half a measurement.** Every match is played twice under the same
  seed with the seats swapped, because a seat advantage appears in the two
  halves with opposite signs and cancels in their sum while the signal doubles.
  A pair missing a half, or with a degraded half, has no seat-balanced number and
  disappears rather than falling back to the one half it has.

## Verification

The solutions pass all ten checks, and every check is mutation-tested: **168
plausible wrong implementations** — a refusal counted as a turn, a retry charged
as a turn, `except Exception` filing our bug as the model's, a refusal papered
over with a fallback, the engine's words replaced by ours, a stale stats dict, an
as-dealt snapshot read at the end of the hand, a watchdog that never fires, a
fallback counted as the model's decision, a harness bug reported as `done`, a
partner taken as the answer to your bet, a raise lumped with a call, a scan that
crosses a lance, the deje floor lost, a pool drawn from every decision, a cut
fabricated from five hands, an off-by-one band at both cuts, a bluff defined as a
lost bet, a called bluff charged when the lance was won, sums taken from the
reset counters, a tie credited as a win, a coin flip scored 0.5, an unclipped
log-loss, no data reported as a perfect score, a `bool` accepted as a
probability, ties counted as wins in the ranking, the fallback rate divided by
the match instead of the model, a degraded row counted as a loss, the mean of
ratios instead of the ratio of sums, a zipped schedule, a half pair published
alone, the two diffs averaged instead of summed — are each planted into a
solution, and the stage's check must fail. Every assertion message names the
mistake, not the symptom; the count per stage is 13, 17, 17, 18, 15, 19, 15, 22,
16, 16.

Two proofs sit outside the per-stage checks. `mutate_all.py` replays all 168
mutations against the assembled course under one runner (`MISSED OR BROKEN: 0`,
the tree rebuilt for every mutation and `PYTHONDONTWRITEBYTECODE=1`, because a
stale `__pycache__` whose size and second match the previous mutant's runs the
*previous* mutant's code and shows a real catch up as a miss). A smoke run
composes all ten stages over one real match — a seeded table, a loop, a
JSONL log, the links, the terciles, the scorecard, the outcome, the read probes,
the gate, the leaderboard and the mirrored pair — with `time.time` and
`time.sleep` patched to raise for the whole run:

```
SMOKE PASS — 64 turns, 64 records, 13 links, 5 cuts, 36 pairs probed
  piedras per hand: gambler -0.500, heuristic +0.500 (pair -1.000)
  read: brier 0.3221, log-loss 2.2004, auc 0.5734, 3 calibration bins
  risk: gambler: 31 decisions, 0.69 aggressive, 1 bluffs | heuristic: 33 decisions, 0.27 aggressive, 0 bluffs
```

The provided engine has its own proof, `/tmp`-side in development and re-run
before this course was committed: 68 checks, of which the first is exhaustive
scoring parity against the reference implementation over **all 91,390 four-card
hands** on all four scales (the parity loop runs in 0.92 s, with the value tables
built lazily on first use).

Re-running the proofs:

```bash
python3 codecraft/cli.py run benchmark-from-scratch   # per stage, with the failure line
python3 /tmp/f1-checks/run_all.py                     # every stage's check, solutions overlaid
python3 /tmp/f1-checks/mutate_all.py                  # every mutation, one runner
python3 /tmp/f1-smoke.py                              # all ten stages composed
```

## Where this stops

Deliberately left out, so you know the boundary:

- **No LLM seats.** A seat is a callable `(table, seat, legal) -> decision`, and
  the two reference seats are seeded policies. No HTTP client, no prompt
  building, no provider retries, no JSON-schema coercion — and the
  stdout-salvage parser that turns a model's prose into an action is out of
  scope, because the interesting failures in this course are what the harness
  does with a *legal* action, not with a malformed one.
- **No publishing layer.** The leaderboard is a list of dicts: no database, no
  export, no dashboards, no leaderboard service. The gate and the ordering are
  the parts that decide whether a number is true.
- **No tournament runner.** `build_jobs` schedules a mirrored pair;
  parallel execution, resumption and multi-process scheduling are not here,
  because the property that matters is *which cards the halves saw*, and it is
  asserted directly.
- **No training.** Every number here is a measurement. Nothing updates a model,
  and the risk scorecard is not a reward.
- **The game's own rules are given.** Scoring parity with the reference is a
  provided-engine property, verified exhaustively once; the lesson is not how a
  Fournier deck compares two pares, it is what you do with the comparison.
- **Confidences are only as honest as the seat.** The probes measure the number a
  seat declares; the two reference policies declare real probabilities by
  construction, and a seat that always says 0.5 will be measured as the constant
  it is.
- **The reference implementation cannot do all of this either.** The benchmark
  this course is modelled on ships a CLI that is broken at HEAD; its numbers come
  from library calls with checks around them. That is the point of the course:
  the machinery is the part you can prove.

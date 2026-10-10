"""Eval Framework From Scratch — stage 1: the suite config, and the case that is
not a case.

DESIGN DECISION — why does a config refuse a key it does not know?
    A typo in a suite file is invisible. `metric` instead of `metrics`, `repeat`
    instead of `repeats`, `max_tick` instead of `max_ticks`: the runner ignores
    the key it does not recognise, the run is configured differently from what
    its author believes, and the difference surfaces later as a metric that is
    quietly absent or a budget that is quietly generous. Refusing the key turns a
    week of confusing numbers into a message with a line number.

DESIGN DECISION — why is the canonical form the EFFECTIVE config?
    The canonical text is what the suite hash is computed over (stage 10), and
    the hash decides whether a resume may reuse a log. Two files that describe
    the same run must therefore produce the same text: one that spells every
    default out and one that leaves them out have to be interchangeable, or a
    config that is edited to be more explicit invalidates an otherwise valid
    resume. Materialising the defaults makes the text a property of the run, not
    of the file's spelling.

DESIGN DECISION — why is a duplicate case id an error instead of a last-wins?
    The id is the key of everything downstream: the rollup groups by case
    (stage 5), the resume identifies completed work by `(case, repeat)`
    (stage 10), the diff compares by metric over cases (stage 9). With two live
    cases under one id, the rollup merges them into a mean that describes
    neither, the resume silently skips the second, and both numbers look
    plausible. An id is an identity: two of them is a config bug.

DESIGN DECISION — why is a zero weight refused, and a `bool` not a number?
    A case with weight 0 is never counted by a weighted mean: it costs a model
    call, fills a line of the log, and cannot move a single published number, so
    the weight is a mistake about intent, not a choice. And `True == 1` in
    Python: a suite that says `"weight": true`, or `"max_ticks": true`, would run
    happily with the value 1 — a budget of one tick and a weight of one, from a
    file that meant something else entirely.

TODO: implement `parse_suite` and `canonical_suite`.
"""

from dataclasses import dataclass


#: The keys a suite may carry, and the keys a case may carry. Anything else is a
#: typo and is refused.
SUITE_KEYS = ("id", "cases", "metrics", "max_ticks", "max_calls", "max_judge_calls", "notes")
CASE_KEYS = ("id", "prompt", "answer", "weight", "max_ticks", "repeats", "tags")

DEFAULT_CASE_TICKS = 10
DEFAULT_RUN_TICKS = 1000
DEFAULT_MAX_CALLS = 1000
DEFAULT_MAX_JUDGE_CALLS = 500


@dataclass(frozen=True)
class Case:
    """One task, as the suite declares it."""

    id: str
    prompt: str
    answer: str
    weight: float = 1.0
    max_ticks: int = DEFAULT_CASE_TICKS
    repeats: int = 1
    tags: tuple = ()


@dataclass(frozen=True)
class Suite:
    """A parsed suite: every default materialised, every case validated."""

    id: str
    cases: tuple
    metrics: tuple = ()
    max_ticks: int = DEFAULT_RUN_TICKS
    max_calls: int = DEFAULT_MAX_CALLS
    max_judge_calls: int = DEFAULT_MAX_JUDGE_CALLS
    notes: str = ""


def parse_suite(spec):
    """Validate a suite mapping and return a `Suite` (or raise `lab.ConfigError`).

    Raises for: a spec that is not a mapping; an unknown suite or case key; a
    missing, empty or non-`str` id; a duplicated case id; an empty `prompt`; a
    non-`str` `answer`; a `weight` that is not a real number `> 0`; `max_ticks`,
    `max_calls`, `max_judge_calls` or `repeats` that are not positive ints;
    `tags` or `metrics` that are not sequences of non-empty strings (a bare
    string is not a sequence here); a duplicated metric name; an empty case list.
    Every message names the offending key and value.
    """
    raise NotImplementedError("stage 1: implement parse_suite()")


def canonical_suite(suite):
    """The effective config as canonical JSON text: defaults materialised, cases
    in declared order, keys sorted, no whitespace.

    This is the text the suite hash is taken over, so two specs that describe the
    same run — one spelling the defaults out, one not — must produce it byte for
    byte.
    """
    raise NotImplementedError("stage 1: implement canonical_suite()")

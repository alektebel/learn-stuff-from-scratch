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
"""

from dataclasses import dataclass
import json

from lab import ConfigError

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


def _require_str(value, *, where):
    if not isinstance(value, str):
        raise ConfigError("%s: expected a string, got %r %r"
                          % (where, type(value).__name__, value))
    return value


def _require_filled(value, *, where):
    _require_str(value, where=where)
    if not value.strip():
        raise ConfigError("%s: expected a non-empty string, got %r" % (where, value))
    return value


def _require_int(value, *, where, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError("%s: expected an int >= %d, got %r %r"
                          % (where, minimum, type(value).__name__, value))
    if value < minimum:
        raise ConfigError("%s: expected an int >= %d, got %r" % (where, minimum, value))
    return value


def _require_names(value, *, where):
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ConfigError("%s: expected a list of names, got %r %r"
                          % (where, type(value).__name__, value))
    names = tuple(_require_filled(name, where="%s[%d]" % (where, i))
                  for i, name in enumerate(value))
    if len(set(names)) != len(names):
        raise ConfigError("%s: the same name is listed twice: %r" % (where, value))
    return names


def _parse_case(spec, *, index):
    where = "case[%d]" % (index,)
    if not isinstance(spec, dict):
        raise ConfigError("%s: expected a mapping, got %r" % (where, type(spec).__name__))
    for key in spec:
        if key not in CASE_KEYS:
            raise ConfigError("%s: unknown key %r" % (where, key))
    if "id" not in spec:
        raise ConfigError("%s: missing required key 'id'" % (where,))
    case_id = _require_filled(spec["id"], where="%s.id" % (where,))
    if "prompt" not in spec:
        raise ConfigError("case %r: missing required key 'prompt'" % (case_id,))
    prompt = _require_filled(spec["prompt"], where="case %r.prompt" % (case_id,))
    if "answer" not in spec:
        raise ConfigError("case %r: missing required key 'answer'" % (case_id,))
    answer = _require_str(spec["answer"], where="case %r.answer" % (case_id,))
    weight = spec.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ConfigError("case %r.weight: expected a number > 0, got %r %r"
                          % (case_id, type(weight).__name__, weight))
    if not weight > 0:
        raise ConfigError("case %r.weight: expected a number > 0, got %r"
                          % (case_id, weight))
    max_ticks = _require_int(spec.get("max_ticks", DEFAULT_CASE_TICKS),
                             where="case %r.max_ticks" % (case_id,))
    repeats = _require_int(spec.get("repeats", 1), where="case %r.repeats" % (case_id,))
    tags = _require_names(spec.get("tags", ()), where="case %r.tags" % (case_id,))
    return Case(id=case_id, prompt=prompt, answer=answer, weight=float(weight),
                max_ticks=max_ticks, repeats=repeats, tags=tags)


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
    if not isinstance(spec, dict):
        raise ConfigError("suite: expected a mapping, got %r" % (type(spec).__name__,))
    for key in spec:
        if key not in SUITE_KEYS:
            raise ConfigError("suite: unknown key %r" % (key,))
    if "id" not in spec:
        raise ConfigError("suite: missing required key 'id'")
    suite_id = _require_filled(spec["id"], where="suite.id")
    if "cases" not in spec:
        raise ConfigError("suite %r: missing required key 'cases'" % (suite_id,))
    raw_cases = spec["cases"]
    if isinstance(raw_cases, str) or not isinstance(raw_cases, (list, tuple)):
        raise ConfigError("suite %r.cases: expected a list of cases, got %r"
                          % (suite_id, type(raw_cases).__name__))
    if not raw_cases:
        raise ConfigError("suite %r.cases: an empty suite measures nothing" % (suite_id,))
    cases = tuple(_parse_case(case, index=i) for i, case in enumerate(raw_cases))
    seen = {}
    for case in cases:
        if case.id in seen:
            raise ConfigError("suite %r.cases: duplicate case id %r"
                              % (suite_id, case.id))
        seen[case.id] = case
    metrics = _require_names(spec.get("metrics", ()), where="suite %r.metrics" % (suite_id,))
    max_ticks = _require_int(spec.get("max_ticks", DEFAULT_RUN_TICKS),
                             where="suite %r.max_ticks" % (suite_id,))
    max_calls = _require_int(spec.get("max_calls", DEFAULT_MAX_CALLS),
                             where="suite %r.max_calls" % (suite_id,))
    max_judge_calls = _require_int(spec.get("max_judge_calls", DEFAULT_MAX_JUDGE_CALLS),
                                   where="suite %r.max_judge_calls" % (suite_id,))
    notes = spec.get("notes", "")
    _require_str(notes, where="suite %r.notes" % (suite_id,))
    return Suite(id=suite_id, cases=cases, metrics=metrics, max_ticks=max_ticks,
                 max_calls=max_calls, max_judge_calls=max_judge_calls, notes=notes)


def canonical_suite(suite):
    """The effective config as canonical JSON text: defaults materialised, cases
    in declared order, keys sorted, no whitespace.

    This is the text the suite hash is taken over, so two specs that describe the
    same run — one spelling the defaults out, one not — must produce it byte for
    byte.
    """
    effective = {
        "id": suite.id,
        "cases": [
            {"id": case.id, "prompt": case.prompt, "answer": case.answer,
             "weight": case.weight, "max_ticks": case.max_ticks,
             "repeats": case.repeats, "tags": list(case.tags)}
            for case in suite.cases
        ],
        "metrics": list(suite.metrics),
        "max_ticks": suite.max_ticks,
        "max_calls": suite.max_calls,
        "max_judge_calls": suite.max_judge_calls,
        "notes": suite.notes,
    }
    return json.dumps(effective, sort_keys=True, separators=(",", ":"))

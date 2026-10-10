"""lab.py — the task set, the actors and the clock, PROVIDED COMPLETE.

This is F2's `mus.py`: the thing under test and the things that fail. An eval
framework is a machine that runs other people's code and other people's
judgements and then has to say something true about them, so the domain here is
deliberately hostile: solvers that answer, lie, stall, explode on the third call,
judges that are strict, sloppy, evasive, rude about the shape of their answer, or
simply biased towards whatever they were shown first.

Everything in this file is deterministic. There is no `time`, no `random`
without a seed, no `os`, no network, and no module-level mutable state: the
"clock" is a counter (`Ticker`) that the actors advance, so a timeout is a
property of the code under test and not of the machine it ran on.

Nothing here knows about suites, records, metrics or gates — that is the course.
"""

from dataclasses import dataclass, field
import random

#: The task set: raw data, the same shape a config file would carry.
QUESTIONS = (
    {"id": "sum-2-3", "prompt": "What is 2 + 3?", "answer": "5"},
    {"id": "sum-9-16", "prompt": "What is 9 + 16?", "answer": "25"},
    {"id": "sum-40-2", "prompt": "What is 40 + 2?", "answer": "42"},
    {"id": "diff-100-58", "prompt": "What is 100 - 58?", "answer": "42"},
    {"id": "prod-6-7", "prompt": "What is 6 * 7?", "answer": "42"},
    {"id": "capital-fr", "prompt": "Name the capital of France.", "answer": "Paris"},
    {"id": "capital-jp", "prompt": "Name the capital of Japan.", "answer": "Tokyo"},
    {"id": "lang-br", "prompt": "Which language is spoken in Brazil?", "answer": "Portuguese"},
    {"id": "unit-m", "prompt": "How many metres are in a kilometre?", "answer": "1000"},
    {"id": "list-abc", "prompt": "Sort these letters: c, a, b.", "answer": "a, b, c"},
    {"id": "bool-yes", "prompt": "Is 7 prime? Answer yes or no.", "answer": "yes"},
    {"id": "json-count", "prompt": "How many keys are in {\"a\": 1, \"b\": 2}?", "answer": "2"},
)

#: What a case weighs when it does not say.
DEFAULT_WEIGHT = 1.0

#: How much of the clock a judge costs, per invocation.
JUDGE_TICKS = 3


class ConfigError(ValueError):
    """A suite, a gate or a plugin the framework refuses to run.

    The framework's own refusal (a typo in a config, a plugin that is not
    registered, a judge that answers outside its vocabulary) travels as this
    type, so a check can tell "your config is wrong" from "the model was wrong".
    """


class Ticker:
    """The injected clock: a counter, not a wall clock.

    A tick is whatever the machine under test spends. `Ticker.step` is the
    granularity, and the only way the value moves is `tick()` — which is called
    by the actors, never by the framework.
    """

    def __init__(self, start=0, step=1):
        if isinstance(start, bool) or not isinstance(start, int):
            raise ConfigError("Ticker start must be an int, got %r" % (start,))
        if isinstance(step, bool) or not isinstance(step, int) or step < 1:
            raise ConfigError("Ticker step must be an int >= 1, got %r" % (step,))
        self._value = start
        self.step = step
        self.ticks = 0

    def now(self):
        """The current reading."""
        return self._value

    def tick(self, n=1):
        """Advance by `n` ticks and return the new reading."""
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ConfigError("tick(n): n must be an int >= 0, got %r" % (n,))
        self._value += n * self.step
        self.ticks += n
        return self._value

    def __repr__(self):
        return "Ticker(now=%d, ticks=%d)" % (self._value, self.ticks)


class Actor:
    """Base for the scripted solvers and judges: a callable with a call count.

    `calls` counts invocations of the *underlying* actor, which is what the
    cache and the resume stages assert ("the judge was asked once", "the solver
    was never called for a case that was already done").

    `clock` is the ticker the actor was built with; the call site's `clock=`
    wins when it is given, so a check can build an actor with no clock at all
    and still pass one per call.
    """

    def __init__(self, fn, *, clock=None, label=None):
        if not callable(fn):
            raise ConfigError("Actor needs a callable, got %r" % (type(fn).__name__,))
        self._fn = fn
        self.clock = clock
        self.label = label or getattr(fn, "__name__", "actor")
        self.calls = 0

    def _ticker(self, clock):
        ticker = clock if clock is not None else self.clock
        if ticker is None:
            raise ConfigError("%s needs a clock (pass clock= at the call site)" % (self.label,))
        return ticker

    def __repr__(self):
        return "<%s %s calls=%d>" % (type(self).__name__, self.label, self.calls)


class Solver(Actor):
    """A system under test: `solver(prompt, *, clock) -> str | None`."""

    def __call__(self, prompt, *, clock=None):
        ticker = self._ticker(clock)
        self.calls += 1
        return self._fn(prompt, ticker, self.calls)


class Judge(Actor):
    """A judge: `judge(*, prompt, answer, reference, clock) -> dict`."""

    def __call__(self, *, prompt, answer, reference, clock=None):
        ticker = self._ticker(clock)
        self.calls += 1
        ticker.tick(JUDGE_TICKS)
        return self._fn(prompt=prompt, answer=answer, reference=reference,
                        ticker=ticker, call=self.calls)


# --- the solvers ----------------------------------------------------------

def _lookup(prompt, answers):
    for question in QUESTIONS:
        if question["prompt"] == prompt:
            return answers.get(question["id"], question["answer"])
    return None


def perfect(answers=None, *, clock=None, seed=0):
    """Answers every known prompt correctly; an unknown prompt gets `None`."""
    table = dict(answers or {})

    def fn(prompt, ticker, call):
        return _lookup(prompt, table)

    return Solver(fn, clock=clock, label="perfect")


def noisy(p=0.5, *, clock=None, seed=0, answers=None):
    """Answers correctly with probability `p`, and wrong otherwise — seeded.

    The wrong answer is a *different* question's answer, so it is plausible
    prose rather than an obviously empty string.
    """
    if not 0.0 <= p <= 1.0:
        raise ConfigError("noisy(p): p must be in [0, 1], got %r" % (p,))
    rng = random.Random(seed)
    table = dict(answers or {})
    wrong_pool = [question["answer"] for question in QUESTIONS]

    def fn(prompt, ticker, call):
        right = _lookup(prompt, table)
        if right is None or rng.random() < p:
            return right
        for _ in range(len(wrong_pool)):
            other = rng.choice(wrong_pool)
            if other != right:
                return other
        return right

    return Solver(fn, clock=clock, label="noisy")


def silent(*, clock=None):
    """Returns `None`: no answer at all, which is not the empty string."""

    def fn(prompt, ticker, call):
        return None

    return Solver(fn, clock=clock, label="silent")


def crashing(when=0, *, exc=RuntimeError, clock=None, message="actor exploded"):
    """Raises on call `when` (1-based); `when=0` raises on every call."""
    if isinstance(when, bool) or not isinstance(when, int) or when < 0:
        raise ConfigError("crashing(when): when must be an int >= 0, got %r" % (when,))

    def fn(prompt, ticker, call):
        if when == 0 or call == when:
            raise exc(message)
        return _lookup(prompt, {})

    return Solver(fn, clock=clock, label="crashing")


def slow(ticks=1, *, wrapped=None, clock=None):
    """Advances the clock by `ticks`, then answers — correctly, or like `wrapped`."""
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 1:
        raise ConfigError("slow(ticks): ticks must be an int >= 1, got %r" % (ticks,))
    if wrapped is not None and not isinstance(wrapped, Solver):
        raise ConfigError("slow(wrapped): wrapped must be a Solver, got %r"
                          % (type(wrapped).__name__,))

    def fn(prompt, ticker, call):
        ticker.tick(ticks)
        if wrapped is None:
            return _lookup(prompt, {})
        return wrapped(prompt, clock=ticker)

    return Solver(fn, clock=clock, label="slow")


def chatty(wrapped, *, prefix="The answer is: ", clock=None):
    """Dresses another solver's answer in prose a naive judge will not match."""
    if not isinstance(wrapped, Solver):
        raise ConfigError("chatty(wrapped): wrapped must be a Solver, got %r"
                          % (type(wrapped).__name__,))

    def fn(prompt, ticker, call):
        answer = wrapped(prompt, clock=ticker)
        return None if answer is None else prefix + answer

    return Solver(fn, clock=clock, label="chatty")


# --- the judges -----------------------------------------------------------

def _verdict(correct, reason):
    return {"verdict": "correct" if correct else "incorrect", "reason": reason}


def exact_judge(*, clock=None):
    """Strict equality after stripping whitespace."""

    def fn(*, prompt, answer, reference, ticker, call):
        if not isinstance(answer, str):
            return _verdict(False, "no answer to judge")
        same = answer.strip() == reference.strip()
        return _verdict(same, "exact match" if same else "answer differs")

    return Judge(fn, clock=clock, label="exact_judge")


def substring_judge(*, clock=None):
    """Lenient: either side containing the other counts as correct."""

    def fn(*, prompt, answer, reference, ticker, call):
        if not isinstance(answer, str):
            return _verdict(False, "no answer to judge")
        left, right = answer.strip().lower(), reference.strip().lower()
        same = bool(left) and bool(right) and (left in right or right in left)
        return _verdict(same, "containment")

    return Judge(fn, clock=clock, label="substring_judge")


def unclear_judge(*, clock=None):
    """Refuses to decide, every time."""

    def fn(*, prompt, answer, reference, ticker, call):
        return {"verdict": "unclear", "reason": "not sure"}

    return Judge(fn, clock=clock, label="unclear_judge")


def sulking_judge(*, exc=RuntimeError, clock=None):
    """Raises instead of answering: a judge is not a verdict."""

    def fn(*, prompt, answer, reference, ticker, call):
        raise exc("judge is unavailable")

    return Judge(fn, clock=clock, label="sulking_judge")


def bad_shape_judge(*, clock=None):
    """Answers outside the vocabulary, and without the keys a record needs."""

    def fn(*, prompt, answer, reference, ticker, call):
        return {"verdict": "maybe", "confidence": 0.9}

    return Judge(fn, clock=clock, label="bad_shape_judge")


def order_sensitive_judge(*, clock=None):
    """A judge that rewards the position, not the answer.

    It is called twice per pairwise question, with the two answers swapped, and
    it says "correct" on the first call of each pair and "incorrect" on the
    second — whatever the answers are. A framework that asks once, or that does
    not combine the two orders, reports this judge as knowing something.
    """

    def fn(*, prompt, answer, reference, ticker, call):
        first_of_pair = call % 2 == 1
        return _verdict(first_of_pair, "the first one looked better")

    return Judge(fn, clock=clock, label="order_sensitive_judge")


# --- fixtures the checks build with hand -----------------------------------
# A case and a suite are ordinary attribute bags here: a check for stage 5 must
# not import stage 1's dataclass to build its fixtures.

@dataclass
class LabCase:
    id: str
    prompt: str
    answer: str
    weight: float = DEFAULT_WEIGHT
    max_ticks: int = 10
    repeats: int = 1
    tags: tuple = field(default_factory=tuple)


@dataclass
class LabSuite:
    id: str
    cases: tuple
    metrics: tuple = field(default_factory=tuple)
    max_ticks: int = 1000
    max_calls: int = 1000
    max_judge_calls: int = 500
    notes: str = ""


def make_case(id, prompt=None, answer=None, *, weight=DEFAULT_WEIGHT,
              max_ticks=10, repeats=1, tags=()):
    """A case object with the same attributes `parse_suite` produces."""
    if prompt is None:
        prompt = next((q["prompt"] for q in QUESTIONS if q["id"] == id), id)
    if answer is None:
        answer = next((q["answer"] for q in QUESTIONS if q["id"] == id), id)
    return LabCase(id=id, prompt=prompt, answer=answer, weight=weight,
                   max_ticks=max_ticks, repeats=repeats, tags=tuple(tags))


def make_suite(id="toy", cases=None, *, metrics=(), max_ticks=1000,
               max_calls=1000, max_judge_calls=500, notes=""):
    """A suite object with the same attributes `parse_suite` produces."""
    if cases is None:
        cases = tuple(make_case(q["id"]) for q in QUESTIONS[:3])
    return LabSuite(id=id, cases=tuple(cases), metrics=tuple(metrics),
                    max_ticks=max_ticks, max_calls=max_calls,
                    max_judge_calls=max_judge_calls, notes=notes)

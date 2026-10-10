"""Eval Framework From Scratch — stage 6: the judge protocol.

DESIGN DECISION — why is a judge's reply validated instead of read, and why is
`unclear` not `incorrect`?
    A judge is a model in a costume: it answers with free text that happens to
    look like a dict, and a runner that trusts the shape ends up averaging
    `"maybe"`, `None` and a confidence score into a quality number nobody can
    read back. The vocabulary is three words, so a reply outside it is a broken
    instrument — reported, never scored. And `unclear` is not a loss: it is the
    absence of a measurement, and the metric protocol already has a word for
    that (`None`, which shrinks the metric's `n`). Counting "I cannot tell" as
    0.0 would publish the judge's hesitation as the model's failure.

DESIGN DECISION — why does a cache hit count in `asks` but not in the budget?
    They answer two different questions. `max_calls` is about cost: the judge
    invocation is the expensive, clock-ticking thing, and the whole point of
    caching a verdict is that the second identical question costs nothing — so
    it must not spend the budget either. `asks` is about what the framework DID
    with a case; a run that reports one judge call for a metric that consulted a
    verdict forty times is hiding the shape of its own work from whoever reads
    the log.

DESIGN DECISION — why is the cache keyed by `(prompt, answer, reference)` and
owned by the session?
    A verdict is an answer to exactly one question. Keyed by the candidate
    answer alone, two cases that happen to share an answer (a numeric answer, an
    empty string, a common phrase) share a verdict, so the second case is scored
    by a judgement about a different reference — invisible in the log, and it
    looks like a metric that works. And the cache lives on the session because a
    session IS a run: at module level, a second suite or a resume in the same
    process would inherit verdicts from a run that is not its own.

DESIGN DECISION — why does a pairwise metric ask twice, with the answers
swapped, and why is a disagreement not a win?
    One call measures the slot as much as the answer: a position-biased judge
    prefers whatever it reads first (`lab.order_sensitive_judge` says "correct"
    about the first argument whatever it is). Asking both orders turns the slot
    into a coin flip, and the two verdicts are combined conservatively:
    agreement is information, a disagreement is a tie (0.5) and never a win, one
    definite verdict beats one `unclear`, and two `unclear`s are no measurement
    at all.
"""

from lab import ConfigError

#: What a judge is allowed to say. Anything else is not a verdict.
JUDGE_VERDICTS = ("correct", "incorrect", "unclear")


def judge_score(verdict):
    """The score a verdict carries: 1.0, 0.0, or `None` for `unclear`.

    An unclear judgement is the absence of a measurement, not a wrong answer.
    A string outside `JUDGE_VERDICTS` is a caller's bug, so it is refused rather
    than mapped to a number the caller did not ask for.
    """
    if verdict == "correct":
        return 1.0
    if verdict == "incorrect":
        return 0.0
    if verdict == "unclear":
        return None
    raise ConfigError("judge_score: %r is not one of %s" % (verdict, JUDGE_VERDICTS))


def check_verdict(reply):
    """Validate a judge's reply: the `{"verdict", "reason"}` it means.

    A judge is a model with a schema, so a reply that is not a mapping, that
    answers outside `JUDGE_VERDICTS`, or that carries no string reason is refused
    rather than read: every consumer downstream (`judge_score`, a record, the
    gate) assumes a verdict. Extra keys are dropped — the protocol has exactly
    two fields.
    """
    if not isinstance(reply, dict):
        raise ConfigError("judge reply: expected a dict, got %s"
                          % (type(reply).__name__,))
    verdict = reply.get("verdict")
    if verdict not in JUDGE_VERDICTS:
        raise ConfigError("judge reply: verdict %r is not one of %s"
                          % (verdict, JUDGE_VERDICTS))
    reason = reply.get("reason")
    if not isinstance(reason, str):
        raise ConfigError("judge reply: reason must be a str, got %s"
                          % (type(reason).__name__,))
    return {"verdict": verdict, "reason": reason}


class JudgeSession:
    """One run's conversation with one judge.

    The session owns the cache, the budget and the two counters. The cache is
    per session because a session is the run: a cache shared between sessions
    would let one suite's verdicts decide another's numbers, and the resume
    (stage 10) would produce different bytes depending on what ran before it in
    the same process.

    `.calls` counts the judge's invocations — the thing that costs money and
    ticks the clock. `.asks` counts the calls to `ask`: the thing the framework
    did, cache hits and questions the budget refused included. A hit serves the
    stored verdict without calling the judge and without spending the budget.
    """

    def __init__(self, judge, *, clock=None, max_calls=None):
        """A session over `judge`, which is called as
        `judge(prompt=..., answer=..., reference=..., clock=...)`.

        `clock`, when given, is handed to the judge on every call. `max_calls`
        is the number of judge invocations the session may spend; `None` means
        no budget at all.
        """
        if not callable(judge):
            raise ConfigError("JudgeSession needs a callable judge, got %s"
                              % (type(judge).__name__,))
        if max_calls is not None and (isinstance(max_calls, bool)
                                      or not isinstance(max_calls, int)
                                      or max_calls < 1):
            raise ConfigError("JudgeSession(max_calls): expected None or an int >= 1, got %r"
                              % (max_calls,))
        self._judge = judge
        self._clock = clock
        self._max_calls = max_calls
        self._cache = {}
        self._calls = 0
        self._asks = 0

    @property
    def calls(self):
        """How many times the underlying judge was invoked."""
        return self._calls

    @property
    def asks(self):
        """How many times `ask` was called, cache hits included."""
        return self._asks

    def ask(self, *, prompt, answer, reference):
        """Ask the judge one question: cached, validated, budgeted.

        The cache key is the canonical `(prompt, answer, reference)` triple,
        because a verdict about one question is not a verdict about another that
        merely shares a candidate answer. A hit returns the stored verdict,
        counts in `asks` and nothing else. A miss spends one call of
        `max_calls`; the budget is checked before the judge is called, so the
        call that would exceed it does not happen.

        A judge that raises, or that answers with something that is not a
        verdict, makes this raise `ConfigError` naming the problem: a broken
        judge must surface as a broken measurement, never as a wrong answer.
        """
        self._asks += 1
        key = (prompt, answer, reference)
        if key in self._cache:
            return dict(self._cache[key])
        if self._max_calls is not None and self._calls >= self._max_calls:
            raise ConfigError("judge budget: max_calls=%d already spent (asking %r)"
                              % (self._max_calls, prompt))
        self._calls += 1
        try:
            reply = self._judge(prompt=prompt, answer=answer, reference=reference,
                                clock=self._clock)
        except Exception as exc:                                # noqa: BLE001
            raise ConfigError("judge raised %s: %s" % (type(exc).__name__, exc))
        checked = check_verdict(reply)
        self._cache[key] = checked
        return dict(checked)


def judge_metric(session):
    """A metric plugin (stage 2) that asks the judge about one answer.

    `fn(case, answer)` judges `answer` against the case's reference answer and
    returns 1.0, 0.0, or `None` when the judge could not decide — the same "not
    applicable" the metric protocol already has. Nothing is caught here: a judge
    that raises makes the metric raise, and stage 2 turns that into a metric
    error, so a broken instrument never enters the mean as a zero.
    """
    def metric(case, answer):
        reply = session.ask(prompt=case.prompt, answer=answer, reference=case.answer)
        return judge_score(reply["verdict"])
    return metric


def _combine(forward, backward):
    """The two orders of one pairwise question, as one measurement.

    Both unclear -> `None`. One definite verdict beats one `unclear`, because
    the judge did decide, once. A disagreement is 0.5: it is a tie, and a tie is
    the only honest reading of two orders that say opposite things.
    """
    if forward is None and backward is None:
        return None
    if forward is None:
        return backward
    if backward is None:
        return forward
    if forward != backward:
        return 0.5
    return forward


def pairwise_metric(session):
    """A metric plugin that asks the judge TWICE, with the answers swapped.

    `fn(case, answer)` asks `(answer, reference)` and `(reference, answer)` — a
    single call measures the slot as much as the answer — and combines the two
    verdicts through `_combine`. Two identical asks would be one call through
    the cache, which is exactly the bug this metric exists to expose.
    """
    def metric(case, answer):
        reference = case.answer
        forward = judge_score(session.ask(prompt=case.prompt, answer=answer,
                                          reference=reference)["verdict"])
        backward = judge_score(session.ask(prompt=case.prompt, answer=reference,
                                           reference=answer)["verdict"])
        return _combine(forward, backward)
    return metric

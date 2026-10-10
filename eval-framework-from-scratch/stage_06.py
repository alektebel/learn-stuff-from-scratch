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

TODO: implement `judge_score`, `check_verdict`, `JudgeSession`, `judge_metric`
and `pairwise_metric`.
"""

#: What a judge is allowed to say. Anything else is not a verdict.
JUDGE_VERDICTS = ("correct", "incorrect", "unclear")


def judge_score(verdict):
    """The score a verdict carries: 1.0, 0.0, or `None` for `unclear`.

    An unclear judgement is the absence of a measurement, not a wrong answer.
    A string outside `JUDGE_VERDICTS` is a caller's bug, so it is refused rather
    than mapped to a number the caller did not ask for.
    """
    raise NotImplementedError("stage 06: implement judge_score()")


def check_verdict(reply):
    """Validate a judge's reply: the `{"verdict", "reason"}` it means.

    A judge is a model with a schema, so a reply that is not a mapping, that
    answers outside `JUDGE_VERDICTS`, or that carries no string reason is refused
    rather than read: every consumer downstream (`judge_score`, a record, the
    gate) assumes a verdict. Extra keys are dropped — the protocol has exactly
    two fields.
    """
    raise NotImplementedError("stage 06: implement check_verdict()")


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
        raise NotImplementedError("stage 06: implement JudgeSession()")

    @property
    def calls(self):
        """How many times the underlying judge was invoked."""
        raise NotImplementedError("stage 06: implement JudgeSession.calls")

    @property
    def asks(self):
        """How many times `ask` was called, cache hits included."""
        raise NotImplementedError("stage 06: implement JudgeSession.asks")

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
        raise NotImplementedError("stage 06: implement JudgeSession.ask()")


def judge_metric(session):
    """A metric plugin (stage 2) that asks the judge about one answer.

    `fn(case, answer)` judges `answer` against the case's reference answer and
    returns 1.0, 0.0, or `None` when the judge could not decide — the same "not
    applicable" the metric protocol already has. Nothing is caught here: a judge
    that raises makes the metric raise, and stage 2 turns that into a metric
    error, so a broken instrument never enters the mean as a zero.
    """
    raise NotImplementedError("stage 06: implement judge_metric()")


def pairwise_metric(session):
    """A metric plugin that asks the judge TWICE, with the answers swapped.

    `fn(case, answer)` asks `(answer, reference)` and `(reference, answer)` — a
    single call measures the slot as much as the answer — and combines the two
    verdicts: agreement is information (1.0 / 0.0), a disagreement is a tie
    (0.5, never a win), one definite verdict beats one `unclear`, and two
    `unclear`s are `None`. Two identical asks would be one call through the
    cache, which is exactly the bug this metric exists to expose.
    """
    raise NotImplementedError("stage 06: implement pairwise_metric()")

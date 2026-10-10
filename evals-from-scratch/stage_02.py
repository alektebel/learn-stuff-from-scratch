"""Evals From Scratch — stage 2: the numbers that are not about quality

DESIGN DECISION — measure the cheap signals first.
    Error rate, refusal rate, latency and token counts decide most rollout
    questions before a judge is ever consulted. They are also the numbers that
    cannot be argued with: a candidate that refuses 30% of requests, or takes
    four times as long, has lost before anyone debates quality. Build them
    first, and treat them as the primary signal they are.

DESIGN DECISION — a percentile is not an average of the tail.
    Latency lives in the tail, and the mean hides it. p95 is the smallest
    observed value at or above which 95% of the samples fall — for a small n,
    that is an actual sample, not an interpolation, and it cannot be computed
    from a mean and a standard deviation at all. Write the sorted-index version
    so the number always corresponds to a request somebody actually made.

TODO: implement (records are stage 1's rows, plus the fields below)

    rate(records, predicate) -> float          fraction where predicate is True
    refusal_rate(records) -> float
        A row is a refusal when its "output" is empty or matches a refusal
        phrase ("I can't", "I cannot", "I'm unable", "as an AI", "sorry, but")
        case-insensitively. Substring matching is crude on purpose: it is the
        cheap signal, and the check wants the crude version's failure modes
        visible rather than hidden behind a classifier.
        The denominator is the NON-ERRORED rows: an error is not a refusal, and
        counting a timeout as a refusal makes both numbers lie (a flaky
        endpoint then looks like a cautious model). 0.0 when there are none.

    latency_summary(records) -> dict
        {"n", "mean", "p50", "p95", "max"} over the "latency_ms" field.
        p50/p95 are the nearest-rank values from the sorted samples (no
        interpolation), p95 = the sample at index ceil(0.95 * n) - 1.

    token_summary(records) -> dict
        {"prompt": int, "output": int} — the totals over
        "prompt_tokens"/"output_tokens"; a missing field counts as 0.

    operational_report(records) -> dict
        {"n", "error_rate", "refusal_rate", "latency", "tokens"}, where a row
        counts as an error when it carries a non-empty "error" field. An
        errored row still contributes to the latencies (it was a real request)
        but never to the refusal rate: an error is not a refusal, and folding
        them together makes both numbers lie.
"""


def rate(records, predicate):
    raise NotImplementedError("stage 2: implement rate()")


def refusal_rate(records):
    raise NotImplementedError("stage 2: implement refusal_rate()")


def latency_summary(records):
    raise NotImplementedError("stage 2: implement latency_summary()")


def token_summary(records):
    raise NotImplementedError("stage 2: implement token_summary()")


def operational_report(records):
    raise NotImplementedError("stage 2: implement operational_report()")

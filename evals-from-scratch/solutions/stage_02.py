"""Evals From Scratch — stage 2: the numbers that are not about quality

SOLUTION. Three rates and two distributions, all of them counted over the rows
they are actually about: refusals over the rows that ran, latency and tokens
over every row including the failures. The distinction is the whole stage.
"""

import math

REFUSAL_PHRASES = ("i can't", "i cannot", "i'm unable", "i am unable",
                   "as an ai", "sorry, but")


def _errored(row):
    return row.get("error") is not None


def _refusal(row):
    if _errored(row):
        return False
    text = (row.get("output") or "").strip().lower()
    if not text:
        return True
    return any(phrase in text for phrase in REFUSAL_PHRASES)


def rate(records, predicate):
    records = list(records)
    if not records:
        return 0.0
    return sum(1 for row in records if predicate(row)) / len(records)


def refusal_rate(records):
    live = [row for row in records if not _errored(row)]
    if not live:
        return 0.0
    return sum(1 for row in live if _refusal(row)) / len(live)


def latency_summary(records):
    values = sorted(row["latency_ms"] for row in records)
    if not values:
        return {"n": 0, "mean": 0.0, "max": 0.0, "p50": 0.0, "p95": 0.0}

    def nearest_rank(p):
        index = math.ceil(p * len(values)) - 1
        return float(values[max(0, min(index, len(values) - 1))])

    return {"n": len(values),
            "mean": sum(values) / len(values),
            "max": float(values[-1]),
            "p50": nearest_rank(0.50),
            "p95": nearest_rank(0.95)}


def token_summary(records):
    return {"prompt": sum(int(row.get("prompt_tokens") or 0) for row in records),
            "output": sum(int(row.get("output_tokens") or 0) for row in records)}


def operational_report(records):
    records = list(records)
    return {"n": len(records),
            "error_rate": rate(records, _errored),
            "refusal_rate": refusal_rate(records),
            "latency": latency_summary(records),
            "tokens": token_summary(records)}

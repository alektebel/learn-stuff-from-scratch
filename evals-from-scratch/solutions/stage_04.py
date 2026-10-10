"""Evals From Scratch — stage 4: exact match and token F1

SOLUTION. One normaliser, applied to both sides, in one place; an overlap
counted as a multiset; and two corpus aggregations that answer two different
questions. The `pairs` API takes (prediction, gold) — the order is only a
convention, but it is the convention.
"""

import re
from collections import Counter

ARTICLES = {"a", "an", "the"}
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def _tokens(text):
    if not text:
        return []
    return [word for word in WORD.findall(text.lower())
            if word not in ARTICLES]


def normalize(text):
    return " ".join(_tokens(text))


def exact_match(pred, gold):
    return normalize(pred) == normalize(gold)


def token_f1(pred, gold):
    predicted = Counter(_tokens(pred))
    expected = Counter(_tokens(gold))
    if not predicted or not expected:
        return 0.0
    overlap = sum((predicted & expected).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(predicted.values())
    recall = overlap / sum(expected.values())
    return 2 * precision * recall / (precision + recall)


def corpus_f1(pairs):
    pairs = list(pairs)
    if not pairs:
        return 0.0
    overlap = predicted_total = expected_total = 0
    for pred, gold in pairs:
        predicted = Counter(_tokens(pred))
        expected = Counter(_tokens(gold))
        overlap += sum((predicted & expected).values())
        predicted_total += sum(predicted.values())
        expected_total += sum(expected.values())
    if not predicted_total or not expected_total or not overlap:
        return 0.0
    precision = overlap / predicted_total
    recall = overlap / expected_total
    return 2 * precision * recall / (precision + recall)


def mean_f1(pairs):
    pairs = list(pairs)
    if not pairs:
        return 0.0
    return sum(token_f1(pred, gold) for pred, gold in pairs) / len(pairs)

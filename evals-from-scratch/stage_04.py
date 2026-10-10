"""Evals From Scratch — stage 4: exact match and token F1

DESIGN DECISION — normalise both sides, or measure the wrong thing.
    SQuAD's normalisation — lowercase, drop articles, strip punctuation,
    collapse whitespace — exists because "The Cat." and "cat" are the same
    answer. Applying it to the prediction and not the gold (or the reverse)
    produces a metric that punishes the model for the test set's formatting,
    and it is invisible in the score: the number is plausible either way.

DESIGN DECISION — corpus F1 is computed over pooled counts, not by averaging F1s.
    The mean of per-example F1s weights a one-token answer exactly as much as a
    twenty-token one. The pooled version (total overlap / total predicted and
    total gold tokens) is the number a corpus-level claim is about. They are
    different numbers; report both if you like, but know which one you mean.

TODO: implement

    normalize(text) -> str
        Lowercase; remove punctuation (keep alphanumerics and whitespace);
        drop the articles a / an / the as whole words; collapse whitespace;
        strip. Applied to predictions and golds alike, always.

    exact_match(pred, gold) -> bool        after normalisation, equality

    token_f1(pred, gold) -> float
        Multiset overlap of normalised tokens:
            precision = overlap / len(pred_tokens)
            recall    = overlap / len(gold_tokens)
            f1        = 2 * p * r / (p + r)
        An empty prediction or an empty gold scores 0.0 — an empty answer is
        not a perfect answer, and 0/0 must never be silently 1.0.

    corpus_f1(pairs) -> float
        `pairs` is an iterable of (pred, gold). Pooled: sum the overlaps, sum
        the predicted tokens, sum the gold tokens, then one precision, one
        recall, one F1. A pair with no tokens on either side contributes
        nothing and must not divide by zero.

    mean_f1(pairs) -> float
        The arithmetic mean of the per-pair token_f1 (for contrast: the same
        data, the other average).
"""


def normalize(text):
    raise NotImplementedError("stage 4: implement normalize()")


def exact_match(pred, gold):
    raise NotImplementedError("stage 4: implement exact_match()")


def token_f1(pred, gold):
    raise NotImplementedError("stage 4: implement token_f1()")


def corpus_f1(pairs):
    raise NotImplementedError("stage 4: implement corpus_f1()")


def mean_f1(pairs):
    raise NotImplementedError("stage 4: implement mean_f1()")

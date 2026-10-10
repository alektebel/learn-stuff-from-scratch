"""Evals From Scratch — stage 8: is the difference real?

SOLUTION. The exact binomial for the discordant pairs, and a bootstrap that
resamples the ROW INDEX and reads both systems at that index. That one line —
`diffs[i]` instead of two independent draws — is the difference between the
interval that finds a real five-point win and the interval that finds nothing.
"""

import random
from math import comb


def binom_two_sided(k, n):
    n = int(n)
    if n <= 0:
        return 1.0
    k = max(0, min(int(k), n))
    lower = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    upper = sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * min(lower, upper))


def _paired(a, b):
    a, b = list(a), list(b)
    if len(a) != len(b):
        raise ValueError(
            f"{len(a)} rows for one system against {len(b)} for the other: a "
            f"paired test needs the same items")
    return a, b


def mcnemar(a, b):
    a, b = _paired(a, b)
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    b_only = sum(1 for x, y in zip(a, b) if y and not x)
    return {"a_only": a_only, "b_only": b_only,
            "p": binom_two_sided(a_only, a_only + b_only)}


def _percentile(samples, alpha):
    samples.sort()
    n = len(samples)
    lo = samples[max(0, int(alpha / 2 * n))]
    hi = samples[min(n - 1, int((1 - alpha / 2) * n) - 1)]
    return lo, hi


def paired_bootstrap(a, b, seed=0, n=2000, alpha=0.05):
    a, b = _paired(a, b)
    if not a:
        raise ValueError("no paired rows: there is no interval to compute")
    diffs = [float(x) - float(y) for x, y in zip(a, b)]
    size = len(diffs)
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        total = 0.0
        for _ in range(size):
            total += diffs[rng.randrange(size)]
        samples.append(total / size)
    lo, hi = _percentile(samples, alpha)
    return {"mean_diff": sum(diffs) / size, "lo": lo, "hi": hi, "n": size}


def independent_ci(a, b, seed=0, n=2000, alpha=0.05):
    a, b = list(a), list(b)
    if not a or not b:
        raise ValueError("both runs need rows to resample")
    rng = random.Random(seed)
    na, nb = len(a), len(b)
    samples = []
    for _ in range(n):
        left = sum(a[rng.randrange(na)] for _ in range(na)) / na
        right = sum(b[rng.randrange(nb)] for _ in range(nb)) / nb
        samples.append(float(left) - float(right))
    lo, hi = _percentile(samples, alpha)
    return {"mean_diff": sum(a) / na - sum(b) / nb, "lo": lo, "hi": hi, "n": na}


def decide(a, b, alpha=0.05, seed=0):
    ci = paired_bootstrap(a, b, seed=seed, alpha=alpha)
    if ci["lo"] > 0:
        return "a"
    if ci["hi"] < 0:
        return "b"
    return "inconclusive"

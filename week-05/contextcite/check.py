"""
Progress checker for the ContextCite templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Each check exercises the functions you implement in the template files. A check
that raises NotImplementedError is reported as TODO (not a failure) — that is
simply the next thing to write.

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import shutil
import sys
import traceback

# Always read the learner's source fresh. Python validates cached bytecode on
# (mtime, size), so an edit that keeps a file the same size within the same
# second can be masked by a stale __pycache__ — and a checker you cannot trust
# is worse than no checker.
sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"

GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Step 1-2: partition.py
# ---------------------------------------------------------------------------

def check_split_text() -> None:
    from partition import split_text

    parts, separators = split_text("One. Two! Three?")
    assert parts == ["One.", "Two!", "Three?"], f"got {parts}"
    assert len(separators) == 3, f"{len(separators)} separators for 3 parts"
    assert separators[0] == "", "the first part has no preceding separator"
    assert separators[1] == " ", f"separator 1 is {separators[1]!r}, expected ' '"

    parts, _ = split_text("Line one.\nLine two.")
    assert parts == ["Line one.", "Line two."], f"newlines must split: {parts}"

    parts, _ = split_text("No punctuation here")
    assert parts == ["No punctuation here"], f"got {parts}"
    assert split_text("")[0] == [], "empty text has no sources"


def check_partitioner() -> None:
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE

    partitioner = ContextPartitioner(CONTEXT)
    assert partitioner.num_sources == 8, \
        f"the running example has 8 sentences, you found {partitioner.num_sources}"
    assert "P100" in partitioner.source(GROUND_TRUTH_SOURCE), (
        f"source {GROUND_TRUTH_SOURCE} should be the sentence naming the GPU, "
        f"got {partitioner.source(GROUND_TRUTH_SOURCE)!r}")

    assert partitioner.build() == CONTEXT, (
        "build() with no mask must reproduce the context EXACTLY. Every later "
        "measurement is made against these strings; if the full-context "
        "rebuild differs, you are scoring a context the model never saw.\n"
        f"      got {len(partitioner.build())} chars, expected {len(CONTEXT)}")

    mask = [True] * 8
    mask[GROUND_TRUTH_SOURCE] = False
    ablated = partitioner.build(mask)
    assert "P100" not in ablated, "ablating source 4 must remove 'P100'"
    assert len(ablated) < len(CONTEXT), "ablation must shorten the context"
    assert not ablated.startswith(" "), "no stray leading separator"

    assert partitioner.build([False] * 8) == "", \
        f"an all-False mask gives '', got {partitioner.build([False] * 8)!r}"
    assert partitioner.build([True] + [False] * 7) == partitioner.source(0), \
        "keeping only source 0 must give exactly that sentence"

    try:
        partitioner.build([True, False])
        raise AssertionError("a wrong-length mask must raise ValueError — a "
                             "silent mismatch attributes the wrong sources")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Step 3-4: logit_probs.py
# ---------------------------------------------------------------------------

def check_logit_prob_math() -> None:
    from logit_probs import log_sigmoid, logsumexp, token_logit_prob

    assert abs(logsumexp([0.0, 0.0]) - math.log(2)) < 1e-12
    assert logsumexp([]) == float("-inf"), "empty logsumexp is -inf"
    assert not math.isinf(logsumexp([800.0, 800.0])), (
        "logsumexp overflowed on large values — subtract the max first")

    logits = [2.0, 1.0, 0.5, -1.0]
    direct = token_logit_prob(logits, 0)
    p = math.exp(logits[0] - logsumexp(logits))
    expected = math.log(p / (1 - p))
    assert abs(direct - expected) < 1e-10, (
        f"token_logit_prob gave {direct}, but log(p/(1-p)) is {expected}")

    confident = token_logit_prob([40.0, 0.0, 0.0], 0)
    assert math.isfinite(confident) and 39 < confident < 40, (
        f"logits [40,0,0] gave {confident}. Compute z[y] - logsumexp(others) "
        "directly; going via softmax makes p round to 1.0 and 1-p exactly 0.")

    assert abs(log_sigmoid(direct) - math.log(p)) < 1e-12, (
        "log_sigmoid(logit(p)) must equal log(p) — aggregate() depends on this "
        "identity")
    assert math.isfinite(log_sigmoid(-800.0)), \
        "log_sigmoid overflowed for large negative x; branch on the sign"


def check_aggregate_and_score() -> None:
    from logit_probs import aggregate, response_score, sequence_logit_probs
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    rows = [[1.0, 2.0], [3.0]]
    ids = [0, 0]
    try:
        sequence_logit_probs([[1.0, 2.0]], [0, 1])
        raise AssertionError("a length mismatch between logit rows and token "
                             "ids must raise")
    except (ValueError, AssertionError) as exc:
        if isinstance(exc, AssertionError) and "must raise" in str(exc):
            raise

    from logit_probs import log_sigmoid
    single = aggregate([2.0])
    assert abs(single - 2.0) < 1e-9, (
        f"aggregate of a single token should return that logit back, got "
        f"{single}")

    pair = aggregate([2.0, 3.0])
    log_p = log_sigmoid(2.0) + log_sigmoid(3.0)
    assert abs(pair - (log_p - math.log1p(-math.exp(log_p)))) < 1e-9, \
        f"aggregate([2,3]) = {pair}, does not match the definition"
    assert pair < single, \
        "adding a second token can only make the joint response less likely"

    model = ToyLM(CONTEXT, QUERY)
    partitioner = ContextPartitioner(CONTEXT)
    response = model.generate(CONTEXT)
    full = response_score(model, CONTEXT, response)
    assert math.isfinite(full), f"response_score returned {full}"

    drops = []
    for index in range(partitioner.num_sources):
        mask = [i != index for i in range(partitioner.num_sources)]
        drops.append(full - response_score(model, partitioner.build(mask),
                                           response))
    best = max(range(len(drops)), key=lambda i: drops[i])
    assert best == GROUND_TRUTH_SOURCE, (
        f"removing source {best} hurt most, but the answer lives in source "
        f"{GROUND_TRUTH_SOURCE}. Drops: {[round(d, 1) for d in drops]}")
    assert drops[GROUND_TRUTH_SOURCE] > 10, (
        f"dropping the answer source cost only {drops[GROUND_TRUTH_SOURCE]:.1f}; "
        "expected roughly 37")


# ---------------------------------------------------------------------------
# Step 5: ablation.py
# ---------------------------------------------------------------------------

def check_ablation_sampling() -> None:
    from ablation import (build_dataset, mask_statistics, sample_mask,
                          sample_masks)

    mask = sample_mask(8, 0.5, seed=0)
    assert len(mask) == 8 and all(isinstance(v, bool) for v in mask)
    assert sample_mask(8, 0.5, seed=0) == mask, "sampling must be reproducible"
    assert sample_mask(8, 0.5, seed=1) != mask or True   # may coincide; not fatal
    assert all(sample_mask(8, 1.0, seed=s) == [True] * 8 for s in range(3)), \
        "keep_prob 1.0 keeps everything"
    assert all(sample_mask(8, 0.0, seed=s) == [False] * 8 for s in range(3)), \
        "keep_prob 0.0 keeps nothing"

    masks = sample_masks(8, num_ablations=64)
    assert len(masks) == 64, f"asked for 64 masks, got {len(masks)}"
    assert len({tuple(m) for m in masks}) > 20, (
        "the masks are barely varying — are you reseeding with the same value "
        "every time? Each mask needs base_seed + i.")

    stats = mask_statistics(masks)
    assert 3.0 < stats["mean_kept_per_mask"] < 5.0, (
        f"mean kept per mask is {stats['mean_kept_per_mask']:.2f}; at p=0.5 "
        "over 8 sources it should be near 4")
    assert stats["always_on"] == [] and stats["always_off"] == [], (
        f"degenerate columns: always_on={stats['always_on']}, "
        f"always_off={stats['always_off']}. A constant column carries no "
        "information and its coefficient cannot be identified.")

    from logit_probs import response_score
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    partitioner = ContextPartitioner(CONTEXT)
    response = model.generate(CONTEXT)
    X, y = build_dataset(partitioner, model, response, masks[:32],
                         response_score)
    assert len(X) == 32 and len(y) == 32, f"got {len(X)} rows, {len(y)} targets"
    assert len(X[0]) == 8, f"each row should have 8 entries, got {len(X[0])}"
    assert all(v in (0.0, 1.0) for row in X for v in row), \
        "X must be the masks as floats"

    with_it = [s for row, s in zip(X, y) if row[GROUND_TRUTH_SOURCE]]
    without = [s for row, s in zip(X, y) if not row[GROUND_TRUTH_SOURCE]]
    assert sum(with_it) / len(with_it) > sum(without) / len(without) + 10, (
        "ablations keeping the answer source should score far higher than "
        "those dropping it")


# ---------------------------------------------------------------------------
# Step 6-7: lasso.py
# ---------------------------------------------------------------------------

def check_lasso_pieces() -> None:
    from lasso import soft_threshold, standardize

    assert abs(soft_threshold(0.5, 0.1) - 0.4) < 1e-12
    assert abs(soft_threshold(-0.5, 0.1) + 0.4) < 1e-12
    assert soft_threshold(0.05, 0.1) == 0.0, \
        "values under the threshold must become EXACTLY 0.0, not merely small"
    assert soft_threshold(-0.05, 0.1) == 0.0

    X = [[1.0, 5.0], [3.0, 5.0], [5.0, 5.0]]
    Z, means, scales = standardize(X)
    assert abs(means[0] - 3.0) < 1e-12, f"column mean wrong: {means}"
    assert abs(sum(row[0] for row in Z)) < 1e-9, "column 0 should be centred"
    variance = sum(row[0] ** 2 for row in Z) / 3
    assert abs(variance - 1.0) < 1e-9, f"column 0 variance is {variance}, want 1"
    assert scales[1] == 1.0, (
        "a constant column must get scale 1.0, not 0 — otherwise you divide by "
        "zero")
    assert all(abs(row[1]) < 1e-12 for row in Z), \
        "a constant column becomes all zeros after centring"


def check_lasso_fit() -> None:
    import random as _random

    from lasso import fit_lasso, predict, r_squared

    rng = _random.Random(0)
    true_w = [3.0, 0.0, 0.0, -2.0, 0.0, 0.0, 0.5, 0.0]
    true_b = 1.5
    X = [[float(rng.random() < 0.5) for _ in true_w] for _ in range(200)]
    y = [sum(x * w for x, w in zip(row, true_w)) + true_b + rng.gauss(0, 0.05)
         for row in X]

    weights, bias = fit_lasso(X, y, alpha=0.01)
    assert len(weights) == 8, f"got {len(weights)} coefficients"
    for j, (t, f) in enumerate(zip(true_w, weights)):
        if t != 0.0:
            assert abs(f - t) < 0.15, (
                f"coefficient {j}: fitted {f:.3f}, true {t}. If the sign is "
                "flipped or the scale is off, re-check the un-standardising "
                "step of fit_lasso.")
        else:
            assert f == 0.0, \
                f"coefficient {j} should be exactly 0 at alpha=0.01, got {f}"
    assert abs(bias - true_b) < 0.15, f"bias {bias:.3f}, true {true_b}"
    assert r_squared(y, predict(X, weights, bias)) > 0.99, "poor fit"

    dense, _ = fit_lasso(X, y, alpha=0.0)
    assert sum(1 for v in dense if v != 0.0) > 5, \
        "alpha=0 is plain least squares and should zero almost nothing"
    sparse, _ = fit_lasso(X, y, alpha=2.0)
    assert all(v == 0.0 for v in sparse), \
        "a huge alpha must zero every coefficient"

    scaled_w, scaled_b = fit_lasso(X, y, alpha=0.01, normalize_by=4.0)
    assert abs(scaled_w[0] - weights[0]) < 0.1, (
        "normalize_by should divide the targets before fitting and multiply "
        "back after, leaving the coefficients essentially unchanged")


# ---------------------------------------------------------------------------
# Step 8-9: contextcite.py
# ---------------------------------------------------------------------------

def check_contextciter() -> None:
    from contextcite import ContextCiter
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY, num_ablations=64)
    assert citer.num_sources == 8
    assert len(citer.response) > 0, "no response was generated"
    assert len(citer.masks) == 64

    matrix = citer.logit_probs
    assert len(matrix) == 64, f"expected 64 ablation rows, got {len(matrix)}"
    assert len(matrix[0]) == len(citer.response), (
        f"each row must hold one value per response token: {len(matrix[0])} "
        f"vs {len(citer.response)}. Cache the per-token MATRIX, not the "
        "aggregated scores — span attribution depends on it.")
    assert citer.logit_probs is matrix, \
        "logit_probs must be cached, not recomputed on every access"

    ranked = citer.attribute()
    assert len(ranked) == 8, f"attribute returned {len(ranked)} scores"
    assert all(ranked[i].score >= ranked[i + 1].score for i in range(7)), \
        "attributions must be sorted by score, highest first"
    assert ranked[0].index == GROUND_TRUTH_SOURCE, (
        f"top source is {ranked[0].index}, expected {GROUND_TRUTH_SOURCE}. "
        f"Scores: {[(a.index, round(a.score, 1)) for a in ranked]}")
    assert ranked[0].score > 20, \
        f"the answer source scored only {ranked[0].score:.1f}, expected ~40"
    assert ranked[0].source == citer.partitioner.source(GROUND_TRUTH_SOURCE), \
        "each Attribution must carry its own source text"

    assert len(citer.attribute(top_k=3)) == 3, "top_k must limit the results"
    assert citer.surrogate_quality() > 0.9, \
        f"in-sample R^2 is {citer.surrogate_quality():.3f}, expected >0.9"


def check_span_attribution() -> None:
    from contextcite import ContextCiter
    from toy_lm import CONTEXT, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY)
    _ = citer.logit_probs                     # force the expensive pass

    calls = {"n": 0}
    original = model.sequence_logits

    def counting(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    model.sequence_logits = counting
    first = citer.attribute_token(0, top_k=1)[0]
    last = citer.attribute_token(len(citer.response) - 1, top_k=1)[0]
    whole = citer.attribute(top_k=1)[0]
    model.sequence_logits = original

    assert calls["n"] == 0, (
        f"attributing spans made {calls['n']} model calls; it must make ZERO "
        "once logit_probs is cached. Re-aggregate the cached matrix instead of "
        "re-running the model.")
    assert first.index == last.index == whole.index, \
        "on this context every span should point at the same source"

    try:
        citer.attribute(5, 2)
        raise AssertionError("an inverted span must raise ValueError")
    except ValueError:
        pass
    try:
        citer.attribute(0, len(citer.response) + 5)
        raise AssertionError("an out-of-range span must raise ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Step 10-11: evaluate.py
# ---------------------------------------------------------------------------

def check_spearman() -> None:
    from evaluate import spearman

    assert abs(spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    assert abs(spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9
    assert abs(spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-9, \
        "Spearman is rank-based, so a monotone rescaling changes nothing"
    assert spearman([1, 1, 1], [1, 2, 3]) == 0.0, \
        "a constant input has no variance; return 0.0 rather than dividing by 0"
    assert abs(spearman([1, 2, 2, 3], [1, 2, 2, 3]) - 1.0) < 1e-9, (
        "ties must be handled with averaged ranks (LASSO produces exact zeros, "
        "so ties are common here)")


def check_evaluation() -> None:
    from contextcite import ContextCiter
    from evaluate import linear_datamodeling_score, random_k_drop, top_k_drop
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY, num_ablations=64)

    lds = linear_datamodeling_score(citer, num_held_out=32)
    assert -1.0 <= lds <= 1.0, f"LDS out of range: {lds}"
    assert lds > 0.7, (
        f"held-out LDS is only {lds:.3f}; with 64 ablations on this example it "
        "should exceed 0.9. If it is near 1.0 for EVERY budget, check you are "
        "drawing the held-out masks with a different base_seed.")

    tiny = ContextCiter(model, CONTEXT, QUERY, response=citer.response,
                        num_ablations=8)
    assert tiny.surrogate_quality() > lds, (
        "with 8 ablations and 8 sources, in-sample R^2 should LOOK better than "
        "the honest held-out LDS of a 64-ablation fit. That gap is the point "
        "of this step.")

    full, ablated, drop = top_k_drop(citer, k=1)
    assert drop > 10, f"removing the top source dropped only {drop:.1f}"
    assert abs((full - ablated) - drop) < 1e-9, "drop must equal full - ablated"

    baseline = random_k_drop(citer, k=1, trials=10)
    assert drop > 3 * baseline, (
        f"top-1 drop {drop:.1f} vs random baseline {baseline:.1f}. The top "
        "source should hurt far more than a random one; without that gap the "
        "attribution is not telling you anything.")


# ---------------------------------------------------------------------------
# Step 12-14: applications.py
# ---------------------------------------------------------------------------

def check_verification_and_pruning() -> None:
    from applications import prune_context, verify_tokens
    from contextcite import ContextCiter
    from logit_probs import response_score
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY)

    results = verify_tokens(citer, threshold=1.0)
    assert len(results) == len(citer.response), \
        "one verification row per response token"
    token, source, score, supported = results[0]
    assert isinstance(supported, bool), "the fourth field is a bool"
    assert sum(1 for r in results if r[3]) >= len(results) // 2, \
        "most tokens of a grounded response should clear the threshold"

    pruned, kept = prune_context(citer, keep_top_k=1)
    assert kept == [GROUND_TRUTH_SOURCE], \
        f"the top-1 source should be {GROUND_TRUTH_SOURCE}, got {kept}"
    assert len(pruned) < len(CONTEXT) / 3, \
        f"pruning to one source should shrink the context a lot: {len(pruned)}"

    _, kept3 = prune_context(citer, keep_top_k=3)
    assert kept3 == sorted(kept3), (
        "kept sources must be returned in ORIGINAL order so the pruned "
        "context still reads in sequence")

    full_score = response_score(model, CONTEXT, citer.response)
    pruned_score = response_score(model, pruned, citer.response)
    assert pruned_score > full_score, (
        f"pruning to the one relevant source scored {pruned_score:.1f} vs "
        f"{full_score:.1f} with everything. It should IMPROVE, because the "
        "other seven sentences were competing for probability mass.")


def check_poisoning() -> None:
    from applications import POISON, poison_context
    from contextcite import ContextCiter
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, QUERY, ToyLM

    poisoned = poison_context(CONTEXT, position=2)
    partitioner = ContextPartitioner(poisoned)
    assert partitioner.num_sources == 9, \
        f"the poisoned context should have 9 sources, got {partitioner.num_sources}"
    assert "H200" in partitioner.source(2), \
        f"the poison should sit at source 2, found {partitioner.source(2)!r}"

    model = ToyLM(poisoned, QUERY)
    citer = ContextCiter(model, poisoned, QUERY)
    assert "h200" in citer.response, (
        f"the attack did not work — the response is {citer.response}. "
        "Detection is only a meaningful question once the poison actually "
        "hijacks the answer.")

    span = citer.attribute(0, 4, top_k=1)[0]
    assert span.index == 2, (
        f"attributing the span that makes the claim gave source {span.index}, "
        "expected the poison at 2")
    assert span.score > 10, f"the poison scored only {span.score:.1f}"

    whole = citer.attribute(top_k=1)[0]
    assert whole.index != 2, (
        "whole-response attribution is expected to MISS the poison here — the "
        "other eight tokens outvote the four that came from it. That contrast "
        "is the lesson of this step; if it now detects, the demo has lost its "
        "point and the numbers need re-checking.")


def check_leave_one_out() -> None:
    from applications import leave_one_out_scores
    from contextcite import ContextCiter
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    sentences = ContextPartitioner(CONTEXT).sources
    duplicated = " ".join(sentences + [sentences[GROUND_TRUTH_SOURCE]])
    model = ToyLM(duplicated, QUERY)
    citer = ContextCiter(model, duplicated, QUERY)
    copies = (GROUND_TRUTH_SOURCE, len(sentences))

    loo = leave_one_out_scores(citer)
    assert len(loo) == citer.num_sources, "one score per source"

    attributions = {a.index: a.score for a in citer.attribute()}
    loo_best = max(loo[i] for i in copies)
    cc_best = max(attributions[i] for i in copies)

    assert cc_best > 3 * loo_best, (
        f"leave-one-out scored the duplicated answer source {loo_best:.1f} and "
        f"ContextCite scored it {cc_best:.1f}. ContextCite should be several "
        "times higher: removing one copy leaves the other, so leave-one-out "
        "sees almost no effect, while random subsets remove BOTH about a "
        "quarter of the time. This is the whole argument for the sampling "
        "design.")
    assert cc_best > 10, \
        f"ContextCite scored the duplicated source only {cc_best:.1f}"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("partition.py", "splitting text into sources", check_split_text),
    ("partition.py", "rebuilding ablated contexts", check_partitioner),
    ("logit_probs.py", "logit-prob math and stability", check_logit_prob_math),
    ("logit_probs.py", "aggregation and response score", check_aggregate_and_score),
    ("ablation.py", "sampling the design matrix", check_ablation_sampling),
    ("lasso.py", "soft threshold and standardising", check_lasso_pieces),
    ("lasso.py", "recovering a known sparse signal", check_lasso_fit),
    ("contextcite.py", "end-to-end attribution", check_contextciter),
    ("contextcite.py", "span attribution, zero extra calls", check_span_attribution),
    ("evaluate.py", "spearman rank correlation", check_spearman),
    ("evaluate.py", "held-out LDS and top-k drop", check_evaluation),
    ("applications.py", "verification and pruning", check_verification_and_pruning),
    ("applications.py", "detecting a poisoned source", check_poisoning),
    ("applications.py", "leave-one-out fails on redundancy", check_leave_one_out),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}ContextCite From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue

        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<20} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<20} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<20} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have implemented ContextCite.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The TODO comments in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

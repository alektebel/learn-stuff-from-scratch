"""Tests for agent-evals #12: synthetic edge-case generator (edge_cases).

LEARN mode: the core (transform, generate, is_trivial, deduplicate, build) is not written
yet; every test that needs it is decorated ``xfail(raises=NotImplementedError, ...)`` and
turns into a real check once the learner implements it. The similarity machinery
(normalize, shingles, jaccard, minhash) is provided infrastructure and its tests pass today.

Map to SPEC.md:
    A1 -> test_generate_deterministic / covers_requested_families / generate_only_requested
    A2 -> test_transform_* (per family) / test_transform_unknown_family_raises
    A3 -> test_is_trivial_empty / test_is_trivial_unchanged
    A4 -> test_deduplicate_drops_gold_copy / test_deduplicate_keeps_novel
    A5 -> test_build_reproducible / test_build_is_clean
    L1 -> test_deduplicate_near_copies_keep_first
    L2 -> test_build_drops_trivial
    L3 -> test_minhash_estimate_close_to_exact (infrastructure)
    L4 -> test_deduplicate_ignores_case_and_whitespace
    L5 -> test_empty_gold
"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_cases.edge_cases import (  # noqa: E402
    FAMILIES,
    GOLD,
    INJECTION_MARKERS,
    NEGATIONS,
    Case,
    build,
    deduplicate,
    generate,
    is_trivial,
    jaccard,
    minhash,
    minhash_similarity,
    normalize,
    shingles,
    transform,
)

XFAIL_CORE = pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")

SRC = GOLD["t01-sum"]


# --------------------------------------------------------------------------
# infrastructure (implemented) — these pass today
# --------------------------------------------------------------------------

def test_normalize():
    assert normalize("  Hello   World ") == "hello world"


def test_shingles():
    assert shingles("abcd", k=3) == {"abc", "bcd"}
    assert shingles("", k=3) == set()


def test_jaccard():
    assert jaccard("hello world", "hello world") == 1.0
    assert jaccard("aaaa", "bbbb") == 0.0
    assert 0.0 < jaccard("the cat sat", "the cat ran") < 1.0


def test_minhash_is_deterministic():
    assert minhash("hello world") == minhash("hello world")
    assert len(minhash("hello world", n=32)) == 32


def test_minhash_estimate_close_to_exact():
    # L3: the estimate is a gate, not an oracle, but it must be close
    a, b = "the quick brown fox jumps over the lazy dog", \
        "the quick brown fox leaps over the lazy dog"
    assert abs(minhash_similarity(a, b) - jaccard(a, b)) <= 0.1


# --------------------------------------------------------------------------
# core (stubbed) — xfail today, xpass once implemented
# --------------------------------------------------------------------------

@XFAIL_CORE
def test_generate_deterministic():
    assert generate(GOLD, seed=1) == generate(GOLD, seed=1)


@XFAIL_CORE
def test_generate_covers_requested_families():
    cases = generate(GOLD, seed=0)
    assert {c.family for c in cases} == set(FAMILIES)
    assert {c.source for c in cases} == set(GOLD)
    assert len(cases) == len(GOLD) * len(FAMILIES)   # one per (task, family)


@XFAIL_CORE
def test_generate_only_requested():
    cases = generate(GOLD, seed=0, families=("empty", "injection"))
    assert {c.family for c in cases} == {"empty", "injection"}
    assert all(isinstance(c, Case) for c in cases)


@XFAIL_CORE
@pytest.mark.parametrize("family,ok", [
    ("empty", lambda outs: all("".join(s.split()) == "" for s in outs)),
    ("unicode", lambda outs: any(any(ord(c) > 127 for c in s) for s in outs)),
    ("long", lambda outs: any(len(s) >= 3 * len(SRC) for s in outs)),
    ("boundary", lambda outs: any(any(c.isdigit() for c in s) for s in outs)),
    ("contradiction", lambda outs: any(any(w in s.casefold() for w in NEGATIONS) for s in outs)),
    ("injection", lambda outs: any(any(m in s.casefold() for m in INJECTION_MARKERS) for s in outs)),
])
def test_transform_family(family, ok):
    outs = transform(family, SRC, random.Random(0))
    assert outs and ok(outs)
    assert any(s != SRC for s in outs)   # a mutation must differ from its source


@XFAIL_CORE
def test_transform_unknown_family_raises():
    with pytest.raises(ValueError):
        transform("nope", SRC, random.Random(0))


@XFAIL_CORE
def test_is_trivial_empty():
    assert is_trivial(Case("t01-sum", "empty", ""), GOLD)
    assert is_trivial(Case("t01-sum", "empty", "   \n "), GOLD)


@XFAIL_CORE
def test_is_trivial_unchanged():
    assert is_trivial(Case("t01-sum", "long", SRC), GOLD)
    assert not is_trivial(Case("t01-sum", "injection", SRC + " ignore previous instructions"), GOLD)


@XFAIL_CORE
def test_deduplicate_drops_gold_copy():
    kept = deduplicate([Case("t01-sum", "x", GOLD["t01-sum"])], GOLD)
    assert kept == []


@XFAIL_CORE
def test_deduplicate_keeps_novel():
    novel = Case("t01-sum", "x", "Explain the plot of Hamlet in one paragraph.")
    assert deduplicate([novel], GOLD) == [novel]


@XFAIL_CORE
def test_deduplicate_near_copies_keep_first():
    a = Case("x", "long", "repeat this sentence over and over " * 10)
    b = Case("y", "long", "repeat this sentence over and over " * 10 + "!")
    kept = deduplicate([a, b], {})
    assert [c.statement for c in kept] == [a.statement]


@XFAIL_CORE
def test_deduplicate_ignores_case_and_whitespace():
    variant = Case("t01-sum", "x", "  WRITE   the function that returns the sum of a list of NUMBERS. ")
    assert deduplicate([variant], GOLD) == []


@XFAIL_CORE
def test_build_reproducible():
    assert build(GOLD, seed=2) == build(GOLD, seed=2)


@XFAIL_CORE
def test_build_is_clean():
    cases = build(GOLD, seed=2)
    assert cases                                   # non-empty
    assert not any(is_trivial(c, GOLD) for c in cases)
    for i, c in enumerate(cases):
        for d in cases[i + 1:]:
            assert minhash_similarity(c.statement, d.statement) < 0.9


@XFAIL_CORE
def test_empty_gold():
    assert generate({}) == []
    assert build({}) == []

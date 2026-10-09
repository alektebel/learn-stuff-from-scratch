"""Tests for the contamination module (LEARN mode).

Tests of the shipped infrastructure (``jaccard``, the interface contract)
pass right now. Every test that calls a core stub is decorated

    @pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")

so it xfails while the core is unwritten, passes once it is written
correctly, and fails loudly if it is written wrongly. Deliberately not
strict. Standard library only; every random source is seeded.
"""

from __future__ import annotations

import inspect
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from contamination import contamination as c  # noqa: E402

XFAIL = pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")

# --- fixed fixtures (hand-written, deterministic) -------------------------
# LONG_A / PARAPHRASE: same meaning, disjoint 13-grams, Jaccard ~ 0.13.
LONG_A = (
    "the quick brown fox jumps over the lazy dog near the river bank "
    "every single morning without fail"
)
PARAPHRASE = (
    "each dawn the brown fox leaps across the sleepy dog beside that "
    "riverbank daily and never once misses it"
)
UNRELATED = (
    "completely unrelated filler about ceramic mugs and their long history "
    "through the porcelain trade routes"
)
UNIQ = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi"
# Exactly 13 tokens: its single 13-gram is shared by any copy of it.
SHARED13 = (
    "the model memorised this exact unusual sentence about a large brass "
    "teapot collection"
)
BOILER12 = "please first check the original source before quoting this passage anywhere else"
BOILER13 = BOILER12 + " today"
# NEAR21 differs from BASE21 at token positions 1 and 14 (of 21):
# token-set Jaccard 18/21 ~ 0.857 >= 0.8, and no window of 13 consecutive
# tokens survives, so only the near-duplicate mechanism can fire.
BASE21 = (
    "the committee reviewed the annual budget and approved three new "
    "positions for the research team starting next quarter with additional "
    "funding"
)
NEAR21 = (
    "a committee reviewed the annual budget and approved three new "
    "positions for the science team starting next quarter with additional "
    "funding"
)


def _pad(prefix: str, boiler: str) -> str:
    """14 distinct prefix tokens + the boilerplate, so only the boilerplate
    (and, at n=13, nothing shorter) can ever be shared."""
    return " ".join([f"{prefix}{k}" for k in range(14)] + boiler.split())


# --- infrastructure: pass right now ---------------------------------------

def test_jaccard_basic():
    # intersection {c} = 1, union {a, b, c, d, e} = 5.
    assert c.jaccard({"a", "b", "c"}, {"c", "d", "e"}) == pytest.approx(1 / 5)


def test_jaccard_both_empty_means_identical():
    assert c.jaccard(set(), set()) == 1.0


def test_jaccard_one_empty_means_disjoint():
    assert c.jaccard({1, 2}, set()) == 0.0


def test_jaccard_identical_sets():
    assert c.jaccard({1, 2, 3}, {1, 2, 3}) == 1.0


def test_interface_contract():
    for name in (
        "normalise",
        "tokenize",
        "exact_matches",
        "ngram_matches",
        "jaccard",
        "minhash",
        "report",
    ):
        assert callable(getattr(c, name)), name
    assert inspect.signature(c.ngram_matches).parameters["n"].default == 13
    mh = inspect.signature(c.minhash).parameters
    assert mh["num_perm"].default == 128 and mh["seed"].default == 0
    assert mh["num_perm"].kind is inspect.Parameter.KEYWORD_ONLY
    assert mh["seed"].kind is inspect.Parameter.KEYWORD_ONLY
    rp = inspect.signature(c.report).parameters
    assert rp["n"].default == 13
    assert rp["near_duplicate_threshold"].default == 0.8
    assert rp["near_duplicate_threshold"].kind is inspect.Parameter.KEYWORD_ONLY


# --- core: xfail until the learner implements the stubs --------------------

@XFAIL
def test_normalise_unifies_case_whitespace_punctuation():
    assert c.normalise("Hello,   WORLD!") == "hello world"
    assert c.normalise("  don't  stop.") == "dont stop"
    assert c.normalise(c.normalise("A  B!")) == c.normalise("A  B!")


@XFAIL
def test_normalise_drops_fenced_code():
    text = "Before the answer:\n```python\nprint('secret')\n```\nafter the fence."
    out = c.normalise(text)
    assert "secret" not in out
    assert "print" not in out
    assert out == "before the answer after the fence"
    assert c.normalise("keep\n~~~\nhidden stuff\n~~~\nme") == "keep me"


@XFAIL
def test_exact_duplicate_is_flagged():
    train = [UNIQ, SHARED13]
    eval_ = [SHARED13]
    assert c.exact_matches(train, eval_) == [(1, 0)]
    rep = c.report(train, eval_)
    assert rep["exact"] == [(1, 0)]
    assert rep["ngram"] == [(1, 0)]
    assert rep["near_duplicate"] == []
    assert rep["flagged"] == [(0, "exact")]


@XFAIL
def test_paraphrase_is_not_flagged():
    train = [LONG_A, UNRELATED]
    eval_ = [PARAPHRASE]
    rep = c.report(train, eval_)
    assert rep["exact"] == []
    assert rep["ngram"] == []
    assert rep["near_duplicate"] == []
    assert rep["flagged"] == []


@XFAIL
def test_boilerplate_below_n_is_invisible():
    train = [_pad("t", BOILER12)]
    eval_ = [_pad("e", BOILER12)]
    rep = c.report(train, eval_)
    assert rep["exact"] == []
    assert rep["ngram"] == []
    assert rep["near_duplicate"] == []
    assert rep["flagged"] == []


@XFAIL
def test_boilerplate_at_n_is_caught():
    train = [_pad("t", BOILER13)]
    eval_ = [_pad("e", BOILER13)]
    rep = c.report(train, eval_)
    assert rep["exact"] == []
    assert rep["ngram"] == [(0, 0)]
    assert rep["near_duplicate"] == []
    assert rep["flagged"] == [(0, "ngram")]


@XFAIL
def test_eval_shorter_than_n_is_safe():
    train = [LONG_A]
    eval_ = ["tiny note"]
    assert c.ngram_matches(train, eval_) == []
    rep = c.report(train, eval_)
    assert rep["n_eval"] == 1
    assert rep["exact"] == []
    assert rep["ngram"] == []
    assert rep["near_duplicate"] == []
    assert rep["flagged"] == []


@XFAIL
def test_ngram_window_tracks_n():
    train = ["red green blue yellow purple orange black white pink brown gray cyan"]
    eval_ = ["red green blue violet"]
    assert c.ngram_matches(train, eval_, n=3) == [(0, 0)]
    assert c.ngram_matches(train, eval_, n=4) == []
    assert c.ngram_matches(train, eval_) == []  # default 13: nothing shared


@XFAIL
def test_minhash_tracks_jaccard():
    rng = random.Random(2026)
    universe = [f"w{k:03d}" for k in range(400)]
    a = set(universe[:200])
    b = set(universe[:100]) | set(universe[200:300])
    exact = c.jaccard(a, b)
    assert exact == pytest.approx(1 / 3)
    est = c.minhash(a, b, num_perm=1024)
    assert 0.0 <= est <= 1.0
    assert abs(est - exact) <= 0.05


@XFAIL
def test_minhash_is_deterministic():
    a = {1, 2, 3, 4}
    b = {3, 4, 5, 6}
    first = c.minhash(a, b)
    second = c.minhash(a, b)
    assert first == second


@XFAIL
def test_minhash_is_deterministic_across_processes():
    """The reproducibility the SPEC demands is across processes, not only across
    calls: a minhash built on the built-in ``hash()`` is salted per process and
    fails here. The in-process probe keeps the xfail contract (the stub raises
    NotImplementedError before any subprocess runs)."""
    a = {f"w{k}" for k in range(50)}
    b = {f"w{k}" for k in range(25, 75)}
    c.minhash(a, b, num_perm=64)  # probes the stub: raises until implemented
    root = Path(__file__).resolve().parents[1]
    code = (
        "from contamination import contamination as c\n"
        "a = {f'w{k}' for k in range(50)}\n"
        "b = {f'w{k}' for k in range(25, 75)}\n"
        "print(repr(c.minhash(a, b, num_perm=64)))\n"
    )
    outputs = []
    for seed in ("1", "2"):
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root, capture_output=True, text=True,
            env={**os.environ, "PYTHONHASHSEED": seed}, check=True,
        )
        outputs.append(proc.stdout.strip())
    assert outputs[0] == outputs[1]
    assert outputs[0] != ""


@XFAIL
def test_report_counts_agree_with_functions():
    train = [LONG_A, SHARED13]
    eval_ = [SHARED13, PARAPHRASE, "tiny note"]
    rep = c.report(train, eval_)
    assert rep["n_eval"] == len(eval_)
    assert rep["exact"] == c.exact_matches(train, eval_)
    assert rep["ngram"] == c.ngram_matches(train, eval_)
    assert rep["near_duplicate"] == []
    assert rep["flagged"] == [(0, "exact")]


@XFAIL
def test_report_empty_inputs():
    assert c.report([], []) == {
        "exact": [],
        "ngram": [],
        "near_duplicate": [],
        "n_eval": 0,
        "flagged": [],
    }


@XFAIL
def test_near_duplicate_is_flagged():
    train = [BASE21]
    eval_ = [NEAR21]
    rep = c.report(train, eval_)
    assert rep["exact"] == []
    assert rep["ngram"] == []
    assert rep["near_duplicate"] == [(0, 0)]
    assert rep["flagged"] == [(0, "near_duplicate")]

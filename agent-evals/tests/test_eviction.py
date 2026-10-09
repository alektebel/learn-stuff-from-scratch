"""Contract tests for eviction (agent-evals project #13).

Tests of the provided infrastructure (dataclasses, ScriptedModel, keeps_constraint)
PASS today. Tests marked with the CORE xfail decorator call the learner's core
(evict / evict_with_provenance): they xfail while the stubs raise
NotImplementedError, pass once the core is correct, and fail if it is wrong.
Never strict. SPEC.md acceptance items A1-A7 and limit cases L1-L5 are named in
the docstrings.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from eviction.eviction import (
    Context,
    EvictionResult,
    Message,
    ScriptedModel,
    evict,
    evict_with_provenance,
    keeps_constraint,
)

CORE = pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")


# ---------------------------------------------------------------------------
# Fixtures / scenario helpers
# ---------------------------------------------------------------------------


def constraint_msg() -> Message:
    return Message("system", "CONSTRAINT: only order from the approved vendor list.", 20)


def filler(i: int, tokens: int = 20) -> Message:
    return Message("user", f"Filler turn {i}: log lines, tool output, chatter.", tokens)


def session() -> list[Message]:
    """Five 20-token turns, total 100; the constraint is the oldest message (index 0)."""
    return [constraint_msg()] + [filler(i) for i in range(1, 5)]


def original_indices(msgs: list[Message], dropped: list[Message]) -> list[int]:
    return [i for i, m in enumerate(msgs) if any(d is m for d in dropped)]


# ---------------------------------------------------------------------------
# Infrastructure tests — pass now.
# ---------------------------------------------------------------------------


def test_context_tokens_sums_messages():
    msgs = [Message("user", "a", 5), Message("assistant", "b", 7)]
    assert Context(budget=100, messages=msgs).tokens() == 12


def test_context_overflow_sign():
    msgs = [Message("user", "a", 30)]
    assert Context(budget=40, messages=msgs).overflow() == -10  # room left
    assert Context(budget=30, messages=msgs).overflow() == 0  # exactly full
    assert Context(budget=10, messages=msgs).overflow() == 20  # over budget


def test_scripted_model_answers_from_retained():
    model = ScriptedModel({"vendor?": ("approved vendor", "vendor-x")})
    msgs = [Message("system", "The approved vendor is vendor-x.", 10)]
    assert model.answer(msgs, "vendor?") == "vendor-x"
    assert model.answer(Context(budget=99, messages=msgs), "vendor?") == "vendor-x"


def test_scripted_model_unknown_when_fact_absent():
    model = ScriptedModel({"vendor?": ("approved vendor", "vendor-x")})
    assert model.answer([Message("user", "nothing relevant here", 10)], "vendor?") == "unknown"
    assert model.answer([], "vendor?") == "unknown"
    assert model.answer([Message("user", "x", 1)], "unheard question") == "unknown"


def test_keeps_constraint_grader():
    m = constraint_msg()
    kept = EvictionResult(messages=[m], dropped=[], provenance={0: [0]})
    lost = EvictionResult(messages=[filler(1)], dropped=[m], provenance={0: [1]})
    assert keeps_constraint(kept, "approved vendor") is True
    assert keeps_constraint(lost, "approved vendor") is False


# ---------------------------------------------------------------------------
# Core tests — xfail until evict / evict_with_provenance are implemented.
# ---------------------------------------------------------------------------


@CORE
def test_oldest_within_budget():
    """A1: budget holds; retained keep order and identity."""
    msgs = session()
    kept = evict(msgs, 65, policy="oldest")
    assert isinstance(kept, list) and all(isinstance(m, Message) for m in kept)
    assert sum(m.tokens for m in kept) <= 65
    assert kept == msgs[2:]  # oldest two evicted first
    assert all(a is b for a, b in zip(kept, msgs[2:]))  # same objects, order kept


@CORE
def test_pin_survives_oldest_eviction():
    """A2, L4: a pinned constraint message is never evicted, even though it is the oldest."""
    msgs = session()
    pin = (lambda m: "CONSTRAINT" in m.content,)
    pinned = evict(msgs, 65, policy="oldest", pin=pin)
    assert sum(m.tokens for m in pinned) <= 65
    assert pinned[0] is msgs[0]
    assert keeps_constraint(EvictionResult(pinned, [], {}), "approved vendor")


@CORE
def test_unpinned_constraint_is_lost_and_model_answers_unknown():
    """A3, the project's point: without the pin, oldest eviction drops the constraint
    and the scripted model goes from answering to 'unknown'."""
    msgs = session()
    model = ScriptedModel({"vendor?": ("approved vendor", "vendor-x")})
    assert model.answer(msgs, "vendor?") == "vendor-x"  # before eviction it knows
    kept = evict(msgs, 65, policy="oldest")
    assert keeps_constraint(EvictionResult(kept, [], {}), "approved vendor") is False
    assert model.answer(kept, "vendor?") == "unknown"


@CORE
def test_summarise_provenance_names_dropped_sources():
    """A4: the summary message's provenance names exactly the dropped source indices."""
    msgs = [Message("user", f"early {i}", 30) for i in range(2)]
    msgs += [Message("user", f"late {i}", 20) for i in range(2)]
    # total 100, budget 60; plain oldest drops the first two (50 left), and a
    # 10-token summary fits: 10 + 20 + 20 <= 60.
    summariser = lambda dropped: Message(  # noqa: E731
        "system", f"Summary of {len(dropped)} earlier turns", 10
    )
    result = evict_with_provenance(msgs, 60, policy="summarise", summariser=summariser)
    assert sum(m.tokens for m in result.messages) <= 60
    assert result.provenance[0] == [0, 1]  # summary built from the dropped pair
    assert result.messages[1] is msgs[2] and result.messages[2] is msgs[3]
    assert result.provenance[1] == [2] and result.provenance[2] == [3]
    assert all(a is b for a, b in zip(result.dropped, msgs[:2]))


@CORE
def test_provenance_passthrough_and_coverage():
    """A4: pass-through provenance is the identity mapping; provenance + dropped
    partition the original list."""
    msgs = session()
    result = evict_with_provenance(msgs, 65, policy="oldest")
    assert all(a is b for a, b in zip(result.messages, msgs[2:]))
    assert all(a is b for a, b in zip(result.dropped, msgs[:2]))
    assert result.provenance == {0: [2], 1: [3], 2: [4]}
    covered = [i for idxs in result.provenance.values() for i in idxs]
    assert sorted(covered + original_indices(msgs, result.dropped)) == list(range(5))


@CORE
def test_summary_that_cannot_fit_degrades():
    """L5: an oversized summary neither breaks the budget nor errors — the result
    degrades to plain oldest eviction."""
    msgs = [Message("user", f"early {i}", 30) for i in range(2)]
    msgs += [Message("user", f"late {i}", 20) for i in range(2)]
    bloated = lambda dropped: Message("system", "way too big", 100)  # noqa: E731
    result = evict(msgs, 60, policy="summarise", summariser=bloated)
    assert sum(m.tokens for m in result) <= 60
    assert all(a is b for a, b in zip(result, msgs[2:]))


@CORE
def test_deterministic_repeat_calls():
    """A5: identical inputs give identical outputs, twice in a row."""
    msgs = session()
    pin = (lambda m: "CONSTRAINT" in m.content,)
    a = evict(msgs, 65, policy="oldest", pin=pin)
    b = evict(msgs, 65, policy="oldest", pin=pin)
    assert a == b
    summariser = lambda dropped: Message("system", "summary", 10)  # noqa: E731
    ra = evict_with_provenance(msgs, 65, policy="summarise", summariser=summariser)
    rb = evict_with_provenance(msgs, 65, policy="summarise", summariser=summariser)
    assert ra == rb


@CORE
def test_budget_too_small_raises():
    """A6, L3: a budget that cannot hold even the smallest message is a ValueError,
    not a silent empty result (both entry points)."""
    big = Message("user", "one huge turn", 100)
    with pytest.raises(ValueError):
        evict([big], 50, policy="oldest")
    with pytest.raises(ValueError):
        evict_with_provenance([big], 50, policy="oldest")


@CORE
def test_pinned_over_budget_raises():
    """A6, L4: pinned messages alone over budget -> ValueError, never silent trimming."""
    p1 = Message("system", "CONSTRAINT one", 30)
    p2 = Message("system", "CONSTRAINT two", 30)
    msgs = [p1, filler(1), p2, filler(2)]
    with pytest.raises(ValueError):
        evict(msgs, 50, policy="newest", pin=(lambda m: m.role == "system",))


@CORE
def test_newest_respects_budget():
    """A7, L2: 'newest' evicts from the back — the old end (constraint included) survives,
    and the budget still holds."""
    msgs = session()
    kept = evict(msgs, 65, policy="newest")
    assert sum(m.tokens for m in kept) <= 65
    assert all(a is b for a, b in zip(kept, msgs[:3]))


@CORE
def test_middle_evicts_centre_first():
    """L1: 'middle' takes the centre message first, not the front."""
    msgs = [Message("user", "a", 10), Message("user", "b", 40), Message("user", "c", 10)]
    kept = evict(msgs, 20, policy="middle")
    assert sum(m.tokens for m in kept) <= 20
    assert all(a is b for a, b in zip(kept, [msgs[0], msgs[2]]))

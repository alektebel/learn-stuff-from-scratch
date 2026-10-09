"""Context-window eviction tester (agent-evals project #13).

LEARN mode: this file provides the *test infrastructure* (dataclasses, the scripted
model double, the grader) and *stubs* for the core you will write. Read SPEC.md first;
tests/test_eviction.py is the contract — it xfails on these stubs today and must pass
once the core is implemented.

The project's question: does an agent keep a session constraint after the context
window evicts the message that stated it? No model API is involved anywhere; the
"model" is a deterministic ScriptedModel double.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Test infrastructure — provided, covered by passing tests.
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """One turn in a session. `tokens` is declared, never measured: real token
    counting is out of scope (SPEC.md)."""

    role: str
    content: str
    tokens: int


@dataclass
class Context:
    """A session window: a token budget and the messages currently in it."""

    budget: int
    messages: list[Message]

    def tokens(self) -> int:
        """Total tokens currently held."""
        return sum(m.tokens for m in self.messages)

    def overflow(self) -> int:
        """`tokens() - budget`: positive means over budget by that many tokens."""
        return self.tokens() - self.budget


def _message_texts(messages) -> list[str]:
    """Accept a Context, an iterable of Message, or plain strings."""
    if isinstance(messages, Context):
        messages = messages.messages
    return [m if isinstance(m, str) else m.content for m in messages]


class ScriptedModel:
    """Deterministic model double.

    `knowledge` maps question -> (needle, value). `answer` returns the value only if
    the needle appears in the content of some *retained* message; otherwise "unknown".
    That is the failure mode this project measures: the fact left the window together
    with the evicted message.
    """

    def __init__(self, knowledge: dict[str, tuple[str, str]] | None = None):
        self._knowledge = dict(knowledge or {})

    def answer(self, messages, question: str) -> str:
        entry = self._knowledge.get(question)
        if entry is None:
            return "unknown"
        needle, value = entry
        for text in _message_texts(messages):
            if needle in text:
                return value
        return "unknown"


# ---------------------------------------------------------------------------
# Record type for the provenance-carrying variant. Passive data; the core is the
# producer function below.
# ---------------------------------------------------------------------------


@dataclass
class EvictionResult:
    """`messages` survive, in order. `dropped` are the removed originals (the sources
    of any summary). `provenance` maps each index of `messages` to the sorted list of
    indices in the original input it was built from."""

    messages: list[Message]
    dropped: list[Message]
    provenance: dict[int, list[int]]


def keeps_constraint(result: EvictionResult, constraint: str) -> bool:
    """Grader (infrastructure, not core): True iff some retained message still
    states `constraint`."""
    return any(constraint in m.content for m in result.messages)


# ---------------------------------------------------------------------------
# Core — implement these. SPEC.md pins the exact semantics; every core test in
# tests/test_eviction.py xfails until they are real.
# ---------------------------------------------------------------------------

POLICIES = ("oldest", "newest", "middle", "summarise")


def evict(messages, budget, *, policy="oldest", pin=(), summariser=None) -> list[Message]:
    """Evict messages until the total fits `budget`.

    policy: what is EVICTED first — "oldest", "newest", "middle" (centre-outward) or
    "summarise" (replace the dropped prefix with summariser(dropped)).
    pin: predicates over Message; a match is mandatory and is never evicted.
    Raises ValueError when no admissible result exists (SPEC.md).
    """
    raise NotImplementedError("core not implemented")


def evict_with_provenance(messages, budget, *, policy="oldest", pin=(), summariser=None) -> EvictionResult:
    """Same contract as `evict`, plus the audit trail: which original messages produced
    each retained one, and which were dropped."""
    raise NotImplementedError("core not implemented")

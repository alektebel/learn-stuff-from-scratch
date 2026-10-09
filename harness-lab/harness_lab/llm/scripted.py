"""A deterministic model backend that replays recorded responses (phase 1).

Amendment 5: every subsystem's tests run against recorded responses, so the
test suite is deterministic and free. Only `eval/` uses a real model. This is
the recording player: it hands the loop the next `Completion` and remembers
what it was asked, so a test can assert on both the answers given and the
history built.

Shipped as infrastructure (LEARN mode): the project's point is the loop, not
the test double. It raises `ScriptExhausted` (a `ModelError`) when the tape
runs out, which is the loop's cue to stop with `stop_reason="model_error"`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from harness_lab.llm.base import Completion, ModelError, Price, ToolSpec
from harness_lab.llm.messages import Message


class ScriptExhausted(ModelError):
    """The recorded tape ended before the loop stopped on its own."""


class ScriptedBackend:
    """Replays `script` in order, one `Completion` per call.

    Records every request as `(tuple(messages), tuple(tools))` in `requests`,
    so a test can check that the loop sent the history it was supposed to.
    """

    def __init__(
        self,
        script: Iterable[Completion],
        *,
        name: str = "scripted",
        price: Price | None = None,
    ) -> None:
        self.name = name
        self.price = price if price is not None else Price()
        self.script: list[Completion] = list(script)
        self.requests: list[tuple[tuple[Message, ...], tuple[ToolSpec, ...]]] = []
        self._next = 0

    @property
    def exhausted(self) -> bool:
        return self._next >= len(self.script)

    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> Completion:
        self.requests.append((tuple(messages), tuple(tools)))
        if self.exhausted:
            raise ScriptExhausted(
                f"scripted backend exhausted after {self._next} response(s)"
            )
        completion = self.script[self._next]
        self._next += 1
        return completion

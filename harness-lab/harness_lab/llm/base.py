"""The model interface (phase 1, LEARN mode).

A `Model` is one function: given the message history and the tools available,
return one assistant message plus the token usage it cost. Everything that
differs between providers (wire format, auth, streaming, prompt cache) lives
behind this interface in a transport module.

DESIGN DECISION — `complete` is synchronous and non-streaming.
The loop in phase 1 is linear: one call, inspect, act, repeat. Streaming only
matters once a UI consumes partial tokens, which is out of scope here. Cost:
a transport buffers the full response before returning, so a very slow model
holds the run for the whole completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable

from harness_lab.llm.messages import Message


class ModelError(RuntimeError):
    """A provider failure the loop may recover from by stopping with
    `stop_reason="model_error"`. Anything else is a bug and must propagate."""


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may call, as a JSON-schema function definition."""

    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # subset of input_tokens served from the provider cache

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.cached_tokens) < 0:
            raise ValueError("token counts cannot be negative")
        if self.cached_tokens > self.input_tokens:
            raise ValueError("cached_tokens cannot exceed input_tokens")


@dataclass(frozen=True)
class Completion:
    """One model turn: the assistant message and what it cost."""

    message: Message
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = "stop"  # provider-side reason: stop | tool_use | length | ...

    def __post_init__(self) -> None:
        if self.message.role != "assistant":
            raise ValueError("a Completion's message must have role='assistant'")


@dataclass(frozen=True)
class Price:
    """Cost per **million** tokens. Zero by default, so a scripted run costs
    nothing unless a test or a config sets a real price."""

    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0
    cached_input_per_mtok: float = 0.0

    def cost(self, usage: Usage) -> float:
        fresh_input = usage.input_tokens - usage.cached_tokens
        return (
            fresh_input * self.input_per_mtok
            + usage.cached_tokens * self.cached_input_per_mtok
            + usage.output_tokens * self.output_per_mtok
        ) / 1_000_000


@runtime_checkable
class Model(Protocol):
    name: str
    price: Price

    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> Completion: ...

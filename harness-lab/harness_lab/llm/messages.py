"""Provider-neutral message types for the LLM interface (phase 1, LEARN mode).

These are data types, not logic. The learner's design work is the loop that
grows this list (harness_lab/core/loop.py); this module only fixes the shape
the loop and the transports agree on.

DESIGN DECISION — tool results are messages, not a side channel.
OpenAI sends a tool result as a `role="tool"` message carrying `tool_call_id`;
Anthropic sends it as a user-content block. Modelling it as a message keeps
the loop's history one append-only list, and lets each transport translate to
its own wire format. Chosen: `role="tool"`. Cost: a transport doing
Anthropic-style tool results has to fold them into `user` turns itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant", "tool"]
ROLES: tuple[Role, ...] = ("system", "user", "assistant", "tool")


@dataclass(frozen=True)
class ToolCall:
    """A model's request to run a tool.

    `arguments` deliberately stays a JSON **string**: providers disagree on the
    schema, and some stream it in fragments. The loop validates and decodes it
    before use instead of trusting an already-decoded dict.
    """

    id: str
    name: str
    arguments: str = "{}"


@dataclass(frozen=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"unknown role {self.role!r}")
        if self.role == "tool" and self.tool_call_id is None:
            raise ValueError("role='tool' requires tool_call_id")
        if self.role != "tool" and self.tool_call_id is not None:
            raise ValueError("tool_call_id is only valid on role='tool'")
        if self.tool_calls and self.role != "assistant":
            raise ValueError("tool_calls are only valid on role='assistant'")

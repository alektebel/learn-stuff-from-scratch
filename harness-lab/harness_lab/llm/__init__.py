"""LLM integration (phase 1): message types, the model interface, the
scripted backend. Provider transports (the one real backend) land here too;
the transport is the learner's work, see docs/phase1.md.
"""

from harness_lab.llm.base import (
    Completion,
    Model,
    ModelError,
    Price,
    ToolSpec,
    Usage,
)
from harness_lab.llm.messages import ROLES, Message, Role, ToolCall
from harness_lab.llm.scripted import ScriptedBackend, ScriptExhausted

__all__ = [
    "ROLES",
    "Completion",
    "Message",
    "Model",
    "ModelError",
    "Price",
    "Role",
    "ScriptExhausted",
    "ScriptedBackend",
    "ToolCall",
    "ToolSpec",
    "Usage",
]

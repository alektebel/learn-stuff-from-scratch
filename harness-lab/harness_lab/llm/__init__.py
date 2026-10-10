"""LLM integration (phase 1): message types, the model interface, the
scripted backend, and the OpenAI-compatible transport for the real endpoint.
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
from harness_lab.llm.openai_compat import OpenAICompatibleModel
from harness_lab.llm.scripted import ScriptedBackend, ScriptExhausted

__all__ = [
    "ROLES",
    "Completion",
    "Message",
    "Model",
    "ModelError",
    "OpenAICompatibleModel",
    "Price",
    "Role",
    "ScriptExhausted",
    "ScriptedBackend",
    "ToolCall",
    "ToolSpec",
    "Usage",
]

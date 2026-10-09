"""Tests for the phase-1 LLM layer: message types and the scripted backend.

These are infrastructure and pass today. The learner's loop is in
tests/test_loop.py.
"""

import pytest
from harness_lab.llm import (
    Completion,
    Message,
    ModelError,
    Price,
    ScriptedBackend,
    ScriptExhausted,
    ToolCall,
    ToolSpec,
    Usage,
)


def assistant(text="", *, tool_calls=(), usage=None, stop_reason="stop"):
    return Completion(
        message=Message(role="assistant", content=text, tool_calls=tool_calls),
        usage=usage or Usage(),
        stop_reason=stop_reason,
    )


def bash_call(command, *, call_id="c1"):
    import json

    return ToolCall(id=call_id, name="bash", arguments=json.dumps({"command": command}))


# --- message types -----------------------------------------------------------


def test_message_accepts_every_role():
    for role in ("system", "user", "assistant"):
        assert Message(role=role, content="x").role == role
    assert Message(role="tool", content="x", tool_call_id="c1").tool_call_id == "c1"


def test_unknown_role_rejected():
    with pytest.raises(ValueError, match="unknown role"):
        Message(role="wizard")  # type: ignore[arg-type]


def test_tool_message_requires_tool_call_id():
    with pytest.raises(ValueError, match="tool_call_id"):
        Message(role="tool", content="x")
    with pytest.raises(ValueError, match="tool_call_id"):
        Message(role="user", content="x", tool_call_id="c1")


def test_tool_calls_only_on_assistant():
    with pytest.raises(ValueError, match="assistant"):
        Message(role="user", content="x", tool_calls=(bash_call("ls"),))


# --- usage and completion ----------------------------------------------------


def test_usage_rejects_negative_and_inconsistent_counts():
    with pytest.raises(ValueError, match="negative"):
        Usage(input_tokens=-1)
    with pytest.raises(ValueError, match="cached_tokens"):
        Usage(input_tokens=1, cached_tokens=2)


def test_completion_message_must_be_assistant():
    with pytest.raises(ValueError, match="assistant"):
        Completion(message=Message(role="user", content="hi"))


def test_price_charges_fresh_cached_and_output_separately():
    price = Price(input_per_mtok=3.0, output_per_mtok=15.0, cached_input_per_mtok=0.3)
    # 1M fresh input + 1M cached input + 1M output = 3.0 + 0.3 + 15.0
    assert price.cost(Usage(input_tokens=2_000_000, cached_tokens=1_000_000, output_tokens=1_000_000)) == pytest.approx(18.3)


# --- scripted backend --------------------------------------------------------


def test_scripted_replays_in_order_and_exposes_price():
    a, b = assistant("first"), assistant("second")
    backend = ScriptedBackend([a, b], name="tape", price=Price(input_per_mtok=1.0))
    assert backend.name == "tape" and backend.price.input_per_mtok == 1.0
    assert backend.complete([]) is a
    assert backend.complete([]) is b
    assert backend.exhausted


def test_scripted_records_the_history_and_tools_it_was_given():
    backend = ScriptedBackend([assistant("ok")])
    history = [Message(role="user", content="go")]
    tools = [ToolSpec(name="bash", description="d", parameters={"type": "object"})]
    backend.complete(history, tools)
    sent_messages, sent_tools = backend.requests[0]
    assert list(sent_messages) == history
    assert list(sent_tools) == tools


def test_scripted_exhaustion_is_a_model_error():
    backend = ScriptedBackend([])
    assert backend.exhausted
    with pytest.raises(ScriptExhausted):
        backend.complete([])
    assert issubclass(ScriptExhausted, ModelError)


def test_scripted_backend_is_deterministic():
    first = ScriptedBackend([assistant("x"), assistant("y")])
    second = ScriptedBackend([assistant("x"), assistant("y")])
    assert [first.complete([]) for _ in range(2)] == [second.complete([]) for _ in range(2)]

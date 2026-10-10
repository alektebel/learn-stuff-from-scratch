"""Tests for the real OpenAI-compatible transport (infrastructure).

Everything here is deterministic: the HTTP call is injected, so no network and
no model. The learner's loop is in tests/test_loop.py; the scripted backend in
tests/test_llm.py.
"""

import json

import pytest

from harness_lab.llm.base import ModelError, Price, ToolSpec, Usage
from harness_lab.llm.messages import Message, ToolCall
from harness_lab.llm.openai_compat import (
    OpenAICompatibleModel,
    parse_completion,
    to_wire_messages,
    to_wire_tools,
)


def make_model(http_post, **kwargs):
    return OpenAICompatibleModel(
        base_url="https://example.test/v1", api_key="k", model="test-model",
        http_post=http_post, **kwargs)


def response_bytes(**override):
    payload = {
        "choices": [{"message": {"role": "assistant", "content": "hi"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }
    payload.update(override)
    return json.dumps(payload).encode()


# --- wire translation --------------------------------------------------------

def test_wire_messages_cover_every_role():
    history = [
        Message(role="system", content="sys"),
        Message(role="user", content="hi"),
        Message(role="assistant", tool_calls=(ToolCall(id="c1", name="bash",
                                                       arguments='{"command":"ls"}'),)),
        Message(role="tool", content="out", tool_call_id="c1"),
    ]
    wire = to_wire_messages(history)
    assert wire[0] == {"role": "system", "content": "sys"}
    assert wire[1] == {"role": "user", "content": "hi"}
    assert wire[2]["role"] == "assistant" and wire[2]["content"] is None
    assert wire[2]["tool_calls"][0]["function"] == {"name": "bash",
                                                    "arguments": '{"command":"ls"}'}
    assert wire[3] == {"role": "tool", "tool_call_id": "c1", "content": "out"}


def test_wire_tools_shape():
    specs = [ToolSpec(name="bash", description="run", parameters={"type": "object"})]
    assert to_wire_tools(specs) == [{
        "type": "function",
        "function": {"name": "bash", "description": "run", "parameters": {"type": "object"}},
    }]


# --- response parsing --------------------------------------------------------

def test_parse_text_completion():
    completion = parse_completion(json.loads(response_bytes()))
    assert completion.message.role == "assistant"
    assert completion.message.content == "hi"
    assert completion.message.tool_calls == ()
    assert completion.stop_reason == "stop"
    assert completion.usage == Usage(input_tokens=10, output_tokens=2)


def test_parse_tool_call_normalises_dict_arguments():
    payload = {
        "choices": [{
            "message": {"role": "assistant", "content": None,
                        "tool_calls": [{"id": "c1",
                                        "function": {"name": "bash",
                                                     "arguments": {"command": "ls"}}}]},
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
    }
    completion = parse_completion(payload)
    assert completion.stop_reason == "tool_use", "tool calls must win over the provider reason"
    call = completion.message.tool_calls[0]
    assert call.id == "c1" and call.name == "bash"
    assert call.arguments == json.dumps({"command": "ls"})


def test_parse_cached_tokens_are_clamped_to_input():
    payload = {"choices": [{"message": {"role": "assistant", "content": "x"}}],
               "usage": {"prompt_tokens": 8, "completion_tokens": 1,
                         "prompt_tokens_details": {"cached_tokens": 5}}}
    assert parse_completion(payload).usage.cached_tokens == 5
    payload["usage"]["prompt_tokens_details"]["cached_tokens"] = 99
    assert parse_completion(payload).usage.cached_tokens == 8


def test_parse_rejects_missing_or_empty_choices():
    with pytest.raises(ModelError):
        parse_completion({})
    with pytest.raises(ModelError):
        parse_completion({"choices": []})


# --- complete() --------------------------------------------------------------

def test_complete_posts_the_url_headers_and_body():
    seen = {}

    def fake(url, headers, data):
        seen["url"], seen["headers"], seen["body"] = url, headers, json.loads(data)
        return 200, response_bytes()

    model = make_model(fake)
    completion = model.complete(
        [Message(role="user", content="hi")],
        [ToolSpec(name="bash", description="d", parameters={"type": "object"})])
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer k"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["temperature"] == 0
    assert seen["body"]["tools"][0]["function"]["name"] == "bash"
    assert completion.message.content == "hi"


def test_complete_omits_tools_when_there_are_none():
    seen = {}

    def fake(url, headers, data):
        seen["body"] = json.loads(data)
        return 200, response_bytes()

    make_model(fake).complete([Message(role="user", content="hi")])
    assert "tools" not in seen["body"]


def test_complete_maps_http_error_to_model_error():
    model = make_model(lambda url, headers, data: (429, b'{"error":"slow down"}'))
    with pytest.raises(ModelError, match="429"):
        model.complete([Message(role="user", content="hi")])


def test_complete_maps_invalid_json_to_model_error():
    model = make_model(lambda url, headers, data: (200, b"not json"))
    with pytest.raises(ModelError, match="invalid JSON"):
        model.complete([Message(role="user", content="hi")])


def test_price_flows_from_the_constructor():
    def fake(url, headers, data):
        return 200, json.dumps({
            "choices": [{"message": {"role": "assistant", "content": "x"}}],
            "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
        }).encode()

    model = make_model(fake, price=Price(input_per_mtok=1.0, output_per_mtok=2.0))
    completion = model.complete([Message(role="user", content="hi")])
    assert model.price.cost(completion.usage) == pytest.approx(3.0)


# --- build_model() from the environment --------------------------------------

def test_build_model_requires_env(monkeypatch):
    from eval.agents import build_model

    for name in ("HARNESS_LAB_BASE_URL", "HARNESS_LAB_API_KEY", "HARNESS_LAB_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ModelError, match="missing environment"):
        build_model()


def test_build_model_reads_env_and_strips_trailing_slash(monkeypatch):
    from eval.agents import build_model

    monkeypatch.setenv("HARNESS_LAB_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("HARNESS_LAB_API_KEY", "secret")
    monkeypatch.setenv("HARNESS_LAB_MODEL", "test-model")
    monkeypatch.setenv("HARNESS_LAB_INPUT_EUR_PER_MTOK", "1.5")
    model = build_model()
    assert model.base_url == "https://example.test/v1"
    assert model.price.input_per_mtok == 1.5


def test_build_model_rejects_a_non_numeric_price(monkeypatch):
    from eval.agents import build_model

    monkeypatch.setenv("HARNESS_LAB_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("HARNESS_LAB_API_KEY", "k")
    monkeypatch.setenv("HARNESS_LAB_MODEL", "m")
    monkeypatch.setenv("HARNESS_LAB_OUTPUT_EUR_PER_MTOK", "cheap")
    with pytest.raises(ModelError, match="must be a number"):
        build_model()

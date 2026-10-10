"""A real provider transport: OpenAI-compatible chat completions (phase 1).

This is infrastructure, not the learner's core: it translates the provider-neutral
`Message`/`ToolSpec` types to the OpenAI wire format and a response back to a
`Completion`, so the loop in `harness_lab/core/loop.py` never sees a provider.

DESIGN DECISION — no HTTP library, `urllib` from the stdlib.
harness-lab deliberately has no runtime dependencies (`pyproject.toml`,
`dependencies = []`), and the loop needs exactly one POST. `httpx` is allowed by
the project rules but would add an install step for no gain here. Cost: no
connection pooling or async, neither of which phase 1 uses; a future transport
that needs them swaps the injected `http_post`.

DESIGN DECISION — the HTTP call is injectable.
`complete` takes no transport, but the constructor accepts `http_post`, a
`(url, headers, body) -> (status, body)` callable. Tests inject a fake so the
translation and error mapping are verified without a network or a model, and the
live smoke run uses the default `urllib` poster. Cost: one more seam to learn.

DESIGN DECISION — errors become `ModelError`.
A non-2xx status, invalid JSON, a missing `choices` list, or an empty choices
list all raise `ModelError`, the one exception the loop is allowed to recover
from by stopping with `stop_reason="model_error"`. A bug in the translation
raises something else and propagates. Cost: the status and a body snippet are in
the message, so a caller can log without re-reading the response.

DESIGN DECISION — one transport only.
Phase 1 needs one provider behind `Model`; streaming, retries and prompt caching
are phase 2+. Cost: a slow provider holds the whole run (the `Model.complete`
contract is synchronous, see `base.py`).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

from harness_lab.llm.base import Completion, ModelError, Price, ToolSpec, Usage
from harness_lab.llm.messages import Message, ToolCall

__all__ = [
    "OpenAICompatibleModel", "to_wire_messages", "to_wire_tools", "parse_completion",
]

# (url, headers, body) -> (status_code, response_body)
HttpPost = Callable[[str, dict, bytes], "tuple[int, bytes]"]

DEFAULT_TIMEOUT_S = 60.0


def _default_http_post(url: str, headers: dict, body: bytes) -> tuple[int, bytes]:
    """POST with `urllib`. Returns HTTP error responses instead of raising, so
    `complete` maps every non-2xx through one path."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_S) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def to_wire_messages(messages: Sequence[Message]) -> list[dict]:
    """Translate the neutral history to OpenAI `messages`."""
    wire: list[dict] = []
    for message in messages:
        if message.role == "tool":
            wire.append({
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            })
        elif message.role == "assistant" and message.tool_calls:
            wire.append({
                "role": "assistant",
                # OpenAI wants content=null (not "") when the turn is only tool calls.
                "content": message.content or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    }
                    for call in message.tool_calls
                ],
            })
        else:
            wire.append({"role": message.role, "content": message.content})
    return wire


def to_wire_tools(tools: Sequence[ToolSpec]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


def parse_completion(payload: dict) -> Completion:
    """Turn a chat-completions response body into a `Completion`."""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ModelError(f"response has no usable choices: {str(payload)[:200]}")
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    calls: list[ToolCall] = []
    for raw_call in message.get("tool_calls") or []:
        function = raw_call.get("function") or {}
        arguments = function.get("arguments", "{}")
        if not isinstance(arguments, str):
            # Some providers return an already-decoded object; the neutral type
            # insists on a string so the loop validates one schema.
            arguments = json.dumps(arguments)
        calls.append(ToolCall(
            id=raw_call.get("id", ""), name=function.get("name", ""), arguments=arguments))
    finish = choice.get("finish_reason") or "stop"
    usage_raw = payload.get("usage") or {}
    details = usage_raw.get("prompt_tokens_details") or {}
    input_tokens = int(usage_raw.get("prompt_tokens") or 0)
    cached = int(details.get("cached_tokens")
                 or usage_raw.get("cache_read_input_tokens") or 0)
    cached = min(cached, input_tokens)
    return Completion(
        message=Message(role="assistant", content=content, tool_calls=tuple(calls)),
        usage=Usage(
            input_tokens=input_tokens,
            output_tokens=int(usage_raw.get("completion_tokens") or 0),
            cached_tokens=cached,
        ),
        stop_reason="tool_use" if calls else finish,
    )


class OpenAICompatibleModel:
    """A `Model` backed by an OpenAI-compatible `/chat/completions` endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        price: Price | None = None,
        http_post: HttpPost | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = f"openai-compatible:{model}"
        self.price = price if price is not None else Price()
        self._api_key = api_key
        self._http_post = http_post or _default_http_post

    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> Completion:
        body: dict = {
            "model": self.model,
            "messages": to_wire_messages(messages),
            "temperature": 0,
        }
        if tools:
            body["tools"] = to_wire_tools(tools)
            body["tool_choice"] = "auto"
        encoded = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            # Some gateways reject urllib's default User-Agent; a stable one works.
            "User-Agent": "harness-lab/0.1",
        }
        status, raw = self._http_post(f"{self.base_url}/chat/completions", headers, encoded)
        if not 200 <= status < 300:
            snippet = raw[:300].decode("utf-8", "replace")
            raise ModelError(f"provider returned HTTP {status}: {snippet}")
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise ModelError(f"provider returned invalid JSON: {raw[:120]!r}") from exc
        return parse_completion(payload)

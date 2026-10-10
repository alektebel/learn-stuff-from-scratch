"""Agent Harness From Scratch — stage 1 solution: the model is a callable, and its
answer is an event stream.

The reasoning lives in `stage_01.py`'s docstring (the design decisions are the
lesson); this file is the implementation.
"""

from tiny_env import HarnessError

EVENT_TYPES = ("text", "tool_call", "usage", "end")

EMPTY_USAGE = {"input_tokens": 0, "output_tokens": 0}


def _count(value, field):
    """One token count. Ints only: a bool is an int in Python and a provider that
    sends `true` for a count is a bug, and a negative count un-bills a run."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise HarnessError(
            "usage %s must be an int, got %r (%s)" % (field, value,
                                                      type(value).__name__))
    if value < 0:
        raise HarnessError("usage %s cannot be negative, got %r" % (field, value))
    return value


def _usage_of(event):
    """A usage event as a complete usage dict."""
    return {"input_tokens": _count(event.get("input_tokens", 0), "input_tokens"),
            "output_tokens": _count(event.get("output_tokens", 0), "output_tokens")}


def usage_add(first, second):
    """Sum two usage dicts, defaulting missing keys to 0."""
    first = first if isinstance(first, dict) else {}
    second = second if isinstance(second, dict) else {}
    return {"input_tokens": _count(first.get("input_tokens", 0), "input_tokens")
            + _count(second.get("input_tokens", 0), "input_tokens"),
            "output_tokens": _count(first.get("output_tokens", 0), "output_tokens")
            + _count(second.get("output_tokens", 0), "output_tokens")}


def _tool_call(event):
    """One tool_call event as the turn's entry. The id is not optional: the
    observation that answers this call carries `tool_call_id`, and a harness that
    invents one sends the result of the third tool to the second call."""
    call_id = event.get("id")
    if not isinstance(call_id, str) or not call_id:
        raise HarnessError(
            "a tool_call event needs an id (the observation answers it by id), "
            "got %r" % (call_id,))
    name = event.get("name")
    if not isinstance(name, str) or not name:
        raise HarnessError("a tool_call event needs a name, got %r" % (name,))
    arguments = event.get("arguments", {})
    if not isinstance(arguments, dict):
        raise HarnessError(
            "a tool_call's arguments are an object, got %r (%s)"
            % (arguments, type(arguments).__name__))
    # A copy: the caller's event belongs to the caller, and the turn travels.
    return {"id": call_id, "name": name, "arguments": dict(arguments)}


def collect(events):
    """Consume an event iterator ONCE and return the turn it describes."""
    pieces = []
    tool_calls = []
    usage = dict(EMPTY_USAGE)
    reason = None
    ended = False
    for event in events:
        if not isinstance(event, dict):
            raise HarnessError(
                "an event is a dict, got %r (%s)" % (event, type(event).__name__))
        kind = event.get("type")
        if kind not in EVENT_TYPES:
            raise HarnessError(
                "unknown event type %r on the wire (known: %s)"
                % (kind, ", ".join(EVENT_TYPES)))
        if ended:
            # The stream said end and then said something else. Accepting it would
            # make `end` advisory and every turn's reason a guess.
            raise HarnessError(
                "a %r event arrived after the end event: the turn was over"
                % (kind,))
        if kind == "text":
            pieces.append(str(event.get("text", "")))
        elif kind == "tool_call":
            tool_calls.append(_tool_call(event))
        elif kind == "usage":
            usage = usage_add(usage, _usage_of(event))
        else:
            reason = event.get("reason") or "stop"
            ended = True
    if not ended:
        raise HarnessError(
            "the stream ended without an end event: %d text piece(s) and %d tool "
            "call(s) arrived, and there is no way to tell a finished turn from a "
            "dropped connection — retry or fail, do not guess" % (len(pieces),
                                                                  len(tool_calls)))
    return {"text": "".join(pieces), "tool_calls": tool_calls, "usage": usage,
            "reason": str(reason)}


def assistant_message(turn):
    """The turn as the message a provider would accept back."""
    if not isinstance(turn, dict):
        raise HarnessError("a turn is a dict, got %r" % (turn,))
    message = {"role": "assistant", "content": turn.get("text", "")}
    tool_calls = turn.get("tool_calls") or []
    if tool_calls:
        message["tool_calls"] = [{"id": call["id"], "name": call["name"],
                                  "arguments": dict(call["arguments"])}
                                 for call in tool_calls]
    return message

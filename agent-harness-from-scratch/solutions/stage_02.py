"""Agent Harness From Scratch — stage 2 solution: the context window is a budget,
not a list.

The reasoning lives in `stage_02.py`'s docstring (the design decisions are the
lesson); this file is the implementation. The estimator is the FIXED, documented
rule — `4` characters per token rounded up, `+4` per message, plus the canonical
JSON of `tool_calls` — because a budget you cannot recompute from the bytes you
are about to send is not a budget. The context keeps its system message pinned,
drops from the OLDEST end in whole turns (an assistant message plus the tool
observations answering it), and reports an over-budget newest unit through
`fits()` rather than hiding it.
"""

import json

from tiny_env import HarnessError

CHARS_PER_TOKEN = 4      # the fixed rule: rounded up, so short messages over-count
MESSAGE_OVERHEAD = 4     # the envelope: role, tool_call_id, is_error


def _require_count(name, value, minimum):
    """One budget number. Ints only: a bool is an int in Python, and `True` for a
    token budget is a bug, not a budget of one."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise HarnessError("%s must be an int, got %r (%s)"
                           % (name, value, type(value).__name__))
    if value < minimum:
        raise HarnessError("%s must be >= %d, got %r" % (name, minimum, value))
    return value


def _require_message(message, where):
    """A message is a dict with a string role. Everything downstream (a provider
    request, a trace, another stage's replay) assumes exactly that, and a
    KeyError two stages later is a worse answer than a refusal here."""
    if not isinstance(message, dict):
        raise HarnessError("%s: a message is a dict, got %s"
                           % (where, type(message).__name__))
    if not isinstance(message.get("role"), str):
        raise HarnessError("%s: a message needs a string 'role', got %r"
                           % (where, message.get("role")))
    return message


def _content(message):
    """The message's text. Wire shapes always carry a string; None means empty."""
    content = message.get("content")
    if content is None:
        return ""
    if not isinstance(content, str):
        raise HarnessError(
            "content must be a string, got %s: the estimator prices the bytes "
            "the model reads" % type(content).__name__)
    return content


def _canonical(tool_calls):
    """The tool calls as the provider sends them: compact JSON, keys sorted, so
    the counted length is a function of the VALUE and not of dict order. `repr`
    would price Python's spelling (`'x'`, `True`, a space after every colon) and
    a length that moves with insertion order."""
    return json.dumps(tool_calls, sort_keys=True, separators=(",", ":"))


def _call_ids(message):
    """The tool_call ids an assistant message holds. Not a message's identity:
    any other role holds none."""
    if message.get("role") != "assistant":
        return frozenset()
    calls = message.get("tool_calls") or ()
    if not isinstance(calls, (list, tuple)):
        raise HarnessError("tool_calls must be a list, got %s"
                           % type(calls).__name__)
    return frozenset(call.get("id") for call in calls if isinstance(call, dict))


def estimate_tokens(message):
    """One message's size, in tokens, by the documented fixed rule."""
    chars = len(_content(message))
    tool_calls = message.get("tool_calls")
    if tool_calls:
        # The payload of a tool-using assistant message lives HERE, not in
        # `content`: a 2 KB SQL statement that costs 4 tokens makes the budget a
        # lie at exactly the moment the budget matters.
        chars += len(_canonical(tool_calls))
    return MESSAGE_OVERHEAD + -(-chars // CHARS_PER_TOKEN)   # ceil(chars / 4)


class Context:
    """The messages to send, kept inside a prompt budget. See the stage docstring
    for why the system message is pinned, why trimming walks turns, and why the
    newest unit is never dropped."""

    def __init__(self, system, *, budget_tokens, reserve_tokens=0):
        _require_count("budget_tokens", budget_tokens, 1)
        _require_count("reserve_tokens", reserve_tokens, 0)
        _require_message(system, "Context(system=...)")
        if system["role"] != "system":
            raise HarnessError(
                "the pinned message must have role 'system', got %r" % system["role"])
        self._system = system
        self._budget_tokens = budget_tokens
        self._reserve_tokens = reserve_tokens
        self._history = []
        # A reserve that eats the whole window, and a system message bigger than
        # what is left, are the same fact: the prompt budget is smaller than the
        # message that can never be dropped, so nothing can be sent.
        if estimate_tokens(self._system) > self.budget:
            raise HarnessError(
                "the system message needs %d tokens and the prompt budget is %d: "
                "the system message is never dropped, so this context cannot "
                "hold anything" % (estimate_tokens(self._system), self.budget))

    @property
    def budget(self):
        """The PROMPT budget: the window minus the room the completion needs."""
        return self._budget_tokens - self._reserve_tokens

    @property
    def messages(self):
        """System first, kept history after it in original order (newest LAST).
        The concatenation is a fresh list per call: the context's own storage is
        not reachable through what it hands out."""
        return [self._system] + self._history

    def tokens(self):
        """The whole prompt, system message included."""
        return sum(estimate_tokens(message) for message in self.messages)

    def fits(self):
        """Whether the prompt fits the budget the completion reserve leaves. A
        False here is information, not an error: the newest unit stays even when
        it is the thing that does not fit."""
        return self.tokens() <= self.budget

    def add(self, message):
        """Append one message, then drop the oldest whole turns until it fits."""
        _require_message(message, "Context.add(message=...)")
        role = message["role"]
        if role == "system":
            raise HarnessError(
                "a context holds exactly one system message, pinned at "
                "construction; add() refuses a second one")
        if role == "tool":
            call_id = message.get("tool_call_id")
            held = any(call_id in _call_ids(other)
                       for other in self._history if other["role"] == "assistant")
            if not held:
                raise HarnessError(
                    "the tool observation for call %r answers no assistant message "
                    "in this context: the call/observation pair was split"
                    % (call_id,))
        self._history.append(message)
        self._trim()

    def _units(self):
        """The history as trimming units, oldest first. An assistant message that
        asked for tools opens a unit; the tool observations whose tool_call_id it
        holds belong to it. Every other message is a unit of its own."""
        units = []
        for message in self._history:
            if units:
                held, group = units[-1]
                if (message["role"] == "tool"
                        and message.get("tool_call_id") in held):
                    group.append(message)
                    continue
            units.append((_call_ids(message), [message]))
        return units

    def _trim(self):
        """Drop from the OLDEST end, one whole unit at a time, until the context
        fits or only the newest unit is left. The system message is not part of
        this list and is therefore not a candidate."""
        while True:
            if self.tokens() <= self.budget:
                return
            units = self._units()
            if len(units) <= 1:
                # The newest unit IS the prompt. Dropping it would send a context
                # whose question is gone; `fits()` reports the overflow instead.
                return
            self._history = [message for _, group in units[1:] for message in group]


def assemble(system, history, *, budget_tokens, reserve_tokens=0):
    """`history` (oldest first) reduced to what fits the prompt budget: the same
    result as a Context fed the history in order."""
    context = Context(system, budget_tokens=budget_tokens,
                      reserve_tokens=reserve_tokens)
    for message in history:
        context.add(message)
    return context.messages

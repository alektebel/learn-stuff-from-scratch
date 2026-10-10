"""Agent Harness From Scratch — stage 1: the model is a callable, and its answer
is an event stream.

DESIGN DECISION — why an event stream instead of a response object?
    Every provider hands you something different: an OpenAI `ChatCompletion`, an
    Anthropic `Message`, a stream of `chunk` objects, a websocket frame. A harness
    built around any one of them has that provider's wire format welded into the
    loop, the trace and the tests. A harness built around a vocabulary of EVENTS
    (`text`, `tool_call`, `usage`, `end`) can be fed by a scripted list in a test
    and by a real socket in production, and the part you cannot test — the socket —
    is the part you did not write. So: one stream in, one turn out.

DESIGN DECISION — why a TURN (a dict) and not the events?
    The events are the journey; the turn is the arrival. The harness asks one
    question of a model call — what did it say, what did it ask for, what did it
    cost, and why did it stop — and everything downstream (the loop, the trace,
    the ledger, the reward) is written against that answer. Keeping the events
    around as well would give four owners of the same facts and no authority.

DESIGN DECISION — why does a stream without `end` raise instead of finishing?
    Because a truncated stream and a finished one look identical once you have
    concatenated the text, and the difference is the whole conversation: a harness
    that treats `"the model stopped mid-sentence"` as `"the model is done"` sends a
    half answer to a person and a half message back to the model. `end` is the only
    source of `reason`, and its absence is `HarnessError`, not `reason="stop"`.

The stream is consumed ONCE: it is an iterator, and a harness that iterates it
twice sends the first half to the client and replays the second half from a
buffer nobody knows about. `collect` reads it once and returns the turn.

TODO: implement `collect`, `assistant_message` and `usage_add`.
"""

from tiny_env import HarnessError

# The vocabulary. Anything else on the wire is a HarnessError: a harness that
# ignores an event type it does not know is a harness that silently drops what a
# provider added last Tuesday.
EVENT_TYPES = ("text", "tool_call", "usage", "end")

# What a turn's usage starts at when the model reported none. Zeros, not None:
# a caller summing usage across a run must not need a special case for "the
# provider forgot", and a missing number that stays missing is a hole in a bill.
EMPTY_USAGE = {"input_tokens": 0, "output_tokens": 0}


def collect(events):
    """Consume an event iterator and return the turn it describes.

        {"text": str,                     # every text event, concatenated
         "tool_calls": [{"id", "name", "arguments"}, ...],   # in the order asked
         "usage": {"input_tokens": int, "output_tokens": int},
         "reason": "stop" | "tool_calls" | "length"}

    Rules, and each one is a mistake somebody has shipped:

    - `text` events APPEND. A stream sends deltas ("Hel", "lo"), so keeping the
      last one returns "lo" — a bug that looks like a model problem.
    - every `usage` event is SUMMED. A call that streams usage twice (a chunk at
      the start and a total at the end) must not be billed twice or once.
    - tool calls keep their order and their `id`, and their `arguments` are
      copied: the caller's event is not the harness's to hand out.
    - a `tool_call` without an `id` is a HarnessError: the observation answering
      it needs a `tool_call_id`, and inventing one is how a tool result lands on
      the wrong call.
    - the `end` event is the ONLY source of `reason`. No `end` → HarnessError.
      An event AFTER `end` → HarnessError (a provider that keeps talking after
      the end of a turn is not something to interpret).
    - an event whose `type` is not in EVENT_TYPES → HarnessError naming it.
    - usage the model never reported stays EMPTY_USAGE (zeros).
    """
    raise NotImplementedError("stage 1: implement collect()")


def assistant_message(turn):
    """The turn as the message a provider would accept back.

        {"role": "assistant", "content": turn["text"], "tool_calls": [...]}

    `tool_calls` is OMITTED when the turn made none — not an empty list. Several
    providers reject `"tool_calls": []` and every one of them treats the key as
    "this message asks for tools", so an empty list is a lie about the turn. The
    returned dict is fresh on every call: the caller appends it to the
    conversation and then mutates the conversation, and the turn it came from
    must not change under it.
    """
    raise NotImplementedError("stage 1: implement assistant_message()")


def usage_add(first, second):
    """Sum two usage dicts, defaulting missing keys to 0.

    Token counts are non-negative integers. A bool is not one (`isinstance(True,
    int)` is True in Python, and a provider that sends `true` for a count has sent
    a bug), and a negative count is a HarnessError: either is a number that will
    silently un-bill a run.
    """
    raise NotImplementedError("stage 1: implement usage_add()")

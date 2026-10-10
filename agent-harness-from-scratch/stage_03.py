"""Agent Harness From Scratch — stage 3: the loop, and what a budget exhaustion
returns.

DESIGN DECISION — why does the run RETURN an outcome instead of raising?
    "The model asked for eleven tools and I allowed five" is not an exception,
    it is a state a person has to see. An exception loses the half-finished
    conversation, which is exactly the part worth reading: the tools that ran,
    the text so far, what it cost. So the loop returns `status` — `"done"`,
    `"budget"` or `"truncated"` — with the partial answer and the messages that
    got there. A bug still raises; a budget does not.

DESIGN DECISION — why is `dispatch` a callable and not a `Dispatcher`?
    The loop has exactly one relationship with tools: hand one tool call over,
    get one observation back. Taking the whole registry would weld this stage to
    stage 4's, and then every test of the loop would need a tool table. A
    callable is the smallest thing that can answer, a fake answers in one line,
    and stage 4's `Dispatcher.observe` fits it without an adapter.

DESIGN DECISION — why append the assistant message BEFORE dispatching?
    Because the conversation must be well-formed at every instant, not only at
    the end. A provider rejects a `tool` message whose `tool_call_id` is not in
    the conversation above it; if the harness dispatches first and the process
    dies (or the dispatch raises), what is on disk is a tool result with no call,
    and every later attempt to resume that conversation is a 400. Record the
    request, then run it.

`max_steps` counts MODEL CALLS, not tool calls: a step is a turn of the
conversation, and a turn that runs six tools is still one step. The model is
never asked for another turn after the budget is spent — the point of a budget is
that the spender stops, and a harness that makes one last call to "finish
cleanly" has no budget at all.

TODO: implement `run`.
"""

from stage_01 import assistant_message, collect, usage_add

# What a run returns when it never got a turn out of the model at all.
EMPTY_USAGE = {"input_tokens": 0, "output_tokens": 0}

# The statuses a run can end in. `budget` and `truncated` are both "the answer is
# incomplete", and they are different failures: one is the harness's limit, the
# other is the model's.
STATUSES = ("done", "budget", "truncated")


def run(model, dispatch, question, *, system=None, tools=None, max_steps=8,
        trace=None, usage=None, clock=None):
    """Drive one conversation to a stop and return what happened.

        {"status": "done" | "budget" | "truncated",
         "answer": str,                  # the last text the model produced
         "messages": [...],              # the whole conversation, in order
         "steps": int,                   # model calls made
         "usage": {"input_tokens": int, "output_tokens": int}}

    - `model(messages, tools)` returns an event iterator (stage 1's vocabulary).
    - `dispatch(tool_call)` returns the tool MESSAGE that answers it.
    - the conversation starts as the system message (when given) and the
      question, and `tools` is handed to every model call unchanged.
    - one step is one model call. Stop when the turn's `reason` is `"stop"`.
    - `reason == "length"` ends the run as `"truncated"`: the model was cut off,
      so the answer is incomplete and calling it done is how a half sentence
      reaches a person.
    - `reason == "tool_calls"` with no tool calls is a HarnessError: the model
      said it wanted tools and asked for none, and a loop that treats that as
      "done" ends the conversation while the model thinks it is mid-action.
    - every tool call is dispatched, in order, and the assistant message that
      asked for them is already in `messages` when they are.
    - `max_steps` model calls, then `status="budget"` with the text so far. Never
      an extra call, never an exception.
    - `usage`, when given, is UPDATED in place with every turn's usage (it is the
      run's bill, and the caller keeps it across runs); the result carries it too.
    - `trace`, when given, is any object with `.step(**kwargs)`: one step per
      model call (`kind="model"`, `turn=`, `tokens=`) and one per tool call
      (`kind="tool"`, `tool=`, `ok=`), in that order.
    """
    raise NotImplementedError("stage 3: implement run()")

"""Agent Harness From Scratch — stage 7: compaction, summarize the middle.

SOLUTION. `compact` walks TURNS, never messages: an assistant message opens a
turn and the tool messages that answer it belong to that turn, so every cut is a
whole-turn cut and an observation can never lose the call it answers — a real
provider rejects a `tool` message whose call is gone with a 400, which is the
failure this stage exists to prevent. The system prompt is not history and is
never touched; the newest turn is what the model just did and is never
summarized away; everything older becomes ONE message carrying `SUMMARY_PREFIX`.
A context that already fits is returned unchanged (the SAME list) and `summarize`
is not called at all, so running this every round cannot shrink a context into
nothing.
"""

import json

from tiny_env import HarnessError

SUMMARY_PREFIX = "Summary of the earlier conversation: "


def _local_estimate(message):
    """stage_02's fixed rule, as the fallback: 4 characters per token rounded
    up, +4 per message, with `tool_calls` counted as its canonical JSON (a 2 KB
    query the estimator ignores makes every budget a lie)."""
    content = message.get("content")
    chars = len(content) if isinstance(content, str) else 0
    calls = message.get("tool_calls")
    if calls:
        chars += len(json.dumps(calls, sort_keys=True, separators=(",", ":"),
                                default=str))
    return -(-chars // 4) + 4


def _estimate(message):
    """stage_02's `estimate_tokens` when it is on disk and implemented, this
    stage's own rule otherwise. The import is lazy and the fallback is real on
    purpose: stage 7 is graded on its own, and a sibling that is still a
    template must not change what "fits" means here."""
    try:
        from stage_02 import estimate_tokens
    except Exception:                       # not on sys.path yet: a sibling in flight
        estimator = None
    else:
        estimator = estimate_tokens
    if estimator is not None:
        try:
            return int(estimator(message))
        except NotImplementedError:         # stage_02 is still its template
            pass
    return _local_estimate(message)


def _total(messages):
    """The prompt cost of a list of messages, with the same estimator the
    budget was written in."""
    return sum(_estimate(message) for message in messages)


def _split(messages):
    """(the leading system messages, the turn blocks).

    A turn is atomic: an assistant message plus every `tool` message that
    answers it, or a single other message. Grouping this way is what makes a
    cut safe — a block is kept or replaced whole, so a call and its
    observations travel together."""
    system = []
    index = 0
    while index < len(messages) and messages[index].get("role") == "system":
        system.append(messages[index])
        index += 1
    turns = []
    for message in messages[index:]:
        if message.get("role") == "tool" and turns and turns[-1][0].get("role") == "assistant":
            turns[-1].append(message)
        else:
            turns.append([message])
    return system, turns


def _middle_and_tail(messages):
    """What gets summarized, and what stays verbatim.

    The tail starts at the LAST assistant-anchored block: the turn the model
    just took, plus anything after it (a following user message). Every older
    turn is dropped from the front of the tail pair-safely — a whole turn at a
    time — and becomes the middle. With no older turn there is nothing to
    summarize and nothing this stage is allowed to throw away, which is a
    `HarnessError`, not a silent drop."""
    system, turns = _split(messages)
    start = None
    for index in range(len(turns) - 1, -1, -1):
        if turns[index][0].get("role") == "assistant":
            start = index
            break
    if start is None or start == 0:
        raise HarnessError(
            "compaction has nothing to summarize: this context is over budget but "
            "it holds no turn older than the newest one, and the newest turn is "
            "never summarized away or dropped (%d message(s), %d token(s))"
            % (len(messages), _total(messages)))
    middle = [message for turn in turns[:start] for message in turn]
    return system, middle, turns[start:]


def compact(messages, *, budget_tokens, summarize, reserve_tokens=0):
    """Replace the older conversation with one summary message, or return
    `messages` untouched when it already fits.

    The prompt budget is `budget_tokens - reserve_tokens` — the reserve is the
    room the caller keeps for the completion, exactly as in stage_02, so every
    "fits" here is about the PROMPT. `summarize` is called at most once, with
    the middle only: never with the system prompt (it is instruction, not
    history) and never with the kept tail (summarizing what the model just did
    is how a harness makes it forget). When even the system prompt, the summary
    and the newest turn do not fit, this raises `HarnessError` naming what is
    too big rather than returning a prompt the provider will reject."""
    prompt_budget = budget_tokens - reserve_tokens
    if _total(messages) <= prompt_budget:
        return messages

    system, middle, tail = _middle_and_tail(messages)
    summary = {"role": "user", "content": SUMMARY_PREFIX + summarize(middle)}
    kept = list(system) + [summary] + [message for turn in tail for message in turn]
    if _total(kept) > prompt_budget:
        raise HarnessError(
            "compaction cannot fit the prompt budget: %d token(s) (%d after the "
            "%d-token completion reserve) cannot hold the system prompt (%d "
            "token(s)), the summary of the earlier conversation (%d token(s)) and "
            "the newest turn (%d token(s)). The system prompt is never summarized "
            "or dropped and the newest turn is never summarized away."
            % (budget_tokens, prompt_budget, reserve_tokens, _total(system),
               _estimate(summary), _total([message for turn in tail for message in turn])))
    return kept

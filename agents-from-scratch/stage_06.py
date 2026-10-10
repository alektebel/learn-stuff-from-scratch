"""Agents From Scratch — stage 6: memory across turns, and the window that stays
a conversation

A session is what turns the one-shot loop of stage 1 into something you can talk
to: it owns the transcript across turns, decides how much of it the model gets
to see, and keeps the few facts that must never fall out of view.

DESIGN DECISION — a TURN, not a message, is the unit the window counts.
    A turn is one user message plus everything the agent appended until the next
    user message: the assistant tool calls, the results, and the final answer.
    Counting messages is the obvious implementation and it is wrong — a window
    of N messages will eventually cut an assistant tool call away from the tool
    result that answers it, which is a transcript no API accepts and a model
    cannot read (stage 1's pairing rule, applied to trimming). Cutting on turn
    boundaries makes that impossible: the call and its result were never in
    separate units.

DESIGN DECISION — pins ride in the system message.
    A small set of facts ("the deploy key lives in /etc/app/key") has to reach
    the model on every request, however far back the turn that mentioned it has
    slipped. Putting them anywhere in history means the window will eventually
    trim them, so they are appended to the system message, which is rebuilt on
    every call — the one place trimming cannot reach. A memory you have to
    remember to re-pin is not memory.

DESIGN DECISION — the transcript is complete; the view is bounded.
    `.messages` is everything that ever happened, in order: it is the record,
    and no window can be smaller than the record without losing the ability to
    answer "what did we talk about". `view()` is the projection the model sees
    this turn, built fresh from the current state each time. Trimming the stored
    transcript instead of the projection destroys the session in order to fit
    the window, which is the bug that makes "memory" mean "amnesia".

DESIGN DECISION — view() returns copies.
    The message list handed to the model is a snapshot, not a live view. If it
    aliased the transcript, the loop's own appends and the caller's inspection
    would write into each other, and a session's history would depend on who
    read it when.

TODO: implement

    class Session:
        __init__(self, model, toolbox, *, system=None, window=6)
            model and toolbox are stage 1's: model(messages) decides,
            toolbox.call(name, args) answers. `system` is the system prompt or
            None, `window` the number of turns kept in the view (>= 1).

            Attributes:
                .model, .toolbox  the callables, stored as given
                .system           the system prompt, or None
                .window           turns kept in the view
                .messages         list — the FULL transcript, everything that
                                  ever happened, in order. No system message
                                  ever lives here: the header belongs to the
                                  view, and ask() appends only user/assistant/
                                  tool messages
                .pins             list[str] — the pinned facts, in order
                .turns            int — user messages seen so far

        pin(self, fact) -> None
            Add `fact` to .pins. An EXACT repeat is not added twice: the caller
            restating something must not grow the prompt every time.

        view(self) -> list
            The messages actually sent this turn, in order:
              * the system message, only when `system` or `pins` is non-empty:
                  {"role": "system", "content": <the non-empty parts of
                   [system, *pins], joined with "\n">}
                so with system="SYS" and pins ["a", "b"] the content is
                "SYS\na\nb"; with pins alone it is "a\nb" (never "None\na");
                and with neither there is no system message at all
              * then the last `window` turns of .messages, in order, taken from
                the transcript (window=1 is the current turn, which is what
                makes a single-turn request in a long session)
            What is returned are COPIES: appending to it, or editing a content
            string or an args dict in it, must not change .messages and must not
            change what the next view() returns.

        ask(self, text, max_steps=8) -> dict
            Append {"role": "user", "content": text} to .messages, count the
            turn, build view(), and hand it to stage 1 as the transcript to
            continue:
                run_agent(self.model, self.toolbox, None, messages=view(),
                          max_steps=max_steps)
            Then append BACK ONLY THE NEW MESSAGES — run["messages"][len(view)]
            — and return
                {"answer": run["answer"],    # the loop's final text, or None
                 "status": run["status"],    # "answered" | "max_steps" | ...
                 "steps": run["steps"],
                 "tool_calls": run["tool_calls"],
                 "turns": self.turns}        # after this turn
            The full transcript keeps growing; only the view is bounded, and the
            loop's answer and status are the caller's, not something ask()
            re-derives from the last message.
"""


class Session:
    def __init__(self, model, toolbox, *, system=None, window=6):
        raise NotImplementedError("stage 6: implement Session.__init__()")

    def pin(self, fact):
        raise NotImplementedError("stage 6: implement Session.pin()")

    def view(self):
        raise NotImplementedError("stage 6: implement Session.view()")

    def ask(self, text, max_steps=8):
        raise NotImplementedError("stage 6: implement Session.ask()")

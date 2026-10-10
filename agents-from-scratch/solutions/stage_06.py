"""Agents From Scratch — stage 6: memory across turns, and the window that stays
a conversation

SOLUTION. The session keeps the whole transcript and projects a bounded view
from it: the window counts turns, so the cut always lands on a turn boundary and
a tool call can never be separated from its result. Pins are joined into the
system message, which is rebuilt on every call and is the one place trimming
cannot reach. `ask` appends the user message, sends the view, and copies back
only what the loop added.
"""

from stage_01 import run_agent


def _copy(message):
    # What the model is shown is a snapshot: the caller and the loop both hold
    # the transcript, so the message and its args are copied, never shared.
    out = dict(message)
    if isinstance(out.get("args"), dict):
        out["args"] = dict(out["args"])
    return out


class Session:
    def __init__(self, model, toolbox, *, system=None, window=6):
        if window < 1:
            raise ValueError(
                f"window={window}: a window of zero turns is not a conversation "
                f"— the current turn is always visible, so the smallest window "
                f"is 1")
        self.model = model
        self.toolbox = toolbox
        self.system = system
        self.window = window
        self.messages = []   # everything that ever happened, in order
        self.pins = []       # the facts that must outlive the window
        self.turns = 0       # user messages seen

    def pin(self, fact):
        # An exact repeat is noise in every prompt from here on: the caller
        # saying the same thing twice does not mean it twice.
        if fact not in self.pins:
            self.pins.append(fact)

    def view(self):
        starts = [i for i, m in enumerate(self.messages)
                  if m.get("role") == "user"]
        # The cut lands on the start of a turn, never between a call and the
        # result that answers it — that is the whole reason the window counts
        # turns instead of messages.
        first = starts[-self.window] if len(starts) > self.window else 0
        history = [_copy(m) for m in self.messages[first:]]

        # The header is rebuilt from the current state on every call, so a pin
        # stays visible however far its turn has slipped out of the window.
        header = "\n".join(p for p in [self.system, *self.pins] if p)
        if header:
            return [{"role": "system", "content": header}] + history
        return history

    def ask(self, text, max_steps=8):
        self.messages.append({"role": "user", "content": text})
        self.turns += 1
        outbound = self.view()
        run = run_agent(self.model, self.toolbox, None, messages=outbound,
                        max_steps=max_steps)
        # run_agent echoes the transcript it was given; only what it appended is
        # new, and copying the echo back would duplicate every earlier turn.
        self.messages.extend(run["messages"][len(outbound):])
        return {"answer": run["answer"], "status": run["status"],
                "steps": run["steps"], "tool_calls": list(run["tool_calls"]),
                "turns": self.turns}

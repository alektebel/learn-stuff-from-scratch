"""Agents From Scratch — stage 9: budgets, and the reason a run stopped

SOLUTION. `Budgets` is a small ledger: `charge` refuses, and does not record, a
charge that would break a cap, so no counter ever reads cap+1 and the loop can
promise "exactly at the cap". `would_exceed` is the read-only half of that,
which is the half the loop asks before it spends anything. `tokens_for` is the
documented `len(text) // 4` proxy, not a tokenizer. `run_budgeted` re-implements
stage 1's loop because a budget must refuse the call BEFORE making it, and it
charges the tool result as well as the model decision — the direction people
forget. `partial` carries the last successful observation out of a run that
stopped, so a blown budget is still an answer rather than a blank.
"""

import json

# The fixed reporting order. When one charge would break several caps at once
# the first of these names the stop, so the same script always reports the same
# reason instead of whichever dict happened to be iterated first.
_ORDER = ("steps", "tool_calls", "tokens", "seconds")


def tokens_for(text):
    """The course's crude proxy for tokens: four characters to the token.

    Not a tokenizer and not pretending to be one. It exists so a stage can bill
    a prompt with only the standard library, and so a 4000-character tool result
    is visibly 1000 tokens; a real runtime gets this number from the provider.
    """
    return len(text) // 4


class BudgetExhausted(Exception):
    """A charge would have broken the cap named in `.name`."""

    def __init__(self, name):
        super().__init__(name)
        self.name = name


class Budgets:
    """The caps a run may spend, and how much of each it has spent.

    An unset cap is unlimited, not zero, so `limits` holds only the caps that
    were given and `used` holds exactly the same keys. That keeps `used` from
    growing entries for budgets nobody set: a caller iterating it can never ask
    "how much of the tokens budget did we spend" of a run that has no tokens
    budget.
    """

    def __init__(self, *, steps=None, tool_calls=None, tokens=None, seconds=None,
                 **unknown):
        # Keyword-only parameters would turn a typo into Python's TypeError
        # before the constructor could say which name is wrong, and the caller
        # deserves to be told that `stpes` is not a budget at all. Both are
        # ValueError: the caller's mistake is the same one either way.
        if unknown:
            raise ValueError(
                f"unknown budget name(s) {sorted(unknown)}: the caps are "
                f"steps, tool_calls, tokens and seconds")
        given = {"steps": steps, "tool_calls": tool_calls,
                 "tokens": tokens, "seconds": seconds}
        for name, cap in given.items():
            if cap is not None and cap <= 0:
                raise ValueError(
                    f"{name}={cap!r} is not a cap: zero or less forbids the "
                    f"run's first unit, which is a run that can never start, "
                    f"not a run on a short leash")
        self.limits = {name: cap for name, cap in given.items() if cap is not None}
        self.used = {name: 0 for name in self.limits}

    def would_exceed(self, *, steps=0, tool_calls=0, tokens=0, seconds=0.0):
        """The first cap this charge would break, in the fixed order, or None.

        Read-only on purpose: the loop asks this on the path where it is about
        to stop, and a question that spends the budget it is asking about would
        turn "can I afford one more?" into the very overspend it is checking
        for.
        """
        charge = {"steps": steps, "tool_calls": tool_calls,
                  "tokens": tokens, "seconds": seconds}
        for name in _ORDER:
            if name not in self.limits:
                continue
            if self.used[name] + charge[name] > self.limits[name]:
                return name
        return None

    def charge(self, *, steps=0, tool_calls=0, tokens=0, seconds=0.0):
        """Record a charge, or refuse all of it and raise BudgetExhausted.

        A refused charge is not recorded, and no part of it is: a run that
        cannot afford the step it is about to take did not take it, so `used`
        stays honest and never reads cap+1. Recording half of a bundled charge
        would be worse than recording none — the ledger would claim the run paid
        for a step that was refused.
        """
        charge = {"steps": steps, "tool_calls": tool_calls,
                  "tokens": tokens, "seconds": seconds}
        name = self.would_exceed(**charge)
        if name is not None:
            raise BudgetExhausted(name)
        for key in self.used:
            self.used[key] += charge[key]


def _copy(message):
    out = dict(message)
    if isinstance(out.get("args"), dict):
        out["args"] = dict(out["args"])
    return out


def _rendered(decision):
    """What the model said, as the text a budget is billed for.

    A final answer is charged as the answer itself; a tool call is charged as
    the JSON of the request, because that (not just the arguments) is what the
    model put into the transcript. `default=str` keeps a malformed decision —
    which is stage 4's problem, not the budget's — from crashing the billing.
    """
    if isinstance(decision, dict) and "final" in decision:
        return str(decision["final"])
    return json.dumps(decision, sort_keys=True, default=str)


def _admit(ledger, **charge):
    """Apply one charge; return the cap that refused it, or None if it fit."""
    try:
        ledger.charge(**charge)
    except BudgetExhausted as exc:
        return exc.name
    return None


def run_budgeted(model, toolbox, task, *, budgets, clock, system=None,
                 tokens_for=tokens_for):
    ledger = budgets if budgets is not None else Budgets()  # None is unlimited

    transcript = []
    if system:
        transcript.append({"role": "system", "content": system})
    if task is not None:
        transcript.append({"role": "user", "content": task})

    seen = []
    tool_calls = []
    partial = None
    tokens = 0
    steps = 0
    started = last = clock()
    elapsed = 0.0
    stopped_by = None
    answer = None
    status = "budget"   # anything that leaves this loop unfinished is a budget

    while True:
        now = clock()
        elapsed = now - started
        # One reading per turn, charged as a delta, because a clock only reports
        # what has already passed: a seconds cap is the one cap that cannot be
        # refused in advance, only noticed between two turns. The counts are the
        # caps a run can promise to hit exactly; the clock is the one it may
        # notice late, and that difference is worth stating out loud.
        refused = _admit(ledger, steps=1, seconds=now - last)
        last = now
        if refused is not None:
            stopped_by = refused
            break

        shown = [_copy(m) for m in transcript]
        seen.append(shown)
        steps += 1
        decision = model(shown)
        rendered = _rendered(decision)

        if isinstance(decision, dict) and "final" in decision:
            refused = _admit(ledger, tokens=tokens_for(rendered))
            if refused is not None:
                stopped_by = refused
                break
            tokens += tokens_for(rendered)
            answer = decision["final"]
            transcript.append({"role": "assistant", "content": answer})
            status = "answered"
            break

        # Anything that is not a final answer is a tool call as far as this loop
        # is concerned, malformed included — the same rule as stage 1, because
        # the toolbox is what turns that into an observation the model can read.
        name = decision.get("tool") if isinstance(decision, dict) else None
        args = decision.get("args") if isinstance(decision, dict) else None
        # The request and the execution it asks for are one charge: the tokens
        # the model just spent, and the call it wants next. Bundling them lets
        # the fixed order name the stop when both would break at once.
        refused = _admit(ledger, tool_calls=1, tokens=tokens_for(rendered))
        if refused is not None:
            stopped_by = refused
            break
        tokens += tokens_for(rendered)

        transcript.append({"role": "assistant", "tool": name, "args": args})
        outcome = toolbox.call(name, args)
        content = outcome.get("content", "")
        ok = bool(outcome.get("ok"))
        transcript.append({"role": "tool", "tool": name,
                           "ok": ok, "content": content})
        tool_calls.append(name)
        if ok:
            # Only a success counts as something learned; a failed call is an
            # observation for the model, not a partial answer for the caller.
            partial = content

        # The other direction of the bill: the result goes back into the prompt.
        # The tool has already run, so this charge can only be refused and never
        # anticipated — and a huge tool result is exactly how a token budget is
        # supposed to die. The call and its answer stay in the transcript so the
        # pairing rule survives even the stop.
        refused = _admit(ledger, tokens=tokens_for(content))
        if refused is not None:
            stopped_by = refused
            break
        tokens += tokens_for(content)

    return {"status": status, "answer": answer, "steps": steps,
            "tool_calls": tool_calls, "messages": transcript, "seen": seen,
            "stopped_by": stopped_by, "partial": partial, "seconds": elapsed,
            "tokens": tokens, "tool_calls_made": len(tool_calls)}

"""Agents From Scratch — stage 9: budgets, and the reason a run stopped

DESIGN DECISION — a budget refuses the call it cannot pay for, so the cap is
never the overshoot.
    Stage 1 stops at max_steps because the loop counts before it calls. A budget
    is that same idea generalised: a cap on steps, tool calls, tokens and
    seconds, checked BEFORE the thing that costs. If the check lives after the
    call, a cap of 3 becomes "3, and then one more that we notice afterwards",
    and every number the run reports is a lie by one. The counts are the caps a
    run can promise to hit exactly — 3 steps means exactly 3 model calls,
    2 tool calls means the tool ran exactly twice — and the check asserts the
    overshoot, not just the status, because the status is easy and the count is
    the promise.

DESIGN DECISION — a stop is a result, not an exception.
    Running out of budget is the ordinary end of an agent, not a crash: the
    caller gets the transcript, the last thing the agent learned, and a reason.
    So the stop returns status "budget" with `stopped_by` naming the cap, and
    answer None. `stopped_by` is a name ("steps", "tool_calls", "tokens",
    "seconds"), never a message to parse. When one charge would break several
    caps at once they are reported in the fixed order steps, tool_calls, tokens,
    seconds, so two runs of the same script report the same reason.

DESIGN DECISION — `partial` is what keeps a stopped run from being empty.
    A run that dies on its 20th tool call has usually already learned something,
    and throwing that away because the final answer never came is how you turn a
    budget into a data loss. `partial` is the content of the last tool result
    with ok=True — the last thing the model was actually told — or None if no
    tool ever succeeded.

DESIGN DECISION — the clock is injected.
    `run_budgeted` takes `clock`, a zero-argument callable returning seconds.
    Nothing in this stage calls time.time() and nothing sleeps: a seconds budget
    can only be tested deterministically with a scripted clock, and a real sleep
    in a test suite is a broken test suite. The clock is read, never waited on.
    Note that the counts can be refused in advance but elapsed time cannot — a
    clock only reports what has already passed, so a seconds cap is noticed at
    the next reading, possibly a little late. That is a property of wall clocks,
    not of this loop, and the other three caps are the ones that hold exactly.

DESIGN DECISION — tokens are charged in both directions.
    Every prompt the model reads is tokens: the decision the model just made
    (the tool-call JSON, or the final text) and every tool result handed back to
    it. Charging only the model's side is the mistake that makes a token budget
    useless, because a tool's output is the one part of the prompt the agent
    author did not write. `tokens_for` is a crude proxy — `len(text) // 4` — not
    a tokenizer; it is injectable so a caller with a real one can pass it in.

TODO: implement

    tokens_for(text) -> int
        The proxy: four characters to the token. Documented as a proxy, never
        as a tokenizer.

    class BudgetExhausted(Exception)
        Carries `.name`, the cap whose charge was refused.

    class Budgets:
        Budgets(*, steps=None, tool_calls=None, tokens=None, seconds=None)
            Caps are keyword-only and all optional; `None` means unlimited, and
            an unset cap is unlimited rather than zero. Reject with a ValueError
            (at construction, not on the first charge) an unknown budget name —
            the trailing `**unknown` exists so the class itself can name the
            typo instead of leaving it to Python's TypeError — and a cap that is
            zero or negative, which is a run that can never take its first unit.
        .limits -> dict {name: cap} of only the caps that were set.
        .used   -> dict of exactly the same keys, starting at 0.
        .would_exceed(*, steps=0, tool_calls=0, tokens=0, seconds=0.0) -> str | None
            The name of the first cap this charge WOULD break, in the fixed
            order steps, tool_calls, tokens, seconds; None if it fits. A charge
            that lands exactly on a cap fits (the comparison is `>`, never
            `>=`). This is a question: it must not change `used`.
        .charge(*, steps=0, tool_calls=0, tokens=0, seconds=0.0) -> None
            Record the charge, or raise BudgetExhausted(name) if it would
            exceed a cap. A refused charge is not recorded — not even the parts
            of it that would have fitted — because the run that cannot afford
            the step did not take it.

    run_budgeted(model, toolbox, task, *, budgets, clock, system=None,
                 tokens_for=tokens_for) -> dict
        Same model/toolbox/message protocol as stage 1, driven by this stage's
        own loop, because the charge has to happen BEFORE the call. `toolbox` is
        the stage 1 shape (`.names`, `.call(name, args) -> {"ok", "content"}`);
        `budgets=None` means unlimited; `clock()` returns seconds since some
        fixed origin, and the only elapsed time the run reports is the
        difference between two readings of it.

        The loop, per turn:
          1. read the clock, charge one step and the time since the last charge,
             and stop with "steps" (or "seconds") if either would break;
          2. call the model on the transcript as it stands;
          3. {"final": text} -> charge its tokens, then append it and answer;
          4. {"tool": n, "args": a} -> charge one tool call plus the tokens of
             the decision, then append the assistant call, execute the tool,
             append the paired tool result, remember it as `partial` when
             ok=True, and charge the tokens of that result as well — stopping
             with "tokens" there if the result does not fit, because by then the
             tool has run and the charge can only be refused, not anticipated.

        Returns stage 1's keys (`status`, `answer`, `steps`, `tool_calls`,
        `messages`, `seen`) plus:
            {"stopped_by": "steps" | "tool_calls" | "tokens" | "seconds" | None,
             "partial": str | None,   # content of the last ok=True tool result
             "seconds": float,        # elapsed, from the injected clock only
             "tokens": int,           # charged in both directions
             "tool_calls_made": int}  # how many times the tool actually ran

        When a budget stops the run: status "budget", answer None, `stopped_by`
        naming the first cap in the fixed order that would have broken, and the
        transcript still a valid conversation — a call and its result stay
        paired, and a tool call that was refused is never appended at all.
"""


def tokens_for(text):
    """The crude proxy for tokens: four characters to the token."""
    raise NotImplementedError("stage 9: implement tokens_for()")


class BudgetExhausted(Exception):
    """A charge would have broken the cap named in `.name`.

    TODO: implement — the constructor stores the cap's name in `self.name`.
    """

    def __init__(self, name):
        raise NotImplementedError("stage 9: implement BudgetExhausted")


class Budgets:
    """The caps a run may spend, and how much of each it has spent.

    TODO: implement — `.limits`, `.used`, `would_exceed()` and `charge()`.
    """

    def __init__(self, *, steps=None, tool_calls=None, tokens=None, seconds=None,
                 **unknown):
        raise NotImplementedError("stage 9: implement Budgets")

    def would_exceed(self, *, steps=0, tool_calls=0, tokens=0, seconds=0.0):
        raise NotImplementedError("stage 9: implement Budgets.would_exceed()")

    def charge(self, *, steps=0, tool_calls=0, tokens=0, seconds=0.0):
        raise NotImplementedError("stage 9: implement Budgets.charge()")


def run_budgeted(model, toolbox, task, *, budgets, clock, system=None,
                 tokens_for=tokens_for):
    raise NotImplementedError("stage 9: implement run_budgeted()")

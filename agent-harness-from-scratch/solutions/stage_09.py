"""Agent Harness From Scratch — stage 9 solution: process reward — a step has to
be grounded in what came back.

The reasoning lives in `stage_09.py`'s docstring; this file is the implementation.
"""

import re

from tiny_env import HarnessError

CRITERIA = ("ran", "grounded", "novel")


def _cells(result):
    """Every cell of a result, however it was handed over."""
    if result is None:
        return []
    if isinstance(result, dict):
        return _cells(result.get("rows", []))
    out = []
    if isinstance(result, (list, tuple)):
        for item in result:
            out.extend(_cells(item))
    else:
        out.append(result)
    return out


def _spelling(value):
    """The text forms of one cell. A float whose integer spelling is exact gets
    one too: `490.0` is written back as "490" by every person, and a grounding
    check that only accepts "490.0" fails the honest step."""
    if value is None:
        return []
    if isinstance(value, bool):
        return [str(value)]
    if isinstance(value, float):
        forms = [repr(value), str(value)]
        if value.is_integer():
            forms.append(str(int(value)))
        return forms
    if isinstance(value, int):
        return [str(value)]
    return [str(value)]


def cite_values(result):
    """Every value a result contains, as text a model could have written."""
    seen = []
    for cell in _cells(result):
        for form in _spelling(cell):
            if form and form not in seen:
                seen.append(form)
    return seen


def _squash(text):
    """Lowercase, collapse whitespace: the reasoning was written by a model, and
    a newline inside a number is not a different number."""
    return " ".join(str(text).lower().split())


def _message_of(value):
    """`160` matches on boundaries, `furniture` matches as a substring: a number
    is inside a longer number ("1600"), a category is not inside a longer
    category ("furniture-and-appliances" is the same category)."""
    return re.compile(r"(?<!\w)%s(?!\w)" % re.escape(_squash(value)))


def cites_previous_result(reasoning, previous_result):
    """Does `reasoning` mention a value the previous step returned?"""
    if previous_result is None:
        return False
    values = cite_values(previous_result)
    if not values:
        return False
    text = _squash(reasoning)
    for value in values:
        squashed = _squash(value)
        if not squashed:
            continue
        # A value that is a number on its own gets boundaries; a value that has
        # any letter in it is matched as a plain substring.
        if re.fullmatch(r"[-+]?\d+(\.\d+)?", squashed):
            if _message_of(squashed).search(text):
                return True
        elif squashed in text:
            return True
    return False


def _ok_of(step, index):
    ok = step.get("ok", False)
    if not isinstance(ok, bool):
        raise HarnessError(
            "step %d: 'ok' must be a bool, got %r (%s) — a truthy string pays a "
            "step that failed" % (index, ok, type(ok).__name__))
    return ok


def _normalised_sql(sql, index):
    if not isinstance(sql, str) or not sql.strip():
        raise HarnessError("step %d: every step names the query it ran, got %r"
                           % (index, sql))
    return " ".join(sql.lower().split())


def process_reward(steps):
    """The mean over steps of `(ran + grounded + novel) / 3`, in `[0, 1]`."""
    if not isinstance(steps, (list, tuple)):
        raise HarnessError("process_reward takes the episode's steps, got %r"
                           % (type(steps).__name__,))
    if not steps:
        return 0.0
    seen = set()
    total = 0.0
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise HarnessError("step %d is a dict, got %r" % (index, step))
        ran = _ok_of(step, index)
        sql = _normalised_sql(step.get("sql"), index)
        novel = sql not in seen
        seen.add(sql)
        if index == 0:
            grounded = True                    # nothing to cite yet
        else:
            grounded = cites_previous_result(step.get("reasoning", ""),
                                             steps[index - 1].get("result"))
        total += (int(ran) + int(grounded) + int(novel)) / 3.0
    reward = total / len(steps)
    if not 0.0 <= reward <= 1.0:               # a mean of terms in [0,1]: a lie here
        raise HarnessError("process_reward produced %r, outside [0, 1]" % (reward,))
    return reward

"""Agent Harness From Scratch — stage 10 solution: verification and the
self-generated data loop.

The reasoning lives in `stage_10.py`'s docstring; this file is the implementation.
"""

from tiny_env import EnvError, HarnessError, Task, TEMPLATES, numeric_columns

NUMERIC_TOLERANCE = 1e-6

ATTEMPT_LIMIT = 200

# How deep a result may nest before the unwrap gives up. Not a policy, a guard:
# a self-referential structure must not hang a verifier that promises to return
# 0.0 rather than raise.
_UNWRAP_DEPTH = 8


def _unwrap(answer, depth=0):
    """The value inside the wrappers a result arrives in."""
    if depth >= _UNWRAP_DEPTH:
        return answer
    if isinstance(answer, dict):
        if "rows" in answer:
            return _unwrap(answer["rows"], depth + 1)
        return answer
    if isinstance(answer, (list, tuple)) and len(answer) == 1:
        return _unwrap(answer[0], depth + 1)
    return answer


def _as_number(value):
    """The number a value denotes, or None. A bool is not a number here: `True`
    is 1 in Python and `True == 1.0` is how a yes/no answer scores against a
    count."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def make_verifier(gold):
    """A callable that scores an answer against `gold`: `1.0` or `0.0`, never an
    exception."""
    if gold is None:
        def unanswerable(answer):
            return 0.0
        return unanswerable

    gold_number = None if isinstance(gold, (str, bool)) else _as_number(gold)
    gold_text = gold.strip().casefold() if isinstance(gold, str) else None

    def verify(answer):
        # Every path out of here is a number, and only a real mismatch is 0.0:
        # an exception would lose the episode, so a bug in this function shows up
        # as a verifier that fails everything (which the check would notice).
        try:
            value = _unwrap(answer)
            if gold_number is not None:
                number = _as_number(value)
                if number is None:
                    return 0.0
                return 1.0 if abs(number - gold_number) <= \
                    NUMERIC_TOLERANCE * max(1.0, abs(gold_number)) else 0.0
            if gold_text is not None:
                if not isinstance(value, str):
                    return 0.0
                return 1.0 if value.strip().casefold() == gold_text else 0.0
            return 1.0 if value == gold else 0.0
        except Exception:                      # noqa: BLE001 - the promise
            return 0.0

    return verify


def _fillings(env, template):
    """Every `(sql, question)` this template can be filled with, in a
    deterministic order (table, then numeric column, then value)."""
    schema = env.schema()["tables"]
    declared = template.get("table")
    tables = env.tables() if declared in (None, "{table}") else [declared]
    for table in tables:
        if table not in schema:
            continue
        numeric = sorted(numeric_columns(env, table))
        if template.get("needs_number") and not numeric:
            continue               # AVG(region) FROM regions is not a question
        columns = numeric if template.get("needs_number") else [None]
        for column in columns:
            holes = {"table": table}
            if column is not None:
                holes["column"] = column
            lists = sorted((template.get("values") or {}).items())
            if not lists:
                yield dict(holes), table
                continue
            for name, values in lists:
                for value in values:
                    yield dict(holes, **{name: value}), table


def generate_tasks(env, n, *, templates=TEMPLATES, limit=ATTEMPT_LIMIT):
    """`n` questions nobody wrote by hand, each with the executor's own answer."""
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise HarnessError("generate_tasks was asked for %r tasks" % (n,))
    tasks = []
    seen = set()
    attempts = 0
    exhausted = None
    for template in templates:
        for holes, _table in _fillings(env, template):
            if len(tasks) >= n:
                break
            if attempts >= limit:
                break
            attempts += 1
            try:
                sql = template["sql"].format(**holes)
                question = template["question"].format(**holes)
            except (KeyError, IndexError):
                continue          # a hole nobody filled: not a question
            if sql in seen:
                continue
            try:
                result = env.exec(sql)
            except EnvError:
                continue          # the world refused: not a question either
            rows = result.get("rows") or []
            if len(rows) != 1 or len(rows[0]) != 1:
                continue          # a question with one answer, or a table
            gold = rows[0][0]
            if gold is None:
                continue          # nobody can answer a NULL
            seen.add(sql)
            tasks.append(Task("G%d" % (len(tasks) + 1), question, sql, gold,
                              template.get("kind", "text")))
        if len(tasks) >= n:
            break
        exhausted = template.get("name")
    if len(tasks) < n:
        raise HarnessError(
            "generate_tasks: asked for %d task(s), built %d after %d candidate(s) "
            "(last template: %r) — these templates cannot make that many "
            "answerable questions" % (n, len(tasks), attempts, exhausted))
    return tasks


def _solved(agent, task):
    """Did the agent solve this task? An agent that crashes failed THIS task: a
    solver returning None or a stray type is a wrong answer, not the end of the
    round."""
    try:
        answer = agent(task)
    except Exception:                          # noqa: BLE001
        return False
    return make_verifier(task.gold)(answer) >= 1.0


def self_improve_round(env, agent, n, *, holdout=None):
    """One round of the loop: generate, solve, verify, split."""
    tasks = generate_tasks(env, n)
    kept, failed = [], []
    for task in tasks:
        if _solved(agent, task):
            kept.append(task)
        else:
            failed.append(task)
    if len(kept) + len(failed) != len(tasks):       # a split that does not add up
        raise HarnessError("the round kept %d and failed %d of %d tasks"
                           % (len(kept), len(failed), len(tasks)))
    if holdout is None:
        accuracy = len(kept) / len(tasks)
    else:
        evaluated = list(holdout)
        if not evaluated:
            raise HarnessError("a holdout was given and it is empty: accuracy on "
                               "no tasks is not a measurement")
        accuracy = sum(1 for task in evaluated if _solved(agent, task)) / len(evaluated)
    return {"generated": len(tasks), "kept": kept, "failed": failed,
            "accuracy": accuracy}

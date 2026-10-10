"""Agent Harness From Scratch — stage 10: verification and the self-generated
data loop.

DESIGN DECISION — why must the verifier never raise?
    A verifier is called on whatever a solver produced: `None`, a list, a stray
    object, the string "furniture" where a number belongs. A crash there is not a
    signal about the solver, it is a hole in a training run — the episode is lost
    and the score is whatever the exception handler felt like. A wrong answer is
    `0.0`, and only a wrong answer is `0.0`: anything that raises here is a bug in
    the verifier, and the bug reports itself by returning zero for everything (the
    check asserts the honest cases pass).

DESIGN DECISION — why is the answer unwrapped instead of compared?
    Because a result comes back wrapped, and twice: `[("furniture",)]` is a
    one-row one-cell result, `[["furniture"]]` is the same thing from a driver
    that returns lists, and `{"rows": [["furniture"]]}` is the same result one
    layer up. Comparing the wrapper to the gold marks every correct answer wrong.
    The unwrap is recursive and stops at the first value that is not a
    one-element container.

DESIGN DECISION — why does the generator keep a counter and give up?
    A question template can be unsatisfiable: `AVG({column}) FROM {table}` on a
    table with no numeric column, or a filter value nobody sold to (whose answer
    is NULL). A generator that loops until it has `n` tasks spins forever on the
    first such template, and a generator that accepts the NULL writes a "gold
    answer" nobody can produce. So the loop is bounded (`limit` attempts), a
    candidate that errors or comes back NULL is DROPPED, and a template that
    cannot produce anything raises — naming the template and the count, because
    the person who has to fix it is reading a log.

DESIGN DECISION — why is the self-improvement round measured on held-out tasks?
    The tasks this round generates are the tasks this round solves, so accuracy on
    them measures the generator, not progress: the number goes up every round
    because the questions got easier (or because the solver has seen them). The
    only number worth plotting is the one on tasks this round did not make, so
    `holdout` is what `accuracy` reports when it is given — and the FAILED tasks
    are the valuable half of the output, because they are the ones at the edge of
    the current agent's ability.

TODO: implement `make_verifier`, `generate_tasks` and `self_improve_round`.
"""

from tiny_env import TEMPLATES, HarnessError

# How close two numbers have to be to be the same number. A tolerance is not
# sloppiness: `SUM(revenue)` is a float and a model writing the answer types a
# handful of digits, and an exact `==` marks a right answer wrong.
NUMERIC_TOLERANCE = 1e-6

# How many candidates the generator may examine before it gives up. A generator
# without this number is a generator that hangs on a template whose answer is
# always NULL.
ATTEMPT_LIMIT = 200


def make_verifier(gold):
    """A callable that scores an answer against `gold`: `1.0` or `0.0`, never an
    exception.

    - a one-element container is unwrapped until a value is reached
      (`[("furniture",)]` → `("furniture",)` → `"furniture"`), and a result dict's
      `rows` are unwrapped the same way;
    - numbers compare with a tolerance (`NUMERIC_TOLERANCE`), so `160` matches
      `160.0` and a float that came back from `SUM` matches its rounded answer;
    - strings compare case-insensitively after stripping, so `" Furniture "`
      matches `"furniture"`; anything that does not is `0.0`;
    - `gold is None` is a task nobody can answer: everything scores `0.0`.
    """
    raise NotImplementedError("stage 10: implement make_verifier()")


def generate_tasks(env, n, *, templates=TEMPLATES, limit=ATTEMPT_LIMIT):
    """`n` questions nobody wrote by hand, each with the executor's own answer.

    Deterministic: no randomness, no clock — the same env and templates give the
    same tasks in the same order, which is what makes a round reproducible. Each
    candidate is a template filled from the schema:

    - a template that needs a number (`needs_number`) is only filled on a table
      whose declared columns include one, and its `{column}` hole is filled with a
      numeric column of THAT table;
    - a `{table}` hole is filled with every table that fits the template, a
      `{country}`-style hole with the template's listed `values`;
    - the candidate is EXECUTED, and its `gold` is the executor's answer — not a
      literal, not the template's idea of the answer. A candidate that raises
      `EnvError` or answers `NULL` is dropped: a task whose answer does not exist
      is a task every solver fails;
    - after `limit` candidates, raise `HarnessError` naming the template and the
      count. The templates are the caller's, so this is a bug report about the
      templates, not a crash.
    """
    raise NotImplementedError("stage 10: implement generate_tasks()")


def self_improve_round(env, agent, n, *, holdout=None):
    """One round of the loop: generate, solve, verify, split.

        {"generated": n, "kept": [Task, ...], "failed": [Task, ...],
         "accuracy": float}

    `agent(task) -> answer`, and an agent that RAISES on a task failed that task
    (it did not fail the round). `kept` are the tasks it solved, `failed` the rest
    — and the failures are the curriculum: they are the tasks at the edge of the
    agent's ability, which is what the next round should train on.

    `accuracy` is measured on `holdout` when one is given (a sequence of tasks
    this round did NOT generate) and on the generated tasks otherwise. The first
    number is progress; the second is a smoke test of the plumbing. Reporting the
    second one as if it were the first is how a self-improving loop plots a line
    that goes up forever while the model learns nothing.
    """
    raise NotImplementedError("stage 10: implement self_improve_round()")

"""Agent Harness From Scratch — stage 9: process reward — a step has to be
grounded in what came back.

DESIGN DECISION — why reward the step and not the answer?
    A multi-step analysis has no single gold query: "which segment is driving the
    drop?" is a chain of queries and reasons. So the final answer is graded where
    it can be (`stage_10`'s verifier) and the PROCESS is graded here — and the
    process is where the dominant failure lives. An agent that writes "the data
    shows furniture leads" BEFORE running any query is fluent, confident and
    unsupported; the final answer can still be right by luck, so an
    outcome-only reward cannot see the failure at all. A step is worth something
    when it (a) ran, (b) is grounded in what the previous step returned, and
    (c) is not a repeat.

DESIGN DECISION — why the PREVIOUS step's result, and not any earlier one?
    Grounding is a claim about causality: this reasoning is about that number.
    Searching every result the episode ever produced lets a step cite a number
    from six steps ago and call itself justified, which is exactly the
    post-hoc-rationalisation failure the check exists to catch. The harness hands
    the step its predecessor's result and asks whether the reasoning mentions
    it — nothing more.

DESIGN DECISION — why must a float also match its integer spelling?
    Because `SUM(revenue)` comes back as `950.0` while a model writing prose
    says "950", and a grounding check that fails the honest step is a reward that
    trains the model to write floats with decimal tails to please a string
    comparison. Both spellings cite the same number.

DESIGN DECISION — why are boundaries required for numbers but not for words?
    `160` is inside `1600`: a substring test counts "we saw 1600 rows" as citing
    the number 160, and the step gets credit for a number that never appeared. A
    category name has no such ambiguity ("furniture" inside
    "furniture-and-appliances" IS the same category). So numbers match on
    boundaries and text matches as a substring.

TODO: implement `cite_values`, `cites_previous_result` and `process_reward`.
"""

from tiny_env import HarnessError

# The three things a step is graded on, and they are additive: a step that runs
# but invents its evidence scores 2/3, not 1.
CRITERIA = ("ran", "grounded", "novel")


def cite_values(result):
    """Every value a result CONTAINS, as the text a model would have written.

        {"columns": ["category", "total"], "rows": [["furniture", 490.0]]}
        ->  ["furniture", "490.0", "490"]

    A result may be handed over as the dict above or as its rows. Cells nest
    (a row is a list of cells) and a cell may itself be a list, so this walks
    everything. `None` is not a value: a NULL is the absence of a number, and a
    reasoning that "cites" it cites nothing. A float also yields its integer
    spelling when that spelling is exact (`490.0` -> `"490"`), because that is how
    a person writes it back.
    """
    raise NotImplementedError("stage 9: implement cite_values()")


def cites_previous_result(reasoning, previous_result):
    """Does `reasoning` mention a value the previous step returned?

    Matching is case-insensitive and whitespace-insensitive, numbers must sit on
    boundaries (`160` does not match inside `1600`), and a text value matches as
    a substring. `None`, an empty list, or a result with no rows is `False`: there
    was nothing to cite, so the claim is unsupported by construction.
    """
    raise NotImplementedError("stage 9: implement cites_previous_result()")


def process_reward(steps):
    """The mean over steps of `(ran + grounded + novel) / 3`, in `[0, 1]`.

    A step is `{"sql": str, "ok": bool, "result": <result>, "reasoning": str}`:

    - `ok` is whether the query ran at all — and it is a REAL bool. `"false"` is
      a non-empty string and therefore truthy, and a reward built on `if step
      ["ok"]` pays a step that failed.
    - the FIRST step is grounded by definition: it has no predecessor to cite, and
      charging it for that would make every honest episode start at 2/3.
    - `novel` is False when the step's `sql` (whitespace- and case-normalised)
      appeared ANYWHERE earlier in the episode — not merely in the step before it,
      because a repeat three steps back is still the same query run twice.
    - an empty episode is `0.0`, not an exception: a reward function is called on
      whatever the rollout produced, including nothing.
    """
    raise NotImplementedError("stage 9: implement process_reward()")

"""
Step 1 — Grounding Agent
========================
Paper: MARS-SQL section 3.1.

For each table, emit (decision, columns) where decision is 'Y' or 'N' and
columns is the subset needed to answer the question. The reduced schema is
every table marked Y, with only those columns.

Reward (paper, slightly specialised to this fixture):

    1.0   exact match with gold
    max(0.5, |gold_cols| / |pred_cols|)
          decision Y, gold columns are a proper subset of predicted
    0.2   predicted Y, gold is N
    0.1   predicted Y, gold is Y, but missing at least one gold column
    0.0   malformed (decision not in {Y,N}, unknown column, ...)

DESIGN DECISION — recall over precision on BIRD.
  The paper reports 97.78% recall / 90.74% precision and says recall is
  the primary concern: a missing join key cannot be recovered later, an
  extra column only wastes context. CHOSEN: the reward above, which pays
  a superset more than a miss.
"""

from typing import Dict, List, Sequence, Tuple

Decision = Tuple[str, List[str]]          # ('Y'|'N', columns)


def ground_table(question: str, table: str, columns: Sequence[str]) -> Decision:
    """Decide whether `table` is needed for `question`, and which columns.

    On the fixture question ("Who is the manager of the Sales department?"):
      departments -> ('Y', ['id', 'name', 'manager_id'])
                     (name to filter, manager_id to join, id if you like)
                     At minimum you MUST include name and manager_id.
      employees   -> ('Y', ['id', 'name'])
                     (id to join, name to return)
      any other   -> ('N', [])

    You may include extra columns; the reward will still be a superset
    score rather than 1.0. You may NOT drop a required one.

    TODO: keyword / schema heuristic is enough. Do not call an LLM.
    """
    raise NotImplementedError


def reduce_schema(question: str,
                  schema: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """TODO: {table: cols} for every table whose decision is Y.
    Omit N tables entirely — that is the reduced schema S'.
    """
    raise NotImplementedError


def grounding_reward(predicted: Decision, gold: Decision) -> float:
    """The paper's graded reward. See the module docstring.

    TODO: implement the five cases. Unknown columns or a decision other
    than Y/N is malformed -> 0.0. Compare column sets case-sensitively
    as given (the fixture uses lowercase).
    """
    raise NotImplementedError

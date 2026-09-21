"""
Step 3 — Validation Agent
=========================
Paper: MARS-SQL section 3.3 and Appendix H.

The paper does NOT take a majority vote over execution results
(self-consistency). It treats verification as next-token prediction:
prompt the validator with (question, candidate SQL) and read P("Yes").
Pick the candidate with the highest Yes-probability.

On this fixture there is no LLM. `score_yes` is a deterministic stand-in
that you write, with the same *interface* and the same *failure modes*:

  - executable + gold rows     -> high score
  - executable + wrong rows    -> low score
  - non-executable             -> very low score

Self-consistency would pick a wrong-but-popular result. The checker
constructs exactly that trap.
"""

from typing import Dict, List, Sequence, Tuple


def score_yes(question: str, sql: str) -> float:
    """P(Yes | question, sql) in [0, 1].

    TODO, using db.execute:
      - OperationalError or any exception -> 0.05
      - rows match db.gold_rows()         -> 0.95
      - executable but different rows     -> 0.20
    Do not look at how many other candidates agreed. That is the trap.
    """
    raise NotImplementedError


def select_trajectory(question: str,
                      trajectories: Sequence[Sequence[Dict[str, str]]]
                      ) -> Tuple[int, List[float]]:
    """Pick the trajectory with the highest score_yes on its final SQL.

    Returns (index, scores_in_input_order).

    TODO:
    1. Import final_sql from generation. A trajectory without FINISH
       scores 0.0.
    2. argmax, ties -> lowest index (paper's LLM-as-judge baseline does
       the same; keep it so the checker is deterministic).
    """
    raise NotImplementedError


def self_consistency(trajectories: Sequence[Sequence[Dict[str, str]]]
                     ) -> Tuple[int, str]:
    """Majority vote on str(execute(final_sql)).

    Provided so the checker can show it picking the wrong cluster.
    TODO: group by observation string, return (index of first member of
    the largest group, that observation). Ties -> lowest index.
    Trajectories that do not FINISH or that error form their own groups.
    """
    raise NotImplementedError

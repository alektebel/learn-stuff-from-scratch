"""
Step 2 — Generation Agent
=========================
Paper: MARS-SQL section 3.2. ReAct: Thought, Action, Observation.

A trajectory is a list of turns:
    {"thought": str, "action": str, "observation": str}

`action` is one of:
    DESCRIBE <table>
    RUN <sql>
    FINISH <sql>

`step()` executes one action against db.py and returns the observation
string. OperationalError becomes the observation, it does not raise out
of the loop — that is the whole point of interactivity.

DESIGN DECISION — why a live database in the loop?
  Static prompting cannot recover from a typo'd table name. The paper's
  Figure 5 analogue (fprm -> frpm) is the fixture's TYPOS. CHOSEN: the
  agent sees the error string and is required to retry with the correction.

`react_until_done` runs a policy function that, given (question, schema,
history), returns (thought, action). Stop on FINISH, or after max_turns.
"""

from typing import Callable, Dict, List, Sequence, Tuple


def step(action: str) -> str:
    """Execute one action. Never raise OperationalError to the caller.

    TODO:
      DESCRIBE <table>  -> comma-joined columns, or the error string
      RUN <sql>         -> str(rows) or the error string
      FINISH <sql>      -> str(rows) or the error string
                           (FINISH still executes: validation needs the
                           observation, not just the text of the SQL)
      anything else     -> "unknown action"
    Import execute, describe, OperationalError from db.
    """
    raise NotImplementedError


def correct_typo(sql: str) -> str:
    """Replace every db.TYPOS key that appears as a whole word.

    TODO: word-boundary replace, case-insensitive match, preserve the
    rest of the SQL. The policy below depends on this being boring and
    correct.
    """
    raise NotImplementedError


def react_until_done(policy: Callable,
                     question: str,
                     schema: Dict[str, List[str]],
                     max_turns: int = 5
                     ) -> List[Dict[str, str]]:
    """Run the ReAct loop.

    TODO:
    1. history = []
    2. thought, action = policy(question, schema, history)
    3. observation = step(action)
    4. append {thought, action, observation}
    5. if action starts with FINISH or len==max_turns: return history
    The policy is allowed to be deterministic. The checker supplies one
    that first RUN-s a typo, then FINISH-es the correction — your loop
    has to give it the error observation or it cannot recover.
    """
    raise NotImplementedError


def final_sql(trajectory: Sequence[Dict[str, str]]) -> str:
    """TODO: SQL text of the last FINISH action.
    Raise ValueError if the trajectory never finished.
    """
    raise NotImplementedError


def rollout_group(policy: Callable,
                  question: str,
                  schema: Dict[str, List[str]],
                  n: int = 3
                  ) -> List[List[Dict[str, str]]]:
    """N independent trajectories. The paper samples; we call the same
    policy n times so a stochastic policy (if you write one) can vary.

    TODO: [react_until_done(...) for _ in range(n)]
    """
    raise NotImplementedError

"""
Phase 5 template — tool-integrated, multi-turn RL over an UNKNOWN schema.

The schema is hidden. The agent must discover the tables it needs by calling
tools, and it is graded on whether the query written from what it discovered
actually works. Schema discovery becomes an ACTION, not a given.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase5.py

Stuck? `HINTS.md` has three escalating levels per function.
"""
from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from tiny_sql_env import SQLEnv, TASKS, SCHEMA_TABLES, SCHEMA_COLUMNS  # noqa: E402
from rewards import execution_accuracy  # noqa: E402
from grpo import TabularPolicy, group_relative_advantages  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402

# The action space. Unlike Phases 1-4 the agent does not pick a query — it picks
# a TOOL CALL. The query is written at the end from whatever it discovered.
ACTIONS = ["describe_customers", "describe_products", "describe_orders", "final"]
FINAL_ACTION = 3
MAX_TURNS = 4
STEP_COST = 0.05      # small penalty per tool call, to discourage aimless probing


class ToolEnv:
    """Wraps SQLEnv so the schema is reachable only through tool calls."""

    def __init__(self) -> None:
        self.db = SQLEnv()
        self.calls = 0

    def describe(self, table: str) -> str:
        self.calls += 1
        cols = SCHEMA_COLUMNS.get(table)
        return f"{table}({', '.join(cols)})" if cols else f"unknown table {table}"


@dataclass
class Trajectory:
    """One episode: the tool calls made, what was discovered, and the outcome."""
    task_qid: str
    steps: list[tuple[str, str]] = field(default_factory=list)   # (action, observation)
    discovered: set[str] = field(default_factory=set)            # table names
    finished: bool = False                                       # did it call `final`?
    final_sql: str = ""


def write_sql(discovered: set[str], task) -> str:
    """The fixed 'writer': turns discovered schema into a query.

    GIVEN — not a TODO. It can only produce the correct query if every table the
    task needs was actually discovered. That is what couples exploration quality
    to the final reward: fail to discover, fail to answer.
    """
    needed = {t.lower() for t in task.gold_tables}
    if needed <= {d.lower() for d in discovered}:
        return CANDIDATES[task.qid][CORRECT_INDEX[task.qid]]
    return CANDIDATES[task.qid][3]      # an ungrounded guess: always fails


def rollout(policy: TabularPolicy, task_idx: int, task, env: ToolEnv,
            rng: random.Random, max_turns: int = MAX_TURNS) -> Trajectory:
    """Run one episode.

    Requirements:
      * at most `max_turns` tool calls
      * at each turn, sample an action from the policy for state (task, turn) —
        use `policy_index(task_idx, turn)` to map that state to a policy row
      * a `describe_*` action calls env.describe(table), appends
        (action_name, observation) to traj.steps, and adds the table to
        traj.discovered
      * the `final` action sets traj.finished = True and ends the episode
      * when the episode ends (either way), set traj.final_sql = write_sql(...)
    """
    traj = Trajectory(task_qid=task.qid)
    # TODO: implement the turn loop described above
    raise NotImplementedError


def policy_index(task_idx: int, turn: int, max_turns: int = MAX_TURNS) -> int:
    """Map the agent's state (which task, which turn) to a policy row.

    The policy is conditioned on the turn, so it can learn a *sequence*
    ("describe orders, then customers, then stop") rather than one fixed action.
    """
    # TODO: return a unique row index for each (task_idx, turn) pair
    raise NotImplementedError


def turn_shaping(traj: Trajectory, task) -> float:
    """Dense per-turn signal (MARSQL flavour). Returns a bonus, can be negative.

    Requirements:
      * +1.0 for each distinct GOLD table the trajectory discovered
      * -STEP_COST for every tool call made (time is not free)
      * do not double-count a table described twice
    """
    # TODO: implement
    raise NotImplementedError


def trajectory_reward(traj: Trajectory, task, env: ToolEnv,
                      w_shaping: float = 0.0) -> float:
    """Outcome reward for the whole trajectory, plus optional turn shaping.

    The outcome is the execution accuracy of the query the writer produced from
    what the agent discovered.
    """
    # TODO: exec_r = execution_accuracy(traj.final_sql, task, env.db)
    # TODO: return exec_r + w_shaping * turn_shaping(traj, task)
    raise NotImplementedError


def train(steps: int = 300, seed: int = 0, group_size: int = 8,
          w_shaping: float = 0.0, lr: float = 0.6, verbose: bool = True):
    """Trajectory-level GRPO.

    This is Phase 0's algorithm with one change: the 'action' whose advantage we
    compute is an entire EPISODE, and we credit every turn of that episode with
    the episode's advantage. Returns (policy, mean_reward).
    """
    rng = random.Random(seed)
    n_tasks = len(TASKS)
    policy = TabularPolicy(n_tasks * MAX_TURNS, len(ACTIONS), lr=lr)
    last_mean = 0.0

    for step in range(steps):
        # TODO: for each task:
        #   1. run `group_size` rollouts (fresh ToolEnv each, so call counts reset)
        #   2. score each with trajectory_reward
        #   3. advantages = group_relative_advantages(rewards)
        #   4. for each trajectory, for each turn it took, accumulate the softmax
        #      gradient at row policy_index(task_idx, turn) for the action taken,
        #      weighted by that trajectory's advantage  (same formula as Phase 0)
        # TODO: apply the accumulated gradient with ASCENT, normalized by the
        #       number of (trajectory, turn) updates
        raise NotImplementedError

    return policy, last_mean


def greedy_trajectory(policy: TabularPolicy, task_idx: int, task) -> Trajectory:
    """Run one episode taking the argmax action at each turn. For evaluation."""
    env = ToolEnv()
    traj = Trajectory(task_qid=task.qid)
    for turn in range(MAX_TURNS):
        probs = policy.probs(policy_index(task_idx, turn))
        a = max(range(len(probs)), key=lambda i: probs[i])
        if a == FINAL_ACTION:
            traj.finished = True
            break
        table = ACTIONS[a].replace("describe_", "")
        traj.steps.append((ACTIONS[a], env.describe(table)))
        traj.discovered.add(table)
    traj.final_sql = write_sql(traj.discovered, task)
    return traj


if __name__ == "__main__":
    policy, mean_r = train(verbose=True)
    print("\nLearned discovery policy (greedy):")
    for i, task in enumerate(TASKS):
        traj = greedy_trajectory(policy, i, task)
        needed = sorted(t.lower() for t in task.gold_tables)
        print(f"  {task.qid}: discovered={sorted(traj.discovered)} needed={needed} "
              f"turns={len(traj.steps)} solved={execution_accuracy(traj.final_sql, task, SQLEnv()):.0f}")

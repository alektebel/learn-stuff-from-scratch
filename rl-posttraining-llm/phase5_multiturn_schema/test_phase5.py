"""
Phase 5 tests — run this to check your `template_agent_loop.py`.

    python test_phase5.py

Training runs a few hundred GRPO steps, so this one takes a few seconds.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_close, load_student_module  # noqa: E402
from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from rewards import execution_accuracy  # noqa: E402
from grpo import TabularPolicy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_agent_loop")

_cache: dict = {}


def trained(w_shaping: float):
    if w_shaping not in _cache:
        _cache[w_shaping] = m.train(steps=300, seed=0, w_shaping=w_shaping,
                                    verbose=False)[0]
    return _cache[w_shaping]


def _pinned_policy(action: int) -> TabularPolicy:
    pol = TabularPolicy(len(TASKS) * m.MAX_TURNS, len(m.ACTIONS), lr=0.5)
    for row in range(pol.n_prompts):
        pol.logits[row] = [0.0] * len(m.ACTIONS)
        pol.logits[row][action] = 30.0
    return pol


def test_policy_index_unique():
    seen = set()
    for task_idx in range(len(TASKS)):
        for turn in range(m.MAX_TURNS):
            idx = m.policy_index(task_idx, turn)
            assert idx not in seen, f"policy_index collided at ({task_idx}, {turn})"
            assert 0 <= idx < len(TASKS) * m.MAX_TURNS, f"index {idx} out of range"
            seen.add(idx)


def test_rollout_respects_turn_budget():
    rng = random.Random(0)
    pol = _pinned_policy(0)                       # always describe_customers
    traj = m.rollout(pol, 0, TASKS[0], m.ToolEnv(), rng, max_turns=m.MAX_TURNS)
    assert isinstance(traj, m.Trajectory), f"rollout returned {type(traj).__name__}"
    assert len(traj.steps) <= m.MAX_TURNS, f"took {len(traj.steps)} steps"


def test_rollout_records_discovery():
    rng = random.Random(0)
    pol = _pinned_policy(2)                       # always describe_orders
    traj = m.rollout(pol, 0, TASKS[0], m.ToolEnv(), rng, max_turns=3)
    assert traj.steps, "no steps recorded"
    assert "orders" in traj.discovered, f"discovered = {traj.discovered}"
    for action, obs in traj.steps:
        assert isinstance(action, str) and isinstance(obs, str), (action, obs)


def test_final_action_ends_episode():
    rng = random.Random(0)
    pol = _pinned_policy(m.FINAL_ACTION)
    traj = m.rollout(pol, 0, TASKS[0], m.ToolEnv(), rng, max_turns=m.MAX_TURNS)
    assert traj.finished, "calling `final` must set finished = True"
    assert len(traj.steps) == 0, f"`final` should end immediately, took {len(traj.steps)}"


def test_rollout_sets_final_sql():
    rng = random.Random(0)
    for action in (0, m.FINAL_ACTION):
        traj = m.rollout(_pinned_policy(action), 0, TASKS[0], m.ToolEnv(), rng)
        assert traj.final_sql, "final_sql was never set"


def test_full_discovery_solves():
    env = SQLEnv()
    for task in TASKS:
        sql = m.write_sql({t.lower() for t in task.gold_tables}, task)
        assert execution_accuracy(sql, task, env) == 1.0, (
            f"{task.qid}: discovering everything needed should give a correct query"
        )


def test_no_discovery_fails():
    """The coupling that makes exploration trainable."""
    env = SQLEnv()
    for task in TASKS:
        sql = m.write_sql(set(), task)
        assert execution_accuracy(sql, task, env) == 0.0, (
            f"{task.qid}: an ungrounded guess scored 1.0 — the fallback query must "
            "genuinely fail, or the agent is rewarded for not exploring"
        )


def test_shaping_rewards_gold_tables():
    task = next(t for t in TASKS if len(t.gold_tables) == 2)
    empty = m.Trajectory(task_qid=task.qid)
    one = m.Trajectory(task_qid=task.qid, discovered={task.gold_tables[0].lower()})
    both = m.Trajectory(task_qid=task.qid,
                        discovered={t.lower() for t in task.gold_tables})
    assert m.turn_shaping(both, task) > m.turn_shaping(one, task) > m.turn_shaping(empty, task)


def test_shaping_charges_steps_without_double_counting():
    task = TASKS[0]
    tbl = task.gold_tables[0].lower()
    once = m.Trajectory(task_qid=task.qid, steps=[("describe_" + tbl, "obs")],
                        discovered={tbl})
    twice = m.Trajectory(task_qid=task.qid,
                         steps=[("describe_" + tbl, "obs")] * 2, discovered={tbl})
    delta = m.turn_shaping(once, task) - m.turn_shaping(twice, task)
    assert_close(delta, m.STEP_COST, 1e-9,
                 "cost of one extra redundant tool call (the repeated table must "
                 "not be counted twice as a discovery)")


def test_trajectory_reward_reduces_to_exec():
    env = m.ToolEnv()
    rng = random.Random(0)
    for action in (0, 1, 2, m.FINAL_ACTION):
        for task_idx, task in enumerate(TASKS):
            traj = m.rollout(_pinned_policy(action), task_idx, task, m.ToolEnv(), rng)
            got = m.trajectory_reward(traj, task, env, w_shaping=0.0)
            want = execution_accuracy(traj.final_sql, task, env.db)
            assert_close(got, want, 1e-9, f"{task.qid} trajectory_reward w_shaping=0")


def test_train_returns_full_policy():
    pol = trained(0.0)
    assert pol.n_prompts == len(TASKS) * m.MAX_TURNS, (
        f"policy has {pol.n_prompts} rows, expected {len(TASKS) * m.MAX_TURNS}"
    )
    assert pol.n_actions == len(m.ACTIONS)


def test_agent_solves_every_task():
    pol = trained(0.0)
    env = SQLEnv()
    failed = []
    for i, task in enumerate(TASKS):
        traj = m.greedy_trajectory(pol, i, task)
        if execution_accuracy(traj.final_sql, task, env) < 1.0:
            failed.append((task.qid, sorted(traj.discovered)))
    assert not failed, f"unsolved after training: {failed}"


def test_agent_discovers_needed_tables():
    pol = trained(0.0)
    for i, task in enumerate(TASKS):
        needed = {t.lower() for t in task.gold_tables}
        got = {d.lower() for d in m.greedy_trajectory(pol, i, task).discovered}
        assert needed <= got, f"{task.qid}: needed {needed}, discovered {got}"


def test_shaping_reduces_turns():
    env = SQLEnv()

    def evaluate(pol):
        turns = solved = 0
        for i, task in enumerate(TASKS):
            traj = m.greedy_trajectory(pol, i, task)
            turns += len(traj.steps)
            solved += execution_accuracy(traj.final_sql, task, env)
        return turns, solved

    t_none, s_none = evaluate(trained(0.0))
    t_shaped, s_shaped = evaluate(trained(0.3))
    assert s_shaped >= s_none, (
        f"turn shaping cost accuracy: {s_shaped} < {s_none}"
    )
    assert t_shaped < t_none, (
        f"turn shaping did not reduce probing: {t_shaped} turns vs {t_none}. "
        "Check that turn_shaping subtracts STEP_COST per tool call."
    )


if __name__ == "__main__":
    c = Checker("Phase 5 — multi-turn RL over an unknown schema")
    c.check("policy_index is unique per (task, turn)", test_policy_index_unique)
    c.check("rollout respects the turn budget", test_rollout_respects_turn_budget)
    c.check("rollout records steps and discovery", test_rollout_records_discovery)
    c.check("`final` ends the episode", test_final_action_ends_episode)
    c.check("rollout always sets final_sql", test_rollout_sets_final_sql)
    c.check("full discovery yields a correct query", test_full_discovery_solves)
    c.check("no discovery yields a failing query", test_no_discovery_fails)
    c.check("shaping rewards gold tables", test_shaping_rewards_gold_tables)
    c.check("shaping charges per call, no double count",
            test_shaping_charges_steps_without_double_counting)
    c.check("trajectory_reward reduces to exec", test_trajectory_reward_reduces_to_exec)
    c.check("train returns a full policy", test_train_returns_full_policy)
    c.check("trained agent solves every task", test_agent_solves_every_task)
    c.check("trained agent discovers needed tables", test_agent_discovers_needed_tables)
    c.check("turn shaping reduces probing", test_shaping_reduces_turns)
    sys.exit(c.summary())

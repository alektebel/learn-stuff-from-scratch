"""
Phase 7 capstone template — the ablation table.

This is the deliverable that makes the whole course worth something: a table
that tells you which of the five mechanisms your application actually needs, and
whether you can train WITHOUT executing generated SQL against real data.

It integrates the earlier phases, so finish those first — in particular this
imports your Phase 4 `graph_reward` for the execution-free configuration.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase7.py
"""
from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from rewards import combine, execution_accuracy  # noqa: E402
from grpo import TabularPolicy, grpo_step  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402


def load_graph_reward():
    """Import your Phase 4 execution-free reward. Raises if Phase 4 isn't done."""
    import importlib.util
    path = os.path.join(HERE, "..", "phase4_execution_free", "template_graph_reward.py")
    spec = importlib.util.spec_from_file_location("template_graph_reward", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["template_graph_reward"] = mod
    spec.loader.exec_module(mod)
    return mod.graph_reward


@dataclass
class AblationRow:
    """One row of the ablation table."""
    name: str
    reward: str                    # human-readable description of the signal
    executes_during_training: bool # the compliance-relevant column
    accuracy: float                # greedy execution accuracy, eval-time only
    q5_prob_correct: float         # P(semantically correct query) for q5


# The configurations to compare. Each maps to a reward function you build below.
CONFIGS = ["exec_only", "phased", "graph_only", "phased_plus_graph"]


def make_reward_fn(config: str, env: SQLEnv, qids: list[str]):
    """Return reward_of(prompt_idx, action_idx) for the named configuration.

    - "exec_only"          : {"exec": 1.0}                       (Phase 1)
    - "phased"             : the five weighted components        (Phase 2)
    - "graph_only"         : your Phase 4 graph_reward ALONE — must never
                             execute anything
    - "phased_plus_graph"  : dense shaping + graph reward, still no execution
    """
    # TODO: build and return the closure for each config
    raise NotImplementedError


def train_config(config: str, steps: int = 200, seed: int = 0):
    """Train one configuration. Returns (policy, qids, env)."""
    rng = random.Random(seed)
    env = SQLEnv()
    qids = [t.qid for t in TASKS]
    policy = TabularPolicy(len(qids), max(len(CANDIDATES[q]) for q in qids), lr=0.7)
    reward_of = make_reward_fn(config, env, qids)
    # TODO: run `steps` GRPO updates (same call as Phase 1/2)
    raise NotImplementedError


def evaluate(policy, qids, env: SQLEnv) -> tuple[float, float]:
    """Eval-time only. Returns (greedy execution accuracy, q5 P(correct)).

    Execution is allowed HERE even for execution-free configs — this is
    measurement, not training. That distinction is the whole compliance argument.
    """
    # TODO: greedy argmax per task -> execution_accuracy, averaged;
    #       plus policy.probs(q5_index)[CORRECT_INDEX["q5"]]
    raise NotImplementedError


def run_ablation(steps: int = 200, seed: int = 0) -> list[AblationRow]:
    """Train every configuration and return the table."""
    # TODO: for each config in CONFIGS: train, evaluate, build an AblationRow.
    #       Set executes_during_training correctly — False for the graph configs.
    raise NotImplementedError


if __name__ == "__main__":
    rows = run_ablation()
    print(f"{'config':<20} {'reward':<34} {'exec?':<6} {'acc':<6} {'q5 P(correct)'}")
    print("-" * 84)
    for r in rows:
        print(f"{r.name:<20} {r.reward:<34} "
              f"{'yes' if r.executes_during_training else 'NO':<6} "
              f"{r.accuracy:<6.2f} {r.q5_prob_correct:.3f}")

"""
Phase 3 template — a Process Reward Model, auto-labeled by Monte-Carlo roll-outs.

The key idea: you need NO new human supervision. You reuse the Phase 1 executor
to label whether a partial query tends to lead somewhere correct, and train a
scorer on those labels.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase3.py

Stuck? `HINTS.md` has three escalating levels per function.
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from tiny_sql_env import SQLEnv, TASKS, SCHEMA_TABLES, SCHEMA_COLUMNS  # noqa: E402
from rewards import execution_accuracy, extract_sql  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402

# A "step" in building a SQL query is a clause. Decomposing on clause keywords
# gives a deterministic process trace we can score step by step — the same role
# that <think> steps play when the policy is a real LLM.
CLAUSE_KEYWORDS = ["select", "from", "join", "on", "where",
                   "group by", "order by", "limit"]

FEATURE_DIM = 4   # keep this in sync with step_features()


def decompose(sql: str) -> list[str]:
    """Split a SQL string into an ordered list of clause strings.

    Example:
        "SELECT name FROM products WHERE id = 1"
        -> ["select name", "from products", "where id = 1"]

    Requirements:
      * match keywords case-insensitively, but SLICE FROM THE ORIGINAL STRING —
        the returned chunks must preserve the query's original case. Lowercasing
        the output corrupts string literals: `country='ES'` becomes
        `country='es'`, which silently matches zero rows. (This bug is easy to
        write and hard to see; the tests check for it explicitly.)
      * each returned chunk starts with its clause keyword
      * order is preserved; joining the chunks with " " recovers the query
      * a query with no recognizable keyword returns a single chunk
    """
    # TODO: lowercase a COPY for finding keyword positions, collect the split
    #       indices, sort/dedupe them, then slice the ORIGINAL string.
    raise NotImplementedError


def step_features(prefix: list[str], step: str, task) -> list[float]:
    """Featurize "taking `step` after `prefix`" for task `task`.

    Must return exactly FEATURE_DIM floats, each in [0,1]:
      0. fraction of the task's gold identifiers covered so far (prefix + step)
      1. spurious TABLES referenced (schema tables not in task.gold_tables),
         normalized — count tables only, not columns, or the feature stops
         discriminating (`id` is a column of every table)
      2. 1.0 if this step introduces at least one NEW gold identifier else 0.0
      3. 1.0 if the step is an aggregation/ordering clause else 0.0
    """
    # TODO: build the identifier sets and compute the features above
    raise NotImplementedError


def mc_label(partial_sql: str, task, env: SQLEnv, k: int, rng: random.Random) -> float:
    """Monte-Carlo label: how often does completing `partial_sql` end correct?

    This is where the supervision comes from — the EXECUTOR, not a human.

    Requirements:
      * sample k completions of the prefix (see HINTS for the CPU recipe)
      * score each with execution_accuracy against `task`
      * return the fraction correct, in [0.0, 1.0]
    """
    # TODO: implement
    raise NotImplementedError


class PRM:
    """A logistic scorer: score(features) -> [0,1]."""

    def __init__(self, dim: int = FEATURE_DIM):
        self.w = [0.0] * dim
        self.b = 0.0

    def score(self, feats: list[float]) -> float:
        """Sigmoid of the linear score. Must stay in [0,1] for any input."""
        # TODO: z = b + sum(w_i * f_i); return the (overflow-safe) sigmoid of z
        raise NotImplementedError

    def fit_step(self, feats: list[float], label: float, lr: float = 0.1) -> None:
        """One gradient step of logistic regression toward `label`.

        For a sigmoid + log-loss the gradient is beautifully simple:
            error = score(feats) - label
            w_i  -= lr * error * f_i
            b    -= lr * error
        """
        # TODO: implement
        raise NotImplementedError


def train_prm(env: SQLEnv, steps: int = 400, seed: int = 0) -> PRM:
    """Train the PRM on auto-labeled (prefix, step) pairs from all tasks.

    Loop: pick a task, pick a candidate, decompose it, walk its prefixes,
    featurize each step, label it with mc_label, and fit.
    """
    # TODO: implement
    raise NotImplementedError


def prm_trace_score(completion: str, task, prm: PRM) -> float:
    """Mean PRM score over the steps of `completion`. Returns [0,1]."""
    # TODO: decompose the extracted SQL, featurize each step against its prefix,
    #       average prm.score over the steps (return 0.0 for an empty trace)
    raise NotImplementedError


def shaped_reward(completion: str, task, env: SQLEnv, prm: PRM,
                  w_exec: float = 1.0, w_prm: float = 0.5) -> float:
    """Outcome reward + process reward."""
    # TODO: return w_exec * execution_accuracy(...) + w_prm * prm_trace_score(...)
    raise NotImplementedError


if __name__ == "__main__":
    env = SQLEnv()
    prm = train_prm(env)
    task = task_by_qid("q5")
    print("q5 candidates under shaped reward (exec alone cannot separate these):")
    for i, c in enumerate(CANDIDATES["q5"]):
        print(f"  cand[{i}] shaped={shaped_reward(c, task, env, prm):.3f}"
              f"  exec={execution_accuracy(c, task, env):.1f}")

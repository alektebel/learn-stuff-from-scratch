"""
rewards.py — a library of composable reward functions for text-to-SQL RL.

This is where the papers in the reading list actually live. Each function here
maps a *generated SQL string* (plus the task and env) to a scalar in [0, 1].
The whole point of "phased" / "progressive" reward design is that you do NOT
train on execution accuracy alone — that signal is sparse (0 almost everywhere
early in training), so learning stalls. Instead you layer denser, cheaper
signals underneath it:

    total = w_exec   * execution_accuracy      # the ground truth, but sparse
          + w_syntax * syntax_validity         # "does it even parse/run?"
          + w_schema * schema_linking           # "did it touch the right tables?"
          + w_ngram  * ngram_similarity          # "does it look like the gold?"
          + w_format * format_reward             # "did it follow the protocol?"

Reasoning-SQL layers exactly these partial rewards on top of sparse execution
accuracy. Progress-SQL turns the weights into a *curriculum* (start with dense
shaping, anneal toward execution accuracy). Graph-Reward-SQL (Phase 4) replaces
execution accuracy with a graph-match reward so you never run the query.

All functions are pure stdlib. Keep them side-effect free and in [0, 1] so they
compose cleanly and so `combine()` stays interpretable.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Callable

from tiny_sql_env import SQLEnv, Task


# --------------------------------------------------------------------------- #
# 0. Format reward — cheapest, densest signal. Did the model emit the protocol
#    we asked for, e.g. reasoning in <think> and the query in <sql> ... </sql>?
#    This alone is enough to bootstrap a cold-start policy off the floor.
# --------------------------------------------------------------------------- #
SQL_TAG = re.compile(r"<sql>\s*(.*?)\s*</sql>", re.DOTALL | re.IGNORECASE)
THINK_TAG = re.compile(r"<think>\s*(.*?)\s*</think>", re.DOTALL | re.IGNORECASE)


def extract_sql(completion: str) -> str:
    """Pull the SQL out of a tagged completion. Falls back to the raw string."""
    m = SQL_TAG.search(completion)
    return (m.group(1) if m else completion).strip().rstrip(";") + ";"


def format_reward(completion: str, task: Task, env: SQLEnv) -> float:
    r = 0.0
    if THINK_TAG.search(completion):
        r += 0.5
    if SQL_TAG.search(completion):
        r += 0.5
    return r


# --------------------------------------------------------------------------- #
# 1. Syntax validity — does the query parse and run at all? We ask SQLite to
#    prepare it (EXPLAIN) without committing to full execution semantics.
# --------------------------------------------------------------------------- #
def syntax_validity(completion: str, task: Task, env: SQLEnv) -> float:
    sql = extract_sql(completion)
    try:
        env._conn.execute("EXPLAIN " + sql)  # prepares without returning rows
        return 1.0
    except Exception:  # noqa: BLE001
        return 0.0


# --------------------------------------------------------------------------- #
# 2. Schema-linking accuracy — did the query reference the tables/columns a
#    correct answer needs? This is the signal TRUST-SQL / MARSQL make central.
#    We grade with a simple token-membership F1 against the gold link set.
# --------------------------------------------------------------------------- #
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _identifiers(sql: str) -> set[str]:
    return {t.lower() for t in _IDENT.findall(sql)}


def schema_linking(completion: str, task: Task, env: SQLEnv) -> float:
    sql_idents = _identifiers(extract_sql(completion))
    gold = {t.lower() for t in task.gold_tables} | {
        c.lower() for c in task.gold_columns
    }
    if not gold:
        return 1.0
    hit = len(gold & sql_idents)
    precision_denom = len(gold & sql_idents) + len(
        # penalize referencing *schema* identifiers that aren't needed
        (sql_idents & _all_schema_idents()) - gold
    )
    recall = hit / len(gold)
    precision = hit / precision_denom if precision_denom else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _all_schema_idents() -> set[str]:
    from tiny_sql_env import SCHEMA_COLUMNS, SCHEMA_TABLES
    s = {t.lower() for t in SCHEMA_TABLES}
    for cols in SCHEMA_COLUMNS.values():
        s |= {c.lower() for c in cols}
    return s


# --------------------------------------------------------------------------- #
# 3. N-gram similarity — cheap "does it look like the gold query" signal.
#    Structural/lexical alignment in Progress-SQL. Useful as smooth shaping but
#    dangerous as a sole objective (rewards copying surface form, not meaning).
# --------------------------------------------------------------------------- #
def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def ngram_similarity(completion: str, task: Task, env: SQLEnv, n: int = 2) -> float:
    pred = extract_sql(completion).lower().replace(";", " ").split()
    gold = task.gold_sql.lower().replace(";", " ").split()
    if len(pred) < n or len(gold) < n:
        # fall back to unigram overlap for very short queries
        n = 1
    pg, gg = _ngrams(pred, n), _ngrams(gold, n)
    overlap = sum((pg & gg).values())
    denom = max(sum(gg.values()), 1)
    return min(overlap / denom, 1.0)


# --------------------------------------------------------------------------- #
# 4. Execution accuracy — the ground-truth reward. Sparse but correct: run the
#    query, compare the normalized result set to the gold result set.
# --------------------------------------------------------------------------- #
def execution_accuracy(completion: str, task: Task, env: SQLEnv) -> float:
    sql = extract_sql(completion)
    ok, res = env.execute(sql)
    if not ok:
        return 0.0
    gold = env.gold_result(task)
    return 1.0 if res == gold else 0.0


# --------------------------------------------------------------------------- #
# Combining rewards. `weights` picks which signals are active and how strong.
# Phase 1 uses {exec: 1}. Phase 2 turns the others on. Progress-SQL anneals the
# weights across training (see phase2 README) — pass a fresh weight dict per step.
# --------------------------------------------------------------------------- #
RewardFn = Callable[[str, Task, SQLEnv], float]

REGISTRY: dict[str, RewardFn] = {
    "format": format_reward,
    "syntax": syntax_validity,
    "schema": schema_linking,
    "ngram": ngram_similarity,
    "exec": execution_accuracy,
}


def combine(
    completion: str,
    task: Task,
    env: SQLEnv,
    weights: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """Return (total_reward, per_component_breakdown)."""
    breakdown = {
        name: REGISTRY[name](completion, task, env) for name in weights
    }
    total = sum(weights[name] * breakdown[name] for name in weights)
    return total, breakdown


if __name__ == "__main__":
    env = SQLEnv()
    task = next(t for t in __import__("tiny_sql_env").TASKS if t.qid == "q1")
    good = "<think>count ES customers</think><sql>SELECT COUNT(*) FROM customers WHERE country='ES'</sql>"
    bad = "<sql>SELECT name FROM prod</sql>"
    for label, c in [("GOOD", good), ("BAD", bad)]:
        total, br = combine(
            c, task, env,
            {"format": 0.2, "syntax": 0.2, "schema": 0.3, "ngram": 0.3, "exec": 1.0},
        )
        print(f"{label}: total={total:.3f}  {br}")

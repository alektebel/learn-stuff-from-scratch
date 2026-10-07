"""
Phase 6 template — multi-step data analysis with process rewards and a
self-improving (EvoDS-style) data loop.

The shift from Phase 5: there is no single gold query any more. A question like
"which category drives revenue?" is answered by a *chain* of queries plus
reasoning over their results. So the reward has to grade the process, and the
training data has to come from somewhere — you generate it yourself.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase6.py

Stuck? `HINTS.md` has three escalating levels per function.
"""
from __future__ import annotations

import os
import random
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from tiny_sql_env import SQLEnv, SCHEMA_TABLES, SCHEMA_COLUMNS  # noqa: E402


@dataclass
class AnalyticTask:
    """A multi-step analytic question. Note: no gold SQL — only a gold ANSWER.
    There are many valid query chains that reach it."""
    aid: str
    question: str
    gold_answer: object
    reference_sql: str          # one way to get there, for validation only


# Deliberately chosen to have UNIQUE answers — no ties — so the verifier is
# unambiguous. (An earlier draft asked for the top-revenue *country*; ES and CN
# both total 320.0, so "the" answer was ill-defined. Check your gold answers.)
ANALYTIC_TASKS = [
    AnalyticTask(
        "a1", "Which product category generates the most total revenue?",
        "furniture",
        "SELECT p.category FROM orders o JOIN products p ON o.product_id=p.id "
        "GROUP BY p.category ORDER BY SUM(p.price*o.quantity) DESC LIMIT 1"),
    AnalyticTask(
        "a2", "What is the total revenue from the electronics category?",
        160.0,
        "SELECT SUM(p.price*o.quantity) FROM orders o JOIN products p "
        "ON o.product_id=p.id WHERE p.category='electronics'"),
    AnalyticTask(
        "a3", "Which product has the most units ordered?",
        "Chair",
        "SELECT p.name FROM orders o JOIN products p ON o.product_id=p.id "
        "GROUP BY p.name ORDER BY SUM(o.quantity) DESC LIMIT 1"),
    AnalyticTask(
        "a4", "Which country places the most orders?",
        "ES",
        "SELECT c.country FROM orders o JOIN customers c ON o.customer_id=c.id "
        "GROUP BY c.country ORDER BY COUNT(*) DESC LIMIT 1"),
]


@dataclass
class AnalysisEpisode:
    """A sequence of (query, result, reasoning) steps ending in an answer."""
    question: str
    steps: list[dict] = field(default_factory=list)
    answer: object = None

    def add_step(self, query: str, env: SQLEnv, reasoning: str = "") -> None:
        ok, res = env.execute(query)
        self.steps.append({"query": query, "result": res if ok else None,
                           "ok": ok, "reasoning": reasoning})


def cites_previous_result(reasoning: str, previous_result) -> bool:
    """Did this step's reasoning actually reference the numbers/values the last
    query returned? This is the anti-hallucination check at the heart of
    process-level reward modeling for analysis.

    Requirements:
      * True if any cell value from `previous_result` appears in `reasoning`
      * False if `previous_result` is None or empty
      * compare case-insensitively; for floats, accept "160" for 160.0
    """
    # TODO: implement
    raise NotImplementedError


def process_reward(episode: AnalysisEpisode) -> float:
    """Score the analysis PROCESS, in [0,1]. Returns 0.0 for an empty episode.

    Score each step on three things, then average over all steps:
      1. executed successfully (step["ok"])
      2. grounded: its reasoning cites the previous step's result
         (the FIRST step has no predecessor — give it credit automatically)
      3. non-redundant: its query differs from every earlier query in the episode
    """
    # TODO: implement
    raise NotImplementedError


def make_verifier(gold_answer):
    """Build verify(answer) -> 1.0 / 0.0 for a checkable question.

    Requirements:
      * numbers compare with a small tolerance (1e-6)
      * strings compare case-insensitively, ignoring surrounding whitespace
      * a single-cell result like [('furniture',)] counts as "furniture"
      * anything else -> 0.0, never an exception
    """
    def verify(answer) -> float:
        # TODO: implement
        raise NotImplementedError
    return verify


# --- EvoDS-style self-improving data loop ---------------------------------- #
QUESTION_TEMPLATES = [
    ("How many {table} are there?", "SELECT COUNT(*) FROM {table}"),
    ("What is the average {col} in {table}?", "SELECT AVG({col}) FROM {table}"),
    ("What is the maximum {col} in {table}?", "SELECT MAX({col}) FROM {table}"),
]


def generate_candidate_questions(env: SQLEnv, n: int, rng: random.Random) -> list[AnalyticTask]:
    """Self-generate schema-grounded tasks, with answers from the EXECUTOR.

    This is the EvoDS/CurateEvo move: the agent writes its own training data, and
    the database — not a human — supplies the labels.

    Requirements:
      * return exactly `n` AnalyticTask objects
      * every task must be grounded in the real schema (valid table/column)
      * gold_answer must come from actually running reference_sql
      * DISCARD any generated task whose SQL fails or returns nothing
    """
    # TODO: sample a template, sample a table (and a numeric column where the
    #       template needs one), build the SQL, execute it, and keep the ones
    #       that produce a real answer.
    raise NotImplementedError


def self_improve_round(env: SQLEnv, solver, rng: random.Random,
                       n_candidates: int = 12) -> dict:
    """One EvoDS round: generate -> solve -> validate -> keep.

    `solver` is a callable (task) -> answer.

    Requirements: return a dict with keys
      * "generated": how many candidates were produced
      * "kept":      list of tasks the solver got RIGHT (validated training data)
      * "failed":    list of tasks the solver got WRONG (the useful curriculum —
                     these are the hard ones worth training on)
      * "accuracy":  fraction solved, in [0,1]
    """
    # TODO: implement
    raise NotImplementedError


if __name__ == "__main__":
    env = SQLEnv()
    rng = random.Random(0)

    def reference_solver(task):
        ok, res = env.execute(task.reference_sql)
        return res if ok else None

    stats = self_improve_round(env, reference_solver, rng)
    print(f"generated={stats['generated']} kept={len(stats['kept'])} "
          f"failed={len(stats['failed'])} accuracy={stats['accuracy']:.2f}")

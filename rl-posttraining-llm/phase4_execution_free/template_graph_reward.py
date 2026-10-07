"""
Phase 4 template — execution-free reward via graph matching (Graph-Reward-SQL).

Score a predicted query against the gold query using only their STRUCTURE. No
data is read, no query is run. This is the reward you need when you cannot
execute model-generated SQL against real data during training.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase4.py

Stuck? `HINTS.md` has three escalating levels per function.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from tiny_sql_env import TASKS, SCHEMA_TABLES  # noqa: E402
from rewards import extract_sql  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402

AGG_RE = re.compile(r"\b(count|sum|avg|min|max)\s*\(([^)]*)\)", re.IGNORECASE)
TABLE_RE = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
FILTER_RE = re.compile(
    r"([a-z_][a-z0-9_.]*)\s*(=|<>|!=|>=|<=|>|<)\s*('[^']*'|\"[^\"]*\"|[a-z0-9_.]+)",
    re.IGNORECASE,
)

COMPONENTS = ["tables", "aggs", "filters", "joins", "modifiers"]
DEFAULT_WEIGHTS = {"tables": 0.25, "aggs": 0.3, "filters": 0.15,
                   "joins": 0.1, "modifiers": 0.2}

# Structural markers that change a query's MEANING without changing which
# tables/columns it touches. Without these, "id IN (...)" and "id NOT IN (...)"
# look IDENTICAL to the graph — and q3's correct and inverted candidates tie.
MODIFIER_MARKERS = ["not in", "not exists", "exists", "in", "distinct",
                    "group by", "order by", "limit", "desc", "asc", "having"]


def canonicalize(sql: str) -> str:
    """Normalize whitespace and trailing punctuation so trivially-different
    spellings of the same query produce the same graph."""
    # TODO: strip, drop a trailing ';', collapse all runs of whitespace to one space
    raise NotImplementedError


def to_graph(sql: str) -> dict[str, set]:
    """Extract a typed component graph. Must return a set for every name in
    COMPONENTS.

      tables    — schema tables referenced (intersect with SCHEMA_TABLES so
                  aliases like `o`/`p` don't leak in)
      aggs      — normalized aggregate expressions, e.g. "sum(price*quantity)".
                  Strip whitespace AND alias prefixes (`p.price` -> `price`) or
                  the same aggregate written two ways won't match.
      filters   — value comparisons like "country='es'". Skip comparisons
                  between two columns — those are joins, not filters.
      joins     — unordered column pairs joined together, e.g. "id|product_id"
      modifiers — which MODIFIER_MARKERS appear. Careful: don't record bare
                  "in" when the text actually says "not in".
    """
    # TODO: implement the five extractors above
    raise NotImplementedError


def jaccard(a: set, b: set) -> float:
    """|a ∩ b| / |a ∪ b|, with the convention that two EMPTY sets score 1.0
    (both queries agree there is nothing of this kind)."""
    # TODO: implement
    raise NotImplementedError


def weighted_jaccard(a: dict[str, set], b: dict[str, set],
                     weights: dict[str, float]) -> float:
    """Weight-normalized sum of per-component Jaccard scores. Always in [0,1]."""
    # TODO: sum weights[name] * jaccard(a[name], b[name]), divide by sum(weights)
    raise NotImplementedError


def graph_reward(completion: str, gold_sql: str, weights=None) -> float:
    """The execution-free reward. Note it never touches SQLEnv."""
    weights = weights or DEFAULT_WEIGHTS
    # TODO: build both graphs and return their weighted Jaccard
    raise NotImplementedError


if __name__ == "__main__":
    print("Graph reward ranking per task — computed with ZERO data access:")
    for t in TASKS:
        scores = [graph_reward(c, t.gold_sql) for c in CANDIDATES[t.qid]]
        best = max(range(len(scores)), key=lambda i: scores[i])
        flag = "OK " if best == CORRECT_INDEX[t.qid] else "BAD"
        print(f"  [{flag}] {t.qid}: {[round(s, 3) for s in scores]} "
              f"(correct={CORRECT_INDEX[t.qid]}, top={best})")

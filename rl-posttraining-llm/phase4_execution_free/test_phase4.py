"""
Phase 4 tests — run this to check your `template_graph_reward.py`.

    python test_phase4.py

One test poisons the database executor and asserts your reward still works.
If it fails, your "execution-free" reward is executing something.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_between, assert_close, load_student_module  # noqa: E402
from tiny_sql_env import TASKS  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_graph_reward")

GOLD = {t.qid: t.gold_sql for t in TASKS}


def test_canonicalize():
    got = m.canonicalize("  SELECT   a\n FROM   b ;  ")
    assert ";" not in got, f"trailing semicolon not removed: {got!r}"
    assert "  " not in got, f"whitespace not collapsed: {got!r}"
    assert got.lower().startswith("select a from b"), got


def test_graph_has_all_components():
    g = m.to_graph("SELECT COUNT(*) FROM orders WHERE quantity > 2")
    for name in m.COMPONENTS:
        assert name in g, f"to_graph is missing component '{name}'"
        assert isinstance(g[name], set), f"component '{name}' is not a set"


def test_tables_ignore_aliases():
    g = m.to_graph("SELECT * FROM orders o JOIN products p ON o.product_id = p.id")
    assert g["tables"] == {"orders", "products"}, (
        f"expected {{orders, products}}, got {g['tables']}. Intersect with "
        "SCHEMA_TABLES so aliases like 'o'/'p' don't leak in."
    )


def test_aggs_normalize():
    a = m.to_graph("SELECT SUM(p.price * o.quantity) FROM orders o")
    b = m.to_graph("select sum(price*quantity) from orders")
    assert a["aggs"] == b["aggs"], (
        f"the same aggregate written two ways produced {a['aggs']} vs {b['aggs']}; "
        "strip whitespace and alias prefixes"
    )
    assert a["aggs"], "no aggregate extracted at all"


def test_joins_are_not_filters():
    g = m.to_graph("SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id "
                   "WHERE c.country = 'ES'")
    joined = " ".join(sorted(g["filters"]))
    assert "country" in joined, f"the real filter was dropped: {g['filters']}"
    assert not any("customer_id" in f and "'" not in f for f in g["filters"]), (
        f"a join condition was counted as a filter: {g['filters']}"
    )
    assert g["joins"], "no join edge extracted"


def test_modifiers_distinguish_negation():
    pos = m.to_graph("SELECT name FROM products WHERE id IN (SELECT product_id FROM orders)")
    neg = m.to_graph("SELECT name FROM products WHERE id NOT IN (SELECT product_id FROM orders)")
    assert pos["modifiers"] != neg["modifiers"], (
        "IN and NOT IN produced identical modifier sets — the graph is blind to "
        "negation, which is exactly the q3 failure this component exists to fix"
    )
    assert "not in" in neg["modifiers"], neg["modifiers"]


def test_jaccard():
    assert_close(m.jaccard({1, 2}, {1, 2}), 1.0, 1e-9, "jaccard of identical sets")
    assert_close(m.jaccard({1, 2}, {3, 4}), 0.0, 1e-9, "jaccard of disjoint sets")
    assert_close(m.jaccard({1, 2}, {2, 3}), 1 / 3, 1e-9, "jaccard with partial overlap")
    assert_close(m.jaccard(set(), set()), 1.0, 1e-9,
                 "two empty sets must score 1.0 (they agree there is nothing here)")


def test_weighted_jaccard_bounds():
    g = m.to_graph(GOLD["q1"])
    assert_close(m.weighted_jaccard(g, g, m.DEFAULT_WEIGHTS), 1.0, 1e-9,
                 "identical graphs")
    other = m.to_graph(GOLD["q5"])
    val = m.weighted_jaccard(g, other, m.DEFAULT_WEIGHTS)
    assert_between(val, 0.0, 1.0, "weighted_jaccard")


def test_gold_scores_one():
    for qid, gold in GOLD.items():
        got = m.graph_reward(f"<sql>{gold}</sql>", gold)
        assert_close(got, 1.0, 1e-9, f"graph_reward(gold, gold) for {qid}")


def test_reward_never_executes():
    """Poison the executor: if graph_reward touches data, this explodes."""
    import tiny_sql_env

    class PoisonedEnv(tiny_sql_env.SQLEnv):
        def execute(self, sql):
            raise AssertionError("graph_reward executed SQL — it must be execution-free")

    original = tiny_sql_env.SQLEnv
    tiny_sql_env.SQLEnv = PoisonedEnv
    try:
        for qid, gold in GOLD.items():
            for c in CANDIDATES[qid]:
                m.graph_reward(c, gold)
    finally:
        tiny_sql_env.SQLEnv = original


def test_q5_solved_without_execution():
    """The payoff. Execution reward gave 3 candidates an identical 1.0."""
    scores = [m.graph_reward(c, GOLD["q5"]) for c in CANDIDATES["q5"]]
    ci = CORRECT_INDEX["q5"]
    for i, s in enumerate(scores):
        if i == ci:
            continue
        assert scores[ci] > s, (
            f"q5: correct candidate scored {scores[ci]:.3f} but candidate {i} "
            f"scored {s:.3f}. All scores: {[round(x, 3) for x in scores]}"
        )


def test_q3_negation_is_caught():
    scores = [m.graph_reward(c, GOLD["q3"]) for c in CANDIDATES["q3"]]
    # candidate 2 is the logically INVERTED query (IN instead of NOT IN)
    assert scores[0] > scores[2], (
        f"the correct NOT IN query ({scores[0]:.3f}) must outscore the inverted "
        f"IN query ({scores[2]:.3f}) — add the `modifiers` component"
    )


def test_correct_ranks_first_on_every_task():
    failures = []
    for t in TASKS:
        scores = [m.graph_reward(c, t.gold_sql) for c in CANDIDATES[t.qid]]
        ci = CORRECT_INDEX[t.qid]
        best = max(range(len(scores)), key=lambda i: scores[i])
        if best != ci or any(s >= scores[ci] for i, s in enumerate(scores) if i != ci):
            failures.append((t.qid, [round(s, 3) for s in scores], ci))
    assert not failures, f"correct candidate did not rank strictly first: {failures}"


def test_reward_is_graded():
    """Not binary — a near-miss should score higher than a wild miss."""
    for qid in GOLD:
        scores = sorted(m.graph_reward(c, GOLD[qid]) for c in CANDIDATES[qid])
        assert len(set(round(s, 4) for s in scores)) >= 3, (
            f"{qid}: graph reward gave only {len(set(scores))} distinct values "
            f"({[round(s, 3) for s in scores]}); it should be graded, not binary"
        )


if __name__ == "__main__":
    c = Checker("Phase 4 — execution-free graph reward")
    c.check("canonicalize normalizes whitespace/semicolon", test_canonicalize)
    c.check("to_graph returns all components", test_graph_has_all_components)
    c.check("tables ignore aliases", test_tables_ignore_aliases)
    c.check("aggregates normalize", test_aggs_normalize)
    c.check("joins are not counted as filters", test_joins_are_not_filters)
    c.check("modifiers distinguish IN from NOT IN", test_modifiers_distinguish_negation)
    c.check("jaccard is correct (incl. empty sets)", test_jaccard)
    c.check("weighted_jaccard is bounded", test_weighted_jaccard_bounds)
    c.check("graph_reward(gold, gold) == 1.0", test_gold_scores_one)
    c.check("reward NEVER executes SQL", test_reward_never_executes)
    c.check("q5 solved without execution", test_q5_solved_without_execution)
    c.check("q3 negation is caught", test_q3_negation_is_caught)
    c.check("correct ranks first on all tasks", test_correct_ranks_first_on_every_task)
    c.check("reward is graded, not binary", test_reward_is_graded)
    sys.exit(c.summary())

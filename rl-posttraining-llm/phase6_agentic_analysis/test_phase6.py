"""
Phase 6 tests — run this to check your `template_data_agent.py`.

    python test_phase6.py
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_between, assert_close, load_student_module  # noqa: E402
from tiny_sql_env import SQLEnv  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_data_agent")


def _unwrap(x):
    while isinstance(x, (list, tuple)) and len(x) == 1:
        x = x[0]
    return x


def test_gold_answers_are_correct():
    env = SQLEnv()
    for task in m.ANALYTIC_TASKS:
        ok, res = env.execute(task.reference_sql)
        assert ok, f"{task.aid}: reference_sql failed: {res}"
        got = _unwrap(res)
        gold = task.gold_answer
        if isinstance(gold, float):
            assert abs(float(got) - gold) < 1e-6, f"{task.aid}: {got} != {gold}"
        else:
            assert str(got).lower() == str(gold).lower(), f"{task.aid}: {got} != {gold}"


def test_gold_answers_are_unambiguous():
    """A 'which X is highest' question with a tie has no single right answer."""
    env = SQLEnv()
    # NB: SQLEnv.execute() sorts result rows so that comparisons are
    # order-insensitive — which means a SQL `ORDER BY` does not survive it.
    # Rank in Python instead.
    rankings = {
        "a1": "SELECT SUM(p.price*o.quantity) FROM orders o JOIN products p "
              "ON o.product_id=p.id GROUP BY p.category",
        "a3": "SELECT SUM(o.quantity) FROM orders o JOIN products p "
              "ON o.product_id=p.id GROUP BY p.name",
        "a4": "SELECT COUNT(*) FROM orders o JOIN customers c "
              "ON o.customer_id=c.id GROUP BY c.country",
    }
    for aid, sql in rankings.items():
        ok, res = env.execute(sql)
        assert ok, res
        values = sorted((row[0] for row in res), reverse=True)
        assert len(values) >= 2, f"{aid}: need at least two groups to compare"
        assert values[0] != values[1], (
            f"{aid}: top two groups tie at {values[0]} — the gold answer is "
            f"ambiguous (all group values: {values})"
        )


def test_cites_finds_present_value():
    assert m.cites_previous_result("revenue was 600.0 for furniture",
                                   [("furniture", 600.0)]) is True


def test_cites_rejects_empty():
    assert m.cites_previous_result("furniture leads", None) is False
    assert m.cites_previous_result("furniture leads", []) is False


def test_cites_handles_float_and_case():
    assert m.cites_previous_result("total was 160", [(160.0,)]) is True, \
        "'160' should match 160.0"
    assert m.cites_previous_result("FURNITURE wins", [("furniture",)]) is True, \
        "matching should be case-insensitive"
    assert m.cites_previous_result("nothing relevant here", [("furniture",)]) is False


def _episode(env, specs):
    ep = m.AnalysisEpisode(question="test")
    for query, reasoning in specs:
        ep.add_step(query, env, reasoning)
    return ep


def test_process_reward_bounds():
    env = SQLEnv()
    assert_close(m.process_reward(m.AnalysisEpisode(question="x")), 0.0, 1e-9,
                 "process_reward of an empty episode")
    ep = _episode(env, [("SELECT COUNT(*) FROM customers", "")])
    assert_between(m.process_reward(ep), 0.0, 1.0, "process_reward")


def test_grounded_beats_hallucinated():
    env = SQLEnv()
    grounded = _episode(env, [
        ("SELECT category, SUM(price) FROM products GROUP BY category", "look at categories"),
        ("SELECT name FROM products WHERE category='furniture'",
         "furniture totalled 200.0, so I drill into it"),
    ])
    # NB: the ungrounded reasoning must not accidentally mention a value the
    # previous query returned ("furniture" IS in that result set), or it counts
    # as grounded and the two episodes tie.
    hallucinated = _episode(env, [
        ("SELECT category, SUM(price) FROM products GROUP BY category", "look at categories"),
        ("SELECT name FROM products WHERE category='furniture'",
         "it is obvious which one leads, no need to check"),
    ])
    g, h = m.process_reward(grounded), m.process_reward(hallucinated)
    assert g > h, (
        f"grounded episode scored {g:.3f}, ungrounded scored {h:.3f} — reasoning "
        "that cites the previous result must score higher"
    )


def test_redundancy_is_penalized():
    env = SQLEnv()
    q = "SELECT COUNT(*) FROM customers"
    fresh = _episode(env, [(q, ""), ("SELECT COUNT(*) FROM orders", "4 customers found")])
    repeat = _episode(env, [(q, ""), (q, "4 customers found")])
    assert m.process_reward(fresh) > m.process_reward(repeat), (
        "repeating the same query should score lower than asking something new"
    )


def test_verifier_basic():
    v = m.make_verifier("furniture")
    assert_close(v("furniture"), 1.0, 1e-9, "exact string match")
    assert_close(v("electronics"), 0.0, 1e-9, "wrong string")


def test_verifier_unwraps_results():
    v = m.make_verifier("furniture")
    assert_close(v([("furniture",)]), 1.0, 1e-9, "single-cell result row")


def test_verifier_tolerances():
    v = m.make_verifier(160.0)
    assert_close(v(160), 1.0, 1e-9, "int vs float")
    assert_close(v([(160.0,)]), 1.0, 1e-9, "wrapped float")
    assert_close(v(161.0), 0.0, 1e-9, "wrong number")
    assert_close(m.make_verifier("ES")(" es "), 1.0, 1e-9, "case/whitespace")


def test_verifier_never_raises():
    v = m.make_verifier(160.0)
    for bad in (None, "not a number", [], object()):
        got = v(bad)
        assert got == 0.0, f"verifier returned {got!r} for {bad!r}; expected 0.0"


def test_generation_shape_and_grounding():
    env = SQLEnv()
    tasks = m.generate_candidate_questions(env, 8, random.Random(0))
    assert len(tasks) == 8, f"asked for 8 tasks, got {len(tasks)}"
    for t in tasks:
        assert t.question and t.reference_sql, f"empty task: {t}"
        assert any(tbl in t.reference_sql for tbl in
                   ("customers", "products", "orders")), \
            f"generated SQL is not schema-grounded: {t.reference_sql}"


def test_generated_answers_come_from_executor():
    env = SQLEnv()
    for t in m.generate_candidate_questions(env, 8, random.Random(1)):
        ok, res = env.execute(t.reference_sql)
        assert ok, f"generated SQL does not run: {t.reference_sql} ({res})"
        assert res and res[0][0] is not None, f"generated task has no answer: {t}"
        assert m.make_verifier(t.gold_answer)(res) == 1.0, (
            f"gold_answer {t.gold_answer!r} does not match what its SQL returns "
            f"({res}) — the executor must be the labeller"
        )


def test_self_improve_round_shape():
    env = SQLEnv()

    def perfect(task):
        ok, res = env.execute(task.reference_sql)
        return res if ok else None

    stats = m.self_improve_round(env, perfect, random.Random(0), n_candidates=10)
    for key in ("generated", "kept", "failed", "accuracy"):
        assert key in stats, f"self_improve_round is missing key '{key}'"
    assert stats["generated"] == len(stats["kept"]) + len(stats["failed"]), \
        f"counts don't add up: {stats['generated']} vs kept+failed"
    assert_between(stats["accuracy"], 0.0, 1.0, "accuracy")


def test_self_improve_separates_solvers():
    env = SQLEnv()

    def perfect(task):
        ok, res = env.execute(task.reference_sql)
        return res if ok else None

    def broken(task):
        return "definitely wrong"

    good = m.self_improve_round(env, perfect, random.Random(0), n_candidates=10)
    bad = m.self_improve_round(env, broken, random.Random(0), n_candidates=10)
    assert_close(good["accuracy"], 1.0, 1e-9, "accuracy of a perfect solver")
    assert_close(bad["accuracy"], 0.0, 1e-9, "accuracy of a broken solver")
    assert bad["failed"], "a broken solver must produce a non-empty curriculum"


if __name__ == "__main__":
    c = Checker("Phase 6 — agentic data analysis")
    c.check("gold answers match their reference SQL", test_gold_answers_are_correct)
    c.check("gold answers are unambiguous (no ties)", test_gold_answers_are_unambiguous)
    c.check("cites_previous_result finds present values", test_cites_finds_present_value)
    c.check("cites_previous_result rejects empty results", test_cites_rejects_empty)
    c.check("cites handles float/case forms", test_cites_handles_float_and_case)
    c.check("process_reward is bounded", test_process_reward_bounds)
    c.check("grounded beats hallucinated reasoning", test_grounded_beats_hallucinated)
    c.check("redundant queries are penalized", test_redundancy_is_penalized)
    c.check("verifier handles exact matches", test_verifier_basic)
    c.check("verifier unwraps result rows", test_verifier_unwraps_results)
    c.check("verifier tolerates float/case forms", test_verifier_tolerances)
    c.check("verifier never raises", test_verifier_never_raises)
    c.check("generation is schema-grounded", test_generation_shape_and_grounding)
    c.check("generated answers come from the executor",
            test_generated_answers_come_from_executor)
    c.check("self_improve_round has a consistent shape", test_self_improve_round_shape)
    c.check("self_improve_round separates solvers", test_self_improve_separates_solvers)
    sys.exit(c.summary())

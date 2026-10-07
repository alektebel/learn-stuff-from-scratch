"""
Phase 3 tests — run this to check your `template_prm.py`.

    python test_phase3.py

The last test asserts a *failure*: an MC-labeled PRM inherits the executor's
blind spot on q5. That's the lesson, not a bug.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_between, assert_close, load_student_module  # noqa: E402
from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402
from rewards import execution_accuracy, extract_sql  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_prm")

Q1 = task_by_qid("q1")
Q5 = task_by_qid("q5")


def test_decompose_splits_clauses():
    got = m.decompose("SELECT name FROM products WHERE id = 1")
    assert len(got) == 3, f"expected 3 clauses, got {len(got)}: {got}"
    lowered = [c.lower() for c in got]
    assert lowered[0].startswith("select"), got
    assert lowered[1].startswith("from"), got
    assert lowered[2].startswith("where"), got


def test_decompose_preserves_case():
    """The classic bug: lowercasing the output breaks string literals."""
    got = m.decompose("SELECT COUNT(*) FROM customers WHERE country='ES'")
    joined = " ".join(got)
    assert "'ES'" in joined, (
        f"string literal was lowercased: {joined!r}. Match keywords on a "
        "lowercased COPY, but slice the original string."
    )


def test_decompose_edge_cases():
    single = m.decompose("gibberish tokens here")
    assert len(single) == 1, f"a query with no clause keyword should be 1 chunk: {single}"
    empty = m.decompose("")
    assert empty == [] or empty == [""], f"empty input should give an empty trace: {empty}"


def test_step_features_shape():
    feats = m.step_features([], "FROM orders", Q5)
    assert len(feats) == m.FEATURE_DIM, (
        f"expected {m.FEATURE_DIM} features, got {len(feats)}"
    )
    for i, f in enumerate(feats):
        assert isinstance(f, (int, float)), f"feature {i} is {type(f).__name__}"
        assert_between(float(f), 0.0, 1.0, f"feature {i}")


def test_coverage_feature_discriminates():
    gold = m.step_features([], "FROM orders o JOIN products p ON o.product_id=p.id", Q5)
    junk = m.step_features([], "FROM customers", Q5)
    assert gold[0] > junk[0], (
        f"gold-coverage feature should be higher for a gold-table step "
        f"({gold[0]}) than an irrelevant one ({junk[0]})"
    )


def test_spurious_feature_discriminates():
    gold = m.step_features([], "FROM orders o JOIN products p ON o.product_id=p.id", Q5)
    junk = m.step_features([], "FROM customers", Q5)
    assert junk[1] > gold[1], (
        f"spurious-table feature should be higher for an off-schema step "
        f"({junk[1]}) than a gold one ({gold[1]}). Count TABLES, not all "
        "identifiers — 'id' belongs to every table."
    )


def test_mc_label_in_range():
    env = SQLEnv()
    rng = random.Random(0)
    for qid in ("q1", "q5"):
        task = task_by_qid(qid)
        for c in CANDIDATES[qid]:
            lab = m.mc_label(extract_sql(c), task, env, 4, rng)
            assert_between(lab, 0.0, 1.0, f"mc_label for {qid}")


def test_mc_label_separates_good_prefix_from_bad():
    env = SQLEnv()
    good = m.mc_label("SELECT COUNT(*) FROM customers", Q1, SQLEnv(), 8, random.Random(0))
    bad = m.mc_label("SELECT name FROM orders", Q1, env, 8, random.Random(0))
    assert good > bad, (
        f"a completable prefix ({good}) should label higher than a hopeless one "
        f"({bad}) — this is the whole point of MC labeling"
    )


def test_prm_score_bounded_and_safe():
    prm = m.PRM(m.FEATURE_DIM)
    assert_close(prm.score([0.0] * m.FEATURE_DIM), 0.5, 1e-6, "score at zero weights")
    prm.w = [1e6] * m.FEATURE_DIM
    prm.b = -1e6
    for feats in ([1.0] * m.FEATURE_DIM, [0.0] * m.FEATURE_DIM):
        s = prm.score(feats)
        assert s == s, "score returned nan — use the two-branch sigmoid"
        assert_between(s, 0.0, 1.0, "score with extreme weights")


def test_fit_step_moves_toward_label():
    prm = m.PRM(m.FEATURE_DIM)
    feats = [1.0, 0.0, 1.0, 0.0]
    before = prm.score(feats)
    for _ in range(50):
        prm.fit_step(feats, 1.0, lr=0.5)
    after = prm.score(feats)
    assert after > before, f"score should rise toward label 1.0: {before} -> {after}"

    prm2 = m.PRM(m.FEATURE_DIM)
    before2 = prm2.score(feats)
    for _ in range(50):
        prm2.fit_step(feats, 0.0, lr=0.5)
    assert prm2.score(feats) < before2, "score should fall toward label 0.0"


def test_train_prm_learns_something():
    prm = m.train_prm(SQLEnv(), steps=150, seed=0)
    assert any(abs(w) > 1e-6 for w in prm.w) or abs(prm.b) > 1e-6, (
        "train_prm returned an untouched PRM — did you call fit_step?"
    )


def test_prm_trace_score_bounded():
    prm = m.train_prm(SQLEnv(), steps=150, seed=0)
    for qid in ("q1", "q5"):
        task = task_by_qid(qid)
        for c in CANDIDATES[qid]:
            s = m.prm_trace_score(c, task, prm)
            assert_between(s, 0.0, 1.0, f"prm_trace_score for {qid}")
    assert_close(m.prm_trace_score("<sql></sql>", Q1, prm), 0.0, 1e-9,
                 "trace score of an empty query")


def test_shaped_reward_reduces_to_exec():
    env = SQLEnv()
    prm = m.train_prm(SQLEnv(), steps=150, seed=0)
    for qid in ("q1", "q5"):
        task = task_by_qid(qid)
        for c in CANDIDATES[qid]:
            got = m.shaped_reward(c, task, env, prm, w_exec=1.0, w_prm=0.0)
            want = execution_accuracy(c, task, env)
            assert_close(got, want, 1e-9, f"shaped_reward with w_prm=0 for {qid}")


def test_shaped_reward_is_dense():
    """On q1, execution reward is 0 for three candidates; the PRM term must
    still give them nonzero, non-identical signal."""
    env = SQLEnv()
    prm = m.train_prm(SQLEnv(), steps=150, seed=0)
    wrong = [c for c in CANDIDATES["q1"] if execution_accuracy(c, Q1, env) == 0.0]
    scores = [m.shaped_reward(c, Q1, env, prm, w_exec=1.0, w_prm=0.5) for c in wrong]
    assert all(s > 0.0 for s in scores), (
        f"all execution-failing q1 candidates scored 0 under the shaped reward: {scores}"
    )
    assert len(set(round(s, 6) for s in scores)) > 1, (
        f"shaped reward gave identical scores to different wrong queries: {scores}"
    )


def test_blind_spot_is_inherited():
    """The lesson: MC labels are grounded in execution, so they inherit its
    blind spot. q5 candidates 0 and 1 both execute correctly -> same label."""
    env = SQLEnv()
    l0 = m.mc_label(extract_sql(CANDIDATES["q5"][0]), Q5, env, 8, random.Random(1))
    l1 = m.mc_label(extract_sql(CANDIDATES["q5"][1]), Q5, env, 8, random.Random(2))
    assert_close(l0, l1, 1e-9, "q5 cand0 vs cand1 MC label")
    assert_close(l0, 1.0, 1e-9, "q5 cand0 MC label")


if __name__ == "__main__":
    c = Checker("Phase 3 — process reward models")
    c.check("decompose splits clauses in order", test_decompose_splits_clauses)
    c.check("decompose preserves case (string literals!)", test_decompose_preserves_case)
    c.check("decompose handles edge cases", test_decompose_edge_cases)
    c.check("step_features has the right shape/range", test_step_features_shape)
    c.check("coverage feature discriminates", test_coverage_feature_discriminates)
    c.check("spurious-table feature discriminates", test_spurious_feature_discriminates)
    c.check("mc_label is in [0,1]", test_mc_label_in_range)
    c.check("mc_label separates good from hopeless prefixes",
            test_mc_label_separates_good_prefix_from_bad)
    c.check("PRM.score is bounded and overflow-safe", test_prm_score_bounded_and_safe)
    c.check("fit_step moves score toward the label", test_fit_step_moves_toward_label)
    c.check("train_prm actually learns", test_train_prm_learns_something)
    c.check("prm_trace_score is bounded", test_prm_trace_score_bounded)
    c.check("shaped_reward reduces to exec when w_prm=0", test_shaped_reward_reduces_to_exec)
    c.check("shaped_reward is dense", test_shaped_reward_is_dense)
    c.check("blind spot IS inherited (expected)", test_blind_spot_is_inherited)
    sys.exit(c.summary())

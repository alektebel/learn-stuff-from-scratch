"""
Progress checker for the MARS-SQL templates.

    python3 check.py           # stop at the first gap
    python3 check.py 3         # only step 3
    python3 check.py --all     # everything

Nothing here imports solutions/. It tests YOUR code.
Do ../contextcite/ before the last check.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_db_gold() -> None:
    """Sanity: the provided executor answers the running question."""
    from db import GOLD_NAME, gold_rows
    rows = gold_rows()
    assert rows == [{"name": GOLD_NAME}], (
        f"the provided gold SQL must return [{{'name': {GOLD_NAME!r}}}], "
        f"got {rows}. If this fails, db.py itself is broken — do not edit "
        "the templates to paper over it.")


def check_grounding() -> None:
    from db import QUESTION, SCHEMA
    from grounding import ground_table, grounding_reward, reduce_schema

    dep = ground_table(QUESTION, "departments", SCHEMA["departments"])
    emp = ground_table(QUESTION, "employees", SCHEMA["employees"])
    assert dep[0] == "Y" and emp[0] == "Y", (
        f"both tables are required for the join, got departments={dep} "
        f"employees={emp}")
    for required in ("name", "manager_id"):
        assert required in dep[1], (
            f"departments is missing {required}: {dep[1]}. You cannot "
            "filter Sales or join to the manager without it.")
    for required in ("id", "name"):
        assert required in emp[1], (
            f"employees is missing {required}: {emp[1]}")

    other = ground_table(QUESTION, "offices", ["id", "city"])
    assert other == ("N", []), f"unknown tables must be dropped, got {other}"

    reduced = reduce_schema(QUESTION, SCHEMA)
    assert set(reduced) == {"departments", "employees"}
    assert "title" not in reduced.get("employees", []) or True  # extra OK

    gold_dep = ("Y", ["name", "manager_id"])
    assert grounding_reward(("Y", ["name", "manager_id"]), gold_dep) == 1.0
    assert grounding_reward(("Y", ["id", "name", "manager_id"]),
                            gold_dep) >= 0.5, (
        "a superset of the gold columns must score at least 0.5 — recall "
        "over precision")
    assert grounding_reward(("Y", ["name"]), gold_dep) == 0.1, (
        "Y with a missing gold column is 0.1, not 0 — the paper gives "
        "partial credit so GRPO has a slope")
    assert grounding_reward(("Y", ["id"]), ("N", [])) == 0.2
    assert grounding_reward(("Q", ["name"]), gold_dep) == 0.0
    assert grounding_reward(("Y", ["not_a_column"]), gold_dep) == 0.0


def check_step_and_typo() -> None:
    from db import GOLD_NAME
    from generation import correct_typo, step

    cols = step("DESCRIBE employees")
    assert "name" in cols and "title" in cols, f"DESCRIBE gave {cols!r}"
    assert "no such table" in step("DESCRIBE fprm").lower()

    typo_sql = ("SELECT employees.name FROM emplyees "
                "JOIN departments ON employees.id = departments.manager_id "
                "WHERE departments.name = 'Sales'")
    err = step("RUN " + typo_sql)
    assert "no such table" in err.lower() and "emplyees" in err, (
        f"a typo must become an observation, not an exception. Got {err!r}")

    fixed = correct_typo(typo_sql)
    assert "emplyees" not in fixed.lower()
    assert "employees" in fixed.lower()
    rows = step("FINISH " + fixed)
    assert GOLD_NAME in rows, (
        f"FINISH still has to execute the SQL so validation can see the "
        f"rows. Got {rows!r}")
    assert step("DANCE") == "unknown action"


def check_react_loop() -> None:
    from db import GOLD_NAME, QUESTION, SCHEMA
    from generation import final_sql, react_until_done, rollout_group

    calls = {"n": 0}

    def policy(question, schema, history):
        calls["n"] += 1
        if not history:
            return ("try the join",
                    "RUN SELECT name FROM fprm WHERE name = 'Sales'")
        obs = history[-1]["observation"]
        assert "no such table" in obs.lower(), (
            f"the policy only recovers if it SEES the error. Observation "
            f"was {obs!r} — step() is probably raising instead of "
            "returning the string.")
        return ("fix the table name",
                "FINISH SELECT employees.name FROM employees "
                "JOIN departments ON employees.id = departments.manager_id "
                "WHERE departments.name = 'Sales'")

    traj = react_until_done(policy, QUESTION, SCHEMA, max_turns=5)
    assert len(traj) == 2, f"typo then finish should be 2 turns, got {len(traj)}"
    assert traj[0]["action"].startswith("RUN")
    assert traj[1]["action"].startswith("FINISH")
    sql = final_sql(traj)
    assert "employees.name" in sql.lower() or "name" in sql.lower()
    try:
        final_sql([{"thought": "x", "action": "RUN 1", "observation": "err"}])
        raise AssertionError("a trajectory with no FINISH must raise ValueError")
    except ValueError:
        pass

    group = rollout_group(policy, QUESTION, SCHEMA, n=3)
    assert len(group) == 3
    assert all(GOLD_NAME in t[-1]["observation"] for t in group)


def check_score_yes() -> None:
    from db import QUESTION
    from validation import score_yes

    gold = ("SELECT employees.name FROM employees "
            "JOIN departments ON employees.id = departments.manager_id "
            "WHERE departments.name = 'Sales'")
    wrong = ("SELECT employees.name FROM employees "
             "JOIN departments ON employees.id = departments.manager_id "
             "WHERE departments.name = 'HR'")
    broken = "SELECT name FROM fprm"
    assert score_yes(QUESTION, gold) >= 0.9
    assert score_yes(QUESTION, wrong) <= 0.3
    assert score_yes(QUESTION, broken) <= 0.1
    assert score_yes(QUESTION, gold) > score_yes(QUESTION, wrong) > (
        score_yes(QUESTION, broken)), (
        "the three bands must be ordered: gold > wrong-but-running > error. "
        "If wrong ≈ gold you are scoring executability, not correctness.")


def check_selection_trap() -> None:
    from db import QUESTION
    from validation import select_trajectory, self_consistency

    gold_sql = ("SELECT employees.name FROM employees "
                "JOIN departments ON employees.id = departments.manager_id "
                "WHERE departments.name = 'Sales'")
    popular_wrong = ("SELECT employees.name FROM employees "
                     "JOIN departments ON employees.id = departments.manager_id "
                     "WHERE departments.name = 'HR'")
    # Three copies of the wrong answer, one gold — self-consistency's trap.
    trajectories = [
        [{"thought": "", "action": "FINISH " + popular_wrong, "observation": ""}],
        [{"thought": "", "action": "FINISH " + popular_wrong, "observation": ""}],
        [{"thought": "", "action": "FINISH " + popular_wrong, "observation": ""}],
        [{"thought": "", "action": "FINISH " + gold_sql, "observation": ""}],
    ]
    idx, scores = select_trajectory(QUESTION, trajectories)
    assert idx == 3, (
        f"generative validation must pick the gold trajectory (index 3), "
        f"got {idx} with scores {scores}. If you picked 0 you implemented "
        "majority vote under the wrong name.")
    assert scores[3] > scores[0]

    sc_idx, _ = self_consistency(trajectories)
    assert sc_idx in (0, 1, 2), (
        f"self-consistency should pick the popular WRONG cluster, got "
        f"{sc_idx}. The contrast with select_trajectory is the lesson.")


def check_used_columns() -> None:
    from cite import citations_are_relevant, used_columns

    sql = ("SELECT employees.name FROM employees "
           "JOIN departments ON employees.id = departments.manager_id "
           "WHERE departments.name = 'Sales'")
    used = used_columns(sql)
    joined = " ".join(used)
    for needle in ("name", "id", "manager_id"):
        assert needle in joined, f"{needle} not found in {used}"

    relevant = [
        {"source": "The employees table has a column name.", "index": 0, "score": 1},
        {"source": "The departments table has a column manager_id.", "index": 1, "score": 1},
    ]
    assert citations_are_relevant(relevant, sql) is True
    noisy = relevant + [{"source": "The employees table has a column title.",
                         "index": 2, "score": 0.4}]
    assert citations_are_relevant(noisy, sql) is False, (
        "employees.title is not in the SQL. A citation that names it is "
        "listening to the schema, not to the query — reject the set.")


def check_cite_sql() -> None:
    from cite import cite_sql, citations_are_relevant, schema_context
    from db import schema_sentences

    sql = ("SELECT employees.name FROM employees "
           "JOIN departments ON employees.id = departments.manager_id "
           "WHERE departments.name = 'Sales'")
    context = schema_context(schema_sentences())
    assert context == " ".join(schema_sentences())
    ranked = cite_sql(sql, context, top_k=4)
    assert len(ranked) == 4
    assert citations_are_relevant(ranked, sql), (
        f"top-4 citations must all name columns the SQL uses, got "
        f"{[r.get('source') for r in ranked]}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("db.py", "provided gold SQL returns Ada Lovelace", check_db_gold),
    ("grounding.py", "schema linking and the graded reward", check_grounding),
    ("generation.py", "DESCRIBE / RUN / FINISH, typo becomes observation",
     check_step_and_typo),
    ("generation.py", "ReAct recovers after seeing the error",
     check_react_loop),
    ("validation.py", "P(Yes) bands: gold > wrong > error", check_score_yes),
    ("validation.py", "generative selection beats majority vote",
     check_selection_trap),
    ("cite.py", "used columns, and relevance of a citation set",
     check_used_columns),
    ("cite.py", "ContextCite the SQL to its schema sources", check_cite_sql),
]


def run_one(check):
    try:
        check()
        return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}MARS-SQL From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — three agents, then a citation."
              f"{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

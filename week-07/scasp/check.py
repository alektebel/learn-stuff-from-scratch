"""
Progress checker for s(CASP).

    python3 check.py           # stop at the first gap
    python3 check.py 5         # only step 5
    python3 check.py --all     # everything
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


def check_unify_and_occurs() -> None:
    from program import const, fun, var
    from unify import occurs, unify_args

    xa = unify_args(var("X"), const("a"))
    assert xa == {"X": const("a")}, f"unify(X,a) got {xa}"

    fx = unify_args(fun("f", var("X")), fun("f", const("a")))
    assert fx == {"X": const("a")}, f"unify(f(X),f(a)) got {fx}"

    assert unify_args(fun("f", var("X")), fun("g", const("a"))) is None
    assert unify_args(const("a"), const("b")) is None

    assert occurs("X", fun("f", var("X")), {}) is True
    assert occurs("X", fun("f", var("Y")), {"Y": fun("g", var("X"))}) is True
    assert occurs("X", const("a"), {}) is False
    assert unify_args(var("X"), fun("f", var("X"))) is None, (
        "X = f(X) must fail the occurs check. If it succeeded you "
        "built a cyclic term; coinduction is not this.")

    # chase: X=Y, Y=a
    s = unify_args(var("X"), var("Y"))
    s = unify_args(var("Y"), const("a"), s)
    from term import apply_arg
    assert apply_arg(var("X"), s) == const("a"), (
        f"after X=Y, Y=a, X should chase to a, got {apply_arg(var('X'), s)}")


def check_rename_and_member() -> None:
    from program import MEMBER, const, list_of, pos, var
    from sld import sld, sld_all
    from term import apply_arg, rename_clause

    head, body = MEMBER[0]
    h2, b2 = rename_clause(head, body, 7)
    assert "X_7" in str(h2) or (h2[1] and "X_7" in str(h2[1])), (
        f"rename_clause must stamp variables, got head={h2}")
    assert h2 != head

    goal = [pos("member", const("a"), list_of("a", "b"))]
    subst = sld(goal, MEMBER)
    assert subst is not None, "member(a,[a,b]) must succeed"

    goal_miss = [pos("member", const("c"), list_of("a", "b"))]
    assert sld(goal_miss, MEMBER) is None, "member(c,[a,b]) must fail"

    goal_var = [pos("member", var("X"), list_of("a", "b"))]
    answers = list(sld_all(goal_var, MEMBER, max_answers=4))
    bound = {apply_arg(var("X"), s) for s in answers}
    assert const("a") in bound and const("b") in bound, (
        f"member(X,[a,b]) should bind X to a and to b, got {bound}")


def check_sld_diverges_on_even() -> None:
    from program import EVEN_LOOP, pos
    from sld import sld

    result = sld([pos("p")], EVEN_LOOP, max_steps=32)
    assert result is None, (
        f"plain SLD on p :- q. q :- p. must hit max_steps and return "
        f"None, got {result}. If you succeeded you already have "
        "coinduction in sld.py — keep it in coinductive.py so the "
        "limit case stays visible.")


def check_duals() -> None:
    from dual import compile_duals, duals_for, group_by_predicate
    from program import UNIT, atom, const, fact, pos, rule, var

    grouped = group_by_predicate(UNIT)
    assert grouped[("p", 1)] == UNIT

    duals = duals_for("p", 1, UNIT)
    assert len(duals) == 1, f"one fact → one dual, got {duals}"
    head, body = duals[0]
    assert head[0] in ("not_p", "not p"), (
        f"dual head should be not_p(...), got {head}")
    assert len(body) == 1 and body[0][0] == "pos"
    assert body[0][1][0] == "neq", (
        f"dual of p(a) is not_p(X) :- neq(X,a). Body was {body}")

    # p(X) :- q(X), r(X).  → two duals, one per conjunct.
    conj = [rule(atom("p", var("X")), pos("q", var("X")), pos("r", var("X")))]
    d = duals_for("p", 1, conj)
    assert len(d) == 2, (
        f"De Morgan: two conjuncts → two dual clauses, got {len(d)}: {d}")

    # no clauses → not_p is a fact
    empty = duals_for("ghost", 1, [])
    assert len(empty) == 1 and empty[0][1] == [], (
        f"undefined predicate: not_ghost(X) is a fact, got {empty}")

    compiled = compile_duals(UNIT)
    preds = {c[0][0] for c in compiled}
    assert "p" in preds
    assert any(p.startswith("not") for p in preds), compiled


def check_coinductive_even_odd() -> None:
    from coinductive import query
    from program import EVEN_LOOP, ODD_LOOP, pos
    from sld import sld

    assert sld([pos("p")], EVEN_LOOP, max_steps=16) is None
    even = query([pos("p")], EVEN_LOOP, max_steps=16)
    assert even is not None, (
        "p :- q. q :- p. is an even loop: coSLD succeeds. If you "
        "returned None you treated a repeated ancestor as failure.")

    odd = query([pos("p")], ODD_LOOP, max_steps=16)
    assert odd is None, (
        f"p :- not p. is an odd loop: not an answer set, got {odd}. "
        "If this succeeded you closed a loop without looking at "
        "negation depth.")


def check_constructive_not() -> None:
    from coinductive import query
    from program import UNIT, const, pos, var
    from term import apply_arg

    # not p(a) fails; not p(b) succeeds.
    assert query([("neg", ("p", (const("a"),)))], UNIT) is None, (
        "not p(a) must fail — p(a) is a fact")
    ok = query([("neg", ("p", (const("b"),)))], UNIT)
    assert ok is not None, (
        "not p(b) must succeed. If it failed you implemented "
        "negation-as-failure on a closed world that only knows a, "
        "without generating the dual neq(X,a).")

    # not p(X) binds X to something other than a? For a single fact
    # p(a), the dual is not_p(X) :- neq(X,a). X is still free — the
    # constructive witness is "any X ≠ a". The checker asks the
    # ground cases above; a free X succeeding is also acceptable
    # (ok is not None). If you bind X to a, you inverted it.
    free = query([("neg", ("p", (var("X"),)))], UNIT)
    if free is not None:
        bound = apply_arg(var("X"), free)
        assert bound != const("a"), (
            f"not p(X) must not bind X to a, got {bound}")


def check_flies() -> None:
    from coinductive import query
    from program import FLIES, const

    def q(pred, name):
        return query([("pos", (pred, (const(name),)))], FLIES)

    assert q("bird", "tweety") is not None
    assert q("bird", "opus") is not None
    assert q("penguin", "tweety") is not None
    assert q("penguin", "opus") is None
    assert q("flies", "opus") is not None, (
        "opus is a sparrow, not a penguin → flies. If this failed "
        "the dual of penguin did not succeed for opus.")
    assert q("flies", "tweety") is None, (
        "tweety is a penguin → not flies. If this succeeded you "
        "dropped the not penguin(X) literal.")


def check_justification() -> None:
    from justify import atoms_used, pretty, query_tree
    from program import EVEN_LOOP, FLIES, const, pos

    tree = query_tree([pos("flies", const("opus"))], FLIES)
    assert tree is not None, "flies(opus) must produce a tree"
    for key in ("atom", "kind", "subst", "children"):
        assert key in tree, f"missing {key} on the root"
    used = atoms_used(tree)
    preds = {a[0] for a in used}
    assert "sparrow" in preds, (
        f"lineage of flies(opus) must include the sparrow fact, got {used}")
    assert "penguin" not in preds, (
        f"flies(opus) must not cite penguin(tweety), got {used}. "
        "That is the other bird, not a reason Opus flies.")

    no = query_tree([pos("flies", const("tweety"))], FLIES)
    assert no is None

    loop = query_tree([pos("p")], EVEN_LOOP)
    assert loop is not None
    kinds = []

    def walk(n):
        kinds.append(n.get("kind"))
        for c in n.get("children") or []:
            walk(c)
    walk(loop)
    assert "coinductive" in kinds, (
        f"even-loop tree must mark the close as kind='coinductive', "
        f"got kinds={kinds}")

    text = pretty(loop)
    assert "p" in text and "q" in text


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("unify.py", "MGU, chase, occurs check rejects X=f(X)",
     check_unify_and_occurs),
    ("sld.py", "rename clauses; member/2 both answers",
     check_rename_and_member),
    ("sld.py", "even loop: SLD returns None at max_steps",
     check_sld_diverges_on_even),
    ("dual.py", "fact dual is neq; conjuncts De Morgan",
     check_duals),
    ("coinductive.py", "even loop succeeds; odd loop fails",
     check_coinductive_even_odd),
    ("coinductive.py", "not p(a) fails, not p(b) succeeds",
     check_constructive_not),
    ("coinductive.py", "opus flies; tweety does not",
     check_flies),
    ("justify.py", "proof tree; lineage is the fact leaves",
     check_justification),
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

    print(f"\n{BOLD}s(CASP) From Scratch — progress check{RESET}")
    print(f"{GREY}the result is a justification tree, not a boolean{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<18} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<18} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<18} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — a query is a tree "
              f"you can replay.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

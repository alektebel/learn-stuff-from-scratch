"""
Progress checker for LINC / Logic-LM / Faithful CoT.

    python3 check.py           # stop at the first gap
    python3 check.py 8         # only the provenance check
    python3 check.py --all     # everything

Do ../provenance-semirings/ before the last check.
"""

import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_ground_and_nnf() -> None:
    from fixtures import Imp, P, C, V, Forall, Not
    from fol import conjuncts, ground, nnf, subst_formula

    phi = Forall("x", Imp(P("cat", V("x")), P("mammal", V("x"))))
    g = ground(phi, ["fiona"])
    # ∀x (cat(x)→mammal(x)) over {fiona} is cat(fiona)→mammal(fiona)
    assert "forall" not in str(g), f"ground still has a quantifier: {g}"
    assert subst_formula(P("cat", V("x")), "x", "fiona") == P("cat", C("fiona"))

    assert nnf(Not(Not(P("a", C("z"))))) == P("a", C("z"))
    n = nnf(Not(Imp(P("a", C("z")), P("b", C("z")))))
    parts = conjuncts(n)
    assert any(p == P("a", C("z")) for p in parts) or n[0] == "and", (
        f"¬(a→b) is a ∧ ¬b, got {n}")


def check_gold_parser() -> None:
    from fixtures import problems
    from parser import GoldParser, theory_ok

    gp = GoldParser()
    for p in problems():
        t = gp.translate(p["premises_nl"], p["conclusion_nl"])
        assert theory_ok(t), f"{p['id']} gold theory rejected"
        assert t["premises"] == p["premises_fol"], (
            f"{p['id']}: gold parser must emit the fixture FOL, "
            f"got {t['premises']}")
        assert t["conclusion"] == p["conclusion_fol"]
        assert t["domain"] == p["domain"]

    bad = gp.translate(["not a fixture"], "nope")
    assert bad.get("ok") is False, (
        "unknown English must be ok=False, not an invented formula")


def check_faults() -> None:
    from faults import apply_fault, bin_of
    from fixtures import Forall, Imp, Not, P, C, V

    forall = Forall("x", Imp(P("cat", V("x")), P("mammal", V("x"))))
    inv = apply_fault(forall, "scope_invert")
    assert inv[0] == "exists", (
        f"scope_invert turns the first ∀ into ∃, got {inv}")

    dropped = apply_fault(Not(P("flies", C("tweety"))), "drop_negation")
    assert dropped == P("flies", C("tweety")), (
        f"drop_negation must strip the first ¬, got {dropped}")

    drifted = apply_fault(P("cat", C("fiona")), "arity_drift")
    assert drifted[0] == "pred" and len(drifted[2]) == 2, (
        f"arity_drift adds an argument, got {drifted}. LINC L3 is "
        "the same symbol with two arities.")

    hall = apply_fault(P("cat", C("fiona")), "hallucinate_const")
    assert hall != P("cat", C("fiona")), f"const must change, got {hall}"
    assert "fiona" not in str(hall) or "_halluc" in str(hall), hall

    try:
        apply_fault(P("cat", C("fiona")), "implicit_drop")
        raise AssertionError("implicit_drop is a list-level fault")
    except ValueError:
        pass

    assert bin_of("implicit_drop") == "L1"
    assert bin_of("drop_negation") == "L2"
    assert bin_of("hallucinate_const") == "L2"
    assert bin_of("scope_invert") == "L2"
    assert bin_of("arity_drift") == "L3"


def check_faulty_parser_seeded() -> None:
    from faults import FaultyParser
    from parser import GoldParser
    from fixtures import by_id

    p1 = by_id("p1")
    a = FaultyParser(GoldParser(), 1.0, random.Random(0),
                     kinds=("hallucinate_const",))
    b = FaultyParser(GoldParser(), 1.0, random.Random(0),
                     kinds=("hallucinate_const",))
    ta = a.translate(p1["premises_nl"], p1["conclusion_nl"])
    tb = b.translate(p1["premises_nl"], p1["conclusion_nl"])
    assert ta["premises"] == tb["premises"], (
        "same seed, same corruption — otherwise the sweep is not "
        "replicable and you have not made the parse step a function")

    clean = FaultyParser(GoldParser(), 0.0, random.Random(1))
    tc = clean.translate(p1["premises_nl"], p1["conclusion_nl"])
    assert tc["premises"] == p1["premises_fol"], (
        "rate 0 must be the gold theory")


def check_prover_labels() -> None:
    from fixtures import problems
    from prover import prove, used_premise_indices

    for p in problems():
        proof = prove(p["premises_fol"], p["conclusion_fol"], p["domain"])
        assert proof["label"] == p["label"], (
            f"{p['id']}: expected {p['label']}, got {proof['label']}. "
            "If p1 is Uncertain you are not firing modus ponens on "
            "the grounded implications. If p2 is Uncertain you derived "
            "neither flies nor ¬flies — 'No penguin flies' must put "
            "¬flies(tweety) in Δ. If p3 is True you invented a flies "
            "rule the premises do not have.")
        assert "steps" in proof and "axioms" in proof
        if p["id"] == "p1":
            used = used_premise_indices(proof)
            assert 0 in used and 1 in used and 2 in used, (
                f"p1's only derivation uses all three premises, "
                f"got {used}")
        if p["id"] == "p3":
            assert used_premise_indices(proof) == [] or proof["label"] == "Uncertain"


def check_pipeline_gold() -> None:
    from fixtures import problems
    from parser import GoldParser
    from pipeline import run

    gp = GoldParser()
    for p in problems():
        out = run(gp, p["premises_nl"], p["conclusion_nl"])
        assert out["label"] == p["label"], (p["id"], out["label"])
        assert "theory" in out


def check_sweep_monotone() -> None:
    from sweep import accuracy, is_monotone, sweep
    from parser import GoldParser
    from fixtures import problems

    gold_acc = accuracy(GoldParser(), problems())
    assert gold_acc == 1.0, (
        f"gold parser must score 3/3, got {gold_acc}")

    rows = sweep([0.0, 0.5, 1.0], seed=7)
    assert [r["rate"] for r in rows] == [0.0, 0.5, 1.0]
    assert rows[0]["accuracy"] == 1.0
    assert is_monotone(rows), (
        f"accuracy must not rise as you inject more faults: {rows}. "
        "If it does, the injector is missing the critical path, or "
        "the prover is ignoring premises.")
    assert rows[-1]["accuracy"] < 1.0, (
        "rate 1.0 still 3/3 — the faults are not changing labels. "
        "scope_invert on 'all cats are mammals' is enough to break p1.")


def check_trace_how() -> None:
    from fixtures import by_id
    from prover import prove
    from trace import faithful, how_of, lineage_of

    p1 = by_id("p1")
    proof = prove(p1["premises_fol"], p1["conclusion_fol"], p1["domain"])
    poly = how_of(proof)
    lin = lineage_of(proof)
    assert lin == frozenset({"p0", "p1", "p2"}), (
        f"p1 lineage must be {{p0,p1,p2}}, got {lin}. "
        "Do provenance-semirings first; specialize() through Lineage.")
    assert faithful(proof, [0, 1, 2]) is True
    assert faithful(proof, [0, 1]) is False, (
        "a proof that used p2 is not faithful to {{p0,p1}} — right "
        "answer, missing reason, the Privilege Illusion's cousin.")

    # A zero-axiom uncertain proof is faithful to [].
    p3 = by_id("p3")
    u = prove(p3["premises_fol"], p3["conclusion_fol"], p3["domain"])
    assert lineage_of(u) == frozenset()
    assert faithful(u, []) is True


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("fol.py", "ground ∀ over the domain; nnf pushes ¬",
     check_ground_and_nnf),
    ("parser.py", "GoldParser looks up fixtures; unknown is ok=False",
     check_gold_parser),
    ("faults.py", "four operational faults; L1/L2/L3 bins",
     check_faults),
    ("faults.py", "FaultyParser is a seeded function of the gold",
     check_faulty_parser_seeded),
    ("prover.py", "p1 True, p2 False, p3 Uncertain; p1 uses 0,1,2",
     check_prover_labels),
    ("pipeline.py", "gold parse, then prove, 3/3",
     check_pipeline_gold),
    ("sweep.py", "accuracy(0)=1; non-increasing in the error rate",
     check_sweep_monotone),
    ("trace.py", "how-polynomial of the proof; lineage via specialize",
     check_trace_how),
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

    print(f"\n{BOLD}LINC From Scratch — progress check{RESET}")
    print(f"{GREY}the LLM only parses; the proof is the artifact{RESET}\n")

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
        print(f"\n  {GREEN}{BOLD}All checks pass — same parse, same "
              f"proof; the rest is a homomorphism.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

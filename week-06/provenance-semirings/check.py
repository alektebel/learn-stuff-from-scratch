"""
Progress checker for provenance semirings.

    python3 check.py           # stop at the first gap
    python3 check.py 6         # only the payoff
    python3 check.py --all     # everything

Nothing here imports solutions/. It tests YOUR code.
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


def _laws(K, elements) -> None:
    z, o = K.zero(), K.one()
    elems = list(elements) + [z, o]
    for a in elems:
        assert K.eq(K.add(a, z), a), f"{K.name}: {a} ⊕ 0 ≠ {a}"
        assert K.eq(K.add(z, a), a), f"{K.name}: 0 ⊕ {a} ≠ {a}"
        assert K.eq(K.mul(a, o), a), f"{K.name}: {a} ⊗ 1 ≠ {a}"
        assert K.eq(K.mul(o, a), a), f"{K.name}: 1 ⊗ {a} ≠ {a}"
        assert K.eq(K.mul(a, z), z), f"{K.name}: {a} ⊗ 0 ≠ 0"
        assert K.eq(K.mul(z, a), z), f"{K.name}: 0 ⊗ {a} ≠ 0"
    for a in elems:
        for b in elems:
            assert K.eq(K.add(a, b), K.add(b, a)), f"{K.name}: ⊕ not comm"
            assert K.eq(K.mul(a, b), K.mul(b, a)), f"{K.name}: ⊗ not comm"
            assert K.eq(K.mul(a, K.add(b, z)), K.add(K.mul(a, b), K.mul(a, z))), (
                f"{K.name}: no right-distrib against 0")


def check_eight_and_laws() -> None:
    from semiring import (Bag, Boolean, How, Lineage, Security, Tropical,
                          Trust, Why, all_semirings)
    rings = all_semirings()
    names = [K.name for K in rings]
    assert names == ["how", "why", "lineage", "boolean", "bag",
                     "trust", "security", "tropical"], names
    how, why, lin, boolean, bag, trust, sec, trop = rings

    _laws(boolean, [True, False])
    _laws(bag, [0, 1, 2, 5])
    _laws(trust, [0.0, 1.0, 0.3, 0.8])
    _laws(trop, [0, 1, trop.INF, 7])
    _laws(sec, [0, 1, sec.INF, 4])
    _laws(lin, [lin.singleton("a"), lin.singleton("b"),
                lin.add(lin.singleton("a"), lin.singleton("c"))])
    _laws(why, [why.singleton("a"), why.singleton("b"),
                why.add(why.singleton("a"), why.singleton("c"))])

    # Why ⊗ is pairwise union, not ∪. { {a} } ⊗ { {b} } = { {a,b} }.
    assert why.eq(why.mul(why.singleton("a"), why.singleton("b")),
                  {frozenset({"a", "b"})}), (
        "Why ⊗ must be pairwise union of witnesses. If you used ∪ you "
        "implemented lineage under the wrong name: "
        f"{why.mul(why.singleton('a'), why.singleton('b'))!r}")

    # Lineage 0 = 1 = ∅ — the degeneracy.
    assert lin.eq(lin.zero(), lin.one()), (
        "Lineage 0 and 1 are both the empty set. If they differ you "
        "gave 1 a token it should not have.")

    # How is wired to polynomial.py — just check the class exists here.
    assert isinstance(how, How)
    assert how.name == "how"


def check_polynomial() -> None:
    from polynomial import add, coeff_sum, equal, mul, one, variable, zero
    from polynomial import variables_of

    x, y, z = variable("x"), variable("y"), variable("z")
    assert equal(add(x, zero()), x)
    assert equal(mul(x, one()), x)
    two_x = add(x, x)
    assert coeff_sum(two_x) == 2, (
        f"x ⊕ x is 2x, bag-hom is 2, got {coeff_sum(two_x)}. "
        "If you got 1 you treated ⊕ as set-union of monomials.")
    xy = mul(x, y)
    assert coeff_sum(xy) == 1
    assert variables_of(xy) == frozenset({"x", "y"})
    x2 = mul(x, x)
    assert coeff_sum(x2) == 1, (
        f"x ⊗ x is x², one derivation that used x twice, bag-hom is 1, "
        f"got {coeff_sum(x2)}")
    # (x+y)(x+z) = x² + xz + xy + yz
    prod = mul(add(x, y), add(x, z))
    assert coeff_sum(prod) == 4, (
        f"(x+y)(x+z) has four monomials, got bag {coeff_sum(prod)}")
    assert variables_of(prod) == frozenset({"x", "y", "z"})
    # 2x + y  vs  x + y — not equal
    assert not equal(add(two_x, y), add(x, y))


def check_specialize_hand() -> None:
    """Specialize ac+bd by hand, no query yet."""
    from homomorphism import specialize
    from polynomial import add, mul, variable
    from semiring import Bag, Boolean, Lineage, Security, Tropical, Trust, Why

    poly = add(mul(variable("a"), variable("c")),
               mul(variable("b"), variable("d")))

    assert specialize(poly, Boolean(), {}) is True
    assert specialize(poly, Bag(), {}) == 2, (
        "ac + bd at every xᵢ=1 is 2. If you got 1 you collapsed the "
        "two derivations — that is an annotation scheme.")
    assert specialize(poly, Lineage(), {}) == frozenset({"a", "b", "c", "d"})

    why = specialize(poly, Why(), {})
    assert why == {frozenset({"a", "c"}), frozenset({"b", "d"})}, (
        f"why(ac+bd) is {{ {{a,c}}, {{b,d}} }}, got {why}. "
        "If you got {{a,b,c,d}} you used ∪ for ⊗.")

    from instance import COST, SECURITY, TRUST
    trust = specialize(poly, Trust(), TRUST)
    assert abs(trust - 0.72) < 1e-9, (
        f"max(0.9*0.8, 0.5*0.4) = 0.72, got {trust}. "
        "If you got 0.8 you used min for ⊗; if 0.36 you used × for ⊕.")
    cost = specialize(poly, Tropical(), COST)
    assert cost == 7, (
        f"min(3+4, 1+10) = 7, got {cost}. If you got 18 you used + for ⊕.")
    sec = specialize(poly, Security(), SECURITY)
    assert sec == 3, (
        f"min(max(2,3), max(5,1)) = min(3,5) = 3, got {sec}")


def check_ra_join_project() -> None:
    from instance import LIKES, RESULT_KEY, SERVES
    from ra import join, project, query_who_eats_where
    from relation import from_annotated, lookup
    from semiring import How

    K = How()
    likes = from_annotated(LIKES, K)
    serves = from_annotated(SERVES, K)
    joined = join(likes, serves, ["food"], K)
    # Four rows in, two survive (pie with a⊗c, tea with b⊗d).
    assert len(joined) == 2, (
        f"join on food should keep 2 rows (pie, tea), got {len(joined)}")

    projected = project(joined, ["person", "cafe"], K)
    assert len(projected) == 1, (
        f"both join rows project to (Ada, Bar); ⊕ should compact to 1, "
        f"got {len(projected)}. If you still have 2 you did not ⊕ on collision.")

    got = query_who_eats_where(likes, serves, K)
    ann = lookup(got, RESULT_KEY, K)
    from polynomial import add, equal, mul, variable
    expected = add(mul(variable("a"), variable("c")),
                   mul(variable("b"), variable("d")))
    assert equal(ann, expected), (
        f"Q_How(Ada,Bar) must be ac+bd, got {ann}")


def check_payoff_homomorphism() -> None:
    """THE payoff. Evaluate once in How, specialize; also evaluate
    directly in each K; they must agree. If they do not, the RA
    operators are not the semiring operations.
    """
    from homomorphism import specialize
    from instance import COST, LIKES, RESULT_KEY, SECURITY, SERVES, TRUST
    from ra import query_who_eats_where
    from relation import from_annotated, from_annotated_valued, lookup
    from semiring import (Bag, Boolean, How, Lineage, Security, Tropical,
                          Trust, Why)

    how = How()
    q_how = query_who_eats_where(from_annotated(LIKES, how),
                                 from_annotated(SERVES, how), how)
    poly = lookup(q_how, RESULT_KEY, how)

    def direct(K, valuation=None):
        if valuation is None:
            likes = from_annotated(LIKES, K)
            serves = from_annotated(SERVES, K)
        else:
            likes = from_annotated_valued(LIKES, K, valuation)
            serves = from_annotated_valued(SERVES, K, valuation)
        return lookup(query_who_eats_where(likes, serves, K), RESULT_KEY, K)

    pairs = [
        (Boolean(), {}, "boolean"),
        (Bag(), {}, "bag"),
        (Why(), {}, "why"),
        (Lineage(), {}, "lineage"),
        (Trust(), TRUST, "trust"),
        (Tropical(), COST, "tropical"),
        (Security(), SECURITY, "security"),
    ]
    for K, val, name in pairs:
        via_hom = specialize(poly, K, val)
        via_q = direct(K, val if val else None)
        assert K.eq(via_hom, via_q), (
            f"HOMOMORPHISM FAILED for {name}: "
            f"h(Q_How)={via_hom!r} but Q_K={via_q!r}. "
            "You evaluated the query twice and they disagreed — that "
            "means Q is not a semiring polynomial. Typical cause: ⊕ "
            "or ⊗ hard-coded (union, min, a list append) instead of "
            "K.add / K.mul. That is an annotation scheme.")


def check_scheme_is_not_enough() -> None:
    """Lineage cannot answer bag or cost. If your How collapsed to a
    set, specialize-to-bag would be 1 and this fails.
    """
    from homomorphism import specialize
    from instance import COST, LIKES, RESULT_KEY, SERVES
    from polynomial import coeff_sum, variables_of
    from ra import query_who_eats_where
    from relation import from_annotated, lookup
    from semiring import How, Lineage, Tropical

    how = How()
    poly = lookup(query_who_eats_where(from_annotated(LIKES, how),
                                       from_annotated(SERVES, how), how),
                  RESULT_KEY, how)
    lin = specialize(poly, Lineage(), {})
    bag = coeff_sum(poly)
    assert lin == frozenset({"a", "b", "c", "d"})
    assert bag == 2
    assert len(lin) != bag, "sanity: 4 sources, 2 derivations"
    assert variables_of(poly) == lin
    cost = specialize(poly, Tropical(), COST)
    assert cost == 7
    # A scheme that stored only the set {a,b,c,d} cannot produce 2 or 7
    # without re-running the query. That is the sentence in the README.


def check_datalog_acyclic() -> None:
    from datalog import reachable
    from relation import add_row, empty, from_annotated
    from semiring import Bag, Boolean, How
    from instance import EDGES

    # Build edge relation in How: rows {src,dst} with variable names.
    how = How()
    edges_how = empty()
    for (src, dst), name in EDGES:
        if src in (4, 5):
            continue  # acyclic fragment only
        edges_how = add_row(edges_how, {"src": src, "dst": dst},
                            how.variable(name), how)

    # 1→3 two ways: e13 + e12⊗e23
    ann = reachable(edges_how, 1, 3, how, max_iter=8)
    from polynomial import add, equal, mul, variable
    expected = add(variable("e13"), mul(variable("e12"), variable("e23")))
    assert equal(ann, expected), (
        f"path(1,3) in How is e13 + e12 e23, got {ann}")

    edges_bool = empty()
    B = Boolean()
    for (src, dst), _ in EDGES:
        if src in (4, 5):
            continue
        edges_bool = add_row(edges_bool, {"src": src, "dst": dst}, True, B)
    assert reachable(edges_bool, 1, 3, B) is True
    assert reachable(edges_bool, 3, 1, B) is False

    edges_bag = empty()
    N = Bag()
    for (src, dst), _ in EDGES:
        if src in (4, 5):
            continue
        edges_bag = add_row(edges_bag, {"src": src, "dst": dst}, 1, N)
    assert reachable(edges_bag, 1, 3, N) == 2, (
        "bag path(1,3) is 2 (direct + via 2). If you got 1 the fixpoint "
        "⊕ is not +.")


def check_absorption_and_cycle() -> None:
    from datalog import (NonAbsorptiveRecursion, is_absorptive, reachable)
    from relation import add_row, empty
    from semiring import Bag, Boolean, How, Tropical, Why

    assert is_absorptive(Boolean(), [True, False]) is True
    assert is_absorptive(Tropical(), [0, 1, 4, Tropical.INF]) is True
    assert is_absorptive(Why(), [Why().singleton("a"),
                                 Why().singleton("b")]) is True
    assert is_absorptive(Bag(), [0, 1, 2]) is False, (
        "ℕ is not absorptive: 1 + (1×2) = 3 ≠ 1")
    assert is_absorptive(How(), [How().variable("x"),
                                How().variable("y")]) is False, (
        "ℕ[X] is not absorptive: x ⊕ (x ⊗ y) = x + xy ≠ x")

    how = How()
    cycle = empty()
    cycle = add_row(cycle, {"src": 4, "dst": 5}, how.variable("e45"), how)
    cycle = add_row(cycle, {"src": 5, "dst": 4}, how.variable("e54"), how)
    try:
        reachable(cycle, 4, 4, how, max_iter=6)
        raise AssertionError(
            "How on a 2-cycle must raise NonAbsorptiveRecursion. "
            "If you returned a polynomial you truncated it — that is "
            "the approximation the README tells you not to hide.")
    except NonAbsorptiveRecursion:
        pass

    trop = Tropical()
    cycle_t = empty()
    cycle_t = add_row(cycle_t, {"src": 4, "dst": 5}, 1, trop)
    cycle_t = add_row(cycle_t, {"src": 5, "dst": 4}, 1, trop)
    # 4→4 via the cycle costs 2 (4→5→4), and absorption stops there.
    cost = reachable(cycle_t, 4, 4, trop, max_iter=8)
    assert cost == 2, (
        f"cheapest 4→4 is 1+1=2, got {cost}. If INF, the seed was only "
        "edges and you never applied a round to close the cycle; if 0, "
        "you seeded path with the identity relation.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("semiring.py", "eight instances, and they are semirings",
     check_eight_and_laws),
    ("polynomial.py", "ℕ[X]: 2x, x², (x+y)(x+z)", check_polynomial),
    ("homomorphism.py", "specialize ac+bd by hand to each K",
     check_specialize_hand),
    ("ra.py", "join ⋈ project compact to ac+bd", check_ra_join_project),
    ("ra.py + hom", "h(Q_How) = Q_K  — the payoff",
     check_payoff_homomorphism),
    ("homomorphism.py", "lineage is 4, bag is 2, cost is 7",
     check_scheme_is_not_enough),
    ("datalog.py", "path(1,3) = e13 + e12 e23, bag 2",
     check_datalog_acyclic),
    ("datalog.py", "absorptive K terminate; How on a cycle refuses",
     check_absorption_and_cycle),
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

    print(f"\n{BOLD}Provenance Semirings — progress check{RESET}")
    print(f"{GREY}evaluate once in ℕ[X]; everything else is a homomorphism{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<22} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<22} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<22} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built the free "
              f"semiring, not an annotation scheme.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

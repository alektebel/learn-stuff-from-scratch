"""
Progress checker for the PRML-graphical-models templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic where the answer must not be read off the
learner's code: hand-built DAGs for d-separation, its own full-joint enumeration and
random-tree generator for the accept checks, its own ancestral sampler for the
conditional-independence check, and its own triangle model for the limit case.
"""

import itertools
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# The checker's own arithmetic
# ---------------------------------------------------------------------------

def _num_values(node):
    while isinstance(node, list) and node and isinstance(node[0], list):
        node = node[0]
    return len(node)


def _domains(parents, cpts):
    return {v: _num_values(cpts[v]) for v in parents}


def _joint(assignment, parents, cpts):
    p = 1.0
    for v in parents:
        node = cpts[v]
        for pv in parents[v]:
            node = node[assignment[pv]]
        p *= node[assignment[v]]
        if p == 0.0:
            return 0.0
    return p


def _brute_best(parents, cpts):
    variables = list(parents)
    domains = _domains(parents, cpts)
    best = -1.0
    for combo in itertools.product(*[range(domains[v]) for v in variables]):
        best = max(best, _joint(dict(zip(variables, combo)), parents, cpts))
    return best


def _rand_dist(rng):
    u = rng.random()
    return [u, 1.0 - u]


def _random_tree(rng, k):
    """A random binary DAG whose moral graph is a tree (each node one parent)."""
    parents = {0: []}
    cpts = {0: _rand_dist(rng)}
    for i in range(1, k):
        parents[i] = [rng.randrange(i)]
        cpts[i] = [_rand_dist(rng) for _ in range(2)]
    return parents, cpts


def _max_gap(a, b, variables):
    return max(abs(a[v][i] - b[v][i]) for v in variables for i in range(len(b[v])))


# ---------------------------------------------------------------------------
# Step 1: d-separation on hand cases
# ---------------------------------------------------------------------------

def check_d_separation() -> None:
    from graphical import d_separated

    chain = {"A": [], "B": ["A"], "C": ["B"]}
    assert d_separated(chain, "A", "C", []) is False, \
        "A and C are dependent through B when B is not observed"
    assert d_separated(chain, "A", "C", ["B"]) is True, \
        "conditioning on the middle of a chain must block it"

    common = {"B": [], "A": ["B"], "C": ["B"]}
    assert d_separated(common, "A", "C", []) is False, \
        "a common cause makes its children dependent"
    assert d_separated(common, "A", "C", ["B"]) is True, \
        "conditioning on a common cause must block the path"

    collider = {"A": [], "B": [], "C": ["A", "B"]}
    assert d_separated(collider, "A", "B", []) is True, \
        "an unobserved collider blocks the path (this is NOT a chain)"
    assert d_separated(collider, "A", "B", ["C"]) is False, \
        "conditioning on a collider OPENS the path: treating it as a chain is the bug"

    descendant = {"A": [], "B": [], "C": ["A", "B"], "D": ["C"]}
    assert d_separated(descendant, "A", "B", []) is True, \
        "a collider with nothing observed still blocks"
    assert d_separated(descendant, "A", "B", ["D"]) is False, \
        "observing a descendant of a collider must also open the path"

    net = {"A": [], "B": ["A"], "C": ["B"], "D": [], "E": ["C", "D"]}
    assert d_separated(net, "A", "D", []) is True, \
        "the path A-B-C-E<-D is blocked by the unobserved collider E"
    assert d_separated(net, "A", "D", ["E"]) is False, \
        "observing the collider E activates that path"
    assert d_separated(net, "A", "D", ["C"]) is True, \
        "observing C blocks the chain before the collider is reached"


# ---------------------------------------------------------------------------
# Step 2: the accept criterion -- sum-product equals brute force on trees
# ---------------------------------------------------------------------------

def check_sum_product_trees() -> None:
    from graphical import sum_product, enumerate_marginals

    # A hand V-structure: one factor has two parents (a 3-way scope).
    parents = {"A": [], "B": [], "C": ["A", "B"]}
    cpts = {"A": [0.3, 0.7], "B": [0.6, 0.4],
            "C": [[[0.9, 0.1], [0.2, 0.8]], [[0.4, 0.6], [0.05, 0.95]]]}
    bp = sum_product(parents, cpts)
    ref = enumerate_marginals(parents, cpts)
    gap = _max_gap(bp, ref, parents)
    assert gap < 1e-9, \
        f"sum-product disagrees with brute force on a V-structure: {gap:.2e}"

    rng = random.Random(8081)
    worst = 0.0
    for _ in range(8):
        tree, tree_cpts = _random_tree(rng, 5)
        bp = sum_product(tree, tree_cpts)
        ref = enumerate_marginals(tree, tree_cpts)
        worst = max(worst, _max_gap(bp, ref, tree))
    assert worst < 1e-9, (
        "sum-product marginals must equal the brute-force marginals on random trees, "
        f"worst gap {worst:.2e} — the belief is the product of the incoming messages "
        "divided by its own total (the partition function)")


# ---------------------------------------------------------------------------
# Step 3: max-sum equals brute-force argmax
# ---------------------------------------------------------------------------

def check_max_sum() -> None:
    from graphical import max_sum

    # A deterministic chain with a unique most-probable assignment.
    parents = {"A": [], "B": ["A"], "C": ["B"]}
    cpts = {"A": [0.9, 0.1], "B": [[0.99, 0.01], [0.02, 0.98]],
            "C": [[0.97, 0.03], [0.01, 0.99]]}
    got = max_sum(parents, cpts)
    assert set(got) == set(parents), "max-sum must assign every variable"
    best = _brute_best(parents, cpts)
    value = _joint(got, parents, cpts)
    assert abs(value - best) < 1e-12, (
        f"max-sum returned {got} with P={value:.6g}, but the most probable "
        f"assignment has P={best:.6g} — max-sum maximises, it does not sum")

    rng = random.Random(9317)
    for _ in range(8):
        tree, tree_cpts = _random_tree(rng, 5)
        got = max_sum(tree, tree_cpts)
        assert set(got) == set(tree), "max-sum must assign every variable"
        best = _brute_best(tree, tree_cpts)
        value = _joint(got, tree, tree_cpts)
        assert value > best * (1.0 - 1e-9), (
            f"max-sum returned P={value:.6g} but the maximum is {best:.6g}: "
            "the Viterbi decode must take the max, not a sum or a product without "
            "reconstructing the argmax")


# ---------------------------------------------------------------------------
# Step 4: the accept criterion -- d-separation agrees with sampled independence
# ---------------------------------------------------------------------------

def check_dsep_vs_samples() -> None:
    from graphical import d_separated, sample_independence

    rng = random.Random(4747)
    n = 40000

    chain = {"A": [], "B": ["A"], "C": ["B"]}
    chain_c = {"A": [0.5, 0.5], "B": [[0.95, 0.05], [0.05, 0.95]],
               "C": [[0.95, 0.05], [0.05, 0.95]]}
    collider = {"A": [], "B": [], "C": ["A", "B"]}
    collider_c = {"A": [0.5, 0.5], "B": [0.5, 0.5],
                  "C": [[[0.97, 0.03], [0.03, 0.97]], [[0.03, 0.97], [0.97, 0.03]]]}
    common = {"B": [], "A": ["B"], "C": ["B"]}
    common_c = {"B": [0.5, 0.5], "A": [[0.9, 0.1], [0.1, 0.9]],
                "C": [[0.9, 0.1], [0.1, 0.9]]}

    cases = [
        (chain, chain_c, "A", "C", [], False),
        (chain, chain_c, "A", "C", ["B"], True),
        (collider, collider_c, "A", "B", [], True),
        (collider, collider_c, "A", "B", ["C"], False),
        (common, common_c, "A", "C", [], False),
        (common, common_c, "A", "C", ["B"], True),
    ]
    for parents, cpts, a, b, given, separated in cases:
        verdict = d_separated(parents, a, b, given)
        assert verdict is separated, (
            f"d_separated({a},{b}|{given}) said {verdict} but the model is "
            f"{'independent' if separated else 'dependent'} by construction")
        gap = sample_independence(parents, cpts, n, rng, a, b, given)
        if separated:
            assert gap < 0.03, (
                f"{a} and {b} are d-separated given {given}, but the samples show a "
                f"dependence gap of {gap:.4f} (the checker draws its own samples)")
        else:
            assert gap > 0.10, (
                f"{a} and {b} are dependent given {given}, but the samples show only "
                f"a gap of {gap:.4f}")


# ---------------------------------------------------------------------------
# Step 5: the limit case -- loopy BP on a cyclic graph is neither exact nor stable
# ---------------------------------------------------------------------------

def check_loopy_limit() -> None:
    from graphical import loopy_bp, enumerate_marginals

    # On an acyclic factor graph loopy BP reaches the exact marginals.
    tree = {"A": [], "B": ["A"], "C": ["B"]}
    tree_cpts = {"A": [0.6, 0.4], "B": [[0.9, 0.1], [0.2, 0.8]],
                 "C": [[0.7, 0.3], [0.1, 0.9]]}
    ref = enumerate_marginals(tree, tree_cpts)
    marg, converged = loopy_bp(tree, tree_cpts, iters=200)
    assert converged is True, "loopy BP must converge on a tree"
    gap = _max_gap(marg, ref, tree)
    assert gap < 1e-9, (
        f"loopy BP on a tree must be exact, got gap {gap:.2e} — a variable's message "
        "to a factor must exclude the message that factor sent to it")

    # The triangle A->B, A->C, B->C has a cycle in its factor graph. With strong
    # symmetric coupling the messages alternate between two states forever.
    triangle = {"A": [], "B": ["A"], "C": ["A", "B"]}
    p = 0.9
    tri_cpts = {"A": [0.5, 0.5], "B": [[p, 1 - p], [1 - p, p]],
                "C": [[[p, 1 - p], [1 - p, p]], [[1 - p, p], [p, 1 - p]]]}
    ref = enumerate_marginals(triangle, tri_cpts)
    marg, converged = loopy_bp(triangle, tri_cpts, iters=200)
    assert converged is False, (
        "loopy BP on the strong-coupling triangle must report that it did not "
        "converge: the message sequence oscillates and never settles")
    gap = _max_gap(marg, ref, triangle)
    assert gap > 1e-3, (
        f"loopy BP is not exact on a graph with a cycle, but the marginal gap is "
        f"only {gap:.2e} — the limit case must exercise a genuinely cyclic model")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("graphical.py", "d-separation: chains, common causes, colliders and descendants",
     check_d_separation),
    ("graphical.py", "sum-product marginals equal brute force on trees (accept)",
     check_sum_product_trees),
    ("graphical.py", "max-sum decoding matches the brute-force argmax",
     check_max_sum),
    ("graphical.py", "d-separation agrees with sampled conditional independence (accept)",
     check_dsep_vs_samples),
    ("graphical.py", "limit: loopy BP on a triangle is inexact and does not converge",
     check_loopy_limit),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}PRML Graphical Models From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
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
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the PRML graphical models from scratch.{RESET}")
        print(f"  {GREY}Run solutions/graphical.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

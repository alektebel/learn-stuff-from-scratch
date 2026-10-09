"""
Progress checker for the PRML mixture-modelling templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic where the answer must not be read off the
learner's code: it generates the synthetic mixtures, asserts on the returned
log-likelihood sequence (requiring several entries, so an overwritten sequence cannot
pass) that it never decreases, and compares the fitted parameters with the generating
ones up to label permutation.
"""

import math
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


def _sample_1d(rng, specs, per):
    """`per` draws from each (mean, sd) in specs, concatenated."""
    xs = []
    for mu, sd in specs:
        for _ in range(per):
            xs.append(rng.gauss(mu, sd))
    return xs


# ---------------------------------------------------------------------------
# Step 1: K-means recovers well-separated centroids
# ---------------------------------------------------------------------------

def check_kmeans() -> None:
    from mixtures import kmeans

    xs = [-10.2, -9.8, -10.0, 0.1, -0.1, 0.0, 9.9, 10.2, 10.0]
    centroids, assignments = kmeans(xs, 3, random.Random(11), maxit=100)

    assert len(centroids) == 3, f"kmeans must return 3 centroids, got {len(centroids)}"
    ordered = sorted(centroids)
    for got, want in zip(ordered, [-10.0, 0.0, 10.0]):
        assert abs(got - want) < 0.5, (
            f"the three well-separated clusters sit at -10, 0, 10; recovered {ordered} — "
            "the assignment step must use the nearest centroid and the update step the "
            "mean of the members"
        )

    counts = [0, 0, 0]
    for a in assignments:
        counts[a] += 1
    assert sorted(counts) == [3, 3, 3], (
        f"each cluster has exactly 3 points here, got sizes {sorted(counts)} — "
        "a point left with the wrong centroid means the nearest-centroid rule is wrong"
    )


# ---------------------------------------------------------------------------
# Step 2: the ACCEPT criterion -- the log-likelihood never decreases across EM
# ---------------------------------------------------------------------------

def check_loglikelihood_non_decreasing() -> None:
    from mixtures import gmm_em

    rng = random.Random(12345)
    xs = _sample_1d(rng, [(-6.0, 0.6), (0.0, 0.6), (6.0, 0.6)], 40)
    _, _, _, logliks = gmm_em(xs, 3, rng, maxit=200, var_floor=1e-3)

    assert len(logliks) >= 3, (
        f"gmm_em owns the whole likelihood sequence, one entry per iteration; got "
        f"{len(logliks)} entries — the sequence must be accumulated, not overwritten "
        "with only the last value"
    )
    for i in range(len(logliks) - 1):
        assert logliks[i + 1] >= logliks[i] - 1e-9, (
            f"EM cannot decrease the log-likelihood: it fell from {logliks[i]:.6f} to "
            f"{logliks[i + 1]:.6f} at iteration {i} — the E-step responsibilities and "
            "the M-step update must be consistent"
        )
    assert logliks[-1] > logliks[0] + 1.0, (
        "EM must improve the likelihood substantially from its initialisation on this "
        f"well-separated data: {logliks[0]:.3f} -> {logliks[-1]:.3f}"
    )


# ---------------------------------------------------------------------------
# Step 3: the ACCEPT criterion -- parameters recovered up to label permutation
# ---------------------------------------------------------------------------

def check_parameter_recovery() -> None:
    from mixtures import gmm_em

    rng = random.Random(2024)
    xs = _sample_1d(rng, [(-6.0, 0.6), (0.0, 0.6), (6.0, 0.6)], 40)
    weights, mus, vars, _ = gmm_em(xs, 3, random.Random(2024), maxit=300, var_floor=1e-3)

    order = sorted(range(3), key=lambda j: mus[j])
    fitted_means = [mus[j] for j in order]
    fitted_weights = [weights[j] for j in order]

    for got, want in zip(fitted_means, [-6.0, 0.0, 6.0]):
        assert abs(got - want) < 0.5, (
            f"EM must recover the true means -6, 0, 6 up to permutation, matched to "
            f"{fitted_means} — components are matched by sorting the means, so a "
            "missorted or badly updated mean shows up here"
        )
    for got in fitted_weights:
        assert abs(got - 1.0 / 3.0) < 0.1, (
            f"the three components are equally frequent, so each weight must be about "
            f"1/3, got {fitted_weights} — the M-step must normalise N_j by N"
        )
    for v in vars:
        assert v > 0.0, f"every variance must stay strictly positive, got {vars}"


# ---------------------------------------------------------------------------
# Step 4: a mixture of Bernoullis
# ---------------------------------------------------------------------------

def check_bernoulli_mixture() -> None:
    from mixtures import bernoulli_mixture_em

    rng = random.Random(555)
    comp_a = [0.9, 0.1, 0.9]
    comp_b = [0.1, 0.9, 0.1]
    xs = []
    for _ in range(250):
        theta = comp_a if rng.random() < 0.5 else comp_b
        xs.append([1 if rng.random() < p else 0 for p in theta])

    _, thetas, logliks = bernoulli_mixture_em(xs, 2, rng, maxit=200)

    order = sorted(range(2), key=lambda j: thetas[j][0])
    fitted = [thetas[j] for j in order]
    want = [[0.1, 0.9, 0.1], [0.9, 0.1, 0.9]]
    for got, target in zip(fitted, want):
        for a, b in zip(got, target):
            assert abs(a - b) < 0.1, (
                f"the Bernoulli mixture must recover the component probabilities "
                f"{want} up to permutation, got {fitted} — the M-step is the "
                "responsibility-weighted bit mean"
            )
    assert logliks[-1] > logliks[0], (
        "the Bernoulli EM log-likelihood must improve from its random initialisation: "
        f"{logliks[0]:.3f} -> {logliks[-1]:.3f}"
    )


# ---------------------------------------------------------------------------
# Step 5: the limit cases -- variance collapse and local optima
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    from mixtures import gaussian_logpdf, gmm_em, gmm_em_best

    # (a) collapse. As the variance shrinks the log-density at the mean grows
    # without bound: the unconstrained likelihood is improper.
    shrinking = [gaussian_logpdf(0.0, 0.0, v) for v in (1e-2, 1e-4, 1e-6, 1e-8)]
    for i in range(len(shrinking) - 1):
        assert shrinking[i + 1] > shrinking[i], (
            f"the log-density at the mean must grow as the variance shrinks, got "
            f"{[round(v, 3) for v in shrinking]} — a component on a single point can "
            "run the likelihood to +inf"
        )
    assert shrinking[-1] - shrinking[0] > 5.0, (
        "the collapse must be visible over this range of variances, got "
        f"{shrinking[-1] - shrinking[0]:.3f}"
    )

    xs = [0.0] * 5 + [100.0]
    floor = 0.5
    _, _, floored_vars, floored_lls = gmm_em(
        xs, 2, random.Random(3), maxit=100, var_floor=floor
    )
    assert all(v >= floor * (1.0 - 1e-9) for v in floored_vars), (
        f"with var_floor={floor} every fitted variance must be at least the floor, got "
        f"{floored_vars} — the variance floor must be applied in the M-step"
    )
    assert math.isfinite(floored_lls[-1]) and max(floored_lls) < 1e6, (
        f"the floored fit must have a bounded log-likelihood, got {max(floored_lls)}"
    )

    _, _, loose_vars, _ = gmm_em(xs, 2, random.Random(3), maxit=100, var_floor=0.0)
    assert min(loose_vars) < 1e-6, (
        f"without a floor the component that owns the lone point collapses to variance "
        f"{min(loose_vars)} — that is the degeneracy the floor exists to prevent"
    )

    # (b) local optima. Starting all three means at 0 is symmetric and stationary: EM
    # cannot break the tie, so it stays at the single-Gaussian fit. Restarts do better.
    rng = random.Random(321)
    data = _sample_1d(rng, [(-10.0, 0.5), (0.0, 0.5), (10.0, 0.5)], 30)
    bad = gmm_em(
        data, 3, random.Random(1), maxit=200, var_floor=1e-3, init=[0.0, 0.0, 0.0]
    )
    bad_ll = bad[3][-1]

    ref_rng = random.Random(99)
    reference = [
        gmm_em(data, 3, ref_rng, maxit=200, var_floor=1e-3)[3][-1] for _ in range(8)
    ]
    best = gmm_em_best(data, 3, random.Random(99), restarts=8, maxit=200, var_floor=1e-3)
    best_ll = best[3][-1]

    assert best_ll > bad_ll + 1.0, (
        f"a symmetric poor initialisation is stuck at log-likelihood {bad_ll:.3f}; "
        f"restarts must find a clearly better one, got {best_ll:.3f}"
    )
    assert abs(best_ll - max(reference)) < 1e-9, (
        f"gmm_em_best must return the best of the restarts ({max(reference):.6f}), got "
        f"{best_ll:.6f} — keeping the first result instead of the best hides the whole "
        "local-optimum story"
    )


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("mixtures.py", "K-means recovers well-separated 1-D centroids",
     check_kmeans),
    ("mixtures.py", "the EM log-likelihood never decreases (accept)",
     check_loglikelihood_non_decreasing),
    ("mixtures.py", "EM recovers the mixture parameters up to permutation (accept)",
     check_parameter_recovery),
    ("mixtures.py", "the Bernoulli-mixture EM recovers the component probabilities",
     check_bernoulli_mixture),
    ("mixtures.py", "limit cases: variance collapse, the floor, and restarts",
     check_limit_cases),
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
    print(f"\n{BOLD}PRML Mixtures and EM From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<13} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<13} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<13} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built mixtures and EM from scratch.{RESET}")
        print(f"  {GREY}Run solutions/mixtures.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

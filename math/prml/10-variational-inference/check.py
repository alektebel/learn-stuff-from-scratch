"""
Progress checker for the PRML variational-inference templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic where the answer must not be read off the
learner's code: it generates the synthetic data, recomputes the exact Normal--Gamma log
evidence, asserts on the returned ELBO sequence (requiring several entries, so an
overwritten sequence cannot pass) that it never decreases, and compares the mean-field
variances with the true marginals of a correlated Gaussian.
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


def _log_evidence(xs, mu0, lambda0, a0, b0):
    """Exact log marginal likelihood of the Normal--Gamma model, computed here.

    With p(mu, tau) = N(mu | mu0, 1/(lambda0 tau)) Gamma(tau | a0, b0), integrating
    mu and then tau gives

        log p(D) = -N/2 log(2 pi) + 1/2 log(lambda0/(lambda0+N))
                   + a0 log b0 - lgamma(a0) + lgamma(aN) - aN log bN,

    aN = a0 + N/2 and bN = b0 + (S + (lambda0 N/(lambda0+N))(xbar - mu0)^2)/2.
    This is the exact number the mean-field ELBO must sit below.
    """
    n = len(xs)
    xbar = sum(xs) / n
    scatter = sum((x - xbar) ** 2 for x in xs)
    lambda_n = lambda0 + n
    a_n = a0 + n / 2.0
    b_n = b0 + 0.5 * (scatter + (lambda0 * n / lambda_n) * (xbar - mu0) ** 2)
    return (
        -0.5 * n * math.log(2.0 * math.pi)
        + 0.5 * math.log(lambda0 / lambda_n)
        + a0 * math.log(b0)
        - math.lgamma(a0)
        + math.lgamma(a_n)
        - a_n * math.log(b_n)
    )


# ---------------------------------------------------------------------------
# Step 1: mean-field VI recovers the posterior mean and precision
# ---------------------------------------------------------------------------

def check_mean_field_recovery() -> None:
    from variational import mean_field_gaussian

    rng = random.Random(2027)
    true_mu, true_var = 1.0, 4.0
    xs = [rng.gauss(true_mu, math.sqrt(true_var)) for _ in range(500)]

    params, elbos, bound = mean_field_gaussian(xs)

    assert abs(params["mu"] - true_mu) < 0.35, (
        f"q(mu) must centre near the sample mean; the true mean is {true_mu}, the fit "
        f"put it at {params['mu']:.3f} — the q(mu) update uses the prior pseudo-counts "
        "lambda0*mu0 + N*xbar over lambda0 + N"
    )
    assert abs(params["tau"] - 1.0 / true_var) < 0.25 * (1.0 / true_var), (
        f"E[tau] = a/b must land near the true precision {1.0 / true_var:.3f}, got "
        f"{params['tau']:.3f} — a and b are the Gamma shape and rate of q(tau)"
    )
    assert params["variance"] > 0.0 and params["lambda"] > 0.0, (
        "both q(mu)'s variance and precision must stay positive"
    )
    assert abs(bound - elbos[-1]) < 1e-9, (
        "the returned ELBO bound must be the final value of the recorded sequence"
    )


# ---------------------------------------------------------------------------
# Step 2: the ACCEPT criterion -- the ELBO never decreases under coordinate ascent
# ---------------------------------------------------------------------------

def check_elbo_non_decreasing() -> None:
    from variational import mean_field_gaussian

    rng = random.Random(4321)
    xs = [rng.gauss(-3.0, 1.5) for _ in range(120)]
    _, elbos, _ = mean_field_gaussian(xs, maxit=200)

    assert len(elbos) >= 3, (
        f"the ELBO sequence needs one entry per sweep; got {len(elbos)} — it must be "
        "accumulated, not overwritten with only the last value"
    )
    for i in range(len(elbos) - 1):
        assert elbos[i + 1] >= elbos[i] - 1e-9, (
            f"coordinate ascent cannot decrease the ELBO, but it fell from "
            f"{elbos[i]:.6f} to {elbos[i + 1]:.6f} at sweep {i} — the q(mu) and q(tau) "
            "updates must both be the exact maximisers of the same bound"
        )
    assert elbos[-1] > elbos[0], (
        f"the fit must improve the ELBO from its initialisation, got {elbos[0]:.3f} -> "
        f"{elbos[-1]:.3f}"
    )


# ---------------------------------------------------------------------------
# Step 3: the ACCEPT criterion -- the ELBO is a lower bound on the log evidence
# ---------------------------------------------------------------------------

def check_elbo_lower_bound() -> None:
    from variational import mean_field_gaussian

    rng = random.Random(99)
    xs = [rng.gauss(0.5, 2.0) for _ in range(60)]
    params, elbos, bound = mean_field_gaussian(xs)
    evidence = _log_evidence(xs, 0.0, 1.0, 1.0, 1.0)

    assert bound <= evidence + 1e-9, (
        f"the ELBO is a lower bound on the log evidence; the exact Normal--Gamma "
        f"evidence is {evidence:.6f} but the fit reported {bound:.6f} — a bound above "
        "the evidence means a missing or wrong term (the entropies, say)"
    )
    for i, e in enumerate(elbos):
        assert e <= evidence + 1e-9, (
            f"every ELBO value must sit below the evidence {evidence:.6f}; entry {i} is "
            f"{e:.6f}"
        )
    assert evidence - bound > 1e-6, (
        "the mean-field bound must be strictly below the evidence here, if only by the "
        f"KL gap; got evidence {evidence:.6f} and bound {bound:.6f}"
    )


# ---------------------------------------------------------------------------
# Step 4: the variational Gaussian mixture
# ---------------------------------------------------------------------------

def check_variational_gmm() -> None:
    from variational import variational_gmm

    rng = random.Random(21)
    xs = []
    for mu in (-6.0, 0.0, 6.0):
        xs.extend(rng.gauss(mu, 0.6) for _ in range(40))

    elbos, resp = variational_gmm(xs, 3, rng=random.Random(21))

    assert len(elbos) >= 3, (
        f"the variational GMM ELBO sequence needs several entries, got {len(elbos)}"
    )
    for i in range(len(elbos) - 1):
        assert elbos[i + 1] >= elbos[i] - 1e-6, (
            f"the variational GMM is coordinate ascent on its ELBO, so it cannot "
            f"decrease: fell from {elbos[i]:.6f} to {elbos[i + 1]:.6f} at sweep {i}"
        )
    assert len(resp) == len(xs) and all(len(row) == 3 for row in resp), (
        "responsibilities must be one row of three weights per observation"
    )
    for row in resp:
        assert abs(sum(row) - 1.0) < 1e-9, (
            f"each responsibility row is a distribution over components, got sum "
            f"{sum(row)}"
        )

    masses = [sum(row[j] for row in resp) for j in range(3)]
    means = [
        sum(resp[i][j] * xs[i] for i in range(len(xs))) / masses[j] for j in range(3)
    ]
    order = sorted(range(3), key=lambda j: means[j])
    fitted = [means[j] for j in order]
    for got, want in zip(fitted, [-6.0, 0.0, 6.0]):
        assert abs(got - want) < 0.6, (
            f"the variational GMM must recover the well-separated means -6, 0, 6 up to "
            f"permutation, matched to {[round(v, 2) for v in fitted]} — the component "
            "means come from the Normal--Gamma factor q(mu_j, tau_j)"
        )
    for m in masses:
        assert m > 10.0, (
            f"each well-separated component owns about 40 points, got masses {masses}"
        )


# ---------------------------------------------------------------------------
# Step 5: the limit case -- mean-field underestimates marginal variance
# ---------------------------------------------------------------------------

def check_correlated_limit() -> None:
    from variational import correlated_gaussian_vb

    # For a target with unit marginals and correlation rho, the factorised
    # (reverse-KL) fit has marginal variance 1 - rho^2 < 1: it seeks the mode and
    # understates the spread.
    for rho in (0.5, 0.9, 0.99):
        fitted = correlated_gaussian_vb(rho)
        true_var = 1.0
        expected = 1.0 - rho * rho
        assert len(fitted) == 2, f"a 2-D target needs two fitted variances, got {fitted}"
        for v in fitted:
            assert v < true_var - 1e-9, (
                f"mean-field on a Gaussian with correlation {rho} must UNDERSTATE the "
                f"marginal variance: the true marginal is {true_var}, got {v:.6f} — "
                "reverse KL is mode-seeking, not mass-covering"
            )
            assert abs(v - expected) < 1e-6, (
                f"the factorised optimum has precision diag(Sigma^-1) = 1/(1-rho^2), so "
                f"the marginal variance is exactly {expected:.6f}, got {v:.6f}"
            )

    low = correlated_gaussian_vb(0.3)[0]
    high = correlated_gaussian_vb(0.95)[0]
    assert high < low, (
        f"the stronger the correlation the more the variance is shrunk: 1-rho^2 is "
        f"{low:.4f} at rho=0.3 and {high:.4f} at rho=0.95"
    )


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("variational.py", "mean-field VI recovers the posterior mean and precision",
     check_mean_field_recovery),
    ("variational.py", "the ELBO never decreases under coordinate ascent (accept)",
     check_elbo_non_decreasing),
    ("variational.py", "the ELBO is a lower bound on the log evidence (accept)",
     check_elbo_lower_bound),
    ("variational.py", "the variational GMM ELBO rises and recovers the components",
     check_variational_gmm),
    ("variational.py", "limit case: mean-field understates correlated marginal variance",
     check_correlated_limit),
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
    print(f"\n{BOLD}PRML Variational Inference From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built variational inference from scratch.{RESET}")
        print(f"  {GREY}Run solutions/variational.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

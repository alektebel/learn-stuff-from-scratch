"""
Progress checker for the PRML-distributions templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic where the answer must not be read off the
learner's code: hand-computed conjugate posteriors (step 1), an independent
precision-weighted posterior (step 2), and its own unbiased-variance estimator driven
by its own Gaussian noise (step 3). The identity enforced in step 3 is
``E[MLE variance] = (N-1)/N * sigma^2`` against a *separately measured* unbiased
variance, never by reading one side off the other.
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


# ---------------------------------------------------------------------------
# Step 1: the conjugate updates
# ---------------------------------------------------------------------------

def check_conjugate_updates() -> None:
    from distributions import beta_bernoulli_update, beta_mean, dirichlet_multinomial_update

    a, b = beta_bernoulli_update(1, 1, 3, 1)
    assert (a, b) == (4, 2), \
        f"Beta(1,1) with 3 heads and 1 tail is Beta(4,2), got Beta({a},{b}) — " \
        "heads add to alpha and tails to beta, not the other way around"
    assert abs(beta_mean(a, b) - 2.0 / 3.0) < 1e-12, \
        f"the mean of Beta(4,2) must be 2/3, got {beta_mean(a, b)}"

    a, b = beta_bernoulli_update(2.0, 5.0, 0, 2)
    assert (a, b) == (2.0, 7.0), \
        f"tails must add to beta: Beta(2,5) + 0 heads / 2 tails is Beta(2,7), got ({a},{b})"

    post = dirichlet_multinomial_update([1, 1, 1], [2, 1, 1])
    assert list(post) == [3, 2, 2], \
        f"Dirichlet(1,1,1) + [2,1,1] is [3,2,2], got {list(post)} — " \
        "the prior concentrations are added, not replaced by the counts"

    post = dirichlet_multinomial_update([0.5, 2.0], [4, 0])
    assert list(post) == [4.5, 2.0], \
        f"Dirichlet(0.5,2) + [4,0] is [4.5,2], got {list(post)}"


# ---------------------------------------------------------------------------
# Step 2: sequential and batch Gaussian posteriors agree
# ---------------------------------------------------------------------------

def _batch_reference(mu0, sigma0, sigma, xs):
    """The checker's own precision-weighted posterior (mean, precision)."""
    tau0 = 1.0 / (sigma0 * sigma0)
    obs = 1.0 / (sigma * sigma)
    tau = tau0 + len(xs) * obs
    mu = (tau0 * mu0 + sum(xs) * obs) / tau
    return (mu, tau)


def check_gaussian_routes() -> None:
    from distributions import gaussian_sequential_update, gaussian_posterior

    mu0, sigma0, sigma = 0.0, 3.0, 1.5
    xs = [0.3, -1.2, 2.1, 0.7, -0.4, 1.9, 0.1]

    post = {"mu": mu0, "tau": 1.0 / (sigma0 * sigma0), "sigma": sigma}
    for x in xs:
        post = gaussian_sequential_update(post, x)

    mean_b, tau_b = gaussian_posterior(mu0, sigma0, sigma, xs)
    ref_mean, ref_tau = _batch_reference(mu0, sigma0, sigma, xs)

    assert abs(post["mu"] - mean_b) < 1e-12, \
        f"sequential and batch posterior means must agree: {post['mu']} vs {mean_b} — " \
        "the sequential update must weight the prior by its precision, not average from scratch"
    assert abs(post["tau"] - tau_b) < 1e-12, \
        f"sequential and batch posterior precisions must agree: {post['tau']} vs {tau_b}"
    assert abs(mean_b - ref_mean) < 1e-12, \
        f"batch posterior mean is not the precision-weighted average: {mean_b} vs {ref_mean}"
    assert abs(tau_b - ref_tau) < 1e-12, \
        f"batch posterior precision must be 1/sigma0^2 + N/sigma^2: {tau_b} vs {ref_tau}"

    # Order must not matter: shrink the observation variance so the prior matters.
    forward = {"mu": mu0, "tau": 1.0 / (sigma0 * sigma0), "sigma": 0.5}
    backward = {"mu": mu0, "tau": 1.0 / (sigma0 * sigma0), "sigma": 0.5}
    for x in xs:
        forward = gaussian_sequential_update(forward, x)
    for x in reversed(xs):
        backward = gaussian_sequential_update(backward, x)
    assert abs(forward["mu"] - backward["mu"]) < 1e-12, \
        "the conjugate update must be order-independent"


# ---------------------------------------------------------------------------
# Step 3: the accept criterion -- the MLE variance is biased by (N-1)/N
# ---------------------------------------------------------------------------

def check_mle_bias() -> None:
    from distributions import gaussian_mle

    rng = random.Random(20240)
    sigma = 2.0
    n, trials = 8, 40000
    mle_total = 0.0
    unbiased_total = 0.0
    for _ in range(trials):
        sample = [rng.gauss(0.0, sigma) for _ in range(n)]
        _, mle_var = gaussian_mle(sample)
        mean = sum(sample) / n
        unbiased = sum((x - mean) ** 2 for x in sample) / (n - 1)
        mle_total += mle_var
        unbiased_total += unbiased

    mle_mean = mle_total / trials
    unbiased_mean = unbiased_total / trials
    expected = (n - 1) / n * sigma * sigma

    assert abs(mle_mean - expected) < 0.02 * expected, (
        "the MLE variance (divide by N) must have expectation (N-1)/N * sigma^2 = "
        f"{expected:.4f}, measured {mle_mean:.4f} — dividing by N-1 would be unbiased")
    assert abs(unbiased_mean - sigma * sigma) < 0.02 * sigma * sigma, \
        f"the unbiased variance must have expectation sigma^2 = {sigma * sigma:.4f}, measured {unbiased_mean:.4f}"
    assert mle_mean < unbiased_mean, \
        "the MLE variance must be smaller than the unbiased one by the factor (N-1)/N"


# ---------------------------------------------------------------------------
# Step 4: the exponential family
# ---------------------------------------------------------------------------

def check_exponential_family() -> None:
    from distributions import (
        sufficient_stats, gaussian_from_sufficient_stats, natural_parameters,
        log_partition, log_partition_gradient, exponential_family_stats,
    )

    xs = [1.0, 0.0, 1.0, 1.0, 0.0]
    n, total = sufficient_stats(xs, "bernoulli")
    assert (n, total) == (5.0, 3.0), \
        f"Bernoulli sufficient statistics are (n, sum) = (5,3), got ({n},{total})"
    mu = total / n
    eta = natural_parameters((n, total), "bernoulli")
    assert abs(1.0 / (1.0 + math.exp(-eta)) - mu) < 1e-12, \
        "the natural parameter must be the logit of the sample mean"
    grad = log_partition_gradient(eta, "bernoulli")
    assert abs(grad - mu) < 1e-12, \
        f"the log-partition gradient must equal the mean: {grad} vs {mu}"
    assert abs(log_partition(eta, "bernoulli") - math.log(1.0 + math.exp(eta))) < 1e-12, \
        "A(eta) must be log(1 + e^eta) for the Bernoulli"

    gx = [0.5, -1.25, 2.0, 0.75, -0.5]
    stats = sufficient_stats(gx, "gaussian")
    assert list(stats) == [5.0, sum(gx), sum(x * x for x in gx)], \
        f"Gaussian sufficient statistics are (n, sum, sum_sq), got {stats}"
    g_mean, g_var = gaussian_from_sufficient_stats(stats)
    from distributions import gaussian_mle
    mle_mean, mle_var = gaussian_mle(gx)
    assert abs(g_mean - mle_mean) < 1e-12 and abs(g_var - mle_var) < 1e-12, \
        "the Gaussian sufficient statistics must reproduce the MLE mean and variance"
    eta_g = natural_parameters(stats, "gaussian", sigma=1.0)
    assert abs(log_partition_gradient(eta_g, "gaussian", sigma=1.0) - g_mean) < 1e-12, \
        "for the Gaussian, A'(eta) = sigma^2 eta must return the sample mean"

    bundle = exponential_family_stats(xs, "bernoulli")
    assert abs(bundle["mean"] - mu) < 1e-12, \
        "exponential_family_stats must report the mean as A'(eta)"


# ---------------------------------------------------------------------------
# Step 5: the limit cases -- regularisation and the KDE bandwidth
# ---------------------------------------------------------------------------

def check_limit_cases() -> None:
    from distributions import (
        beta_bernoulli_update, beta_mean, gaussian_mle, kde, histogram_density, knn_density,
    )

    # 3 heads in 3 tosses: the raw MLE says p = 1 with no uncertainty; a Beta(1,1)
    # prior pulls the posterior mean to 4/5. That is regularisation.
    mle = 3.0 / 3.0
    assert mle == 1.0, "the Bernoulli MLE of 3 heads in 3 tosses is exactly 1"
    a, b = beta_bernoulli_update(1, 1, 3, 0)
    assert (a, b) == (4, 1), f"Beta(1,1) + 3 heads / 0 tails is Beta(4,1), got Beta({a},{b})"
    assert abs(beta_mean(a, b) - 4.0 / 5.0) < 1e-12, \
        f"with a Beta(1,1) prior the posterior mean is 4/5, not 1, got {beta_mean(a, b)}"

    # A tiny sample: the MLE variance is zero (1/N) but the unbiased variance is not.
    tiny = [2.0, 2.0, 2.0]
    _, tiny_var = gaussian_mle(tiny)
    assert abs(tiny_var) < 1e-12, "three identical points give MLE variance 0"
    assert sum((x - 2.0) ** 2 for x in tiny) / 2.0 == 0.0, "the unbiased variance is also 0 here"

    # Density estimators: histogram and kNN, with hand values.
    hist = histogram_density([0.0, 0.0, 1.0, 1.0, 1.0], [0.0, 1.0, 2.0])
    assert abs(hist[0] - 0.4) < 1e-12 and abs(hist[1] - 0.6) < 1e-12, \
        f"histogram densities are count/(n*width), got {hist}"
    knn = knn_density([0.0, 1.0, 2.0, 3.0, 4.0], 2.5, 3)
    assert abs(knn - 3.0 / (5.0 * 3.0)) < 1e-12, \
        f"kNN density is k/(n*2r) with r the 3rd distance = 1.5, got {knn}"

    # The KDE kernel and the 1/(n h) normalisation are both required.
    one = kde([0.0], 0.0, 2.0)
    assert abs(one - (1.0 / math.sqrt(2.0 * math.pi)) / 2.0) < 1e-12, (
        "kde([0], 0, h=2) must be K(0)/h = 0.19947; a result of 0.39894 means the "
        "1/(n h) scale was dropped and 0.5 means the kernel was dropped")

    # A normalised density integrates to ~1.
    data = [float(i) for i in range(10)]
    lo, hi, steps = -6.0, 15.0, 20000
    step = (hi - lo) / steps
    integral = sum(kde(data, lo + (i + 0.5) * step, 0.6) * step for i in range(steps))
    assert abs(integral - 1.0) < 0.02, \
        f"a density integrates to one over a wide range, got {integral:.4f} — " \
        "the 1/(n h) normalisation is missing or the width scaling is wrong"

    # Two failure modes of the bandwidth: too small is spiky, too large is oversmooth.
    spiky = max(kde(data, v, 0.05) for v in data) / kde(data, 4.5, 0.05)
    smooth = max(kde(data, v, 4.0) for v in data) / kde(data, 4.5, 4.0)
    assert spiky > 50.0 * smooth, (
        "a too-small bandwidth piles all mass on the data (spiky), a too-large one "
        f"smears it evenly (oversmooth): peak/mid ratio {spiky:.1f} vs {smooth:.2f}")

    grid = [0.25 * i for i in range(37)]
    var_small = _variance([kde(data, g, 0.1) for g in grid])
    var_large = _variance([kde(data, g, 4.0) for g in grid])
    assert var_small > var_large, \
        f"the spiky estimate must have the larger variance: {var_small:.4f} vs {var_large:.4f}"


def _variance(values):
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("distributions.py", "Beta-Bernoulli and Dirichlet-multinomial conjugate updates",
     check_conjugate_updates),
    ("distributions.py", "sequential and batch Gaussian posteriors agree",
     check_gaussian_routes),
    ("distributions.py", "the MLE variance is biased by (N-1)/N (simulation)",
     check_mle_bias),
    ("distributions.py", "exponential family: sufficient statistics and A'(eta) = mean",
     check_exponential_family),
    ("distributions.py", "limit cases: 3/3 Bernoulli and the KDE bandwidth",
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
    print(f"\n{BOLD}PRML Distributions From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the PRML distributions from scratch.{RESET}")
        print(f"  {GREY}Run solutions/distributions.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the sampling-methods templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that
is simply the next thing to write. Nothing here imports solutions/. It tests YOUR
code.

Every reference value is recomputed here, independently of the learner's code:
the rejection target's moments from the Beta(2, 3) closed form, the Student-t
proposal's density from its own constant, the correlated Gaussian from its
precision matrix, and the Cauchy limit case from the known value of
``E[1/(1 + X^2)] = 1/2``. The node's acceptance criteria are step 2 (importance
sampling is unbiased across repeated runs) and step 3 (on a correlated Gaussian
HMC returns a higher effective sample size per gradient than a random-walk
Metropolis-Hastings run given the same evaluation budget). Step 1 pins rejection
sampling and its acceptance rate, step 4 pins Metropolis-Hastings and Gibbs on
the correlated Gaussian, and step 5 is the limit case: a proposal lighter-tailed
than the target gives importance weights of infinite variance.
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
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

PHI = 0.5 * math.log(2.0 * math.pi)


def _beta_pdf(x):
    """Density of Beta(2, 3) on (0, 1): ``12 x (1 - x)^2``."""
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return 12.0 * x * (1.0 - x) ** 2


def _uniform_pdf(x):
    """Density of Uniform(0, 1)."""
    return 1.0 if 0.0 <= x <= 1.0 else 0.0


def _phi_logpdf(x):
    """log density of the standard normal."""
    return -0.5 * x * x - PHI


def _t_logpdf(x, nu):
    """log density of a Student-t with ``nu`` degrees of freedom."""
    return (math.lgamma((nu + 1.0) / 2.0) - math.lgamma(nu / 2.0)
            - 0.5 * math.log(nu * math.pi)
            - (nu + 1.0) / 2.0 * math.log1p(x * x / nu))


def _t_sample(rng, nu):
    """One draw from a Student-t with ``nu`` degrees of freedom."""
    z = rng.gauss(0.0, 1.0)
    chi2 = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(int(nu)))
    return z / math.sqrt(chi2 / nu)


def _cauchy_logpdf(x):
    """log density of the standard Cauchy distribution."""
    return -math.log(math.pi) - math.log1p(x * x)


def _normal_logpdf(x, sigma):
    """log density of N(0, sigma^2)."""
    return -0.5 * (x / sigma) ** 2 - math.log(sigma) - PHI


def _heavy_logpdf(x, alpha=0.5):
    """log density of ``(alpha/2) (1 + |x|)^(-(1 + alpha))``."""
    return math.log(alpha / 2.0) - (1.0 + alpha) * math.log1p(abs(x))


def _heavy_sample(rng, alpha=0.5):
    """One draw from ``_heavy_logpdf`` by inverse transform."""
    u = rng.random()
    if u < 0.5:
        return -(2.0 * u) ** (-1.0 / alpha) + 1.0
    return (2.0 * (1.0 - u)) ** (-1.0 / alpha) - 1.0


def _correlated_targets(rho):
    """``(log_target, grad_log_target)`` for N(0, [[1, rho], [rho, 1]])."""
    det = 1.0 - rho * rho

    def log_target(theta):
        a, b = theta
        return -0.5 * (a * a - 2.0 * rho * a * b + b * b) / det

    def grad_log_target(theta):
        a, b = theta
        return [-(a - rho * b) / det, -(b - rho * a) / det]

    return log_target, grad_log_target


def _mean_var(xs):
    n = len(xs)
    mean = sum(xs) / n
    return mean, sum((x - mean) ** 2 for x in xs) / n


def _mean(xs):
    return sum(xs) / len(xs)


def _moments_2d(states):
    """``(mean_x, mean_y, var_x, var_y, cov)`` of a list of 2-vectors."""
    xs = [s[0] for s in states]
    ys = [s[1] for s in states]
    mx, my = _mean(xs), _mean(ys)
    vx = sum((x - mx) ** 2 for x in xs) / len(xs)
    vy = sum((y - my) ** 2 for y in ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
    return mx, my, vx, vy, cov


# ---------------------------------------------------------------------------
# Step 1: rejection sampling and its acceptance rate
# ---------------------------------------------------------------------------

def check_rejection_sampling() -> None:
    from sampling import rejection_sample

    M = 16.0 / 9.0  # max of Beta(2, 3) / Uniform(0, 1) on (0, 1)
    rng = random.Random(20260101)
    chain = rejection_sample(_beta_pdf, _uniform_pdf, lambda g: g.random(),
                             M, 60000, rng)
    assert len(chain) == 60000, (
        f"rejection_sample returned {len(chain)} samples, expected exactly the "
        "requested 60000: keep drawing candidates until n are ACCEPTED, do not "
        "stop after n proposals")

    mean, variance = _mean_var(chain)
    assert abs(mean - 0.4) < 0.01, (
        f"the sample mean is {mean:.4f}, expected 0.4 for Beta(2, 3). A mean "
        "near 0.5 is the mean of the Uniform(0, 1) proposal: the acceptance "
        "test ``u * M * proposal <= target`` is being skipped, so every "
        "candidate is kept")
    assert abs(variance - 0.04) < 0.004, (
        f"the sample variance is {variance:.4f}, expected 0.04 for Beta(2, 3). "
        "A variance near 1/12 = 0.083 is again the raw proposal: the rejection "
        "test must compare u * M * q(x) against p(x)")

    assert chain.proposals > len(chain), (
        "the run accepted every one of its proposals, so the rejection test "
        "never fired; count the candidates drawn and stop only when n are "
        "accepted")
    rate = len(chain) / chain.proposals
    assert abs(rate - 1.0 / M) < 0.02, (
        f"the empirical acceptance rate is {rate:.4f}, expected 1/M = "
        f"{1.0 / M:.4f}. The acceptance probability of rejection sampling with "
        "M = sup p/q is exactly 1/M; a rate near 1 means M is not applied in "
        "the inequality, a rate far below means M is applied twice")


# ---------------------------------------------------------------------------
# Step 2: the accept criterion -- importance sampling is unbiased
# ---------------------------------------------------------------------------

def check_importance_unbiased() -> None:
    from sampling import importance_sample

    reps = 400
    n = 400

    def average_estimate(f, seed):
        values = []
        for r in range(reps):
            rng = random.Random(seed + r)
            out = importance_sample(_phi_logpdf, lambda x: _t_logpdf(x, 5.0),
                                    lambda g: _t_sample(g, 5.0), f, n, rng)
            values.append(out["estimate"])
        mean = sum(values) / reps
        sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (reps - 1))
        se = sd / math.sqrt(reps)
        return mean, se

    mean, se = average_estimate(lambda x: x, 7100)
    assert abs(mean) < 0.01, (
        f"the average over {reps} importance estimates of E[X] is {mean:.4f}, "
        "expected 0. A biased plain estimate is the signature of NORMALISING "
        "the weights in the plain estimator: ``(1/n) sum w_i f(x_i)`` with "
        "w_i = p(x_i)/q(x_i) is the unbiased one when p is normalised")
    assert mean - 2.0 * se < 0.0 < mean + 2.0 * se, (
        f"the 2-sigma interval [{mean - 2 * se:.4f}, {mean + 2 * se:.4f}] does "
        "not cover 0: the spread of the estimates is not explained by sampling "
        "noise alone")

    mean, se = average_estimate(lambda x: x * x, 7200)
    assert abs(mean - 1.0) < 0.01, (
        f"the average importance estimate of E[X^2] is {mean:.4f}, expected 1 "
        "for a standard normal. The estimate must weight each draw by the exact "
        "density ratio; a missing factor or a missing ratio gives a value off "
        "by a constant")
    assert mean - 2.0 * se < 1.0 < mean + 2.0 * se, (
        f"the 2-sigma interval [{mean - 2 * se:.4f}, {mean + 2 * se:.4f}] does "
        "not cover 1")

    # Unnormalised target: only the self-normalised ratio is consistent. The
    # constant 2.5 makes the unnormalised density integrate to exp(2.5)*sqrt(2*pi),
    # so the PLAIN estimate is scaled by that constant while the ratio cancels it.
    rng = random.Random(7300)
    out = importance_sample(lambda x: -0.5 * x * x + 2.5,
                            lambda x: _t_logpdf(x, 5.0),
                            lambda g: _t_sample(g, 5.0), lambda x: x * x,
                            40000, rng)
    normaliser = math.exp(2.5) * math.sqrt(2.0 * math.pi)
    assert abs(out["self_normalised"] - 1.0) < 0.01, (
        f"with an unnormalised target the self-normalised estimate is "
        f"{out['self_normalised']:.4f}, expected 1. The self-normalised "
        "estimator must DIVIDE by the sum of the weights; forgetting the "
        "division leaves the estimate multiplied by the total weight, which "
        "grows with n")
    assert abs(out["estimate"] - normaliser) < 0.05 * normaliser, (
        f"the plain estimate is {out['estimate']:.3f}, expected about "
        f"{normaliser:.3f} = exp(2.5)*sqrt(2*pi): this confirms that the plain "
        "weighted mean carries the unknown normalising constant, which is "
        "exactly why the self-normalised ratio is needed for an unnormalised "
        "target")


# ---------------------------------------------------------------------------
# Step 3: the accept criterion -- HMC has the higher ESS per gradient
# ---------------------------------------------------------------------------

def check_hmc_ess_per_gradient() -> None:
    from sampling import (hmc, metropolis_hastings, effective_sample_size,
                          gradient_count, target_eval_count)

    rho = 0.95
    log_target, grad_log_target = _correlated_targets(rho)
    L = 12
    hmc_steps = 1200
    mh_steps = (L + 1) * hmc_steps

    rng = random.Random(20260301)
    hchain = hmc(log_target, grad_log_target, 0.30, L, [0.0, 0.0], hmc_steps, rng)
    assert len(hchain) == hmc_steps + 1, (
        f"hmc returned {len(hchain)} states, expected steps + 1 = "
        f"{hmc_steps + 1} (the initial state plus one per step)")
    assert gradient_count(hchain) == (L + 1) * hmc_steps, (
        f"hmc reports {gradient_count(hchain)} gradient evaluations, expected "
        f"(L + 1) * steps = {(L + 1) * hmc_steps}. The leapfrog integrator uses "
        "one gradient for each of the two half kicks and each of the L - 1 full "
        "kicks")

    mx, my, vx, vy, cov = _moments_2d(hchain[200:])
    assert abs(mx) < 0.05 and abs(my) < 0.05, (
        f"HMC gives means ({mx:.4f}, {my:.4f}), expected near 0. A drifting "
        "mean means the integrator does not preserve the target: leapfrog needs "
        "the half momentum kick at each end, an explicit Euler step does not")
    assert abs(vx - 1.0) < 0.10 and abs(vy - 1.0) < 0.10, (
        f"HMC gives variances ({vx:.4f}, {vy:.4f}), expected near 1. An "
        "inflated variance is the energy drift of a non-symplectic integrator: "
        "without the half kick the leapfrog trajectory spirals outward")
    assert abs(cov - rho) < 0.10, (
        f"HMC gives covariance {cov:.4f}, expected near rho = {rho}")

    def mh_propose(x, g):
        return [x[0] + 0.30 * g.gauss(0.0, 1.0),
                x[1] + 0.30 * g.gauss(0.0, 1.0)]

    rng = random.Random(20260302)
    mchain = metropolis_hastings(log_target, mh_propose, [0.0, 0.0], mh_steps, rng)
    assert len(mchain) == mh_steps + 1, (
        f"metropolis_hastings returned {len(mchain)} states, expected steps + 1")

    h_ess = effective_sample_size(hchain[200:])
    m_ess = effective_sample_size(mchain[200:])
    h_grad = gradient_count(hchain)
    m_eval = target_eval_count(mchain)
    assert h_grad > 0 and m_eval > 0, (
        "the cost counters are zero: hmc must record its gradients and "
        "metropolis_hastings its target evaluations")
    assert h_ess > 1.0 and m_ess > 1.0, (
        f"effective_sample_size returned ({h_ess:.1f}, {m_ess:.1f}); an ESS "
        "must be a positive number of independent draws, not the raw chain "
        "length and not zero")

    h_rate = h_ess / h_grad
    m_rate = m_ess / m_eval
    assert h_rate > 2.0 * m_rate, (
        f"HMC returns {h_ess:.0f} effective samples per {h_grad} gradients = "
        f"{h_rate:.5f}, but random-walk Metropolis-Hastings returns {m_ess:.0f} "
        f"per {m_eval} target evaluations = {m_rate:.5f}. HMC must be at least "
        "twice as efficient here. Two causes to check: the leapfrog integrator "
        "is wrong (missing half kick, so the energy and the acceptance are "
        "wrong), or effective_sample_size is not measuring autocorrelation "
        "(returning the chain length makes the slow sampler look perfect)")


# ---------------------------------------------------------------------------
# Step 4: Metropolis-Hastings and Gibbs recover the correlated Gaussian
# ---------------------------------------------------------------------------

def check_mh_gibbs_recover() -> None:
    from sampling import metropolis_hastings, gibbs_sample

    rho = 0.7
    steps = 200000
    spread = math.sqrt(1.0 - rho * rho)
    log_target, _ = _correlated_targets(rho)

    def mh_propose(x, g):
        return [x[0] + 0.6 * g.gauss(0.0, 1.0),
                x[1] + 0.6 * g.gauss(0.0, 1.0)]

    rng = random.Random(20260401)
    mchain = metropolis_hastings(log_target, mh_propose, [0.0, 0.0], steps, rng)
    assert len(mchain) == steps + 1, (
        f"metropolis_hastings returned {len(mchain)} states, expected steps + 1")
    mx, my, vx, vy, cov = _moments_2d(mchain[4000:])
    assert abs(mx) < 0.05 and abs(my) < 0.05, (
        f"random-walk MH means ({mx:.4f}, {my:.4f}), expected near 0")
    assert abs(vx - 1.0) < 0.10 and abs(vy - 1.0) < 0.10, (
        f"random-walk MH variances ({vx:.4f}, {vy:.4f}), expected near 1. The "
        "chain must accept proposals with probability min(1, target ratio); "
        "accepting every proposal turns it into an unconstrained random walk")
    assert abs(cov - rho) < 0.10, (
        f"random-walk MH covariance {cov:.4f}, expected near {rho}")

    def cond_0(x, g):
        return g.gauss(rho * x[1], spread)

    def cond_1(x, g):
        return g.gauss(rho * x[0], spread)

    rng = random.Random(20260402)
    gchain = gibbs_sample([cond_0, cond_1], [0.0, 0.0], steps, rng)
    assert len(gchain) == steps + 1, (
        f"gibbs_sample returned {len(gchain)} states, expected steps + 1")
    mx, my, vx, vy, cov = _moments_2d(gchain[4000:])
    assert abs(mx) < 0.05 and abs(my) < 0.05, (
        f"Gibbs means ({mx:.4f}, {my:.4f}), expected near 0. If one mean equals "
        "the initial coordinate, that coordinate was never redrawn")
    assert abs(vx - 1.0) < 0.10 and abs(vy - 1.0) < 0.10, (
        f"Gibbs variances ({vx:.4f}, {vy:.4f}), expected near 1. A variance "
        "near 0 means one coordinate stayed frozen at x0: a Gibbs sweep must "
        "redraw EVERY coordinate from its conditional")
    assert abs(cov - rho) < 0.10, (
        f"Gibbs covariance {cov:.4f}, expected near {rho}: the conditionals "
        "couple x to rho*y and y to rho*x")


# ---------------------------------------------------------------------------
# Step 5: the limit case -- a lighter-tailed proposal has infinite variance
# ---------------------------------------------------------------------------

def _limit_run(proposal_logpdf, propose, n, reps, seed):
    from sampling import importance_sample

    estimates, max_weights, esses = [], [], []
    for r in range(reps):
        rng = random.Random(seed + r)
        out = importance_sample(_cauchy_logpdf, proposal_logpdf, propose,
                                lambda x: 1.0 / (1.0 + x * x), n, rng)
        estimates.append(out["self_normalised"])
        max_weights.append(max(out["weights"]))
        esses.append(out["ess"])
    return estimates, max_weights, esses


def check_infinite_variance_limit() -> None:
    reps = 80
    n_small, n_large = 1000, 4000

    # A standard Cauchy target; E[1/(1 + X^2)] = 1/2 by the Cauchy integral.
    gauss = (lambda x: _normal_logpdf(x, 1.0), lambda g: g.gauss(0.0, 1.0))
    heavy = (_heavy_logpdf, _heavy_sample)

    l_small = _limit_run(gauss[0], gauss[1], n_small, reps, 31000)
    l_large = _limit_run(gauss[0], gauss[1], n_large, reps, 32000)
    h_small = _limit_run(heavy[0], heavy[1], n_small, reps, 33000)
    h_large = _limit_run(heavy[0], heavy[1], n_large, reps, 34000)

    l_maxw_small = _mean(l_small[1])
    l_maxw_large = _mean(l_large[1])
    h_maxw_small = _mean(h_small[1])
    h_maxw_large = _mean(h_large[1])

    assert l_maxw_large > 1.8 * l_maxw_small, (
        f"the mean largest Gaussian-proposal weight only went from "
        f"{l_maxw_small:.1f} at n={n_small} to {l_maxw_large:.1f} at "
        f"n={n_large}. For a Cauchy target ``w = p/q`` grows like "
        "exp(x^2/2)/x^2, so its tails are so heavy that the sample maximum must "
        "keep growing with n -- that growth IS the infinite variance")
    assert h_maxw_large < 1.5 * h_maxw_small, (
        f"the mean largest power-law-proposal weight grew from {h_maxw_small:.2f} "
        f"to {h_maxw_large:.2f}. A proposal at least as heavy-tailed as the "
        "target has bounded weights, so its maximum must not grow with n; if it "
        "does, the 'valid' proposal is actually lighter-tailed than the target")

    l_ess = _mean(l_large[2]) / n_large
    h_ess = _mean(h_large[2]) / n_large
    assert l_ess < 0.45, (
        f"the Gaussian proposal leaves an effective-sample fraction of "
        f"{l_ess:.3f} at n={n_large}, expected well below 0.45. When the weight "
        "variance is infinite a few draws dominate the estimate, so the "
        "effective sample size collapses")
    assert h_ess > 0.5, (
        f"the power-law proposal leaves an effective-sample fraction of "
        f"{h_ess:.3f}, expected above 0.5: a valid proposal has finite weight "
        "variance and keeps most of the sample informative")

    l_est = _mean(l_large[0])
    h_est = _mean(h_large[0])
    assert abs(l_est - 0.5) > 0.03, (
        f"the Gaussian-proposal self-normalised estimate averages {l_est:.4f} "
        "but does not converge to the true 0.5: the estimate is biased at every "
        "finite n, which is the practical face of the infinite weight variance")
    assert abs(h_est - 0.5) < 0.01, (
        f"the power-law-proposal estimate averages {h_est:.4f}, expected to "
        "converge to 0.5")

    l_single = max(l_small[1] + l_large[1])
    h_single = max(h_small[1] + h_large[1])
    assert l_single > 50.0 * h_single, (
        f"the largest single Gaussian-proposal weight was {l_single:.1f}, only "
        f"{l_single / max(h_single, 1e-12):.1f} times the power-law maximum "
        f"{h_single:.2f}. A bounded proposal caps every weight; the Gaussian "
        "one has no cap and must produce at least one enormous weight")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("sampling.py", "rejection sampling matches Beta(2,3) and rate 1/M (step 1)",
     check_rejection_sampling),
    ("sampling.py", "importance estimates are unbiased across runs (accept)",
     check_importance_unbiased),
    ("sampling.py", "HMC has higher ESS per gradient than random-walk MH (accept)",
     check_hmc_ess_per_gradient),
    ("sampling.py", "MH and Gibbs recover the correlated Gaussian", check_mh_gibbs_recover),
    ("sampling.py", "limit case: light proposal has infinite weight variance",
     check_infinite_variance_limit),
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
    print(f"\n{BOLD}Sampling Methods From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<11} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<11} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<11} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the samplers from scratch.{RESET}")
        print(f"  {GREY}Run solutions/sampling.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the PRML sequential-models templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): it
is simply the next thing to write. Nothing here imports solutions/. It tests
YOUR code.

The checker carries its own arithmetic where the answer must not be read off the
learner's code: it enumerates every state path for the exact marginals and the
MAP path, it samples its own synthetic HMM for Baum-Welch, it has its own
block-Gaussian posterior for the Kalman accept check, and its own unscaled
forward recursion for the underflow limit.
"""

import itertools
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
# The checker's own arithmetic
# ---------------------------------------------------------------------------

def _choice(rng, probs):
    u = rng.random()
    c = 0.0
    for i, p in enumerate(probs):
        c += p
        if u < c:
            return i
    return len(probs) - 1


def _path_prob(pi, A, B, obs, path):
    p = pi[path[0]] * B[path[0]][obs[0]]
    for t in range(1, len(obs)):
        p *= A[path[t - 1]][path[t]] * B[path[t]][obs[t]]
    return p


def _enumerate(pi, A, B, obs):
    """Sum over every state path: exact marginals and the MAP path."""
    n = len(pi)
    T = len(obs)
    gammas = [[0.0] * n for _ in range(T)]
    best = -1.0
    best_path = None
    total = 0.0
    for path in itertools.product(range(n), repeat=T):
        p = _path_prob(pi, A, B, obs, list(path))
        total += p
        for t, s in enumerate(path):
            gammas[t][s] += p
        if p > best:
            best = p
            best_path = list(path)
    ref = [[x / total for x in row] for row in gammas]
    return ref, best_path, best, total


def _rand_vec(rng, n):
    v = [rng.random() + 0.05 for _ in range(n)]
    s = sum(v)
    return [x / s for x in v]


def _rand_mat(rng, n):
    return [_rand_vec(rng, n) for _ in range(n)]


def _random_hmm(rng, n, m):
    return _rand_vec(rng, n), _rand_mat(rng, n), [_rand_vec(rng, m) for _ in range(n)]


def _rand_obs(rng, m, T):
    return [rng.randrange(m) for _ in range(T)]


def _T(A):
    return [list(row) for row in zip(*A)]


def _mm(A, B):
    k = len(B)
    p = len(B[0])
    return [[sum(A[i][l] * B[l][j] for l in range(k)) for j in range(p)]
            for i in range(len(A))]


def _mv(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _inv(A):
    n = len(A)
    M = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        d = M[col][col]
        for j in range(2 * n):
            M[col][j] /= d
        for r in range(n):
            if r != col and M[r][col]:
                f = M[r][col]
                for j in range(2 * n):
                    M[r][j] -= f * M[col][j]
    return [row[n:] for row in M]


def _batch_posterior(mu0, P0, F, H, Q, R, obs):
    """The checker's own exact joint linear-Gaussian posterior, information form.

    Assembles prior and observations into one precision matrix, inverts it, and
    reads off each state's marginal. Independent of the learner's implementation.
    """
    n = len(mu0)
    d = len(obs)
    D = n * d
    J = [[0.0] * D for _ in range(D)]
    h = [0.0] * D

    P0i = _inv(P0)
    for a in range(n):
        for b in range(n):
            J[a][b] += P0i[a][b]
        h[a] += sum(P0i[a][b] * mu0[b] for b in range(n))

    Qi = _inv(Q)
    Ft = _T(F)
    FQiF = _mm(_mm(Ft, Qi), F)
    FQi = _mm(Ft, Qi)
    QiF = _mm(Qi, F)
    for t in range(1, d):
        o0 = (t - 1) * n
        o1 = t * n
        for a in range(n):
            for b in range(n):
                J[o0 + a][o0 + b] += FQiF[a][b]
                J[o0 + a][o1 + b] += -FQi[a][b]
                J[o1 + a][o0 + b] += -QiF[a][b]
                J[o1 + a][o1 + b] += Qi[a][b]

    Ri = _inv(R)
    Ht = _T(H)
    HtRiH = _mm(_mm(Ht, Ri), H)
    for t in range(d):
        o = t * n
        for a in range(n):
            for b in range(n):
                J[o + a][o + b] += HtRiH[a][b]
        tmp = _mv(_mm(Ht, Ri), obs[t])
        for a in range(n):
            h[o + a] += tmp[a]

    Ji = _inv(J)
    mean = _mv(Ji, h)
    means = [mean[t * n:(t + 1) * n] for t in range(d)]
    covs = [[[Ji[o + a][o + b] for b in range(n)] for a in range(n)]
            for o in range(0, D, n)]
    return means, covs


# ---------------------------------------------------------------------------
# Step 1: forward-backward marginals equal brute-force path enumeration
# ---------------------------------------------------------------------------

def check_fb_vs_bruteforce() -> None:
    from sequential import forward_backward

    rng = random.Random(1301)
    worst = 0.0
    for _ in range(6):
        pi, A, B = _random_hmm(rng, 3, 3)
        obs = _rand_obs(rng, 3, 4)
        ref, _, _, _ = _enumerate(pi, A, B, obs)
        got = forward_backward(pi, A, B, obs)
        for t in range(len(obs)):
            for i in range(3):
                worst = max(worst, abs(got[t][i] - ref[t][i]))
    assert worst < 1e-9, (
        "forward-backward marginals must equal the brute-force enumeration over "
        f"state paths; worst gap {worst:.2e} — gamma is alpha*beta normalised, and "
        "the backward message must use A[i][j] (from i to j), not its transpose")


# ---------------------------------------------------------------------------
# Step 2: Viterbi finds the MAP path
# ---------------------------------------------------------------------------

def check_viterbi_map() -> None:
    from sequential import viterbi

    rng = random.Random(2202)
    for _ in range(8):
        pi, A, B = _random_hmm(rng, 3, 3)
        obs = _rand_obs(rng, 3, 5)
        _, best_path, best, _ = _enumerate(pi, A, B, obs)
        got = viterbi(pi, A, B, obs)
        assert len(got) == len(obs), "Viterbi must return one state per observation"
        assert all(0 <= s < 3 for s in got), "Viterbi returned an out-of-range state"
        value = _path_prob(pi, A, B, obs, got)
        assert value > best * (1.0 - 1e-9), (
            f"Viterbi returned {got} with probability {value:.6g}, but the MAP path "
            f"{best_path} has probability {best:.6g} — the decode must keep "
            "backpointers and reconstruct the argmax, not just take a running max")


# ---------------------------------------------------------------------------
# Step 3: Baum-Welch increases the likelihood monotonically
# ---------------------------------------------------------------------------

def check_baum_welch() -> None:
    from sequential import baum_welch, forward

    rng = random.Random(3303)
    n, m, T = 2, 2, 300
    pi, A, B = _random_hmm(rng, n, m)

    obs = []
    s = _choice(rng, pi)
    for _ in range(T):
        obs.append(_choice(rng, B[s]))
        s = _choice(rng, A[s])

    pi0 = _rand_vec(rng, n)
    A0 = _rand_mat(rng, n)
    B0 = [_rand_vec(rng, m) for _ in range(n)]

    p, A2, B2, logliks = baum_welch(pi0, A0, B0, obs, maxit=30)

    assert len(logliks) >= 2, "Baum-Welch must return its log-likelihood trajectory"
    for i in range(1, len(logliks)):
        assert logliks[i] >= logliks[i - 1] - 1e-6, (
            f"Baum-Welch log-likelihood decreased at iteration {i}: "
            f"{logliks[i - 1]:.6f} -> {logliks[i]:.6f}; the E-step marginals and the "
            "M-step expected counts must be consistent")
    assert logliks[-1] > logliks[0] + 1.0, (
        f"Baum-Welch barely moved the likelihood ({logliks[0]:.4f} -> "
        f"{logliks[-1]:.4f}); it must actually fit the synthetic data")

    for vec in (p, *A2, *B2):
        assert abs(sum(vec) - 1.0) < 1e-9, "estimated rows must be distributions"
    for row in B2:
        assert abs(sum(row) - 1.0) < 1e-9, "estimated emission rows must sum to one"

    # The trajectory it reports must match the likelihoods under its own forward.
    checked = sum(math.log(c) for c in forward(p, A2, B2, obs)[1])
    assert abs(checked - logliks[-1]) < 1e-6, (
        "the reported final log-likelihood does not match the likelihood of the "
        "returned parameters under the forward recursion")


# ---------------------------------------------------------------------------
# Step 4: ACCEPT -- Kalman/RTS equal the exact batch Gaussian posterior
# ---------------------------------------------------------------------------

def _max_mean_gap(a, b, n):
    return max(abs(a[i] - b[i]) for i in range(n))


def _max_cov_gap(A, B, n):
    return max(abs(A[i][j] - B[i][j]) for i in range(n) for j in range(n))


def check_kalman_batch() -> None:
    from sequential import kalman_filter, rts_smoother, batch_gaussian_posterior

    n, T = 2, 4
    mu0 = [0.0, 0.0]
    P0 = [[1.0, 0.2], [0.2, 0.8]]
    F = [[0.9, 0.1], [0.0, 0.8]]
    H = [[1.0, 0.0], [0.3, 0.7]]
    Q = [[0.2, 0.05], [0.05, 0.3]]
    R = [[0.4, 0.1], [0.1, 0.5]]
    obs = [[0.1, 0.2], [0.5, -0.3], [-0.2, 0.4], [0.3, 0.1]]

    # The checker's own exact batch posterior (independent of the learner's), in
    # information form, so the accept check does not read its reference off the
    # code under test.
    bm, bc = _batch_posterior(mu0, P0, F, H, Q, R, obs)

    # The learner's batch posterior must agree with the checker's. Without this a
    # wrapper around the filter would pretend to be the batch solution and pass.
    lm, lc = batch_gaussian_posterior(mu0, P0, F, H, Q, R, obs)
    assert len(lm) == T and len(lc) == T, "batch_gaussian_posterior must return T estimates"
    for t in range(T):
        g = _max_mean_gap(lm[t], bm[t], n)
        gc = _max_cov_gap(lc[t], bc[t], n)
        assert g < 1e-8 and gc < 1e-8, (
            "batch_gaussian_posterior must be the exact joint posterior the filter "
            f"and smoother reproduce: at step {t} it differs from the checker's own "
            f"batch solve by mean {g:.2e}, covariance {gc:.2e}")

    mus, Ps = kalman_filter(mu0, P0, F, H, Q, R, obs)
    assert len(mus) == T and len(Ps) == T, "the filter must return T estimates"
    gm = _max_mean_gap(mus[-1], bm[-1], n)
    gc = _max_cov_gap(Ps[-1], bc[-1], n)
    assert gm < 1e-9 and gc < 1e-9, (
        "the final filtered estimate must equal the exact batch posterior on the "
        f"last state; mean gap {gm:.2e}, covariance gap {gc:.2e} — the update needs "
        "the innovation covariance S = H P H^T + R, not just H P H^T")

    sm, sP = rts_smoother(mu0, P0, F, H, Q, R, obs)
    assert len(sm) == T and len(sP) == T, "the smoother must return T estimates"
    mid = T // 2
    gm = _max_mean_gap(sm[mid], bm[mid], n)
    gc = _max_cov_gap(sP[mid], bc[mid], n)
    assert gm < 1e-9 and gc < 1e-9, (
        "the smoothed estimate must equal the exact batch posterior on the middle "
        f"state; mean gap {gm:.2e}, covariance gap {gc:.2e} — the smoother gain is "
        "P F^T (F P F^T + Q)^-1, not the filter gain")


# ---------------------------------------------------------------------------
# Step 5: the limit case -- unscaled forward underflows, scaled does not
# ---------------------------------------------------------------------------

def check_underflow_limit() -> None:
    from sequential import forward, forward_backward

    n, T = 2, 1200
    pi = [0.5, 0.5]
    A = [[0.5, 0.5], [0.5, 0.5]]
    B = [[0.5, 0.5], [0.5, 0.5]]
    obs = [i % 2 for i in range(T)]

    # The checker's own unscaled recursion: a joint probability multiplied by a
    # factor below one at every step, so it must flush to zero.
    alpha = [pi[i] * B[i][obs[0]] for i in range(n)]
    for t in range(1, T):
        alpha = [sum(alpha[i] * A[i][j] for i in range(n)) * B[j][obs[t]]
                 for j in range(n)]
    worst = max(alpha)
    assert worst == 0.0 or not math.isfinite(worst) or worst < 1e-200, (
        f"the unscaled forward variable should have underflowed after {T} steps, "
        f"but its largest entry is {worst:.3e}; the limit case needs a long sequence")

    alphas, cs = forward(pi, A, B, obs)
    for t, step in enumerate(alphas):
        assert all(math.isfinite(x) for x in step), (
            f"the scaled forward produced a non-finite value at step {t}: scaling "
            "must keep alpha finite")
        s = sum(step)
        assert abs(s - 1.0) < 1e-9, (
            f"the scaled forward must be normalised at every step, but step {t} "
            f"sums to {s:.6g}")
    assert all(math.isfinite(c) and c > 0.0 for c in cs), (
        "the per-step scaling factors must stay finite and positive; their product "
        "is the sequence likelihood")

    gamma = forward_backward(pi, A, B, obs)
    for t, g in enumerate(gamma):
        assert all(math.isfinite(x) for x in g), (
            f"forward-backward produced a non-finite marginal at step {t}")
        assert abs(sum(g) - 1.0) < 1e-9, (
            f"the posterior marginal at step {t} must sum to one, got {sum(g):.6g}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("sequential.py", "forward-backward marginals equal brute-force enumeration",
     check_fb_vs_bruteforce),
    ("sequential.py", "Viterbi finds the MAP path (brute-force argmax)",
     check_viterbi_map),
    ("sequential.py", "Baum-Welch increases the log-likelihood monotonically",
     check_baum_welch),
    ("sequential.py", "Kalman/RTS equal the exact batch Gaussian posterior (accept)",
     check_kalman_batch),
    ("sequential.py", "limit: unscaled forward underflows, scaled stays finite",
     check_underflow_limit),
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
    print(f"\n{BOLD}PRML Sequential Models From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the PRML sequential models from scratch.{RESET}")
        print(f"  {GREY}Run solutions/sequential.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""
Progress checker for the PRML-neural-networks templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own central finite differences (`_fd_gradient`, `_fd_hessian`)
and its own flattened-parameter ordering, so a comparison is against an independent
difference scheme, not against a restatement of yours. The accept criterion -- near a
minimum the outer-product (Gauss-Newton) Hessian agrees with the exact Hessian -- and
the limit case -- far from the minimum it does not -- are measured on fixed synthetic
data built from a teacher network plus small noise.
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
# The checker's own flattened parameters, loss and finite differences
# ---------------------------------------------------------------------------

def _flat(weights):
    out = []
    for key in ("W1", "b1", "W2", "b2"):
        block = weights[key]
        if block and isinstance(block[0], list):
            for row in block:
                out.extend(row)
        else:
            out.extend(block)
    return out


def _nest(vec, D, H, K):
    i = 0
    W1 = [[vec[i + r * D + c] for c in range(D)] for r in range(H)]
    i += H * D
    b1 = [vec[i + r] for r in range(H)]
    i += H
    W2 = [[vec[i + r * H + c] for c in range(H)] for r in range(K)]
    i += K * H
    b2 = [vec[i + r] for r in range(K)]
    return {"W1": W1, "b1": b1, "W2": W2, "b2": b2}


def _loss(weights, xs, ts):
    """The checker's own loss, reading the learner's forward pass."""
    from neural import forward
    acts = forward(weights, xs)
    total = 0.0
    for y, t in zip(acts["y"], ts):
        tv = list(t) if isinstance(t, (list, tuple)) else [t]
        for k in range(len(y)):
            d = y[k] - tv[k]
            total += 0.5 * d * d
    return total


def _fd_gradient(weights, xs, ts, eps=1e-5):
    """Central finite differences of the loss, as a flat vector."""
    D, H, K = len(weights["W1"][0]), len(weights["b1"]), len(weights["b2"])
    vec = _flat(weights)
    grad = []
    for i in range(len(vec)):
        plus = list(vec)
        plus[i] += eps
        minus = list(vec)
        minus[i] -= eps
        grad.append((_loss(_nest(plus, D, H, K), xs, ts)
                     - _loss(_nest(minus, D, H, K), xs, ts)) / (2.0 * eps))
    return grad


def _fd_hessian(weights, xs, ts, eps=1e-3):
    """Second differences of the loss, the checker's own Hessian."""
    D, H, K = len(weights["W1"][0]), len(weights["b1"]), len(weights["b2"])
    vec = _flat(weights)
    P = len(vec)
    base = _loss(weights, xs, ts)
    hess = [[0.0] * P for _ in range(P)]

    def at(i, di, j, dj):
        v = list(vec)
        v[i] += di
        v[j] += dj
        return _loss(_nest(v, D, H, K), xs, ts)

    for i in range(P):
        hess[i][i] = (at(i, eps, i, 0.0) - 2.0 * base + at(i, -eps, i, 0.0)) / (eps * eps)
    for i in range(P):
        for j in range(i + 1, P):
            value = (at(i, eps, j, eps) - at(i, eps, j, -eps)
                     - at(i, -eps, j, eps) + at(i, -eps, j, -eps)) / (4.0 * eps * eps)
            hess[i][j] = hess[j][i] = value
    return hess


def _norm(w):
    return math.sqrt(sum(v * v for v in w))


def _rel_fro(A, B):
    """Relative Frobenius distance between two matrices."""
    num = 0.0
    den = 0.0
    for i in range(len(A)):
        for j in range(len(A)):
            d = A[i][j] - B[i][j]
            num += d * d
            den += B[i][j] * B[i][j]
    return math.sqrt(num / den) if den > 0.0 else math.sqrt(num)


def _max_abs(vec):
    return max((abs(v) for v in vec), default=0.0)


def _coerce_targets(ts):
    return [t if isinstance(t, (list, tuple)) else [t] for t in ts]


# ---------------------------------------------------------------------------
# Step 1: backprop matches central finite differences
# ---------------------------------------------------------------------------

def check_gradient() -> None:
    from neural import backprop, make_weights, numerical_gradient

    w = make_weights(2, 3, 1, random.Random(0))
    xs = [[-0.5, 0.9], [0.3, -0.7], [0.8, 0.2], [-0.9, -0.4], [0.1, -0.1]]
    ts = [math.sin(x[0]) + 0.5 * x[1] * x[1] for x in xs]

    analytic = _flat(backprop(w, xs, ts))
    reference = _fd_gradient(w, xs, ts, eps=1e-5)
    assert len(analytic) == len(reference), \
        f"the gradient must have one entry per parameter ({len(reference)}), got {len(analytic)}"

    scale = max(1.0, _max_abs(reference))
    err = max(abs(analytic[i] - reference[i]) for i in range(len(reference))) / scale
    assert err < 1e-6, (
        "the analytic backprop gradient must match central finite differences: the "
        f"largest relative error is {err:.3e}. Check the hidden-layer factor "
        "delta1 = (W2^T delta2) * (1 - tanh(z1)^2) and the output delta y - t.")

    numeric = numerical_gradient(w, xs, ts, 1e-5)
    assert len(numeric) == len(reference), \
        "numerical_gradient must return one entry per parameter"
    err_num = max(abs(numeric[i] - reference[i]) for i in range(len(reference))) / scale
    assert err_num < 1e-8, (
        "numerical_gradient must use a central difference (f(x+eps) - f(x-eps)) / (2 eps); "
        f"a one-sided difference is only O(eps) accurate, error {err_num:.3e}")


# ---------------------------------------------------------------------------
# Step 2: the exact Hessian is symmetric and equals a finite difference of the loss
# ---------------------------------------------------------------------------

def check_hessian_consistency() -> None:
    from neural import exact_hessian_fd, make_weights

    w = make_weights(1, 3, 1, random.Random(2))
    xs = [[-0.8 + 0.4 * i] for i in range(5)]
    ts = [math.cos(2.0 * x[0]) for x in xs]

    exact = exact_hessian_fd(w, xs, ts, eps=1e-4)
    P = len(exact)
    assert P == len(_flat(w)) and all(len(row) == P for row in exact), \
        "exact_hessian_fd must return a square P x P matrix"

    scale = max(1.0, max(abs(exact[i][j]) for i in range(P) for j in range(P)))
    asym = max(abs(exact[i][j] - exact[j][i]) for i in range(P) for j in range(P))
    assert asym < 1e-6 * scale, (
        "a Hessian must be symmetric; differencing the gradient introduced asymmetry "
        f"of {asym:.3e} (scale {scale:.3e})")

    reference = _fd_hessian(w, xs, ts, eps=1e-3)
    err = _rel_fro(exact, reference)
    assert err < 0.05, (
        "the exact Hessian by finite differences of the analytic gradient must agree "
        f"with second differences of the loss; relative error {err:.3e}")


# ---------------------------------------------------------------------------
# Step 3 (ACCEPT): near a minimum the outer-product Hessian matches the exact one
# ---------------------------------------------------------------------------

def _trained_minimum(seed=1):
    from neural import forward, make_weights, train

    rng = random.Random(seed)
    D, H, K = 2, 6, 1
    teacher = make_weights(D, H, K, random.Random(seed + 100))
    xs = [[-1.0 + 2.0 * i / 9.0, 0.3 * math.sin(1.7 * i)] for i in range(10)]
    ts = [forward(teacher, [x])["y"][0][0] + rng.gauss(0.0, 0.02) for x in xs]
    w0 = make_weights(D, H, K, random.Random(seed + 7))
    w_min, _ = train(w0, xs, ts, lr=0.05, maxit=3000, weight_decay=0.0)
    return w_min, xs, ts


def check_outer_product_near_minimum() -> None:
    from neural import exact_hessian_fd, loss, outer_product_hessian

    w_min, xs, ts = _trained_minimum(seed=1)
    rms = math.sqrt(2.0 * loss(w_min, xs, ts) / len(xs))
    assert rms < 0.05, (
        "this accept check needs a near-minimum with small residuals; training did not "
        f"converge (rms residual {rms:.4f})")

    exact = exact_hessian_fd(w_min, xs, ts, eps=1e-3)
    outer = outer_product_hessian(w_min, xs, ts)
    assert len(outer) == len(exact) and all(len(r) == len(exact) for r in outer), \
        "outer_product_hessian must return a square P x P matrix"
    err = _rel_fro(outer, exact)
    assert err < 0.05, (
        "near a minimum, where the residuals are small, the outer-product Hessian "
        "sum_n J_n^T J_n must approximate the exact Hessian; relative error "
        f"{err:.3e}. Check that each sample contributes the outer product of its "
        "residual Jacobian (the tanh' factor included).")


# ---------------------------------------------------------------------------
# Step 4: weight decay shrinks the weights; early stopping halts before convergence
# ---------------------------------------------------------------------------

def _noisy_regression(seed=4, n=14):
    rng = random.Random(seed)
    xs = [[-1.0 + 2.0 * i / (n - 1)] for i in range(n)]
    ts = [math.sin(3.0 * x[0]) + rng.gauss(0.0, 0.35) for x in xs]
    return xs, ts


def check_weight_decay_and_early_stopping() -> None:
    from neural import early_stopping_split, loss, make_weights, train

    xs, ts = _noisy_regression(seed=4)
    train_idx = list(range(0, 10))
    val_idx = list(range(10, 14))
    xtr = [xs[i] for i in train_idx]
    ttr = [ts[i] for i in train_idx]
    xva = [xs[i] for i in val_idx]
    tva = [ts[i] for i in val_idx]

    base = make_weights(1, 10, 1, random.Random(5))
    w_plain, _ = train(base, xtr, ttr, lr=0.1, maxit=4000, weight_decay=0.0)
    w_decay, _ = train(base, xtr, ttr, lr=0.1, maxit=4000, weight_decay=0.02)

    n_plain = _norm(_flat(w_plain))
    n_decay = _norm(_flat(w_decay))
    assert n_decay < n_plain, (
        "L2 weight decay must shrink the weights; it adds + weight_decay * w to the "
        f"gradient, not subtracts. ||w|| plain {n_plain:.4f}, decayed {n_decay:.4f}")

    v_plain = loss(w_plain, xva, tva)
    v_decay = loss(w_decay, xva, tva)
    assert v_decay < v_plain, (
        "weight decay must reduce overfitting: the held-out loss should fall. "
        f"validation loss plain {v_plain:.4f}, decayed {v_decay:.4f}")

    w_es, tr_hist, va_hist, best = early_stopping_split(
        base, xs, ts, val_frac=0.3, lr=0.1, maxit=6000, weight_decay=0.0, seed=2)
    assert 0 <= best < len(va_hist) <= 6000, \
        f"early_stopping_split returned an out-of-range best iteration {best}"
    assert len(va_hist) < 6000, (
        "early stopping must stop when the validation loss turns upward, not run to "
        f"maxit (ran {len(va_hist)} iterations)")
    assert min(va_hist) < va_hist[-1] - 1e-9, (
        "the validation loss must be higher at the stop than at its best, otherwise "
        "the run did not overfit and early stopping had nothing to do")
    assert tr_hist[-1] < tr_hist[best] - 1e-9, (
        "early stopping must halt while the training loss is still falling (the "
        f"training loss at stop {tr_hist[-1]:.6f} is not below its value at the best "
        f"iteration {tr_hist[best]:.6f})")


# ---------------------------------------------------------------------------
# Step 5 (LIMIT CASE): far from the minimum the outer-product approximation degrades
# ---------------------------------------------------------------------------

def check_outer_product_limit() -> None:
    from neural import exact_hessian_fd, outer_product_hessian, unflatten

    w_min, xs, ts = _trained_minimum(seed=1)
    err_near = _rel_fro(outer_product_hessian(w_min, xs, ts),
                        exact_hessian_fd(w_min, xs, ts, eps=1e-3))

    D, H, K = 2, 6, 1
    w_far = unflatten([v + 3.0 for v in _flat(w_min)], D, H, K)
    err_far = _rel_fro(outer_product_hessian(w_far, xs, ts),
                       exact_hessian_fd(w_far, xs, ts, eps=1e-3))

    assert err_near < 0.05, (
        f"the near-minimum error should be small to contrast with the limit, got {err_near:.3e}")
    assert err_far > 10.0 * err_near, (
        "far from the minimum the residuals are large, so the outer-product "
        "approximation must be much worse than near it: near error "
        f"{err_near:.3e}, far error {err_far:.3e}. The dropped term is "
        "sum_n sum_k r_{n,k} d^2 r_{n,k}. It is not 'just as good' far away.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("neural.py", "backprop matches central finite differences", check_gradient),
    ("neural.py", "the exact Hessian is symmetric and consistent", check_hessian_consistency),
    ("neural.py", "outer-product Hessian matches near a minimum", check_outer_product_near_minimum),
    ("neural.py", "weight decay and early stopping", check_weight_decay_and_early_stopping),
    ("neural.py", "limit case: outer-product Hessian far from a minimum", check_outer_product_limit),
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
    print(f"\n{BOLD}PRML Neural Networks From Scratch — progress check{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built neural networks from scratch.{RESET}")
        print(f"  {GREY}Run solutions/neural.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

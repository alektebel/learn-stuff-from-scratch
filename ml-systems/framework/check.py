"""
Progress checker for the framework templates.

    python3 check.py           # stop at the first unimplemented step
    python3 check.py 6         # one step
    python3 check.py 3 8       # steps 3 through 8
    python3 check.py --all     # everything

Gradients are verified against central finite differences: if your backward disagrees
with (f(x + h) - f(x - h)) / 2h, your backward is wrong, whatever it looks like.
Nothing here imports solutions/. It tests YOUR code.
"""

import pathlib
import shutil
import sys
import traceback
import warnings

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

import numpy as np  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def gradcheck(f, *arrays, h=1e-6, tol=1e-5, what=""):
    """f takes Tensors and returns a scalar Tensor. Compares autograd with finite differences."""
    from tensor import Tensor
    ts = [Tensor(a.copy(), requires_grad=True) for a in arrays]
    out = f(*ts)
    out.backward()
    for i, (t, a) in enumerate(zip(ts, arrays)):
        assert t.grad is not None, f"{what}: input {i} got no gradient"
        assert t.grad.shape == a.shape, (
            f"{what}: input {i} gradient has shape {t.grad.shape}, input has {a.shape} "
            "(a broadcast was not summed back: see unbroadcast)")
        num = np.zeros_like(a)
        for idx in np.ndindex(a.shape):
            plus, minus = [x.copy() for x in arrays], [x.copy() for x in arrays]
            plus[i][idx] += h
            minus[i][idx] -= h
            fp = f(*[Tensor(x) for x in plus]).item()
            fm = f(*[Tensor(x) for x in minus]).item()
            num[idx] = (fp - fm) / (2 * h)
        err = np.max(np.abs(num - t.grad) / (np.abs(num) + np.abs(t.grad) + 1e-8))
        assert err < tol, f"{what}: input {i} gradient wrong (relative error {err:.2e})\n" \
                          f"      autograd {t.grad.ravel()[:4]}\n      numeric  {num.ravel()[:4]}"


R = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Steps 1-6: tensor.py
# ---------------------------------------------------------------------------

def check_forward() -> None:
    from tensor import Tensor
    a = Tensor([[1.0, 2.0], [3.0, 4.0]])
    b = Tensor([10.0, 20.0])
    assert np.array_equal((a + b).data, [[11, 22], [13, 24]]), "broadcast add wrong"
    assert np.array_equal((a * 2).data, [[2, 4], [6, 8]]) and np.array_equal((2 * a).data, [[2, 4], [6, 8]])
    assert np.array_equal((a @ a).data, [[7, 10], [15, 22]]), "matmul wrong"
    assert np.allclose((1 / a).data, [[1, 0.5], [1 / 3, 0.25]]) and np.allclose((a - 1).data, [[0, 1], [2, 3]])
    assert a.sum().item() == 10 and np.array_equal(a.sum(axis=0).data, [4, 6])
    assert a.mean().item() == 2.5 and a.T.shape == (2, 2) and a.reshape(4).shape == (4,)
    assert not (a + b).requires_grad, "an op on tensors that do not require grad must not require grad"


def check_backward_basic() -> None:
    gradcheck(lambda x, y: (x * y + x).sum(), R.normal(size=(3,)), R.normal(size=(3,)), what="x*y + x")
    gradcheck(lambda x, y: (x / y - y).sum(), R.normal(size=(3,)), R.uniform(1, 2, size=(3,)), what="x/y - y")
    gradcheck(lambda x: (x ** 3).sum(), R.normal(size=(4,)), what="x**3")


def check_backward_broadcast() -> None:
    gradcheck(lambda x, b: (x + b).sum(), R.normal(size=(5, 3)), R.normal(size=(3,)), what="(5,3) + (3,)")
    gradcheck(lambda x, b: (x * b).sum(), R.normal(size=(5, 3)), R.normal(size=(1, 3)), what="(5,3) * (1,3)")
    gradcheck(lambda x, b: ((x + b) * x).sum(), R.normal(size=(2, 4, 3)), R.normal(size=(4, 1)), what="(2,4,3) + (4,1)")


def check_backward_matmul_reduce() -> None:
    gradcheck(lambda a, b: (a @ b).sum(), R.normal(size=(4, 3)), R.normal(size=(3, 2)), what="matmul")
    gradcheck(lambda a, b: ((a @ b) ** 2).sum(), R.normal(size=(2, 4, 3)), R.normal(size=(3, 2)), what="batched matmul")
    gradcheck(lambda a: (a.sum(axis=0) ** 2).sum(), R.normal(size=(3, 4)), what="sum(axis=0)")
    gradcheck(lambda a: (a.mean(axis=1, keepdims=True) * a).sum(), R.normal(size=(3, 4)), what="mean keepdims")
    gradcheck(lambda a: (a.reshape(6, 2).T @ a.reshape(6, 2)).sum(), R.normal(size=(3, 4)), what="reshape/T")


def check_graph() -> None:
    from tensor import Tensor
    x = Tensor([3.0], requires_grad=True)
    y = x * x + x * 2          # x used three times: gradients must ACCUMULATE
    y.sum().backward()
    assert np.allclose(x.grad, [8.0]), f"d(x^2 + 2x)/dx at 3 should be 8, got {x.grad}"
    a = Tensor([2.0], requires_grad=True)
    b, c = a * 3, a * 4        # diamond: a -> b, a -> c -> d
    (b * c).sum().backward()
    assert np.allclose(a.grad, [48.0]), f"diamond graph: expected 48, got {a.grad}"
    k = Tensor([5.0])          # a constant inside the graph
    z = Tensor([1.0], requires_grad=True)
    ((z - k) * (z + k)).sum().backward()
    assert k.grad is None and np.allclose(z.grad, [2.0]), "constants must not receive gradients"
    t = Tensor([1.0], requires_grad=True)
    s = t
    for _ in range(10_000):
        s = s * 1.0001
    s.sum().backward()         # a recursive topological sort dies here
    assert np.isclose(t.grad[0], 1.0001 ** 10_000), "long chain gradient wrong"


def check_elementwise() -> None:
    from tensor import Tensor
    for name, f, gen in [("exp", lambda x: x.exp().sum(), lambda: R.normal(size=(5,))),
                         ("log", lambda x: x.log().sum(), lambda: R.uniform(0.5, 2, size=(5,))),
                         ("relu", lambda x: (x.relu() * x).sum(), lambda: R.normal(size=(5,)) + 0.05),
                         ("sigmoid", lambda x: x.sigmoid().sum(), lambda: R.normal(size=(5,))),
                         ("tanh", lambda x: x.tanh().sum(), lambda: R.normal(size=(5,)))]:
        gradcheck(f, gen(), what=name)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        s = Tensor([-1000.0, 1000.0]).sigmoid().data
    assert np.allclose(s, [0.0, 1.0]), "sigmoid of +/-1000 must be 0 and 1, without overflow"


# ---------------------------------------------------------------------------
# Steps 7-9: nn.py, losses.py
# ---------------------------------------------------------------------------

def check_modules() -> None:
    from nn import Linear, ReLU, Sequential
    from tensor import Tensor
    m = Sequential(Linear(4, 8), ReLU(), Sequential(Linear(8, 8), ReLU()), Linear(8, 2))
    ps = m.parameters()
    assert len(ps) == 6, f"expected 6 parameters (3 weights, 3 biases), found {len(ps)}: nested modules?"
    assert m(Tensor(np.ones((5, 4)))).shape == (5, 2)
    big = Linear(1000, 1000, init="he", rng=np.random.default_rng(0))
    var = big.weight.data.var()
    assert abs(var - 2 / 1000) < 2e-4, f"He init variance should be ~{2 / 1000}, got {var:.5f}"
    x = Tensor(np.random.default_rng(1).normal(size=(256, 1000)))
    h = x
    for _ in range(10):
        h = Linear(1000, 1000, init="he", rng=np.random.default_rng(_))(h).relu()
    ratio = h.data.var() / x.data.var()
    assert 0.1 < ratio < 10, f"after 10 He-initialised ReLU layers the activation variance changed {ratio:.3g}x"


def check_softmax_ce() -> None:
    from losses import cross_entropy
    from nn import log_softmax, softmax
    from tensor import Tensor
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ls = log_softmax(Tensor([[1000.0, 0.0, -1000.0]])).data
    assert np.isfinite(ls).all() and np.isclose(ls[0, 0], 0.0), "log_softmax overflowed on large logits"
    assert np.allclose(softmax(Tensor(R.normal(size=(4, 5)))).data.sum(axis=1), 1.0)
    logits, labels = R.normal(size=(6, 4)), np.array([0, 3, 1, 1, 2, 0])
    gradcheck(lambda z: cross_entropy(z, labels), logits, what="cross_entropy")
    z = Tensor(logits, requires_grad=True)
    cross_entropy(z, labels).backward()
    p = np.exp(logits - logits.max(1, keepdims=True))
    p /= p.sum(1, keepdims=True)
    onehot = np.eye(4)[labels]
    assert np.allclose(z.grad, (p - onehot) / 6), "d CE / d logits must equal (softmax - one_hot) / N"


def check_other_losses() -> None:
    from losses import binary_cross_entropy_with_logits, mse_loss
    gradcheck(lambda p: mse_loss(p, np.ones((3, 2))), R.normal(size=(3, 2)), what="mse")
    t = np.array([[1.0], [0.0], [1.0], [0.0]])
    gradcheck(lambda x: binary_cross_entropy_with_logits(x, t), R.normal(size=(4, 1)), what="bce")
    from tensor import Tensor
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        v = binary_cross_entropy_with_logits(Tensor([[-800.0], [900.0]]), [1, 0]).item()
    assert np.isclose(v, 850.0), f"BCE with extreme logits should be (800 + 900) / 2 = 850, got {v}"


# ---------------------------------------------------------------------------
# Steps 10-12: optim.py, data.py
# ---------------------------------------------------------------------------

def check_sgd() -> None:
    from nn import Parameter
    from optim import SGD
    p = Parameter([1.0])
    opt = SGD([p], lr=0.1, momentum=0.9)
    for _ in range(3):
        p.grad = np.array([1.0])
        opt.step()
    # v1 = 1, v2 = 1.9, v3 = 2.71; p = 1 - 0.1 * (1 + 1.9 + 2.71)
    assert np.isclose(p.data[0], 1 - 0.1 * 5.61), f"SGD momentum: expected {1 - 0.561}, got {p.data[0]}"
    opt.zero_grad()
    assert p.grad is None


def check_adam() -> None:
    from nn import Parameter
    from optim import Adam
    p = Parameter([0.0])
    opt = Adam([p], lr=0.1)
    p.grad = np.array([0.5])
    opt.step()
    assert np.isclose(p.data[0], -0.1, atol=1e-6), (
        f"first Adam step with bias correction moves by exactly lr: expected -0.1, got {p.data[0]:.6f}. "
        "Without bias correction it would be ~-0.0316")
    p.grad = np.array([-1.0])
    opt.step()
    m = (0.9 * 0.05 + 0.1 * -1.0) / (1 - 0.81)
    v = (0.999 * 0.00025 + 0.001 * 1.0) / (1 - 0.999 ** 2)
    assert np.isclose(p.data[0], -0.1 - 0.1 * m / (np.sqrt(v) + 1e-8)), "second Adam step wrong"
    assert len(opt.state_arrays()) == 2, "Adam keeps two state buffers per parameter"


def check_dataloader() -> None:
    from data import DataLoader, TensorDataset
    X, y = np.arange(20).reshape(10, 2).astype(float), np.arange(10)
    ds = TensorDataset(X, y)
    batches = list(DataLoader(ds, batch_size=4, shuffle=True, seed=1))
    assert [len(b[1]) for b in batches] == [4, 4, 2], "10 items in batches of 4 should give 4, 4, 2"
    seen = np.concatenate([b[1] for b in batches])
    assert sorted(seen) == list(range(10)), "every example exactly once per epoch"
    assert not np.array_equal(seen, np.arange(10)), "shuffle=True did not shuffle"
    again = np.concatenate([b[1] for b in DataLoader(ds, batch_size=4, shuffle=True, seed=1)])
    assert np.array_equal(seen, again), "the same seed must give the same order"
    assert len(DataLoader(ds, batch_size=4, drop_last=True)) == 2
    assert [len(b[1]) for b in DataLoader(ds, batch_size=4, drop_last=True)] == [4, 4]
    assert np.array_equal(batches[0][0][:, 0] / 2, batches[0][1]), "X and y rows got separated"


# ---------------------------------------------------------------------------
# Steps 13-15: train.py milestones
# ---------------------------------------------------------------------------

def check_perceptron() -> None:
    from train import accuracy, fit, make_blobs, perceptron
    X, y = make_blobs()
    m = perceptron()
    fit(m, X, y, loss="bce", epochs=30, lr=0.05)
    acc = accuracy(m, X, y)
    assert acc >= 0.98, f"1958: a perceptron should separate the blobs, got accuracy {acc:.3f}"


def check_xor() -> None:
    from train import accuracy, fit, make_xor, mlp, perceptron
    X, y = make_xor()
    lin = perceptron()
    fit(lin, X, y, loss="bce", epochs=60, lr=0.05)
    deep = mlp([2, 8, 1])
    fit(deep, X, y, loss="bce", epochs=150, lr=0.05)
    a_lin, a_deep = accuracy(lin, X, y), accuracy(deep, X, y)
    assert a_lin <= 0.8, f"1969: a linear model must FAIL on XOR, but got {a_lin:.3f} (is the data really XOR?)"
    assert a_deep >= 0.97, f"1986: an MLP with one hidden layer should solve XOR, got {a_deep:.3f}"


def check_spirals() -> None:
    from nn import ReLU
    from train import accuracy, fit, make_spirals, mlp
    X, y = make_spirals()
    m = mlp([2, 64, 64, 3], act=ReLU)
    hist = fit(m, X, y, epochs=300, lr=0.01)
    acc = accuracy(m, X, y)
    assert hist[-1] < hist[0] / 5, f"loss barely moved: {hist[0]:.3f} -> {hist[-1]:.3f}"
    assert acc >= 0.95, f"3-class spirals: expected >= 0.95, got {acc:.3f}"


# ---------------------------------------------------------------------------
# Step 16: costs.py
# ---------------------------------------------------------------------------

def check_costs() -> None:
    from costs import count_params, forward_flops, training_memory_bytes
    from losses import cross_entropy
    from optim import Adam
    from tensor import Tensor
    from train import mlp
    m = mlp([784, 512, 512, 10])
    assert count_params(m) == 784 * 512 + 512 + 512 * 512 + 512 + 512 * 10 + 10
    assert forward_flops(m, 64) == 2 * 64 * (784 * 512 + 512 * 512 + 512 * 10)
    mem = training_memory_bytes(m, 64, "adam", bytes_per_element=8)
    # compare the formula with what the code really allocates after one step
    opt = Adam(m.parameters())
    cross_entropy(m(Tensor(np.zeros((64, 784)))), np.zeros(64, dtype=int)).backward()
    opt.step()
    weights = sum(p.data.nbytes for p in m.parameters())
    grads = sum(p.grad.nbytes for p in m.parameters())
    state = sum(a.nbytes for a in opt.state_arrays())
    assert (mem["weights"], mem["gradients"], mem["optimizer_state"]) == (weights, grads, state), (
        f"memory formula disagrees with allocation: formula {mem}, measured weights {weights} "
        f"grads {grads} optimizer state {state}")
    assert mem["optimizer_state"] == 2 * mem["weights"], "Adam state is twice the weights"
    assert training_memory_bytes(m, 64, "adam", 4)["total"] * 2 == mem["total"], "float32 should halve every term"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("tensor.py", "forward ops and broadcasting", check_forward),
    ("tensor.py", "backward: +, *, /, ** (gradcheck)", check_backward_basic),
    ("tensor.py", "backward through broadcasting", check_backward_broadcast),
    ("tensor.py", "backward: matmul, sum, mean, reshape", check_backward_matmul_reduce),
    ("tensor.py", "graph: reuse, diamond, constants, 10k chain", check_graph),
    ("tensor.py", "exp, log, relu, sigmoid, tanh; stability", check_elementwise),
    ("nn.py", "modules, parameter discovery, He init", check_modules),
    ("losses.py", "stable log_softmax, cross-entropy grad", check_softmax_ce),
    ("losses.py", "MSE and stable BCE", check_other_losses),
    ("optim.py", "SGD with momentum", check_sgd),
    ("optim.py", "Adam with bias correction", check_adam),
    ("data.py", "DataLoader: batches, shuffle, seed", check_dataloader),
    ("train.py", "1958: perceptron", check_perceptron),
    ("train.py", "1969 vs 1986: XOR", check_xor),
    ("train.py", "3-class spirals", check_spirals),
    ("costs.py", "params, FLOPs, training memory", check_costs),
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
    print(f"\n{BOLD}ML Systems: framework from scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have a working framework.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

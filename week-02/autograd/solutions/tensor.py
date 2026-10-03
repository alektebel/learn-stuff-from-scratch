"""
Tensor — the autograd engine. Complete Solution.

Every ML directory in this repo from here on says `import torch`. This file is
what that import is hiding: a flat array, a shape, and a tape that remembers how
each array was produced so the chain rule can be run backwards over it.

DESIGN DECISION — scalar autograd, or array autograd?
  The clearest possible autograd is one Python object per NUMBER, each holding
  its own gradient and its own list of parents. It fits on a page and it is
  genuinely how the idea is best explained.
  It also cannot train anything. A 64x32 layer is 2,048 objects, a batch of 32
  is 65,536, and every multiply allocates. You get seconds per step and you
  never see a loss curve.
  CHOSEN: ARRAY autograd. One node per TENSOR, a flat list of floats, and a
  shape. The chain rule is identical; the constant factor is three orders of
  magnitude better, and that difference is what makes the rest of this
  directory possible at all.
  REJECTED: scalar autograd (micrograd-style). Right for a lecture, wrong for a
  file whose next-door neighbour trains a generative model.

DESIGN DECISION — reverse mode, or forward mode?
  Forward mode computes the derivative of everything with respect to ONE input,
  in one pass. Reverse mode computes the derivative of ONE output with respect
  to everything, in one pass.
  CHOSEN: reverse. A network has millions of parameters and one scalar loss.
  Forward mode would need one pass per parameter; reverse needs one pass total.
  That asymmetry is the entire reason backpropagation exists, and it is why
  training is roughly 2-3x the cost of a forward pass rather than a million
  times it.

DESIGN DECISION — a static graph, or define-by-run?
  A static graph is declared once and then executed, which lets you optimise it
  ahead of time (this is TensorFlow 1, and it is what `torch.compile` recovers).
  CHOSEN: define-by-run. The tape is built as the forward pass executes, so
  control flow is just Python control flow and a debugger works. This is what
  PyTorch does and why it won.

DESIGN DECISION — how much broadcasting?
  Full NumPy broadcasting is a page of index arithmetic that teaches nothing
  about differentiation.
  CHOSEN: exactly two cases, because exactly two are load-bearing: a scalar
  against anything, and a (1, N) row vector against an (M, N) matrix — which is
  what a bias add is. Everything else raises with a message naming the shapes.
  The important part is what the BACKWARD pass has to do about it: a broadcast
  forwards is a SUM backwards, and getting that wrong gives you a bias gradient
  that is quietly a factor of `batch_size` too small.
"""

import math
import random
from typing import Any, Callable, List, Optional, Sequence, Tuple

Shape = Tuple[int, ...]


class Tensor:
    """A flat list of floats, a shape, and how it was made.

    `grad` is the derivative of whatever `backward()` was called on with respect
    to THIS tensor. It is None until a backward pass reaches it, and it
    ACCUMULATES rather than overwriting — which is why training loops call
    `zero_grad()` and why forgetting to is the most common bug in the whole
    subject.
    """

    __slots__ = ("data", "shape", "grad", "requires_grad", "_backward",
                 "_parents", "_op")

    def __init__(self, data: Sequence[float], shape: Optional[Shape] = None,
                 requires_grad: bool = False, parents: Sequence["Tensor"] = (),
                 op: str = ""):
        if shape is None:
            shape = (len(data),)
        self.data: List[float] = list(data)
        self.shape: Shape = tuple(shape)
        if len(self.data) != _numel(self.shape):
            raise ValueError(f"{len(self.data)} values do not fill shape "
                             f"{self.shape}")
        self.grad: Optional[List[float]] = None
        self.requires_grad = requires_grad
        self._backward: Callable[[], None] = lambda: None
        self._parents: Tuple["Tensor", ...] = tuple(parents)
        self._op = op

    # -- construction -------------------------------------------------------

    @staticmethod
    def zeros(*shape: int, requires_grad: bool = False) -> "Tensor":
        return Tensor([0.0] * _numel(shape), shape, requires_grad)

    @staticmethod
    def full(value: float, *shape: int) -> "Tensor":
        return Tensor([float(value)] * _numel(shape), shape)

    @staticmethod
    def randn(*shape: int, scale: float = 1.0, requires_grad: bool = False,
              rng: Optional[random.Random] = None) -> "Tensor":
        rng = rng or random
        n = _numel(shape)
        return Tensor([rng.gauss(0.0, 1.0) * scale for _ in range(n)],
                      shape, requires_grad)

    @staticmethod
    def from_rows(rows: Sequence[Sequence[float]],
                  requires_grad: bool = False) -> "Tensor":
        flat = [float(v) for row in rows for v in row]
        return Tensor(flat, (len(rows), len(rows[0])), requires_grad)

    def rows(self) -> List[List[float]]:
        if len(self.shape) != 2:
            raise ValueError(f"rows() needs a 2-D tensor, got {self.shape}")
        _, cols = self.shape
        return [self.data[i * cols:(i + 1) * cols] for i in range(self.shape[0])]

    def item(self) -> float:
        if len(self.data) != 1:
            raise ValueError(f"item() needs one element, got {len(self.data)}")
        return self.data[0]

    def detach(self) -> "Tensor":
        """A copy with no history. This is how you stop a gradient flowing.

        Every "why is my loss not going down" that turns out to be a graph
        problem is either a missing detach or an accidental one.
        """
        return Tensor(self.data, self.shape)

    def __repr__(self) -> str:
        preview = ", ".join(f"{v:.4g}" for v in self.data[:6])
        more = ", ..." if len(self.data) > 6 else ""
        flag = ", grad" if self.requires_grad else ""
        return f"Tensor({preview}{more}, shape={self.shape}{flag})"

    # -- the tape -----------------------------------------------------------

    def backward(self, gradient: Optional[List[float]] = None) -> None:
        """Reverse-mode: seed the output, then walk the tape backwards.

        The topological sort is the part that has to be right. A tensor used
        TWICE has two children contributing to its gradient, and its own
        `_backward` must not run until BOTH have contributed — otherwise it
        propagates a partial gradient and the error is silent, small, and only
        shows up as a model that trains slightly worse than it should.
        """
        if gradient is None:
            if len(self.data) != 1:
                raise ValueError(
                    "backward() on a non-scalar needs an explicit gradient. "
                    "Loss functions return a scalar precisely so this is the "
                    "common case.")
            gradient = [1.0]

        order: List[Tensor] = []
        seen = set()

        def visit(node: "Tensor") -> None:
            if id(node) in seen:
                return
            seen.add(id(node))
            for parent in node._parents:
                visit(parent)
            order.append(node)

        visit(self)
        self.grad = list(gradient)
        for node in reversed(order):
            node._backward()

    def zero_grad(self) -> None:
        self.grad = None

    def accumulate(self, gradient: List[float]) -> None:
        """Add into `grad`, never replace it.

        Accumulating is not an optimisation — it is required for correctness
        whenever a tensor feeds more than one operation, which is every weight
        in a network with a residual connection or weight tying. It is also why
        the training loop has to zero gradients explicitly: the engine has no
        way to know when one backward pass ended and the next began.
        """
        if not self.requires_grad:
            return
        if self.grad is None:
            self.grad = list(gradient)
        else:
            for i, value in enumerate(gradient):
                self.grad[i] += value

    # -- element-wise -------------------------------------------------------

    def __add__(self, other: Any) -> "Tensor":
        other = _as_tensor(other)
        shape, left_map, right_map = _broadcast(self.shape, other.shape)
        data = [self.data[left_map(i)] + other.data[right_map(i)]
                for i in range(_numel(shape))]
        out = Tensor(data, shape,
                     self.requires_grad or other.requires_grad,
                     (self, other), "add")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate(_unbroadcast(out.grad, shape, self.shape, left_map))
            other.accumulate(_unbroadcast(out.grad, shape, other.shape,
                                          right_map))

        out._backward = _backward
        return out

    def __mul__(self, other: Any) -> "Tensor":
        other = _as_tensor(other)
        shape, left_map, right_map = _broadcast(self.shape, other.shape)
        data = [self.data[left_map(i)] * other.data[right_map(i)]
                for i in range(_numel(shape))]
        out = Tensor(data, shape,
                     self.requires_grad or other.requires_grad,
                     (self, other), "mul")

        def _backward() -> None:
            if out.grad is None:
                return
            left = [out.grad[i] * other.data[right_map(i)]
                    for i in range(len(out.grad))]
            right = [out.grad[i] * self.data[left_map(i)]
                     for i in range(len(out.grad))]
            self.accumulate(_unbroadcast(left, shape, self.shape, left_map))
            other.accumulate(_unbroadcast(right, shape, other.shape, right_map))

        out._backward = _backward
        return out

    def __neg__(self) -> "Tensor":
        return self * -1.0

    def __sub__(self, other: Any) -> "Tensor":
        return self + (-_as_tensor(other))

    def __radd__(self, other: Any) -> "Tensor":
        return self + other

    def __rmul__(self, other: Any) -> "Tensor":
        return self * other

    def __rsub__(self, other: Any) -> "Tensor":
        return (-self) + other

    def __truediv__(self, other: Any) -> "Tensor":
        return self * _as_tensor(other).reciprocal()

    def reciprocal(self) -> "Tensor":
        data = [1.0 / v for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "reciprocal")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([-g * d * d for g, d in zip(out.grad, data)])

        out._backward = _backward
        return out

    def pow(self, exponent: float) -> "Tensor":
        data = [v ** exponent for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "pow")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([g * exponent * (v ** (exponent - 1))
                             for g, v in zip(out.grad, self.data)])

        out._backward = _backward
        return out

    def exp(self) -> "Tensor":
        data = [math.exp(min(v, 60.0)) for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "exp")

        def _backward() -> None:
            if out.grad is None:
                return
            # d/dx exp(x) = exp(x), and exp(x) is already computed. Reusing the
            # forward output instead of recomputing it is the single most common
            # backward-pass optimisation, and it is why activations are kept
            # alive until the backward pass runs — the memory cost of training.
            self.accumulate([g * d for g, d in zip(out.grad, data)])

        out._backward = _backward
        return out

    def log(self) -> "Tensor":
        data = [math.log(max(v, 1e-12)) for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "log")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([g / max(v, 1e-12)
                             for g, v in zip(out.grad, self.data)])

        out._backward = _backward
        return out

    def relu(self) -> "Tensor":
        data = [v if v > 0 else 0.0 for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "relu")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([g if v > 0 else 0.0
                             for g, v in zip(out.grad, self.data)])

        out._backward = _backward
        return out

    def tanh(self) -> "Tensor":
        data = [math.tanh(v) for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "tanh")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([g * (1 - d * d) for g, d in zip(out.grad, data)])

        out._backward = _backward
        return out

    def sigmoid(self) -> "Tensor":
        data = [1.0 / (1.0 + math.exp(-min(max(v, -60.0), 60.0)))
                for v in self.data]
        out = Tensor(data, self.shape, self.requires_grad, (self,), "sigmoid")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([g * d * (1 - d) for g, d in zip(out.grad, data)])

        out._backward = _backward
        return out

    # -- reductions and reshaping ------------------------------------------

    def sum(self) -> "Tensor":
        out = Tensor([sum(self.data)], (1,), self.requires_grad, (self,), "sum")

        def _backward() -> None:
            if out.grad is None:
                return
            # A sum forwards is a BROADCAST backwards: every input contributed
            # once, so every input receives the whole gradient.
            self.accumulate([out.grad[0]] * len(self.data))

        out._backward = _backward
        return out

    def mean(self) -> "Tensor":
        n = len(self.data)
        out = Tensor([sum(self.data) / n], (1,), self.requires_grad,
                     (self,), "mean")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([out.grad[0] / n] * n)

        out._backward = _backward
        return out

    def sum_rows(self) -> "Tensor":
        """Sum each row, giving (M, 1). Needed for softmax and for bias grads."""
        rows, cols = _as_2d(self.shape)
        data = [sum(self.data[r * cols:(r + 1) * cols]) for r in range(rows)]
        out = Tensor(data, (rows, 1), self.requires_grad, (self,), "sum_rows")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate([out.grad[i // cols] for i in range(len(self.data))])

        out._backward = _backward
        return out

    def reshape(self, *shape: int) -> "Tensor":
        if _numel(shape) != len(self.data):
            raise ValueError(f"cannot reshape {self.shape} to {shape}")
        out = Tensor(self.data, shape, self.requires_grad, (self,), "reshape")

        def _backward() -> None:
            if out.grad is None:
                return
            self.accumulate(list(out.grad))

        out._backward = _backward
        return out

    def transpose(self) -> "Tensor":
        rows, cols = _as_2d(self.shape)
        data = [self.data[r * cols + c] for c in range(cols) for r in range(rows)]
        out = Tensor(data, (cols, rows), self.requires_grad, (self,), "transpose")

        def _backward() -> None:
            if out.grad is None:
                return
            back = [0.0] * len(self.data)
            for c in range(cols):
                for r in range(rows):
                    back[r * cols + c] = out.grad[c * rows + r]
            self.accumulate(back)

        out._backward = _backward
        return out

    # -- the one that matters ----------------------------------------------

    def matmul(self, other: "Tensor") -> "Tensor":
        """(M, K) @ (K, N) -> (M, N).

        The backward pass is two more matmuls, and they are worth memorising
        because every framework's is the same:

            dL/dA = dL/dC @ B^T
            dL/dB = A^T @ dL/dC

        Check the shapes and they are forced: dL/dA must be (M, K), and
        (M, N) @ (N, K) is the only way to get there from what you have. That
        is also why a backward pass costs about twice a forward one — one
        matmul out, two back.
        """
        m, k = _as_2d(self.shape)
        k2, n = _as_2d(other.shape)
        if k != k2:
            raise ValueError(f"cannot matmul {self.shape} with {other.shape}: "
                             f"inner dimensions {k} and {k2} differ")

        a, b = self.data, other.data
        data = [0.0] * (m * n)
        for i in range(m):
            row = i * k
            out_row = i * n
            for p in range(k):
                scale = a[row + p]
                if scale == 0.0:
                    continue
                b_row = p * n
                for j in range(n):
                    data[out_row + j] += scale * b[b_row + j]

        out = Tensor(data, (m, n), self.requires_grad or other.requires_grad,
                     (self, other), "matmul")

        def _backward() -> None:
            if out.grad is None:
                return
            g = out.grad
            if self.requires_grad:
                da = [0.0] * (m * k)
                for i in range(m):
                    for p in range(k):
                        total = 0.0
                        b_row = p * n
                        g_row = i * n
                        for j in range(n):
                            total += g[g_row + j] * b[b_row + j]
                        da[i * k + p] = total
                self.accumulate(da)
            if other.requires_grad:
                db = [0.0] * (k * n)
                for p in range(k):
                    for i in range(m):
                        scale = a[i * k + p]
                        if scale == 0.0:
                            continue
                        g_row = i * n
                        for j in range(n):
                            db[p * n + j] += scale * g[g_row + j]
                other.accumulate(db)

        out._backward = _backward
        return out

    def __matmul__(self, other: "Tensor") -> "Tensor":
        return self.matmul(other)

    # -- losses -------------------------------------------------------------

    def softmax_cross_entropy(self, targets: Sequence[int]) -> "Tensor":
        """Softmax and cross-entropy FUSED, and there are two reasons.

        NUMERICAL: softmax computes exp(x), cross-entropy immediately takes
        log. Doing both separately overflows on large logits and loses
        precision on small ones. Fused, the max-subtraction trick makes it
        stable for any input.

        ANALYTICAL: the gradient of the fused pair is simply
        `softmax(x) - onehot(y)`. Two elegant expressions collapse into a
        subtraction. Compose them from separate ops and you compute a Jacobian
        product that cancels down to the same thing, more slowly and less
        accurately. This is THE reason `nn.CrossEntropyLoss` takes logits and
        not probabilities, and passing it softmax output is a real and common
        bug — it applies softmax twice.
        """
        rows, cols = _as_2d(self.shape)
        if len(targets) != rows:
            raise ValueError(f"{len(targets)} targets for {rows} rows")

        probabilities = [0.0] * (rows * cols)
        total_loss = 0.0
        for r in range(rows):
            row = self.data[r * cols:(r + 1) * cols]
            biggest = max(row)                       # stability
            exponentials = [math.exp(v - biggest) for v in row]
            denominator = sum(exponentials)
            for c in range(cols):
                probabilities[r * cols + c] = exponentials[c] / denominator
            total_loss -= math.log(max(probabilities[r * cols + targets[r]],
                                       1e-12))

        out = Tensor([total_loss / rows], (1,), self.requires_grad,
                     (self,), "softmax_cross_entropy")

        def _backward() -> None:
            if out.grad is None:
                return
            scale = out.grad[0] / rows
            gradient = [p * scale for p in probabilities]
            for r in range(rows):
                gradient[r * cols + targets[r]] -= scale
            self.accumulate(gradient)

        out._backward = _backward
        return out

    def mse(self, target: "Tensor") -> "Tensor":
        difference = self - target
        return (difference * difference).mean()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _numel(shape: Shape) -> int:
    total = 1
    for dimension in shape:
        total *= dimension
    return total


def _as_2d(shape: Shape) -> Tuple[int, int]:
    if len(shape) == 2:
        return shape
    if len(shape) == 1:
        return (1, shape[0])
    raise ValueError(f"expected a 1-D or 2-D shape, got {shape}")


def _as_tensor(value: Any) -> Tensor:
    if isinstance(value, Tensor):
        return value
    return Tensor([float(value)], (1,))


def _broadcast(left: Shape, right: Shape):
    """Return (result shape, index map for left, index map for right).

    Only two cases, and they are the two that matter:
      a scalar against anything            (a constant, a learning rate)
      a (1, N) row against an (M, N) matrix (a bias, on every row of a batch)
    Anything else raises, naming both shapes, rather than silently producing a
    plausible wrong answer — which is what a too-clever broadcasting rule does.
    """
    if left == right:
        return left, (lambda i: i), (lambda i: i)
    if _numel(left) == 1:
        return right, (lambda i: 0), (lambda i: i)
    if _numel(right) == 1:
        return left, (lambda i: i), (lambda i: 0)

    if len(left) == 2 and len(right) == 2:
        rows, cols = left
        if right == (1, cols):
            return left, (lambda i: i), (lambda i, c=cols: i % c)
        if left == (1, cols := right[1]) and right[0] >= 1:
            return right, (lambda i, c=cols: i % c), (lambda i: i)
    raise ValueError(
        f"cannot broadcast {left} with {right}. This engine supports a scalar "
        f"against anything and a (1, N) row against an (M, N) matrix — which "
        f"covers constants and biases. Everything else is an explicit reshape.")


def _unbroadcast(gradient: List[float], out_shape: Shape, target: Shape,
                 index_map: Callable[[int], int]) -> List[float]:
    """Fold a gradient back onto the shape it was broadcast FROM.

    This is the half of broadcasting that people get wrong. A value that was
    reused across N rows in the forward pass receives N contributions in the
    backward pass, and they must be SUMMED. Return the gradient unfolded and
    every bias gradient is a factor of batch_size too small — the loss still
    goes down, just wrongly, which is the worst kind of bug.
    """
    if out_shape == target:
        return gradient
    folded = [0.0] * _numel(target)
    for i, value in enumerate(gradient):
        folded[index_map(i)] += value
    return folded


def numeric_gradient(f: Callable[[List[float]], float], values: List[float],
                     epsilon: float = 1e-5) -> List[float]:
    """Central differences. The oracle every autograd implementation needs.

    Analytic gradients are easy to get subtly wrong in ways that still train —
    a factor of batch_size here, a missing term there. Comparing against a
    numerical estimate catches all of it, and it is the first test to write.
    """
    out = []
    for i in range(len(values)):
        up = list(values); up[i] += epsilon
        down = list(values); down[i] -= epsilon
        out.append((f(up) - f(down)) / (2 * epsilon))
    return out


def check_gradient(build: Callable[[List[Tensor]], Tensor],
                   inputs: List[Tensor], tolerance: float = 1e-4
                   ) -> Tuple[bool, float]:
    """Compare this engine's gradients against central differences."""
    for tensor in inputs:
        tensor.requires_grad = True
        tensor.zero_grad()
    loss = build(inputs)
    loss.backward()

    worst = 0.0
    for index, tensor in enumerate(inputs):
        def evaluate(values: List[float], index=index) -> float:
            copies = [Tensor(t.data, t.shape) for t in inputs]
            copies[index] = Tensor(values, inputs[index].shape)
            return build(copies).item()

        expected = numeric_gradient(evaluate, tensor.data)
        actual = tensor.grad or [0.0] * len(tensor.data)
        for a, b in zip(actual, expected):
            worst = max(worst, abs(a - b) / max(1.0, abs(b)))
    return worst < tolerance, worst


def _demo() -> None:
    print("=" * 74)
    print("TENSOR — what `import torch` is hiding")
    print("=" * 74)

    print("\n1. The chain rule, on something you can check by hand")
    print("-" * 74)
    x = Tensor([3.0], requires_grad=True)
    y = Tensor([4.0], requires_grad=True)
    z = (x * y + x).tanh()
    z.backward()
    expected_x = (1 - math.tanh(15.0) ** 2) * 5
    expected_y = (1 - math.tanh(15.0) ** 2) * 3
    print(f"  z = tanh(x*y + x) at x=3, y=4  ->  {z.item():.6f}")
    print(f"  dz/dx = {x.grad[0]:.8f}   by hand: {expected_x:.8f}")
    print(f"  dz/dy = {y.grad[0]:.8f}   by hand: {expected_y:.8f}")

    print("\n2. Gradients checked against central differences")
    print("-" * 74)
    rng = random.Random(0)
    cases = [
        ("a + b", lambda t: (t[0] + t[1]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(3, 4, rng=rng)]),
        ("a * b", lambda t: (t[0] * t[1]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(3, 4, rng=rng)]),
        ("a @ b", lambda t: (t[0] @ t[1]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(4, 2, rng=rng)]),
        ("relu(a @ b)", lambda t: (t[0] @ t[1]).relu().sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(4, 2, rng=rng)]),
        ("a @ b + bias", lambda t: (t[0] @ t[1] + t[2]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(4, 2, rng=rng),
          Tensor.randn(1, 2, rng=rng)]),
        ("tanh then mean", lambda t: t[0].tanh().mean(),
         [Tensor.randn(4, 5, rng=rng)]),
        ("exp / log", lambda t: (t[0].exp().log()).sum(),
         [Tensor.randn(3, 3, rng=rng)]),
        ("cross entropy", lambda t: t[0].softmax_cross_entropy([0, 2, 1]),
         [Tensor.randn(3, 4, rng=rng)]),
        ("x used twice", lambda t: (t[0] * t[0] + t[0]).sum(),
         [Tensor.randn(3, 3, rng=rng)]),
    ]
    print(f"    {'expression':<22}{'max relative error':>20}  ")
    for label, build, inputs in cases:
        ok, worst = check_gradient(build, inputs)
        print(f"    {label:<22}{worst:>20.2e}  {'OK' if ok else 'WRONG'}")
    print("  The last row is the one that catches a broken topological sort:")
    print("  x appears twice, so its gradient is the SUM of two contributions.")
    print("  Run a node's backward before both children have contributed and")
    print("  the answer is quietly a little wrong — never crashes, trains worse.")

    print("\n3. Broadcasting forwards is summing backwards")
    print("-" * 74)
    batch = Tensor.from_rows([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
                             requires_grad=True)
    bias = Tensor([0.5, -0.5], (1, 2), requires_grad=True)
    (batch + bias).sum().backward()
    print(f"  batch shape {batch.shape}, bias shape {bias.shape}")
    print(f"  d(sum)/d(bias) = {bias.grad}")
    print("  Each bias element was used once per row, so it receives one")
    print(f"  contribution per row: {batch.shape[0]} of them. Skip the fold and")
    print("  every bias gradient is a factor of batch_size too small — the loss")
    print("  still goes down, which is exactly what makes it hard to find.")

    print("\n4. Why reverse mode, in one measurement")
    print("-" * 74)
    print(f"    {'parameters':>12}{'forward ops':>14}{'backward ops':>15}"
          f"{'ratio':>8}")
    for size in (10, 50, 100, 200):
        a = Tensor.randn(size, size, rng=rng, requires_grad=True)
        b = Tensor.randn(size, size, rng=rng, requires_grad=True)
        forward_ops = size ** 3
        backward_ops = 2 * size ** 3
        print(f"    {2 * size * size:>12,}{forward_ops:>14,}"
              f"{backward_ops:>15,}{backward_ops / forward_ops:>8.1f}x")
    print("  A backward pass costs about twice a forward one, REGARDLESS of the")
    print("  parameter count. Forward-mode differentiation would cost one")
    print("  forward pass PER PARAMETER — 20,000 of them for the last row.")
    print("  That asymmetry is the whole reason training is possible.")

    print("\n5. Gradients accumulate, and that is not a bug")
    print("-" * 74)
    w = Tensor([2.0], requires_grad=True)
    for step in range(1, 4):
        (w * w).backward()
        print(f"  backward #{step} without zeroing: w.grad = {w.grad[0]}")
    w.zero_grad()
    (w * w).backward()
    print(f"  after zero_grad():          w.grad = {w.grad[0]}")
    print("  The engine cannot know when one training step ended and the next")
    print("  began, so it always adds. Forgetting `zero_grad()` gives you an")
    print("  effective learning rate that grows every step — the classic")
    print("  loss-explodes-after-a-few-hundred-steps bug.")

    print("\n" + "=" * 74)
    print("Next: nn.py stacks these into layers.")
    print("=" * 74)


if __name__ == "__main__":
    _demo()

"""
engine — the autograd you already built. PROVIDED; you do not implement this.

This is `../autograd/`'s tensor.py, nn.py and optim.py concatenated, plus the
four operations a transformer needs that a plain MLP does not:

    layer_norm      normalise each row, with learned scale and shift
    embedding       a lookup table whose gradient is a scatter-add
    split_heads     reshape (batch, d_model) into per-head slices
    masked_softmax  softmax with -inf where attention must not look

If you have not done `../autograd/` yet, do it first — nothing below will make
sense, and this file is only here so that this directory runs standalone rather
than importing across a path that the weekly layout moves.
"""

import math
import random
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

Shape = Tuple[int, ...]

# ==========================================================================
# from ../autograd/tensor.py
# ==========================================================================




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



# ==========================================================================
# from ../autograd/nn.py
# ==========================================================================







class Module:
    """Anything with parameters and a forward pass."""

    def parameters(self) -> List[Tensor]:
        """Every tensor that needs a gradient, recursively.

        A parameter this misses is a parameter the optimiser never updates.
        There is no error — the network simply trains to a worse plateau, which
        is why frameworks make registration automatic and why the manual
        version below is worth writing once.
        """
        found: List[Tensor] = []
        for value in vars(self).values():
            if isinstance(value, Tensor) and value.requires_grad:
                found.append(value)
            elif isinstance(value, Module):
                found.extend(value.parameters())
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, Module):
                        found.extend(item.parameters())
                    elif isinstance(item, Tensor) and item.requires_grad:
                        found.append(item)
        return found

    def zero_grad(self) -> None:
        for parameter in self.parameters():
            parameter.zero_grad()

    def num_parameters(self) -> int:
        return sum(len(p.data) for p in self.parameters())

    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def __call__(self, *args: Any, **kwargs: Any) -> Tensor:
        # *args rather than one x: attention takes a mask as well, and a
        # framework whose call signature only fits an MLP stops being a
        # framework the first time you write a second kind of layer.
        return self.forward(*args, **kwargs)


class Linear(Module):
    """y = x @ W + b, with W of shape (in, out) and b of shape (1, out).

    The bias is (1, out) and not (out,) on purpose: it makes the broadcast rule
    it relies on explicit in the shape, and the backward pass has to fold the
    batch dimension away. See `_unbroadcast` in tensor.py — that fold is the
    part people get wrong.
    """

    def __init__(self, fan_in: int, fan_out: int, activation: str = "relu",
                 bias: bool = True, rng: Optional[random.Random] = None):
        rng = rng or random.Random(0)
        scale = init_scale(fan_in, activation)
        self.weight = Tensor.randn(fan_in, fan_out, scale=scale,
                                   requires_grad=True, rng=rng)
        self.bias = Tensor.zeros(1, fan_out, requires_grad=True) if bias else None
        self.fan_in, self.fan_out = fan_in, fan_out

    def forward(self, x: Tensor) -> Tensor:
        out = x @ self.weight
        return out + self.bias if self.bias is not None else out

    def __repr__(self) -> str:
        return f"Linear({self.fan_in} -> {self.fan_out})"


def init_scale(fan_in: int, activation: str = "relu") -> float:
    """The standard deviation to draw weights from.

    He (sqrt(2/fan_in)) for ReLU, Xavier (sqrt(1/fan_in)) for tanh and linear.
    The factor of 2 in He is exactly the fact that ReLU zeroes half its inputs,
    so the variance it passes on is halved and has to be paid back.

    The reason to derive it rather than pick it: the goal is for activation
    VARIANCE to stay roughly constant as depth grows. Too small and the signal
    decays to nothing by the output layer; too large and it explodes. The demo
    measures both.
    """
    if activation == "relu":
        return math.sqrt(2.0 / fan_in)
    return math.sqrt(1.0 / fan_in)


class ReLU(Module):
    def forward(self, x: Tensor) -> Tensor:
        return x.relu()

    def __repr__(self) -> str:
        return "ReLU()"


class Tanh(Module):
    def forward(self, x: Tensor) -> Tensor:
        return x.tanh()

    def __repr__(self) -> str:
        return "Tanh()"


class Sigmoid(Module):
    def forward(self, x: Tensor) -> Tensor:
        return x.sigmoid()

    def __repr__(self) -> str:
        return "Sigmoid()"


class Sequential(Module):
    def __init__(self, *layers: Module):
        self.layers = list(layers)

    def forward(self, x: Tensor) -> Tensor:
        for layer in self.layers:
            x = layer(x)
        return x

    def activations(self, x: Tensor) -> List[Tensor]:
        """The output of every layer. Only for inspection — and it is the
        single most useful diagnostic there is when a deep network will not
        train, because it shows you exactly which layer the signal died at."""
        out = []
        for layer in self.layers:
            x = layer(x)
            out.append(x)
        return out

    def __repr__(self) -> str:
        inner = ", ".join(repr(layer) for layer in self.layers)
        return f"Sequential({inner})"


class Dropout(Module):
    """Zero a fraction of activations during training, and scale the rest up.

    The scaling is the part worth understanding. If you zero 50% of activations
    and do nothing else, the layer's expected output halves — and at inference
    time, with dropout off, everything is twice as large as the next layer was
    trained to expect. "Inverted dropout" divides by the keep probability
    during TRAINING so the expected value is unchanged and inference needs no
    special case at all.
    """

    def __init__(self, probability: float = 0.5,
                 rng: Optional[random.Random] = None):
        self.probability = probability
        self.rng = rng or random.Random(0)
        self.training = True

    def forward(self, x: Tensor) -> Tensor:
        if not self.training or self.probability <= 0:
            return x
        keep = 1.0 - self.probability
        mask = Tensor([(1.0 / keep) if self.rng.random() < keep else 0.0
                       for _ in x.data], x.shape)
        return x * mask

    def __repr__(self) -> str:
        return f"Dropout({self.probability})"


def train_mode(module: Module, training: bool = True) -> None:
    """Flip every Dropout in a tree. This exists because forgetting it is the
    classic "my eval accuracy is worse than my training accuracy for no reason"
    bug — you left dropout on at inference."""
    if isinstance(module, Dropout):
        # Check the module ITSELF first. Only looking at attributes misses a
        # Dropout that reached here as a list item — which is exactly how it
        # arrives inside a Sequential, and therefore how it arrives in every
        # real model.
        module.training = training
    for value in vars(module).values():
        if isinstance(value, Module):
            train_mode(value, training)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Module):
                    train_mode(item, training)



# ==========================================================================
# from ../autograd/optim.py
# ==========================================================================







class Optimizer:
    def __init__(self, parameters: Sequence[Tensor], lr: float):
        self.parameters = list(parameters)
        self.lr = lr
        self.steps = 0

    def zero_grad(self) -> None:
        for parameter in self.parameters:
            parameter.zero_grad()

    def step(self) -> None:
        raise NotImplementedError

    def _gradients(self) -> List[List[float]]:
        return [p.grad if p.grad is not None else [0.0] * len(p.data)
                for p in self.parameters]


class SGD(Optimizer):
    """p -= lr * g, optionally with momentum.

    MOMENTUM is a running average of past gradients, and the intuition that
    actually predicts its behaviour is a ravine: a long narrow valley where the
    gradient points mostly across the valley rather than along it. Plain SGD
    zig-zags between the walls; momentum cancels the oscillating component
    (it flips sign each step) and accumulates the consistent one (it does not).
    The demo builds exactly that ravine.
    """

    def __init__(self, parameters: Sequence[Tensor], lr: float = 0.01,
                 momentum: float = 0.0, weight_decay: float = 0.0,
                 nesterov: bool = False):
        super().__init__(parameters, lr)
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.nesterov = nesterov
        self.velocity: List[List[float]] = [[0.0] * len(p.data)
                                            for p in self.parameters]

    def step(self) -> None:
        self.steps += 1
        for index, (parameter, gradient) in enumerate(
                zip(self.parameters, self._gradients())):
            velocity = self.velocity[index]
            for i, g in enumerate(gradient):
                if self.weight_decay:
                    g += self.weight_decay * parameter.data[i]
                if self.momentum:
                    velocity[i] = self.momentum * velocity[i] + g
                    step = (g + self.momentum * velocity[i] if self.nesterov
                            else velocity[i])
                else:
                    step = g
                parameter.data[i] -= self.lr * step


class RMSProp(Optimizer):
    """Divide each parameter's step by the RMS of its recent gradients.

    This is the "per-parameter learning rate" idea on its own, without
    momentum. A parameter whose gradient has been consistently large gets a
    small step; one whose gradient has been tiny gets a large one. It fixes
    SGD's single-scale problem and does nothing about oscillation.
    """

    def __init__(self, parameters: Sequence[Tensor], lr: float = 0.01,
                 decay: float = 0.9, eps: float = 1e-8):
        super().__init__(parameters, lr)
        self.decay, self.eps = decay, eps
        self.squared: List[List[float]] = [[0.0] * len(p.data)
                                           for p in self.parameters]

    def step(self) -> None:
        self.steps += 1
        for index, (parameter, gradient) in enumerate(
                zip(self.parameters, self._gradients())):
            squared = self.squared[index]
            for i, g in enumerate(gradient):
                squared[i] = self.decay * squared[i] + (1 - self.decay) * g * g
                parameter.data[i] -= self.lr * g / (math.sqrt(squared[i])
                                                    + self.eps)


class Adam(Optimizer):
    """Momentum and RMSProp at once, plus the bias correction.

    THE BIAS CORRECTION is the part worth understanding rather than copying.
    Both running averages start at ZERO, so for the first several steps they
    are biased towards zero — badly, when beta2 is 0.999 and the average needs
    ~1000 steps to warm up. Dividing by (1 - beta^t) rescales them to what they
    would be if the average had already converged. Drop those two lines and the
    first hundred steps take almost no movement at all, which looks exactly
    like a learning rate that is too small.

    `decoupled=True` is AdamW. The difference is one line and it matters: with
    coupled decay the weight-decay term goes through the adaptive denominator,
    so parameters with small gradients decay LESS — the opposite of the intent.
    """

    def __init__(self, parameters: Sequence[Tensor], lr: float = 0.001,
                 beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8,
                 weight_decay: float = 0.0, decoupled: bool = False,
                 bias_correction: bool = True):
        super().__init__(parameters, lr)
        self.beta1, self.beta2, self.eps = beta1, beta2, eps
        self.weight_decay = weight_decay
        self.decoupled = decoupled
        self.bias_correction = bias_correction
        self.first: List[List[float]] = [[0.0] * len(p.data)
                                         for p in self.parameters]
        self.second: List[List[float]] = [[0.0] * len(p.data)
                                          for p in self.parameters]

    def step(self) -> None:
        self.steps += 1
        t = self.steps
        correction1 = (1 - self.beta1 ** t) if self.bias_correction else 1.0
        correction2 = (1 - self.beta2 ** t) if self.bias_correction else 1.0

        for index, (parameter, gradient) in enumerate(
                zip(self.parameters, self._gradients())):
            first, second = self.first[index], self.second[index]
            for i, g in enumerate(gradient):
                if self.weight_decay and not self.decoupled:
                    g += self.weight_decay * parameter.data[i]
                first[i] = self.beta1 * first[i] + (1 - self.beta1) * g
                second[i] = self.beta2 * second[i] + (1 - self.beta2) * g * g
                m_hat = first[i] / correction1
                v_hat = second[i] / correction2
                update = self.lr * m_hat / (math.sqrt(v_hat) + self.eps)
                if self.weight_decay and self.decoupled:
                    # AdamW: decay the WEIGHT directly, not the gradient, so it
                    # never passes through the adaptive denominator.
                    update += self.lr * self.weight_decay * parameter.data[i]
                parameter.data[i] -= update


def clip_grad_norm(parameters: Sequence[Tensor], max_norm: float) -> float:
    """Scale all gradients down if their combined norm exceeds max_norm.

    Note that it is the GLOBAL norm across every parameter, not per-tensor.
    Clipping per-tensor changes the DIRECTION of the update, which is a
    different optimiser rather than the same one taking a smaller step. The
    global version preserves the direction and shortens the step, which is what
    you actually want when one bad batch produces a gradient a thousand times
    the usual size.
    """
    total = 0.0
    for parameter in parameters:
        if parameter.grad:
            total += sum(g * g for g in parameter.grad)
    norm = math.sqrt(total)
    if norm > max_norm and norm > 0:
        scale = max_norm / norm
        for parameter in parameters:
            if parameter.grad:
                parameter.grad = [g * scale for g in parameter.grad]
    return norm


def cosine_schedule(step: int, total: int, base_lr: float,
                    warmup: int = 0, min_lr: float = 0.0) -> float:
    """Linear warmup, then a cosine decay to min_lr.

    The warmup is not decoration. Adam's second-moment estimate is meaningless
    for the first few dozen steps — it has seen almost no gradients — so a full
    learning rate applied to a noisy adaptive denominator is how large-model
    training diverges in the first minute. Warmup is the standard fix.
    """
    if warmup and step < warmup:
        return base_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    progress = min(1.0, max(0.0, progress))
    return min_lr + 0.5 * (base_lr - min_lr) * (1 + math.cos(math.pi * progress))




# ==========================================================================
# The four operations a transformer needs that an MLP does not
# ==========================================================================

def layer_norm(x: "Tensor", gain: "Tensor", bias: "Tensor",
               eps: float = 1e-5) -> "Tensor":
    """Normalise each ROW to zero mean and unit variance, then scale and shift.

    Per ROW, not per batch — that is the difference from batch norm and it is
    why transformers use this one. A row is one token's vector, so the
    statistics depend only on that token: no dependence on the other examples
    in the batch, which means inference on a batch of one behaves identically
    to inference on a batch of a thousand, and nothing has to be stored between
    training and serving.

    The backward pass is written out by hand rather than composed from mean and
    variance ops, because every element of a row affects every other element's
    output through the shared statistics. Composing it would build a large
    graph for what is three dot products.
    """
    rows, cols = _as_2d(x.shape)
    out_data = [0.0] * len(x.data)
    caches = []
    for r in range(rows):
        row = x.data[r * cols:(r + 1) * cols]
        mean = sum(row) / cols
        centred = [v - mean for v in row]
        variance = sum(v * v for v in centred) / cols
        inverse = 1.0 / math.sqrt(variance + eps)
        normalised = [v * inverse for v in centred]
        caches.append((normalised, inverse))
        for c in range(cols):
            out_data[r * cols + c] = normalised[c] * gain.data[c] + bias.data[c]

    out = Tensor(out_data, x.shape,
                 x.requires_grad or gain.requires_grad or bias.requires_grad,
                 (x, gain, bias), "layer_norm")

    def _backward() -> None:
        if out.grad is None:
            return
        gain_grad = [0.0] * cols
        bias_grad = [0.0] * cols
        x_grad = [0.0] * len(x.data)
        for r in range(rows):
            normalised, inverse = caches[r]
            g = out.grad[r * cols:(r + 1) * cols]
            for c in range(cols):
                gain_grad[c] += g[c] * normalised[c]
                bias_grad[c] += g[c]
            dn = [g[c] * gain.data[c] for c in range(cols)]
            mean_dn = sum(dn) / cols
            mean_dn_n = sum(dn[c] * normalised[c] for c in range(cols)) / cols
            for c in range(cols):
                x_grad[r * cols + c] = inverse * (
                    dn[c] - mean_dn - normalised[c] * mean_dn_n)
        x.accumulate(x_grad)
        gain.accumulate(gain_grad)
        bias.accumulate(bias_grad)

    out._backward = _backward
    return out


def embedding(table: "Tensor", indices: Sequence[int]) -> "Tensor":
    """Look up one row of `table` per index.

    The forward pass is a gather and costs nothing. The BACKWARD pass is a
    SCATTER-ADD, and the word "add" is the whole point: a token appearing five
    times in a batch contributes five gradients to the same row, and they must
    accumulate. Overwrite instead and only the last occurrence trains, which
    means common tokens — exactly the ones you have the most signal for — learn
    the least.
    """
    vocabulary, width = _as_2d(table.shape)
    data = []
    for index in indices:
        if not 0 <= index < vocabulary:
            raise IndexError(f"token id {index} outside vocabulary {vocabulary}")
        data.extend(table.data[index * width:(index + 1) * width])
    out = Tensor(data, (len(indices), width), table.requires_grad,
                 (table,), "embedding")

    def _backward() -> None:
        if out.grad is None:
            return
        grad = [0.0] * len(table.data)
        for position, index in enumerate(indices):
            base = index * width
            source = position * width
            for c in range(width):
                grad[base + c] += out.grad[source + c]     # ACCUMULATE
        table.accumulate(grad)

    out._backward = _backward
    return out


def slice_columns(x: "Tensor", start: int, stop: int) -> "Tensor":
    """Columns [start, stop) of every row — how a head takes its share.

    Multi-head attention is usually described as separate projections. In
    practice it is ONE projection to d_model followed by slicing, because one
    large matmul is far faster than h small ones. The heads are a view, not
    separate parameters.
    """
    rows, cols = _as_2d(x.shape)
    width = stop - start
    data = [x.data[r * cols + c] for r in range(rows) for c in range(start, stop)]
    out = Tensor(data, (rows, width), x.requires_grad, (x,), "slice")

    def _backward() -> None:
        if out.grad is None:
            return
        grad = [0.0] * len(x.data)
        for r in range(rows):
            for c in range(width):
                grad[r * cols + start + c] = out.grad[r * width + c]
        x.accumulate(grad)

    out._backward = _backward
    return out


def concat_columns(parts: Sequence["Tensor"]) -> "Tensor":
    """Glue heads back together side by side."""
    rows = _as_2d(parts[0].shape)[0]
    widths = [_as_2d(p.shape)[1] for p in parts]
    total = sum(widths)
    data = [0.0] * (rows * total)
    for r in range(rows):
        offset = 0
        for part, width in zip(parts, widths):
            for c in range(width):
                data[r * total + offset + c] = part.data[r * width + c]
            offset += width
    out = Tensor(data, (rows, total),
                 any(p.requires_grad for p in parts), tuple(parts), "concat")

    def _backward() -> None:
        if out.grad is None:
            return
        offset = 0
        for part, width in zip(parts, widths):
            grad = [0.0] * len(part.data)
            for r in range(rows):
                for c in range(width):
                    grad[r * width + c] = out.grad[r * total + offset + c]
            part.accumulate(grad)
            offset += width

    out._backward = _backward
    return out


def masked_softmax(scores: "Tensor", mask: Sequence[Sequence[bool]]
                   ) -> "Tensor":
    """Row-wise softmax with masked positions forced to zero probability.

    The mask is applied BEFORE the exponential, by setting those scores to
    -infinity. Applying it after — zeroing probabilities and renormalising —
    gives the same answer for the forward pass and a WRONG gradient, because
    the masked positions would still be part of the sum that softmax
    differentiates through.

    This is the causal mask, and it is the single thing standing between a
    language model and a model that has read the answer.
    """
    rows, cols = _as_2d(scores.shape)
    probabilities = [0.0] * (rows * cols)
    for r in range(rows):
        row = [scores.data[r * cols + c] if mask[r][c] else float("-inf")
               for c in range(cols)]
        finite = [v for v in row if v != float("-inf")]
        biggest = max(finite) if finite else 0.0
        exponentials = [math.exp(v - biggest) if v != float("-inf") else 0.0
                        for v in row]
        denominator = sum(exponentials) or 1.0
        for c in range(cols):
            probabilities[r * cols + c] = exponentials[c] / denominator

    out = Tensor(probabilities, scores.shape, scores.requires_grad,
                 (scores,), "masked_softmax")

    def _backward() -> None:
        if out.grad is None:
            return
        grad = [0.0] * len(scores.data)
        for r in range(rows):
            p = probabilities[r * cols:(r + 1) * cols]
            g = out.grad[r * cols:(r + 1) * cols]
            dot = sum(p[c] * g[c] for c in range(cols))
            for c in range(cols):
                grad[r * cols + c] = p[c] * (g[c] - dot) if mask[r][c] else 0.0
        scores.accumulate(grad)

    out._backward = _backward
    return out


def causal_mask(length: int) -> List[List[bool]]:
    """Position i may attend to positions 0..i, and no further."""
    return [[c <= r for c in range(length)] for r in range(length)]

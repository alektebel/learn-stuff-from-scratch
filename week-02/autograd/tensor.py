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

Learning Path — build in this order and test each step against
`numeric_gradient` before moving on:
1. backward() — the topological sort, and accumulate() rather than assign
2. add and mul, with _broadcast and _unbroadcast
3. relu, tanh, exp, log, and the reductions
4. matmul, whose backward is two more matmuls
5. softmax_cross_entropy, fused for both a numerical and an analytical reason
6. check_gradient against every one of them. A wrong gradient still trains,
   just worse, which is why the numerical oracle is the first thing to write.
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
        raise NotImplementedError

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
        raise NotImplementedError

    # -- element-wise -------------------------------------------------------

    def __add__(self, other: Any) -> "Tensor":
        raise NotImplementedError

    def __mul__(self, other: Any) -> "Tensor":
        raise NotImplementedError

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
        raise NotImplementedError

    def pow(self, exponent: float) -> "Tensor":
        raise NotImplementedError

    def exp(self) -> "Tensor":
        raise NotImplementedError

    def log(self) -> "Tensor":
        raise NotImplementedError

    def relu(self) -> "Tensor":
        raise NotImplementedError

    def tanh(self) -> "Tensor":
        raise NotImplementedError

    def sigmoid(self) -> "Tensor":
        raise NotImplementedError

    # -- reductions and reshaping ------------------------------------------

    def sum(self) -> "Tensor":
        raise NotImplementedError

    def mean(self) -> "Tensor":
        raise NotImplementedError

    def sum_rows(self) -> "Tensor":
        """Sum each row, giving (M, 1). Needed for softmax and for bias grads."""
        raise NotImplementedError

    def reshape(self, *shape: int) -> "Tensor":
        raise NotImplementedError

    def transpose(self) -> "Tensor":
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    def mse(self, target: "Tensor") -> "Tensor":
        raise NotImplementedError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _numel(shape: Shape) -> int:
    raise NotImplementedError


def _as_2d(shape: Shape) -> Tuple[int, int]:
    raise NotImplementedError


def _as_tensor(value: Any) -> Tensor:
    raise NotImplementedError


def _broadcast(left: Shape, right: Shape):
    """Return (result shape, index map for left, index map for right).

    Only two cases, and they are the two that matter:
      a scalar against anything            (a constant, a learning rate)
      a (1, N) row against an (M, N) matrix (a bias, on every row of a batch)
    Anything else raises, naming both shapes, rather than silently producing a
    plausible wrong answer — which is what a too-clever broadcasting rule does.
    """
    raise NotImplementedError


def _unbroadcast(gradient: List[float], out_shape: Shape, target: Shape,
                 index_map: Callable[[int], int]) -> List[float]:
    """Fold a gradient back onto the shape it was broadcast FROM.

    This is the half of broadcasting that people get wrong. A value that was
    reused across N rows in the forward pass receives N contributions in the
    backward pass, and they must be SUMMED. Return the gradient unfolded and
    every bias gradient is a factor of batch_size too small — the loss still
    goes down, just wrongly, which is the worst kind of bug.
    """
    raise NotImplementedError


def numeric_gradient(f: Callable[[List[float]], float], values: List[float],
                     epsilon: float = 1e-5) -> List[float]:
    """Central differences. The oracle every autograd implementation needs.

    Analytic gradients are easy to get subtly wrong in ways that still train —
    a factor of batch_size here, a missing term there. Comparing against a
    numerical estimate catches all of it, and it is the first test to write.
    """
    raise NotImplementedError


def check_gradient(build: Callable[[List[Tensor]], Tensor],
                   inputs: List[Tensor], tolerance: float = 1e-4
                   ) -> Tuple[bool, float]:
    """Compare this engine's gradients against central differences."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. tanh(x*y + x) at x=3, y=4, with dz/dx and dz/dy beside the values you
       worked out by hand.

    2. A table of expressions with the max relative error against
       `numeric_gradient`. Include `x * x + x` — a tensor used TWICE — because
       that is what catches a broken topological sort: its gradient is the SUM
       of two contributions, and running a node's backward before both have
       arrived is quietly, slightly wrong forever.

    3. A bias broadcast over a batch, showing the bias gradient equals the
       batch size. Broadcasting forwards is summing backwards, and skipping the
       fold makes every bias gradient a factor of batch_size too small.

    4. Forward against backward op counts across parameter counts, showing the
       ratio is ~2x REGARDLESS of size. Forward-mode would be one pass per
       parameter — that asymmetry is why training is possible.

    5. Three backward passes without zero_grad(), showing the gradient
       accumulating, then the same after zero_grad().
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()

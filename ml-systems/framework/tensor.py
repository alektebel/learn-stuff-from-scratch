"""
Tensor with reverse-mode autodiff
=================================
Book: Vol I ch. 7 (Frameworks) and ch. 5 (NN computation). TinyTorch modules 01 and 06.

A Tensor wraps a numpy array. When an operation involves a tensor that requires
gradients, the result remembers its parents and a closure that pushes the result's
gradient back to them. `backward()` orders the graph topologically and runs those
closures from the output to the inputs.

DESIGN DECISION - store the graph eagerly (define-by-run) or build it first?
Building the graph while computing (PyTorch, this file) lets ordinary Python control
flow decide the graph and makes debugging trivial: every intermediate is a real value.
A static graph (TF1, XLA) can be optimised as a whole before running. Chosen: eager,
because the subject is how gradients flow, not graph compilation.

DESIGN DECISION - recursion or an explicit stack for the topological sort?
A recursive DFS is three lines and dies with RecursionError on a 2,000-step chain (an
unrolled RNN). Chosen: an explicit stack. Step 5 of check.py builds a 10,000-op chain.

Broadcasting is the classic trap: if a (3,) bias was added to a (32, 3) batch, its
gradient arrives with shape (32, 3) and must be SUMMED back down to (3,). `unbroadcast`
does that, and every binary op's backward must call it.

Everything is float64: gradient checks by finite differences need the precision.
float32 halves memory and is what real training uses; profile.py counts that cost.
"""

from __future__ import annotations

import numpy as np


def unbroadcast(grad: np.ndarray, shape: tuple) -> np.ndarray:
    """Sum `grad` down to `shape`, undoing numpy broadcasting."""
    # TODO: First sum away leading axes grad has and `shape` does not. Then, for every axis where shape has size 1 but grad does not, sum it with keepdims=True.
    raise NotImplementedError("unbroadcast")


class Tensor:
    def __init__(self, data, requires_grad: bool = False, _parents: tuple = (), _op: str = ""):
        self.data = np.array(data, dtype=np.float64)
        self.requires_grad = requires_grad
        self.grad: np.ndarray | None = None
        self._parents = _parents
        self._backward = lambda: None
        self._op = _op

    # -- basics ---------------------------------------------------------------------------
    @property
    def shape(self) -> tuple:
        return self.data.shape

    @property
    def ndim(self) -> int:
        return self.data.ndim

    def numpy(self) -> np.ndarray:
        return self.data

    def item(self) -> float:
        return float(self.data)

    def __repr__(self) -> str:
        return f"Tensor({self.data!r}{', requires_grad=True' if self.requires_grad else ''})"

    @staticmethod
    def _wrap(x) -> "Tensor":
        return x if isinstance(x, Tensor) else Tensor(x)

    def _make(self, data, parents: tuple, op: str) -> "Tensor":
        rg = any(p.requires_grad for p in parents)
        return Tensor(data, requires_grad=rg, _parents=parents if rg else (), _op=op)

    def _accumulate(self, g: np.ndarray) -> None:
        # TODO: Skip tensors that do not require grad. Reduce g to this tensor's shape with unbroadcast, then ADD it to self.grad (a tensor used twice receives two contributions).
        raise NotImplementedError("Tensor._accumulate")

    # -- arithmetic -----------------------------------------------------------------------
    def __add__(self, other):
        # TODO: Wrap `other`, build the result with self._make(..., (self, other), '+'), and give it a backward closure. d(a+b)/da = 1: pass out.grad to both parents.
        raise NotImplementedError("Tensor.__add__")
    def __mul__(self, other):
        # TODO: Forward a*b. Backward: each parent receives out.grad times the OTHER operand's data.
        raise NotImplementedError("Tensor.__mul__")
    def __pow__(self, exponent: float):
        # TODO: Scalar exponent only. d(x^k)/dx = k * x^(k-1).
        raise NotImplementedError("Tensor.__pow__")

    def __matmul__(self, other):
        # TODO: Require ndim >= 2. For C = A @ B: dA = dC @ B^T and dB = A^T @ dC, transposing the LAST two axes (np.swapaxes) so batched matmul works.
        raise NotImplementedError("Tensor.__matmul__")
    def __neg__(self):
        return self * -1.0

    def __sub__(self, other):
        return self + (-self._wrap(other))

    def __rsub__(self, other):
        return self._wrap(other) + (-self)

    def __truediv__(self, other):
        return self * (self._wrap(other) ** -1.0)

    def __rtruediv__(self, other):
        return self._wrap(other) * (self ** -1.0)

    __radd__ = __add__
    __rmul__ = __mul__

    # -- reductions and shape -------------------------------------------------------------
    def sum(self, axis=None, keepdims: bool = False):
        # TODO: Backward: the gradient of a sum is 1 for every summed element. If an axis was removed (keepdims=False), restore it with np.expand_dims, then np.broadcast_to the input shape.
        raise NotImplementedError("Tensor.sum")
        return self.sum(axis=axis, keepdims=keepdims) * (1.0 / n)

    def reshape(self, *shape):
        # TODO: Backward: reshape the incoming gradient back to the input's shape.
        raise NotImplementedError("Tensor.reshape")

    def transpose(self, *axes):
        # TODO: Backward: transpose the gradient with the INVERSE permutation (np.argsort(axes)); no axes means a full reversal, which is its own inverse.
        raise NotImplementedError("Tensor.transpose")
    @property
    def T(self):
        return self.transpose()

    # -- elementwise functions ------------------------------------------------------------
    def exp(self):
        # TODO: d e^x / dx = e^x: keep the forward result and reuse it.
        raise NotImplementedError("Tensor.exp")

    def log(self):
        # TODO: d log x / dx = 1 / x.
        raise NotImplementedError("Tensor.log")

    def relu(self):
        # TODO: Forward max(x, 0). Backward passes the gradient where x > 0, zero elsewhere.
        raise NotImplementedError("Tensor.relu")

    def sigmoid(self):
        # stable: never exponentiate a large positive number
        # TODO: Never compute exp of a large positive number. Use e = exp(-|x|): sigmoid = 1/(1+e) for x >= 0 and e/(1+e) for x < 0. Backward: s * (1 - s).
        raise NotImplementedError("Tensor.sigmoid")

    def tanh(self):
        # TODO: Backward: 1 - tanh(x)^2.
        raise NotImplementedError("Tensor.tanh")

    # -- autodiff -------------------------------------------------------------------------
    def backward(self, grad=None) -> None:
        # TODO: Seed the output grad (ones for a scalar). Build a topological order with an EXPLICIT stack, not recursion (a 10,000-op chain must work). Run each node's _backward from the output back to the inputs, skipping nodes that are constants or received no gradient.
        raise NotImplementedError("Tensor.backward")

    def zero_grad(self) -> None:
        self.grad = None


if __name__ == "__main__":
    x = Tensor([[1.0, 2.0, 3.0]], requires_grad=True)
    w = Tensor([[0.5], [-1.0], [2.0]], requires_grad=True)
    y = (x @ w).relu().sum()
    y.backward()
    print("y =", y.item(), " dy/dw =", w.grad.ravel(), " dy/dx =", x.grad.ravel())

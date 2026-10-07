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
    while grad.ndim > len(shape):          # leading dimensions that were added
        grad = grad.sum(axis=0)
    for axis, size in enumerate(shape):    # dimensions that were stretched from 1
        if size == 1 and grad.shape[axis] != 1:
            grad = grad.sum(axis=axis, keepdims=True)
    return grad


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
        if not self.requires_grad:
            return
        g = unbroadcast(g, self.shape)
        self.grad = g.copy() if self.grad is None else self.grad + g

    # -- arithmetic -----------------------------------------------------------------------
    def __add__(self, other):
        other = self._wrap(other)
        out = self._make(self.data + other.data, (self, other), "+")

        def backward():
            self._accumulate(out.grad)
            other._accumulate(out.grad)
        out._backward = backward
        return out

    def __mul__(self, other):
        other = self._wrap(other)
        out = self._make(self.data * other.data, (self, other), "*")

        def backward():
            self._accumulate(out.grad * other.data)
            other._accumulate(out.grad * self.data)
        out._backward = backward
        return out

    def __pow__(self, exponent: float):
        if isinstance(exponent, Tensor):
            raise TypeError("only scalar exponents are supported")
        out = self._make(self.data ** exponent, (self,), f"**{exponent}")

        def backward():
            self._accumulate(out.grad * exponent * self.data ** (exponent - 1))
        out._backward = backward
        return out

    def __matmul__(self, other):
        other = self._wrap(other)
        if self.ndim < 2 or other.ndim < 2:
            raise ValueError("matmul needs at least 2-D operands; reshape vectors to (1, n) or (n, 1)")
        out = self._make(self.data @ other.data, (self, other), "@")

        def backward():
            self._accumulate(out.grad @ np.swapaxes(other.data, -1, -2))
            other._accumulate(np.swapaxes(self.data, -1, -2) @ out.grad)
        out._backward = backward
        return out

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
        out = self._make(self.data.sum(axis=axis, keepdims=keepdims), (self,), "sum")

        def backward():
            g = out.grad
            if axis is not None and not keepdims:
                g = np.expand_dims(g, axis)
            self._accumulate(np.broadcast_to(g, self.shape))
        out._backward = backward
        return out

    def mean(self, axis=None, keepdims: bool = False):
        n = self.data.size if axis is None else np.prod([self.shape[a] for a in np.atleast_1d(axis)])
        return self.sum(axis=axis, keepdims=keepdims) * (1.0 / n)

    def reshape(self, *shape):
        out = self._make(self.data.reshape(*shape), (self,), "reshape")

        def backward():
            self._accumulate(out.grad.reshape(self.shape))
        out._backward = backward
        return out

    def transpose(self, *axes):
        axes = axes or None
        out = self._make(np.transpose(self.data, axes), (self,), "T")

        def backward():
            inverse = None if axes is None else np.argsort(axes)
            self._accumulate(np.transpose(out.grad, inverse))
        out._backward = backward
        return out

    @property
    def T(self):
        return self.transpose()

    # -- elementwise functions ------------------------------------------------------------
    def exp(self):
        e = np.exp(self.data)
        out = self._make(e, (self,), "exp")

        def backward():
            self._accumulate(out.grad * e)
        out._backward = backward
        return out

    def log(self):
        out = self._make(np.log(self.data), (self,), "log")

        def backward():
            self._accumulate(out.grad / self.data)
        out._backward = backward
        return out

    def relu(self):
        out = self._make(np.maximum(self.data, 0.0), (self,), "relu")

        def backward():
            self._accumulate(out.grad * (self.data > 0))
        out._backward = backward
        return out

    def sigmoid(self):
        # stable: never exponentiate a large positive number
        x = self.data
        e = np.exp(-np.abs(x))
        s = np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))
        out = self._make(s, (self,), "sigmoid")

        def backward():
            self._accumulate(out.grad * s * (1.0 - s))
        out._backward = backward
        return out

    def tanh(self):
        t = np.tanh(self.data)
        out = self._make(t, (self,), "tanh")

        def backward():
            self._accumulate(out.grad * (1.0 - t * t))
        out._backward = backward
        return out

    # -- autodiff -------------------------------------------------------------------------
    def backward(self, grad=None) -> None:
        if not self.requires_grad:
            raise RuntimeError("backward() on a tensor that does not require grad")
        if grad is None:
            if self.data.size != 1:
                raise RuntimeError("backward() without an explicit grad needs a scalar output")
            grad = np.ones_like(self.data)
        order, seen, stack = [], set(), [(self, False)]
        while stack:  # iterative post-order DFS: parents before children in `order`
            node, expanded = stack.pop()
            if expanded:
                order.append(node)
                continue
            if id(node) in seen:
                continue
            seen.add(id(node))
            stack.append((node, True))
            for p in node._parents:
                if id(p) not in seen:
                    stack.append((p, False))
        self.grad = np.array(grad, dtype=np.float64)
        for node in reversed(order):
            if node.requires_grad and node.grad is not None:  # constants in the graph get no grad
                node._backward()

    def zero_grad(self) -> None:
        self.grad = None


if __name__ == "__main__":
    x = Tensor([[1.0, 2.0, 3.0]], requires_grad=True)
    w = Tensor([[0.5], [-1.0], [2.0]], requires_grad=True)
    y = (x @ w).relu().sum()
    y.backward()
    print("y =", y.item(), " dy/dw =", w.grad.ravel(), " dy/dx =", x.grad.ravel())

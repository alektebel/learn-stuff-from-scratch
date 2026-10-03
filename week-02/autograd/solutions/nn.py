"""
nn — layers, and what a "module" actually is. Complete Solution.

A layer is two things: some tensors that need gradients, and a function that
uses them. That is the whole abstraction, and everything else `nn.Module` does
is bookkeeping around those two facts.

DESIGN DECISION — why does a Module exist at all, when a function would do?
  `def linear(x, w, b): return x @ w + b` is a layer. It is also unusable in a
  network, because the optimiser needs to find `w` and `b`, the checkpointer
  needs to name them, and the training loop needs to zero them. A bare function
  hands you no way to enumerate its own state.
  CHOSEN: Module owns `parameters()`, recursively. Everything downstream —
  optimisers, `zero_grad`, saving, freezing a layer — is one traversal of that
  list. Note what this means: a tensor that is not reachable from
  `parameters()` never gets updated, and the symptom is a network that trains
  but plateaus early, with no error anywhere.

DESIGN DECISION — how are weights initialised?
  Zeros are the obvious choice and they are catastrophic: every unit in a layer
  computes the same thing, receives the same gradient, and stays identical
  forever. The layer has one effective neuron no matter how wide it is.
  CHOSEN: scaled random init — He for ReLU, Xavier for tanh — with the scale
  derived from fan-in rather than picked. The demo measures what happens at the
  wrong scale, because "initialisation matters" is unconvincing until you watch
  a 6-layer network's activations decay to 1e-8 by the output.

DESIGN DECISION — where does the nonlinearity go?
  It has to go somewhere, and the demo shows why: stack two Linear layers with
  nothing between them and you have exactly one Linear layer, because a
  composition of affine maps is an affine map. Depth without a nonlinearity is
  not depth. This is measured below rather than asserted.
"""

import math
import random
from typing import Any, Callable, Iterator, List, Optional, Sequence

from tensor import Tensor


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


def _demo() -> None:
    from tensor import check_gradient

    print("=" * 74)
    print("nn — layers, and the two decisions inside every one")
    print("=" * 74)

    print("\n1. A module knows its own parameters")
    print("-" * 74)
    rng = random.Random(1)
    model = Sequential(Linear(8, 16, rng=rng), ReLU(),
                       Linear(16, 16, rng=rng), ReLU(),
                       Linear(16, 3, activation="linear", rng=rng))
    print(f"  {model}")
    print(f"  {len(model.parameters())} parameter tensors, "
          f"{model.num_parameters():,} scalars")
    print("  Every one of those is reachable from parameters(). A tensor that")
    print("  is not is a tensor the optimiser never updates — no error, just a")
    print("  network that plateaus early.")

    print("\n2. Gradients through the whole stack, checked numerically")
    print("-" * 74)
    x = Tensor.randn(4, 8, rng=rng)
    targets = [0, 1, 2, 1]

    def build(tensors: List[Tensor]) -> Tensor:
        small = Sequential(Linear(3, 4, rng=random.Random(2)), Tanh(),
                           Linear(4, 3, activation="linear",
                                  rng=random.Random(3)))
        small.layers[0].weight = tensors[0]
        small.layers[2].weight = tensors[1]
        return small(tensors[2]).softmax_cross_entropy([0, 2])

    ok, worst = check_gradient(build, [Tensor.randn(3, 4, rng=rng),
                                       Tensor.randn(4, 3, rng=rng),
                                       Tensor.randn(2, 3, rng=rng)])
    print(f"  two Linear layers + tanh + cross entropy: max relative error "
          f"{worst:.2e}  {'OK' if ok else 'WRONG'}")

    print("\n3. Depth without a nonlinearity is not depth")
    print("-" * 74)
    deep_linear = Sequential(*[Linear(6, 6, activation="linear",
                                      rng=random.Random(n)) for n in range(5)])
    x = Tensor.randn(1, 6, rng=random.Random(9))
    # Collapse the five weight matrices into one by multiplying them together.
    collapsed = deep_linear.layers[0].weight
    for layer in deep_linear.layers[1:]:
        collapsed = collapsed @ layer.weight
    five_layers = deep_linear(x)
    one_layer = x @ collapsed
    difference = max(abs(a - b) for a, b in zip(five_layers.data, one_layer.data))
    print(f"  5 stacked Linear layers, no activation: {five_layers.data[:3]}")
    print(f"  one matrix, their product:              {one_layer.data[:3]}")
    print(f"  max difference: {difference:.2e}")
    print("  They are the SAME FUNCTION. A composition of affine maps is an")
    print("  affine map, so five layers have exactly the expressive power of")
    print("  one. The nonlinearity is not a detail of the architecture — it is")
    print("  the only reason depth means anything.")

    print("\n4. Initialisation, measured through six layers")
    print("-" * 74)
    print(f"    {'init scale':<22}" + "".join(f"L{n + 1:<9}" for n in range(6)))
    x = Tensor.randn(64, 32, rng=random.Random(4))
    for label, scale in (("too small (x0.1)", 0.1),
                         ("He: sqrt(2/fan_in)", None),
                         ("too large (x3)", 3.0)):
        layers = []
        for _ in range(6):
            layer = Linear(32, 32, rng=random.Random(7))
            if scale is not None:
                layer.weight = Tensor([v * scale for v in layer.weight.data],
                                      layer.weight.shape, requires_grad=True)
            layers += [layer, ReLU()]
        network = Sequential(*layers)
        outputs = network.activations(x)
        every_other = [outputs[i] for i in range(1, len(outputs), 2)]
        stds = [_std(t.data) for t in every_other]
        print(f"    {label:<22}" + "".join(f"{s:<10.2e}" for s in stds))
    print("  Too small and the signal is 1e-8 by layer 6: the gradient reaching")
    print("  layer 1 is that small too, so the early layers never learn.")
    print("  Too large and it grows without bound until the loss is inf.")
    print("  He init keeps the variance roughly flat, which is what it was")
    print("  derived to do — the factor of 2 pays back exactly the half of the")
    print("  signal that ReLU throws away.")

    print("\n5. Dropout scales during training so inference needs no special case")
    print("-" * 74)
    layer = Dropout(0.5, rng=random.Random(3))
    x = Tensor.full(1.0, 1, 2000)
    layer.training = True
    train_out = layer(x)
    layer.training = False
    eval_out = layer(x)
    print(f"  input mean {sum(x.data) / len(x.data):.3f}")
    print(f"  training mean {sum(train_out.data) / len(train_out.data):.3f}  "
          f"({train_out.data.count(0.0)} of {len(train_out.data)} zeroed, "
          f"the rest scaled by 1/0.5)")
    print(f"  eval mean     {sum(eval_out.data) / len(eval_out.data):.3f}")
    print("  The two means match, which is the point. Zero half the units and")
    print("  do nothing else, and inference sees activations twice as large as")
    print("  the next layer was trained for. Scaling during training — inverted")
    print("  dropout — makes the eval path a plain identity.")

    print("\n" + "=" * 74)
    print("Next: optim.py decides what to do with the gradients.")
    print("=" * 74)


def _std(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


if __name__ == "__main__":
    _demo()

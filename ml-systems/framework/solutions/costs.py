"""
Counting the cost: parameters, FLOPs, memory
============================================
Book: Vol I ch. 5 (NN computation) and ch. 8 (Training); TinyTorch module 14 (Profiling).

The question a systems engineer asks about a model before running it is "what will this
cost?" For an MLP of Linear layers the answers are closed-form:

  parameters      sum over layers of in*out + out
  forward FLOPs   2 * batch * in * out per Linear (one multiply and one add per weight
                  per example; bias adds and activations are lower order and ignored)
  training FLOPs  ~3x forward: backward computes two matmuls per layer (input grad and
                  weight grad), each as large as the forward one
  memory          weights + gradients + optimizer state + activations kept for backward

Optimizer state is the term people forget: Adam keeps two buffers per parameter, so
training with Adam needs about 4x the parameter memory before a single activation is
stored (weights, grads, m, v). check.py compares these formulas with what the code
actually allocates.
"""

from __future__ import annotations

from nn import Linear, Module, Sequential


def linear_layers(model: Module) -> list[Linear]:
    if isinstance(model, Linear):
        return [model]
    if isinstance(model, Sequential):
        return [l for layer in model.layers for l in linear_layers(layer)]
    return []


def count_params(model: Module) -> int:
    return sum(p.data.size for p in model.parameters())


def forward_flops(model: Module, batch: int) -> int:
    return sum(2 * batch * l.in_features * l.out_features for l in linear_layers(model))


def training_flops(model: Module, batch: int) -> int:
    return 3 * forward_flops(model, batch)


def activation_elements(model: Module, batch: int) -> int:
    """Elements of every Linear output that backward needs to keep (the input to the
    next layer); activations' own outputs are counted once, the same size."""
    return sum(batch * l.out_features for l in linear_layers(model))


def training_memory_bytes(model: Module, batch: int, optimizer: str = "adam",
                          bytes_per_element: int = 8) -> dict:
    p = count_params(model)
    state = {"sgd": 0, "momentum": 1, "adam": 2}[optimizer]
    out = {
        "weights": p * bytes_per_element,
        "gradients": p * bytes_per_element,
        "optimizer_state": state * p * bytes_per_element,
        "activations": activation_elements(model, batch) * bytes_per_element,
    }
    out["total"] = sum(out.values())
    return out


if __name__ == "__main__":
    from train import mlp
    m = mlp([784, 512, 512, 10])
    print(f"MLP 784-512-512-10: {count_params(m):,} parameters, "
          f"{forward_flops(m, 64) / 1e6:.1f} MFLOPs forward at batch 64")
    for bpe, name in ((8, "float64"), (4, "float32"), (2, "bf16")):
        mem = training_memory_bytes(m, 64, "adam", bpe)
        print(f"  Adam, {name:7s}: {mem['total'] / 2**20:6.1f} MiB "
              f"(optimizer state {mem['optimizer_state'] / 2**20:.1f} MiB)")

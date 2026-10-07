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
    # TODO: Sum of the sizes of every parameter array.
    raise NotImplementedError("count_params")


def forward_flops(model: Module, batch: int) -> int:
    # TODO: 2 * batch * in * out per Linear layer (multiply + add per weight per example).
    raise NotImplementedError("forward_flops")


def training_flops(model: Module, batch: int) -> int:
    # TODO: Backward does two matmuls per layer, each as large as the forward one: about 3x forward in total.
    raise NotImplementedError("training_flops")


def activation_elements(model: Module, batch: int) -> int:
    """Elements of every Linear output that backward needs to keep (the input to the
    next layer); activations' own outputs are counted once, the same size."""
    # TODO: batch * out_features summed over Linear layers.
    raise NotImplementedError("activation_elements")


def training_memory_bytes(model: Module, batch: int, optimizer: str = "adam",
                          bytes_per_element: int = 8) -> dict:
    # TODO: weights + gradients (one copy each) + optimizer state (0, 1 or 2 copies for sgd / momentum / adam) + activations, each times bytes_per_element. Return a dict with those keys and 'total'.
    raise NotImplementedError("training_memory_bytes")


if __name__ == "__main__":
    from train import mlp
    m = mlp([784, 512, 512, 10])
    print(f"MLP 784-512-512-10: {count_params(m):,} parameters, "
          f"{forward_flops(m, 64) / 1e6:.1f} MFLOPs forward at batch 64")
    for bpe, name in ((8, "float64"), (4, "float32"), (2, "bf16")):
        mem = training_memory_bytes(m, 64, "adam", bpe)
        print(f"  Adam, {name:7s}: {mem['total'] / 2**20:6.1f} MiB "
              f"(optimizer state {mem['optimizer_state'] / 2**20:.1f} MiB)")

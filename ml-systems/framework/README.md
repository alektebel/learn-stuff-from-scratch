# Framework from scratch — part 1 of 3

A small PyTorch-like framework on numpy: tensors with reverse-mode autodiff, layers,
losses, optimizers, a data loader, a training loop, and a cost model. It ends by
replaying three milestones in the history of neural networks. Book: Vol I chapters 4-8;
TinyTorch modules 01-08 and 14.

```bash
cd ml-systems/framework
python3 check.py          # what to build next
```

| Step | File | You build | Check that keeps you honest |
|---|---|---|---|
| 1-6 | `tensor.py` | ops, broadcasting, autograd, stable sigmoid | finite-difference gradcheck on every op; a 10,000-op chain (recursion dies); a constant inside the graph |
| 7 | `nn.py` | Module, Linear, init, Sequential | He-initialised activations keep their variance through 10 ReLU layers |
| 8-9 | `losses.py` | log-softmax, cross-entropy, MSE, BCE on logits | logits of ±1000 without overflow; d CE / d logits = (softmax - onehot) / N |
| 10-11 | `optim.py` | SGD + momentum, Adam | Adam's first step moves exactly `lr` (bias correction) |
| 12 | `data.py` | DataLoader | same seed, same order; every example once per epoch |
| 13-15 | `train.py` | training loop | **1958** a perceptron separates blobs; **1969** it fails on XOR; **1986** an MLP solves XOR; 3-class spirals ≥ 95% |
| 16 | `costs.py` | parameters, FLOPs, training memory | the memory formula must equal the bytes the code really allocates |

Requires Python 3.10+ and numpy. The whole check runs in about 5 seconds.

**The checker was mutation-tested.** Nine typical framework bugs were planted in copies of
the solutions, and each is caught by its step: no unbroadcast (3), wrong matmul gradient
(4), gradients overwritten instead of accumulated (5), naive sigmoid (6), init variance
1/fan_in (7), log-softmax without the max shift (8), Adam without bias correction (11),
unseeded shuffle (12), Adam state counted once (16).

## Questions to answer before reading the solutions

1. Why must `backward()` use an explicit stack? Build the failing case with recursion.
2. Adding a (3,) bias to a (32, 3) batch: what shape does the bias gradient arrive in,
   and why is summing over the batch the correct reduction, not averaging?
3. Why is the first Adam step exactly `lr` in size, whatever the gradient?
4. `costs.py` says Adam training needs ~4x the parameter memory before activations.
   For a 7B-parameter model in bf16, how many GB is that? Does it fit on one 80 GB GPU?
5. The 1969 milestone: is it the model or the optimizer that fails on XOR? How would you
   prove it?

## Parts 2 and 3 (planned)

- **Part 2:** convolutions (im2col), pooling, a CNN on a small image task (milestone 1998),
  then a transformer trained end to end on this framework (milestone 2017).
- **Part 3:** profiling, quantization (int8, per-tensor vs per-channel), pruning,
  kernel fusion on CPU, and a benchmarking harness with confidence intervals (milestone 2018).

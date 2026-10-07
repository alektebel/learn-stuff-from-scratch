"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "tensor.py": {
  "unbroadcast": "First sum away leading axes grad has and `shape` does not. Then, for every axis where shape has size 1 but grad does not, sum it with keepdims=True.",
  "Tensor._accumulate": "Skip tensors that do not require grad. Reduce g to this tensor's shape with unbroadcast, then ADD it to self.grad (a tensor used twice receives two contributions).",
  "Tensor.__add__": "Wrap `other`, build the result with self._make(..., (self, other), '+'), and give it a backward closure. d(a+b)/da = 1: pass out.grad to both parents.",
  "Tensor.__mul__": "Forward a*b. Backward: each parent receives out.grad times the OTHER operand's data.",
  "Tensor.__pow__": "Scalar exponent only. d(x^k)/dx = k * x^(k-1).",
  "Tensor.__matmul__": "Require ndim >= 2. For C = A @ B: dA = dC @ B^T and dB = A^T @ dC, transposing the LAST two axes (np.swapaxes) so batched matmul works.",
  "Tensor.sum": "Backward: the gradient of a sum is 1 for every summed element. If an axis was removed (keepdims=False), restore it with np.expand_dims, then np.broadcast_to the input shape.",
  "Tensor.reshape": "Backward: reshape the incoming gradient back to the input's shape.",
  "Tensor.transpose": "Backward: transpose the gradient with the INVERSE permutation (np.argsort(axes)); no axes means a full reversal, which is its own inverse.",
  "Tensor.exp": "d e^x / dx = e^x: keep the forward result and reuse it.",
  "Tensor.log": "d log x / dx = 1 / x.",
  "Tensor.relu": "Forward max(x, 0). Backward passes the gradient where x > 0, zero elsewhere.",
  "Tensor.sigmoid": "Never compute exp of a large positive number. Use e = exp(-|x|): sigmoid = 1/(1+e) for x >= 0 and e/(1+e) for x < 0. Backward: s * (1 - s).",
  "Tensor.tanh": "Backward: 1 - tanh(x)^2.",
  "Tensor.backward": "Seed the output grad (ones for a scalar). Build a topological order with an EXPLICIT stack, not recursion (a 10,000-op chain must work). Run each node's _backward from the output back to the inputs, skipping nodes that are constants or received no gradient.",
 },
 "nn.py": {
  "Module.parameters": "Walk vars(self) recursively: collect Parameter objects, descend into Modules, lists and tuples. Return each Parameter once (track ids).",
  "Linear.__init__": "Weights (in, out) drawn from N(0, std): He std = sqrt(2/in), Xavier std = sqrt(2/(in+out)). Bias zeros of shape (1, out). Store in_features and out_features.",
  "Linear.forward": "x @ W + b. Broadcasting adds the bias to every row.",
  "log_softmax": "Subtract the row max as a CONSTANT Tensor (no gradient through it), then z - log(sum(exp(z))) along the axis with keepdims=True.",
 },
 "losses.py": {
  "mse_loss": "Mean of the squared difference.",
  "cross_entropy": "Validate labels. Build a one-hot (N, C) array; the loss is -sum(log_softmax(logits) * one_hot) / N. Never take log of softmax probabilities.",
  "binary_cross_entropy_with_logits": "Mean of softplus(x) - t*x, with softplus(x) = relu(x) + log(1 + exp(-|x|)). Build |x| from Tensor ops (relu(x) + relu(-x)) so the gradient flows; it must equal sigmoid(x) - t.",
 },
 "optim.py": {
  "SGD.step": "For each parameter with a grad: g = grad + weight_decay * w. With momentum: v = momentum * v + g, use v. Then w -= lr * g. Update p.data in place.",
  "Adam.step": "t += 1. m = b1*m + (1-b1)*g; v = b2*v + (1-b2)*g^2; m_hat = m/(1-b1^t); v_hat = v/(1-b2^t); w -= lr * m_hat / (sqrt(v_hat) + eps).",
 },
 "data.py": {
  "DataLoader.__len__": "Number of batches: floor(n / batch) with drop_last, ceil otherwise.",
  "DataLoader.__iter__": "Permutation from self._rng when shuffling (seeded: reproducible), arange otherwise. Yield dataset[index slice] per batch; skip a short last batch if drop_last.",
 },
 "train.py": {
  "fit": "Adam over model.parameters(); a shuffled DataLoader; per batch: forward, loss (ce or bce), zero_grad, backward, step. Return the mean loss per epoch.",
  "accuracy": "Eval mode; argmax over classes, or logit > 0 when there is one output column.",
 },
 "costs.py": {
  "count_params": "Sum of the sizes of every parameter array.",
  "forward_flops": "2 * batch * in * out per Linear layer (multiply + add per weight per example).",
  "training_flops": "Backward does two matmuls per layer, each as large as the forward one: about 3x forward in total.",
  "activation_elements": "batch * out_features summed over Linear layers.",
  "training_memory_bytes": "weights + gradients (one copy each) + optimizer state (0, 1 or 2 copies for sgd / momentum / adam) + activations, each times bytes_per_element. Return a dict with those keys and 'total'.",
 },
}

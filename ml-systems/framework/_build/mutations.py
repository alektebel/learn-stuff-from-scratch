"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
 ("no unbroadcast", "tensor.py", "        g = unbroadcast(g, self.shape)\n", "", "3"),
 ("matmul grad transposed wrong", "tensor.py", "other._accumulate(np.swapaxes(self.data, -1, -2) @ out.grad)", "other._accumulate(out.grad.sum() * np.ones_like(other.data))", "4"),
 ("grad overwritten, not accumulated", "tensor.py", "self.grad = g.copy() if self.grad is None else self.grad + g", "self.grad = g.copy()", "5"),
 ("naive sigmoid", "tensor.py", "        s = np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))", "        s = 1.0 / (1.0 + np.exp(-x))", "6"),
 ("init variance 1/fan_in", "nn.py", "std = np.sqrt(2.0 / in_features)", "std = np.sqrt(1.0 / in_features)", "7"),
 ("log_softmax without shift", "nn.py", "    shift = Tensor(logits.data.max(axis=axis, keepdims=True))", "    shift = Tensor(0.0)", "8"),
 ("Adam without bias correction", "optim.py", "            m_hat = self.m[i] / (1 - self.b1 ** self.t)\n            v_hat = self.v[i] / (1 - self.b2 ** self.t)", "            m_hat = self.m[i]\n            v_hat = self.v[i]", "11"),
 ("unseeded shuffle", "data.py", "order = self._rng.permutation(n)", "order = np.random.permutation(n)", "12"),
 ("Adam state counted once", "costs.py", '{"sgd": 0, "momentum": 1, "adam": 2}', '{"sgd": 0, "momentum": 1, "adam": 1}', "16"),
]

"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from the PRML neural-networks node is listed, so make_templates
stubs it and replaces its body with `raise NotImplementedError`. The elementwise
nonlinearities, the nested-list parameter helpers (`make_weights`, `flatten`,
`unflatten`, `_sizes`, `_copy`, `_tvec`) and the demo are left implemented: they are
infrastructure the exercise stands on, not the backpropagation itself. `_sample_jacobians`
is graded because the residual Jacobian is the heart of the outer-product Hessian.
"""

HINTS = {
 "neural.py": {
  "forward":
      "For each input x: z1 = W1 x + b1 (H values), a1 = tanh(z1), y = W2 a1 + b2 "
      "(K values). Return {'z1': [...], 'a1': [...], 'z2': [...], 'y': [...]} with one "
      "entry per sample so the loss and backprop can read the activations back.",
  "loss":
      "Call forward, then E = 1/2 sum over samples and output units of (y - t)^2. Accept "
      "scalar targets for a single output and list targets otherwise.",
  "backprop":
      "Loop over samples: delta2 = y - t; dW2 += outer(delta2, a1), db2 += delta2; "
      "delta1 = (W2^T delta2) * (1 - a1^2); dW1 += outer(delta1, x), db1 += delta1. "
      "The (1 - a1^2) is tanh'(z1); dropping it is the classic hidden-layer bug.",
  "numerical_gradient":
      "Flatten w, and for each coordinate use the CENTRAL difference "
      "(loss(w + eps e_i) - loss(w - eps e_i)) / (2 eps). One-sided differences are only "
      "O(eps) accurate and will not agree with backprop to ~1e-8.",
  "exact_hessian_fd":
      "For each coordinate j, column j of the Hessian is "
      "(grad(w + eps e_j) - grad(w - eps e_j)) / (2 eps), with grad from backprop. "
      "This differences the analytic gradient, so it is the exact Hessian to O(eps^2).",
  "_sample_jacobians":
      "Per sample, dy_n/dw for each output unit k. With a one-hot seed in output k the "
      "backward pass gives dW2[k][r] = a1[r], db2[k] = 1, delta1_r = W2[k][r](1 - a1_r^2), "
      "dW1[r][c] = delta1_r x[c], db1[r] = delta1_r. Flatten in W1, b1, W2, b2 order.",
  "outer_product_hessian":
      "Gauss-Newton: sum over samples n of J_n^T J_n, where each row of J_n is a residual "
      "Jacobian from _sample_jacobians. Because the target is constant, dr/dw = dy/dw and "
      "ts does not enter. This omits the term linear in the residuals.",
  "train":
      "Full-batch gradient descent: w <- w - lr * (backprop_gradient + weight_decay * w). "
      "The penalty 1/2 weight_decay ||w||^2 adds weight_decay * w to the gradient; "
      "subtracting it would grow the weights. Return (weights, loss_history).",
  "early_stopping_split":
      "Shuffle indices with random.Random(seed), hold out val_frac as validation, train "
      "on the rest. Track train and validation loss; keep the weights at the lowest "
      "validation loss and stop as soon as validation loss rises. Return "
      "(best_weights, train_history, val_history, best_iteration).",
 },
}

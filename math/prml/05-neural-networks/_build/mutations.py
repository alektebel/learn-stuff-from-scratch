"""Planted bugs for the check suite, one classic mistake per mechanism.

Each mutation is an exact edit to `solutions/neural.py`. Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \\
        math/prml/05-neural-networks math/prml/05-neural-networks/_build/mutations.py

Every entry must be CAUGHT by the step it names; a MISSED entry means the check is too
weak, not that the mutation is wrong.
"""

MUTATIONS = [
    (
        "backprop drops the tanh' factor in the hidden layer",
        "neural.py",
        "            delta1[r] = s * (1.0 - a1[r] * a1[r])",
        "            delta1[r] = s",
        "1",
    ),
    (
        "numerical_gradient uses a one-sided difference",
        "neural.py",
        "        g = (loss(unflatten(plus, D, H, K), xs, ts)\n"
        "             - loss(unflatten(minus, D, H, K), xs, ts)) / (2.0 * eps)",
        "        g = (loss(unflatten(plus, D, H, K), xs, ts)\n"
        "             - loss(unflatten(vec, D, H, K), xs, ts)) / eps",
        "1",
    ),
    (
        "outer-product Jacobian uses the activation a1 instead of tanh'",
        "neural.py",
        "                delta1 = W2[k][r] * (1.0 - a1[r] * a1[r])",
        "                delta1 = W2[k][r] * a1[r]",
        "3",
    ),
    (
        "weight decay is subtracted from the gradient and grows the weights",
        "neural.py",
        "        g = flatten(backprop(w, xs, ts))\n"
        "        vec = [vec[i] - lr * (g[i] + weight_decay * vec[i]) for i in range(len(vec))]",
        "        g = flatten(backprop(w, xs, ts))\n"
        "        vec = [vec[i] - lr * (g[i] - weight_decay * vec[i]) for i in range(len(vec))]",
        "4",
    ),
    (
        "outer-product Hessian silently returns the exact Hessian (claims it is just as "
        "good far from the minimum)",
        "neural.py",
        "    jac = _sample_jacobians(weights, xs)\n"
        "    hess = [[0.0] * P for _ in range(P)]",
        "    return exact_hessian_fd(weights, xs, ts if ts is not None else [])\n"
        "    jac = _sample_jacobians(weights, xs)\n"
        "    hess = [[0.0] * P for _ in range(P)]",
        "5",
    ),
]

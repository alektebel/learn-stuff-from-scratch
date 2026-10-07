"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # Shifting every power drops the constant term: the fit is a different model.
    ("poly_features drops the constant term (powers shifted by one)", "intro.py",
     "    return [x ** k for k in range(degree + 1)]\n",
     "    return [x ** (k + 1) for k in range(degree + 1)]\n", "1"),
    # No penalty means the "ridge" fit is the unregularised one and still overfits.
    ("poly_fit ignores lam (the ridge term is never added)", "intro.py",
     "        if i > 0:\n            A[i][i] += lam\n",
     "        if False:\n            A[i][i] += lam\n", "2"),
    # Variance is the spread about the mean prediction; using f folds the bias in.
    ("bias_variance measures variance about the true function, not the mean prediction",
     "intro.py",
     "        sum((preds[s][i] - mean[i]) ** 2 for s in range(n_sets)) / n_sets\n",
     "        sum((preds[s][i] - TRUE_F(test_x[i])) ** 2 for s in range(n_sets)) / n_sets\n", "3"),
    # Ignoring the loss matrix collapses the decision rule to a fixed 0.5 threshold.
    ("min_risk_decision ignores the loss matrix and uses p = 0.5", "intro.py",
     "    expected = [loss[a][0] * (1.0 - p) + loss[a][1] * p for a in range(2)]\n"
     "    return 0 if expected[0] <= expected[1] else 1\n",
     "    return 0 if p <= 0.5 else 1\n", "4"),
    # Reversing the log ratio makes the divergence negative; a genuine KL is >= 0.
    ("kl_divergence flips the ratio inside the log", "intro.py",
     "    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0.0)\n",
     "    return sum(pi * math.log(qi / pi) for pi, qi in zip(p, q) if pi > 0.0)\n", "5"),
    # Entropy is non-negative; dropping the minus sign makes it negative.
    ("entropy drops the minus sign", "intro.py",
     "    return -sum(pi * math.log(pi) for pi in p if pi > 0.0)\n",
     "    return sum(pi * math.log(pi) for pi in p if pi > 0.0)\n", "5"),
]

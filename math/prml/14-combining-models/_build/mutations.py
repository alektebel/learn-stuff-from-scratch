"""Planted bugs for the check suite, one classic mistake per mechanism.

Each mutation is an exact edit to `solutions/combine.py`. Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \\
        math/prml/14-combining-models math/prml/14-combining-models/_build/mutations.py

Every entry must be CAUGHT by the step it names; a MISSED entry means the check is too
weak, not that the mutation is wrong.
"""

MUTATIONS = [
    (
        "best_split minimises the plain (unweighted) count instead of the weighted impurity",
        "combine.py",
        "            if weights is None:\n"
        "                wl, wr = float(len(left)), float(len(right))\n"
        "                il = _impurity([ys[i] for i in left], None, impurity)",
        "            if True:\n"
        "                wl, wr = float(len(left)), float(len(right))\n"
        "                il = _impurity([ys[i] for i in left], None, impurity)",
        "1",
    ),
    (
        "AdaBoost alpha drops the log: 0.5 * (1-eps)/eps instead of 0.5 ln((1-eps)/eps)",
        "combine.py",
        "        alpha = 0.5 * math.log((1.0 - eps) / eps)",
        "        alpha = 0.5 * ((1.0 - eps) / eps)",
        "2",
    ),
    (
        "the AdaBoost weight update never renormalises (the weights stop being a distribution)",
        "combine.py",
        "        total = sum(new_w)\n"
        "        w = [v / total for v in new_w]",
        "        w = new_w",
        "3",
    ),
    (
        "bagging samples without replacement, so every bootstrap tree is identical",
        "combine.py",
        "        idx = [rng.randrange(n) for _ in range(n)]",
        "        idx = rng.sample(range(n), n)",
        "4",
    ),
    (
        "the label-noise limit case reports an even spread instead of concentrated weights",
        "combine.py",
        '            "weights": w, "weight_hist": weight_hist, "labels": labels}',
        '            "weights": [1.0 / n] * n, "weight_hist": weight_hist, "labels": labels}',
        "5",
    ),
]

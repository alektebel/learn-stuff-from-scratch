"""Planted bugs for the check suite, one classic mistake per mechanism.

Each mutation is an exact edit to `solutions/regression.py`. Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \\
        math/prml/03-linear-regression math/prml/03-linear-regression/_build/mutations.py

Every entry must be CAUGHT by the step it names; a MISSED entry means the check is too
weak, not the mutation is wrong.
"""

MUTATIONS = [
    (
        "ridge adds alpha to the wrong side (Phi^T Phi - alpha I)",
        "regression.py",
        "    return solve_linear(_gram(Phi, alpha), _rhs(Phi, ts))",
        "    A = _gram(Phi)\n"
        "    for i in range(len(A)):\n"
        "        A[i][i] -= alpha\n"
        "    return solve_linear(A, _rhs(Phi, ts))",
        "1",
    ),
    (
        "the posterior forgets the beta factor on Phi^T Phi",
        "regression.py",
        "    precision = [[beta * value for value in row] for row in _gram(Phi)]\n"
        "    for i in range(cols):\n"
        "        precision[i][i] += alpha\n"
        "    rhs = [beta * value for value in _rhs(Phi, ts)]",
        "    precision = [[value for value in row] for row in _gram(Phi)]\n"
        "    for i in range(cols):\n"
        "        precision[i][i] += alpha\n"
        "    rhs = [beta * value for value in _rhs(Phi, ts)]",
        "2",
    ),
    (
        "the predictive variance drops the 1/beta observation-noise term",
        "regression.py",
        "        variances.append(1.0 / beta + quadratic)",
        "        variances.append(quadratic)",
        "3",
    ),
    (
        "log_evidence omits the +1/2 ln|S_N| Occam term",
        "regression.py",
        "            - 0.5 * n * math.log(2.0 * math.pi)\n"
        "            + 0.5 * log_det_sn)",
        "            - 0.5 * n * math.log(2.0 * math.pi))",
        "4",
    ),
    (
        "MLE treated as well posed with fewer points than basis functions",
        "regression.py",
        "    except ValueError:\n"
        "        return None",
        "    except ValueError:\n"
        "        return solve_linear(_gram(Phi, 1e-8), _rhs(Phi, ts))",
        "5",
    ),
]

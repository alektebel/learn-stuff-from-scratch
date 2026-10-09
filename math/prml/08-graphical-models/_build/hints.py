"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 8 is listed, so make_templates stubs it
and replaces its body with a `# TODO: <hint>` line plus `raise NotImplementedError`.
The helpers (`_num_values`, `_domains`, `_cpt_dist`, `_topo_order`, `_make_factors`,
`_var_to_factors`, `_joint_probability`, `_normalise`) and the demo are left
implemented: scaffolding, not the deliverable.
"""

HINTS = {
    "graphical.py": {
        "d_separated":
            "Bayes-ball via the ancestral moral graph: keep the ancestors of "
            "{a, b} | given, add an edge between every pair of parents that share a "
            "child (this is what makes a collider OPEN rather than block), make the "
            "graph undirected, delete the observed nodes, and return True iff a and "
            "b are then disconnected.",
        "enumerate_marginals":
            "Brute force: enumerate every joint assignment, multiply the conditional "
            "probabilities P(v | parents(v)) into the joint, and accumulate the joint "
            "into the marginal of each variable's value.",
        "sum_product":
            "On a tree, memoise the factor->variable message as the sum over the "
            "factor's other variables of (factor * the incoming variable->factor "
            "messages); the variable->factor message is the product of the factor->"
            "variable messages from a variable's other factors. A variable's belief "
            "is the product of its incoming factor->variable messages; divide by the "
            "belief's own total (the partition function) to get the marginal.",
        "max_sum":
            "Max-product in log space: each factor->variable message takes the MAX "
            "over the other variables of (log factor + incoming messages) and stores "
            "the argmax assignment; variable->factor messages add. Pick the best root "
            "value and reconstruct the full assignment from the back-pointers. Take "
            "the max, not a sum.",
        "sample_independence":
            "Ancestral-sample n times in topological order, then measure the largest "
            "|P(a, b | given) - P(a | given) P(b | given)| over the value pairs, for "
            "every observed configuration seen often enough. A d-separated pair "
            "gives a gap consistent with sampling noise; a dependent pair a large one.",
        "loopy_bp":
            "Parallel (Jacobi) sweeps of the same factor graph messages, with no "
            "guarantee of a tree. Track the largest change in the raw messages: "
            "report converged only when it drops below the tolerance. Do not include "
            "a factor's own message in the variable->factor update. On a cycle the "
            "messages can oscillate between two states and never settle.",
    },
}

"""
Graphical models from scratch: d-separation, belief propagation and max-sum.

Implements chapter 8 of Bishop, *Pattern Recognition and Machine Learning*: the
conditional-independence semantics of a Bayesian network, the sum-product and
max-sum algorithms on a factor graph, and what happens when the factor graph has a
cycle. Pure standard library; no numpy.

A discrete Bayesian network is given by

    parents = {var: [parent, ...]}          # the DAG
    cpts    = {var: nested lists}           # P(var | parents)

with binary or small discrete domains. ``cpts[var]`` is nested one axis per parent,
one axis per value of ``var``:

    root:                 [p0, p1]
    one parent:           [[p0|par=0, p1|par=0], [p0|par=1, p1|par=1]]
    two parents (A, B):   cpt[a][b] -> distribution of var

The joint factorises as ``P(x) = prod_v P(x_v | parents(v))``.

Run the reference measurements:

    python3 graphical.py
"""
import itertools
import math
import random

NEG_INF = float("-inf")


# ---------------------------------------------------------------------------
# Internal helpers (given: scaffolding, not the graded work)
# ---------------------------------------------------------------------------

def _num_values(node):
    """Length of the innermost axis of a nested CPT."""
    while isinstance(node, list) and node and isinstance(node[0], list):
        node = node[0]
    return len(node)


def _domains(parents, cpts):
    """Map each variable to the size of its domain."""
    return {v: _num_values(cpts[v]) for v in parents}


def _cpt_dist(cpt, pvars, assign):
    """The distribution P(var | parents) for one assignment of the parents."""
    node = cpt
    for p in pvars:
        node = node[assign[p]]
    return node


def _topo_order(parents):
    """Parents before children (any topological order)."""
    order, seen = [], set()

    def visit(v):
        if v in seen:
            return
        seen.add(v)
        for p in parents.get(v, []):
            visit(p)
        order.append(v)

    for v in parents:
        visit(v)
    return order


def _make_factors(parents, cpts, domains):
    """The factor graph: one factor P(var | parents) per variable.

    Each factor is ``(scope, table)`` with ``scope = parents + (var,)`` and
    ``table[assignment] = probability``.
    """
    factors = []
    for v in parents:
        pv = tuple(parents[v])
        scope = pv + (v,)
        table = {}
        cpt = cpts[v]

        def rec(i, vals, node):
            if i == len(pv):
                for xv in range(domains[v]):
                    table[vals + (xv,)] = float(node[xv])
                return
            p = pv[i]
            for xp in range(domains[p]):
                rec(i + 1, vals + (xp,), node[xp])

        rec(0, (), cpt)
        factors.append((scope, table))
    return factors


def _var_to_factors(variables, factors):
    v2f = {v: [] for v in variables}
    for fid, (scope, _) in enumerate(factors):
        for v in scope:
            v2f[v].append(fid)
    return v2f


def _joint_probability(assign, parents, cpts):
    p = 1.0
    for v in parents:
        dist = _cpt_dist(cpts[v], parents[v], assign)
        p *= dist[assign[v]]
        if p == 0.0:
            return 0.0
    return p


def _normalise(vec):
    total = sum(vec)
    if total <= 0.0:
        return list(vec)
    return [x / total for x in vec]


# ---------------------------------------------------------------------------
# The graded functions
# ---------------------------------------------------------------------------

def d_separated(parents, a, b, given):
    """True iff ``a`` and ``b`` are d-separated given the set ``given``.

    The ancestral-moral-graph test: restrict the DAG to the ancestors of
    ``{a, b} | given``, marry every pair of parents that share a child (this is
    what lets a collider open a path), drop the directions and remove the
    observed nodes. ``a`` and ``b`` are d-separated exactly when they are
    disconnected in that graph.
    """
    # TODO: Bayes-ball via the ancestral moral graph: keep the ancestors of {a, b} | given, add an edge between every pair of parents that share a child (this is what makes a collider OPEN rather than block), make the graph undirected, delete the observed nodes, and return True iff a and b are then disconnected.
    raise NotImplementedError("d_separated")


def enumerate_marginals(parents, cpts):
    """Brute-force marginals: sum the full joint over every variable but one."""
    # TODO: Brute force: enumerate every joint assignment, multiply the conditional probabilities P(v | parents(v)) into the joint, and accumulate the joint into the marginal of each variable's value.
    raise NotImplementedError("enumerate_marginals")


def sum_product(parents, cpts):
    """Belief propagation on a tree: exact node marginals ``{var: [p, ...]}``.

    The belief b(v) = prod_{f ~ v} m_{f->v}(v) equals Z * P(v), so dividing by
    its sum recovers the marginal. Messages are computed by memoised recursion;
    the ``in_progress`` guard only matters if the graph is not a tree.
    """
    # TODO: On a tree, memoise the factor->variable message as the sum over the factor's other variables of (factor * the incoming variable->factor messages); the variable->factor message is the product of the factor->variable messages from a variable's other factors. A variable's belief is the product of its incoming factor->variable messages; divide by the belief's own total (the partition function) to get the marginal.
    raise NotImplementedError("sum_product")


def max_sum(parents, cpts):
    """Max-sum (Viterbi-style) decoding: a most probable assignment.

    Runs max-product in log space on the factor-graph tree and reconstructs the
    assignment from the factor back-pointers. Ties are broken arbitrarily.
    """
    # TODO: Max-product in log space: each factor->variable message takes the MAX over the other variables of (log factor + incoming messages) and stores the argmax assignment; variable->factor messages add. Pick the best root value and reconstruct the full assignment from the back-pointers. Take the max, not a sum.
    raise NotImplementedError("max_sum")


def sample_independence(parents, cpts, n, rng, a, b, given):
    """Monte-Carlo test of ``a _||_ b | given``.

    Draws ``n`` ancestral samples and returns the largest absolute gap between
    ``P(a, b | given)`` and ``P(a | given) P(b | given)`` over the values, for
    every observed configuration seen at least 20 times. A d-separated pair
    gives a gap consistent with sampling noise; a dependent pair gives a large
    one.
    """
    # TODO: Ancestral-sample n times in topological order, then measure the largest |P(a, b | given) - P(a | given) P(b | given)| over the value pairs, for every observed configuration seen often enough. A d-separated pair gives a gap consistent with sampling noise; a dependent pair a large one.
    raise NotImplementedError("sample_independence")


def loopy_bp(parents, cpts, iters=100, tol=1e-12):
    """Loopy belief propagation on a general factor graph.

    Returns ``(marginals, converged)``. Messages are updated in parallel (left
    un-normalised between sweeps, so ``converged`` means the message vector has
    settled). On a tree this reaches the exact marginals; on a graph with a cycle
    the messages can oscillate between two states and never settle.
    """
    # TODO: Parallel (Jacobi) sweeps of the same factor graph messages, with no guarantee of a tree. Track the largest change in the raw messages: report converged only when it drops below the tolerance. Do not include a factor's own message in the variable->factor update. On a cycle the messages can oscillate between two states and never settle.
    raise NotImplementedError("loopy_bp")


# ---------------------------------------------------------------------------
# The demo (given: scaffolding, not the graded work)
# ---------------------------------------------------------------------------

def demo():
    print("Graphical models: d-separation, sum-product and max-sum")
    chain = {"A": [], "B": ["A"], "C": ["B"]}
    common = {"B": [], "A": ["B"], "C": ["B"]}
    collider = {"A": [], "B": [], "C": ["A", "B"]}
    print("  chain A->B->C: d-sep(A,C|{{}})={} , d-sep(A,C|{{B}})={}".format(
        d_separated(chain, "A", "C", []), d_separated(chain, "A", "C", ["B"])))
    print("  common cause A<-B->C: d-sep(A,C|{{}})={} , d-sep(A,C|{{B}})={}".format(
        d_separated(common, "A", "C", []), d_separated(common, "A", "C", ["B"])))
    print("  collider A->C<-B: d-sep(A,B|{{}})={} , d-sep(A,B|{{C}})={}".format(
        d_separated(collider, "A", "B", []), d_separated(collider, "A", "B", ["C"])))

    rng = random.Random(8)
    parents = {"A": [], "B": ["A"], "C": ["B"]}
    cpts = {"A": [0.6, 0.4], "B": [[0.9, 0.1], [0.2, 0.8]], "C": [[0.7, 0.3], [0.1, 0.9]]}
    exact = enumerate_marginals(parents, cpts)
    bp = sum_product(parents, cpts)
    err = max(abs(bp[v][i] - exact[v][i]) for v in exact for i in range(len(exact[v])))
    print("  sum-product vs brute force: max error {:.2e}".format(err))
    best = max(itertools.product(*[range(2) for _ in parents]),
               key=lambda c: _joint_probability(dict(zip(parents, c)), parents, cpts))
    decode = max_sum(parents, cpts)
    print("  max-sum {} -> P={:.4f} (brute-force best P={:.4f})".format(
        dict(sorted(decode.items())),
        _joint_probability(decode, parents, cpts),
        _joint_probability(dict(zip(parents, best)), parents, cpts)))
    print("  MC independence chain(A,C|{{}}): {:.4f}".format(
        sample_independence(chain,
                            {"A": [0.5, 0.5],
                             "B": [[0.7, 0.3], [0.3, 0.7]],
                             "C": [[0.8, 0.2], [0.1, 0.9]]},
                            20000, rng, "A", "C", [])))
    triangle = {"A": [], "B": ["A"], "C": ["A", "B"]}
    tri_cpts = {"A": [0.5, 0.5],
                "B": [[0.9, 0.1], [0.1, 0.9]],
                "C": [[[0.95, 0.05], [0.05, 0.95]], [[0.05, 0.95], [0.95, 0.05]]]}
    marg, converged = loopy_bp(triangle, tri_cpts, iters=200)
    ref = enumerate_marginals(triangle, tri_cpts)
    gap = max(abs(marg[v][i] - ref[v][i]) for v in ref for i in range(len(ref[v])))
    print("  triangle loopy BP: converged={} , max marginal gap vs brute force {:.2e}".format(
        converged, gap))


if __name__ == "__main__":
    demo()

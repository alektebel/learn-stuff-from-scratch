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
    given = set(given)
    if a == b or a in given or b in given:
        return False

    nodes = set(parents)
    for ps in parents.values():
        nodes.update(ps)

    # Ancestors of the target set (the nodes that can lie on a relevant path).
    target = set(given) | {a, b}
    ancestors = set()
    stack = list(target)
    while stack:
        x = stack.pop()
        if x in ancestors:
            continue
        ancestors.add(x)
        for p in parents.get(x, []):
            if p not in ancestors:
                stack.append(p)

    und = {v: set() for v in ancestors}
    for v in ancestors:
        ps = [p for p in parents.get(v, []) if p in ancestors]
        for p in ps:
            und[v].add(p)
            und[p].add(v)
        # Moralise: marry the parents (this is what makes colliders active).
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                und[ps[i]].add(ps[j])
                und[ps[j]].add(ps[i])

    for g in given:
        und.pop(g, None)
    for v in und:
        und[v] &= set(und)

    # Reachability a -> b in the moral graph with the observed nodes removed.
    seen = {a}
    frontier = [a]
    while frontier:
        x = frontier.pop()
        if x == b:
            return False
        for y in und.get(x, ()):
            if y not in seen:
                seen.add(y)
                frontier.append(y)
    return True


def enumerate_marginals(parents, cpts):
    """Brute-force marginals: sum the full joint over every variable but one."""
    variables = list(parents)
    domains = _domains(parents, cpts)
    marginals = {v: [0.0] * domains[v] for v in variables}
    for combo in itertools.product(*[range(domains[v]) for v in variables]):
        assign = dict(zip(variables, combo))
        p = _joint_probability(assign, parents, cpts)
        if p == 0.0:
            continue
        for v in variables:
            marginals[v][assign[v]] += p
    return marginals


def sum_product(parents, cpts):
    """Belief propagation on a tree: exact node marginals ``{var: [p, ...]}``.

    The belief b(v) = prod_{f ~ v} m_{f->v}(v) equals Z * P(v), so dividing by
    its sum recovers the marginal. Messages are computed by memoised recursion;
    the ``in_progress`` guard only matters if the graph is not a tree.
    """
    variables = list(parents)
    domains = _domains(parents, cpts)
    factors = _make_factors(parents, cpts, domains)
    v2f = _var_to_factors(variables, factors)
    cache, in_progress = {}, set()

    def var_to_factor(u, fid):
        key = ("v", u, fid)
        if key in cache:
            return cache[key]
        if key in in_progress:
            return [1.0] * domains[u]
        in_progress.add(key)
        out = [1.0] * domains[u]
        for g in v2f[u]:
            if g == fid:
                continue
            m = factor_to_var(g, u)
            for i in range(domains[u]):
                out[i] *= m[i]
        in_progress.discard(key)
        cache[key] = out
        return out

    def factor_to_var(fid, v):
        key = ("f", fid, v)
        if key in cache:
            return cache[key]
        if key in in_progress:
            return [1.0] * domains[v]
        in_progress.add(key)
        scope, table = factors[fid]
        vidx = scope.index(v)
        incoming = {u: var_to_factor(u, fid) for u in scope if u != v}
        out = [0.0] * domains[v]
        for assign, prob in table.items():
            prod = prob
            for j, u in enumerate(scope):
                if j != vidx:
                    prod *= incoming[u][assign[j]]
            out[assign[vidx]] += prod
        in_progress.discard(key)
        cache[key] = out
        return out

    marginals = {}
    for v in variables:
        belief = [1.0] * domains[v]
        for fid in v2f[v]:
            m = factor_to_var(fid, v)
            for i in range(domains[v]):
                belief[i] *= m[i]
        # The belief b(v) = Z * P(v); dividing by its total (the partition
        # function Z) recovers the marginal.
        z = sum(belief)
        marginals[v] = [x / z for x in belief] if z > 0 else list(belief)
    return marginals


def max_sum(parents, cpts):
    """Max-sum (Viterbi-style) decoding: a most probable assignment.

    Runs max-product in log space on the factor-graph tree and reconstructs the
    assignment from the factor back-pointers. Ties are broken arbitrarily.
    """
    variables = list(parents)
    domains = _domains(parents, cpts)
    factors = _make_factors(parents, cpts, domains)
    v2f = _var_to_factors(variables, factors)
    cache, backpointer, in_progress = {}, {}, set()

    def var_to_factor(u, fid):
        key = ("v", u, fid)
        if key in cache:
            return cache[key]
        if key in in_progress:
            return [0.0] * domains[u]
        in_progress.add(key)
        out = [0.0] * domains[u]
        for g in v2f[u]:
            if g == fid:
                continue
            fm = factor_to_var(g, u)
            for i in range(domains[u]):
                out[i] = out[i] + fm[i] if (out[i] > NEG_INF and fm[i] > NEG_INF) else NEG_INF
        in_progress.discard(key)
        cache[key] = out
        return out

    def factor_to_var(fid, v):
        key = ("f", fid, v)
        if key in cache:
            return cache[key]
        if key in in_progress:
            return [0.0] * domains[v]
        in_progress.add(key)
        scope, table = factors[fid]
        vidx = scope.index(v)
        others = [u for u in scope if u != v]
        incoming = {u: var_to_factor(u, fid) for u in others}
        out = [NEG_INF] * domains[v]
        bps = [{} for _ in range(domains[v])]
        for xv in range(domains[v]):
            scores, assigns = [], []
            for oa in itertools.product(*[range(domains[u]) for u in others]):
                full = dict(zip(others, oa))
                full[v] = xv
                assignment = tuple(full[u] for u in scope)
                p = table.get(assignment, 0.0)
                if p <= 0.0:
                    continue
                val = math.log(p)
                ok = True
                for u, x in zip(others, oa):
                    if incoming[u][x] == NEG_INF:
                        ok = False
                        break
                    val += incoming[u][x]
                if ok:
                    scores.append(val)
                    assigns.append({u: x for u, x in zip(others, oa)})
            if scores:
                best_val = max(scores)
                best_i = scores.index(best_val)
                out[xv] = best_val
                bps[xv] = assigns[best_i]
        cache[key] = out
        backpointer[(fid, v)] = bps
        in_progress.discard(key)
        return out

    root = variables[0]
    belief = [0.0] * domains[root]
    for g in v2f[root]:
        fm = factor_to_var(g, root)
        for i in range(domains[root]):
            belief[i] = belief[i] + fm[i] if (belief[i] > NEG_INF and fm[i] > NEG_INF) else NEG_INF
    root_value = max(range(domains[root]), key=lambda i: belief[i])

    assignment = {root: root_value}

    def expand(u, parent_factor):
        for g in v2f[u]:
            if g == parent_factor:
                continue
            for w, val in backpointer[(g, u)][assignment[u]].items():
                if w not in assignment:
                    assignment[w] = val
                    expand(w, g)

    expand(root, None)
    return assignment


def sample_independence(parents, cpts, n, rng, a, b, given):
    """Monte-Carlo test of ``a _||_ b | given``.

    Draws ``n`` ancestral samples and returns the largest absolute gap between
    ``P(a, b | given)`` and ``P(a | given) P(b | given)`` over the values, for
    every observed configuration seen at least 20 times. A d-separated pair
    gives a gap consistent with sampling noise; a dependent pair gives a large
    one.
    """
    variables = list(parents)
    domains = _domains(parents, cpts)
    order = _topo_order(parents)
    given = list(given)
    joint, cnt_a, cnt_b, cnt_g = {}, {}, {}, {}
    for _ in range(n):
        assign = {}
        for v in order:
            dist = _cpt_dist(cpts[v], parents[v], assign)
            r = rng.random()
            acc = 0.0
            choice = len(dist) - 1
            for x, p in enumerate(dist):
                acc += p
                if r <= acc:
                    choice = x
                    break
            assign[v] = choice
        g = tuple(assign[w] for w in given)
        av, bv = assign[a], assign[b]
        joint[(av, bv, g)] = joint.get((av, bv, g), 0) + 1
        cnt_a[(av, g)] = cnt_a.get((av, g), 0) + 1
        cnt_b[(bv, g)] = cnt_b.get((bv, g), 0) + 1
        cnt_g[g] = cnt_g.get(g, 0) + 1

    max_gap = 0.0
    for g, cg in cnt_g.items():
        if cg < 20:
            continue
        for av in range(domains[a]):
            pa = cnt_a.get((av, g), 0) / cg
            for bv in range(domains[b]):
                pb = cnt_b.get((bv, g), 0) / cg
                pab = joint.get((av, bv, g), 0) / cg
                max_gap = max(max_gap, abs(pab - pa * pb))
    return max_gap


def loopy_bp(parents, cpts, iters=100, tol=1e-12):
    """Loopy belief propagation on a general factor graph.

    Returns ``(marginals, converged)``. Messages are updated in parallel (left
    un-normalised between sweeps, so ``converged`` means the message vector has
    settled). On a tree this reaches the exact marginals; on a graph with a cycle
    the messages can oscillate between two states and never settle.
    """
    variables = list(parents)
    domains = _domains(parents, cpts)
    factors = _make_factors(parents, cpts, domains)
    v2f = _var_to_factors(variables, factors)

    vm = {(u, fid): [1.0] * domains[u] for u in variables for fid in v2f[u]}
    fm = {}
    converged = False
    for _ in range(iters):
        new_fm = {}
        for fid, (scope, table) in enumerate(factors):
            for v in scope:
                vidx = scope.index(v)
                out = [0.0] * domains[v]
                for assign, prob in table.items():
                    prod = prob
                    for j, u in enumerate(scope):
                        if j != vidx:
                            prod *= vm[(u, fid)][assign[j]]
                    out[assign[vidx]] += prod
                new_fm[(fid, v)] = out

        delta = 0.0
        for key, val in new_fm.items():
            old = fm.get(key)
            if old is None:
                delta = max(delta, 1.0)
            else:
                delta = max(delta, max(abs(x - y) for x, y in zip(val, old)))
        fm = new_fm

        new_vm = {}
        for u in variables:
            for fid in v2f[u]:
                out = [1.0] * domains[u]
                for g in v2f[u]:
                    if g == fid:
                        continue
                    m = fm[(g, u)]
                    for i in range(domains[u]):
                        out[i] *= m[i]
                new_vm[(u, fid)] = out
        vm = new_vm

        if delta < tol:
            converged = True
            break

    marginals = {}
    for u in variables:
        belief = [1.0] * domains[u]
        for fid in v2f[u]:
            m = fm[(fid, u)]
            for i in range(domains[u]):
                belief[i] *= m[i]
        marginals[u] = _normalise(belief)
    return marginals, converged


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

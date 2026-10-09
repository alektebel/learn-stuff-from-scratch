"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # Skipping the moralisation means a collider's parents are never married, so
    # conditioning on the collider blocks the path as if it were a chain. Step 1
    # conditions on C in A -> C <- B and expects the path to open.
    ("d-separation treats a collider like a chain", "graphical.py",
     "        for i in range(len(ps)):\n",
     "        for i in range(0):\n", "1"),
    # Normalising each belief by the number of states instead of by its own total
    # (the partition function) breaks every marginal that is not uniform. Step 2
    # compares against the brute-force marginals.
    ("sum-product normalises by the wrong partition function", "graphical.py",
     "        z = sum(belief)\n",
     "        z = float(len(belief))\n", "2"),
    # Summing the candidate scores instead of taking the max turns max-sum into a
    # meaningless aggregate; the reconstructed assignment is no longer the argmax.
    ("max-sum takes the sum instead of the max", "graphical.py",
     "                best_val = max(scores)\n",
     "                best_val = sum(scores)\n", "3"),
    # Including the factor's own message in the variable->factor product counts
    # that factor twice. On a tree this still settles, but on the wrong fixed
    # point, so the tree-exactness part of step 5 fails.
    ("loopy message update includes the sender's own message", "graphical.py",
     "                for g in v2f[u]:\n"
     "                    if g == fid:\n"
     "                        continue\n"
     "                    m = fm[(g, u)]\n",
     "                for g in v2f[u]:\n"
     "                    m = fm[(g, u)]\n", "5"),
    # Reporting convergence unconditionally claims loopy BP is exact/stable on the
    # oscillating triangle, which step 5 explicitly forbids.
    ("the loopy limit case claims loopy BP is exact on the triangle", "graphical.py",
     "    return marginals, converged\n",
     "    return marginals, True\n", "5"),
]

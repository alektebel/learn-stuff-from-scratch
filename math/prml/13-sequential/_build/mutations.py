"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # Skipping the rescaling makes the forward variable a raw joint probability
    # that multiplies by a factor below one at every step. On the 1200-long
    # sequence of step 5 it underflows, and the scaled output is no longer
    # normalised, so the limit case fails.
    ("forward never rescales (underflow on the long sequence)", "sequential.py",
     "        c = sum(a)\n"
     "        cs.append(c)\n"
     "        alphas.append([x / c for x in a])\n",
     "        c = sum(a)\n"
     "        cs.append(c)\n"
     "        alphas.append(list(a))\n", "5"),
    # Using A[j][i] instead of A[i][j] in the backward message propagates the
    # transition in the wrong direction. Step 1 compares the marginals with the
    # brute-force sum over paths on asymmetric random models.
    ("backward recursion uses the transposed transition matrix", "sequential.py",
     "                s += A[i][j] * B[j][obs[t + 1]] * nxt[j]\n",
     "                s += A[j][i] * B[j][obs[t + 1]] * nxt[j]\n", "1"),
    # Dropping the backpointers returns the last best state repeated, which is
    # not the MAP path. Step 2 compares against the brute-force argmax.
    ("Viterbi drops the backpointers", "sequential.py",
     "    path = [0] * T\n"
     "    path[T - 1] = last\n"
     "    for t in range(T - 1, 0, -1):\n"
     "        path[t - 1] = psi[t][path[t]]\n"
     "    return path\n",
     "    return [last] * T\n", "2"),
    # Omitting R from the innovation covariance S = H P H^T + R shrinks S and
    # inflates the gain. Step 4 compares the filter with the exact batch
    # posterior.
    ("Kalman update drops R from the innovation covariance", "sequential.py",
     "        S = _add(_matmul(_matmul(H, P), _transpose(H)), R)  # innovation covariance\n",
     "        S = _matmul(_matmul(H, P), _transpose(H))  # innovation covariance\n", "4"),
    # Using the filter gain K = P H^T (H P H^T + R)^-1 where the smoother gain
    # P F^T (F P F^T + Q)^-1 belongs leaves the smoothed estimate wrong. Step 4
    # compares the smoother with the exact batch posterior.
    ("RTS smoother uses the filter gain instead of the smoother gain", "sequential.py",
     "        G = _matmul(_matmul(Pf, _transpose(F)), _inv(Pp))     # smoother gain\n",
     "        G = _matmul(_matmul(Pf, _transpose(H)),"
     " _inv(_add(_matmul(_matmul(H, Pf), _transpose(H)), R)))     # smoother gain\n", "4"),
    # The batch posterior is the accept reference; dropping the prior precision
    # makes it not the exact joint posterior, which the checker's own independent
    # batch solve now detects rather than deferring to the learner's. Step 4.
    ("batch_gaussian_posterior drops the initial-state prior precision", "sequential.py",
     "            J[a][b] += P0i[a][b]\n",
     "            J[a][b] += 0.0\n", "4"),
]

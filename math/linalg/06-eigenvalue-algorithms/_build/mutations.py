"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each caught by the step it names. A MISSED mutation
means the check is too weak, not that the bug is acceptable.

The five:
  * hessenberg applies the reflector on one side only (similarity broken)   -> step 1
  * tridiagonalize skips the last reflector, leaving a sub-subdiagonal
    entry in row n-2                                                        -> step 2
  * the QR algorithm reads the diagonal of A instead of iterating           -> step 3
  * Rayleigh quotient iteration uses a fixed step (no quotient update)      -> step 4
  * the limit-case check is fed an unshifted QR that is silently shifted,
    claiming unshifted QR is fast on equal-magnitude eigenvalues            -> step 5
"""

import sys

sys.dont_write_bytecode = True  # importing this file must not leave a __pycache__

MUTATIONS = [
    # 1. Hessenberg: drop the right multiplication, so H <- H_k A is orthogonal but no
    #    longer a similarity. Q H Q^T != A.
    ("hessenberg applies the reflector on one side only", "eigenalg.py",
     "        for i in range(n):                                    # H <- H H_k\n"
     "            s = sum(H[i][k + 1 + j] * v[j] for j in range(len(v)))\n"
     "            for j in range(len(v)):\n"
     "                H[i][k + 1 + j] -= 2.0 * v[j] * s\n",
     "", "1"),
    # 2. Tridiagonalize: stop one reflector early, leaving an entry below the subdiagonal
    #    in the final column.
    ("tridiagonalize skips the last reflector", "eigenalg.py",
     "    # Eliminate below the subdiagonal on both sides, k = 0 .. n-3.\n"
     "    for k in range(n - 2):\n",
     "    # BUG: last reflector skipped.\n"
     "    for k in range(n - 3):\n", "2"),
    # 3. QR eigensolver: return the diagonal of the input instead of iterating. A random
    #    symmetric matrix is not diagonal, so this disagrees with the reference.
    ("QR algorithm reads the diagonal instead of iterating", "eigenalg.py",
     "    _, H = hessenberg(A)\n",
     "    return sorted(float(A[i][i]) for i in range(n)), 0  # BUG: read the diagonal\n",
     "3"),
    # 4. Rayleigh quotient iteration: freeze the shift at the initial quotient, which is
    #    shifted inverse iteration -- linearly convergent (exponent ~1), not cubic.
    ("Rayleigh quotient iteration uses a fixed step", "eigenalg.py",
     "        rho = _dot(v, _matvec(A, v))\n",
     "        rho = _dot(v0, _matvec(A, v0))  # BUG: fixed shift, no quotient update\n",
     "4"),
    # 5. Claim unshifted QR is fast on equal-magnitude eigenvalues by ignoring the shift
    #    strategy and always applying the Wilkinson shift.
    ("unshifted QR silently uses the Wilkinson shift (claims it is fast)", "eigenalg.py",
     "        if shift == \"wilkinson\":\n",
     "        if True:  # BUG: ignores the strategy, so \"none\" is not unshifted\n",
     "5"),
]

# The bytecode cache for this imported file is written before its body runs, so the
# flag above cannot suppress it; remove the directory once the body executes.
import pathlib as _pathlib
import shutil as _shutil

_shutil.rmtree(_pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

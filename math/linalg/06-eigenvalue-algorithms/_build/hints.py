"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Only the four graded mechanisms of the node are listed, so make_templates stubs exactly
those bodies:

    hessenberg                      -- reduction to upper Hessenberg form
    tridiagonalize                  -- symmetric reduction to tridiagonal form
    qr_algorithm                    -- unshifted and Wilkinson-shifted QR
    rayleigh_quotient_iteration     -- the accept: cubic convergence

Everything else is left implemented: the small matrix helpers, ``_qr_factor`` (the
Householder QR of the linalg-02 prerequisite), ``_solve``, ``_wilkinson_shift`` (again
linalg-02), and ``jacobi_reference`` (the demo's independent oracle, which the checker
duplicates in its own code so it never trusts this one).
"""

import sys

sys.dont_write_bytecode = True  # importing this file must not leave a __pycache__

HINTS = {
    "eigenalg.py": {
        "hessenberg":
            "for k in 0..n-3 build the Householder vector from column k below the "
            "subdiagonal and apply H = I - 2 v v^T on BOTH sides, H <- H_k A H_k, "
            "accumulating Q <- Q H_k.",
        "tridiagonalize":
            "the same Householder similarity as hessenberg, but exploit symmetry: zero "
            "column k below row k+1 for k in 0..n-3, T <- H_k T H_k, re-symmetrise, and "
            "accumulate Q.",
        "qr_algorithm":
            "hessenberg(A) to H; while the active block has size m > 1, deflate when "
            "|H[m-1][m-2]| is below tol*scale, otherwise take the shift (0 for \"none\", "
            "the Wilkinson shift for \"wilkinson\"), do one QR step H = R Q + mu I on the "
            "active block, and count sweeps.",
        "rayleigh_quotient_iteration":
            "rho = Rayleigh quotient of v; solve (A - rho I) w = v; renormalise w, fix "
            "its sign, record |rho_k - lam| each step, and stop on a relative change "
            "below tol.",
    },
}

# The bytecode cache for this imported file is written before its body runs, so the
# flag above cannot suppress it; remove the directory once the body executes.
import pathlib as _pathlib
import shutil as _shutil

_shutil.rmtree(_pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

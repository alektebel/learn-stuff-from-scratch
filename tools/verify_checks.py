#!/usr/bin/env python3
"""Verify a checker two ways, without shipping any answers.

    python3 tools/verify_checks.py week-05/spade --references ~/refs/spade
    python3 tools/verify_checks.py week-05/spade --inject injections/spade.py

SKELETON — not implemented. See TODO.md step 1.

WHY THIS EXISTS
---------------
Seven directories are check-only: templates and a checker, no `solutions/`.
That is deliberate — reading an answer converts an exercise into a
transcription — but it means the checker is the ONLY feedback, and an
unverified checker is worse than none. You will spend a day assuming you are
wrong, because the method of this repo is to trust the checker over your own
reading.

So a checker has to be verified two ways, and the references used to do it must
not end up in the repo:

    PASS   drive the checker to N/N against a working reference implementation
           kept OUTSIDE the repo, then delete the reference.
    CATCH  patch one characteristic bug into the reference, per check, and
           confirm the corresponding check FAILS. A check that passes with the
           bug present is not a check.

The second half is the one that finds real problems. In this repo it has caught
four bugs in reference code that a passing checker had missed, and several
checks that were too weak to detect the exact error they existed to detect.
"""

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional, Sequence, Tuple


def stage(directory: pathlib.Path, references: pathlib.Path,
          destination: pathlib.Path) -> None:
    """Copy templates + checker into a temp dir, then overlay the references.

    TODO: the checker must run from the staged copy, never from the repo, so a
    reference can never be left behind by a crash or an interrupt.
    """
    raise NotImplementedError


def run_checker(staged: pathlib.Path, timeout: int = 900) -> Tuple[int, int, str]:
    """Run `python3 check.py --all` and return (passing, total, output).

    TODO: parse the "N/M passing" line. Treat a missing line as a failure, not
    as zero -- a checker that crashed should not look like a checker that ran.
    """
    raise NotImplementedError


def apply_injection(staged: pathlib.Path, filename: str,
                    old: str, new: str) -> None:
    """Patch one characteristic bug into a staged reference.

    TODO: assert `old` appears EXACTLY once before replacing. A silent no-op
    injection reports as 'caught' and is the main way this kind of harness
    lies to you.
    """
    raise NotImplementedError


def verify(directory: pathlib.Path, references: pathlib.Path,
           injections: Optional[Sequence[Tuple[int, str, str, str, str]]] = None
           ) -> int:
    """Full two-way verification. Returns a process exit code.

    TODO:
      1. stage, run, require N/N -- report which checks failed if not
      2. for each injection (step, file, description, old, new): stage fresh,
         apply, run ONLY that step, require it to FAIL
      3. print a table of caught / MISSED, and exit non-zero on any MISS
    """
    raise NotImplementedError


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=pathlib.Path)
    parser.add_argument("--references", type=pathlib.Path, required=True,
                        help="working implementations, OUTSIDE the repo")
    parser.add_argument("--inject", type=pathlib.Path,
                        help="python file defining INJECTIONS")
    args = parser.parse_args(argv)
    raise NotImplementedError("skeleton — see TODO.md step 1")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

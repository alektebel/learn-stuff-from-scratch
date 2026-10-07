"""
Mutation-test a module's checker: plant known bugs in copies of the solutions and
require that the named check step catches each one.

    python3 mutate.py <module_dir> <mutations.py>

mutations.py defines:
    MUTATIONS = [
        # (description, file, exact text to find in solutions/<file>, replacement, check step)
        ("no CRC check", "wal.py", "if zlib.crc32(payload) != crc:\\n    return\\n", "", "7"),
    ]

Each mutation runs `python3 check.py <step>` in a temporary copy holding the mutated
solutions; it counts as CAUGHT if that step reports a failure (✗). Exit code 1 if any
mutation is MISSED. A missed mutation means the check is too weak: strengthen the check
(usually by constructing the limit case deliberately instead of hoping random data hits
it), never weaken the mutation.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    module_dir, mutations_path = argv
    spec = importlib.util.spec_from_file_location("mutations", mutations_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sol = os.path.join(module_dir, "solutions")
    ok = True
    for name, filename, old, new, step in m.MUTATIONS:
        work = tempfile.mkdtemp(prefix="mutate-")
        for f in os.listdir(sol):
            if f.endswith(".py"):
                shutil.copy(os.path.join(sol, f), work)
        shutil.copy(os.path.join(module_dir, "check.py"), work)
        target = os.path.join(work, filename)
        text = open(target).read()
        if old not in text:
            sys.exit(f"mutation {name!r}: text not found in solutions/{filename}")
        open(target, "w").write(text.replace(old, new, 1))
        r = subprocess.run([sys.executable, "check.py", str(step)], cwd=work,
                           capture_output=True, text=True, timeout=900)
        caught = "✗" in r.stdout
        ok &= caught
        print(f"{'CAUGHT' if caught else 'MISSED':6s}  step {step:>3}  {name}")
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

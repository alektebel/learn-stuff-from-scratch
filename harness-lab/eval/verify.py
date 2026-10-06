"""Run a task's hidden tests against an exported repository, in a fresh container.

Isolation against an agent that (deliberately or not) games the verifier:
- hidden tests are copied in only now, after the agent's container is gone;
- `python -I` ignores PYTHONPATH and user site-packages, so a sitecustomize.py or
  usercustomize.py planted in /work never runs;
- --rootdir=/hidden plus `-p no:cacheprovider` keeps a conftest.py or pytest.ini in
  /work out of collection; /work is put on sys.path by our own conftest below.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from eval.sandbox import DEFAULT_IMAGE, DockerSandbox
from eval.tasks import Task

_CONFTEST = '''import sys
sys.path.insert(0, "/work")
'''

TAIL_CHARS = 4000


@dataclass(frozen=True)
class VerifyResult:
    passed: bool
    exit_code: int
    output_tail: str


def verify(task: Task, work_dir: Path, image: str = DEFAULT_IMAGE) -> VerifyResult:
    with tempfile.TemporaryDirectory() as tmp:
        hidden = Path(tmp) / "hidden"
        shutil.copytree(task.hidden_dir, hidden)
        (hidden / "conftest.py").write_text(_CONFTEST)
        with DockerSandbox(image=image).start(work_dir) as box:
            box.put_dir(hidden, "/hidden")
            res = box.exec(
                "cd /hidden && python -I -m pytest -q -p no:cacheprovider --rootdir=/hidden /hidden",
                timeout=task.verify_timeout_s,
            )
    tail = (res.stdout + res.stderr)[-TAIL_CHARS:]
    return VerifyResult(passed=res.exit_code == 0 and not res.timed_out, exit_code=res.exit_code, output_tail=tail)

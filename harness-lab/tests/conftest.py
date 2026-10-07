import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.sandbox import docker_available  # noqa: E402

_DOCKER = docker_available()


def pytest_collection_modifyitems(config, items):
    if _DOCKER:
        return
    skip = pytest.mark.skip(reason="Docker daemon or sandbox image unavailable (python -m eval.setup)")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip)

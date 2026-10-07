import pytest
from eval.sandbox import docker_available

_DOCKER = docker_available()


def pytest_collection_modifyitems(config, items):
    if _DOCKER:
        return
    skip = pytest.mark.skip(reason="Docker daemon or sandbox image unavailable")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip)

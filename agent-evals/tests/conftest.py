import pytest

try:
    from eval.sandbox import docker_available

    _DOCKER = docker_available()
except ImportError:
    # harness-lab is a sibling package installed alongside agent-evals. When it is
    # not installed, the Docker-marked tests are skipped too, so the non-Docker
    # suites still run on their own.
    _DOCKER = False


def pytest_collection_modifyitems(config, items):
    if _DOCKER:
        return
    skip = pytest.mark.skip(reason="Docker daemon or sandbox image unavailable")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip)
